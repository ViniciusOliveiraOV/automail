from flask import Blueprint, current_app, jsonify, redirect, request, url_for
import os
import json
import requests
from app.utils.gmail_oauth import build_consent_url, CLIENT_ID, CLIENT_SECRET
from app.utils.gmail_reader import fetch_today_messages
try:
    from googleapiclient.errors import HttpError
except Exception:
    # googleapiclient may not be installed in all environments (tests); defensively handle
    HttpError = None

bp = Blueprint("gmail_auth", __name__)


@bp.route("/gmail/start")
def start_oauth():
    url = build_consent_url(state="fetch_today")
    return redirect(url)


@bp.route('/gmail/connect')
def gmail_connect():
    # Simple UI page to start the OAuth flow
    try:
        from flask import render_template
        return render_template('gmail_connect.html')
    except Exception:
        return redirect(url_for('gmail_auth.start_oauth'))


def _persist_token(token_json: dict) -> str:
    """Persist token JSON to the Flask instance folder and return path."""
    try:
        inst = current_app.instance_path
        os.makedirs(inst, exist_ok=True)
        path = os.path.join(inst, "gmail_token.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(token_json, f)
        return path
    except Exception:
        current_app.logger.exception("failed to persist gmail token")
        return ""


@bp.route("/gmail/callback")
def oauth_callback():
    # Full server-side code exchange: exchange `code` for tokens and persist the
    # refresh token for later server use. This is safe for local development.
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "no_code"}), 400

    # ensure client credentials are present
    if not CLIENT_ID or not CLIENT_SECRET:
        current_app.logger.error("GMAIL_OAUTH_CLIENT_ID/SECRET not configured")
        return jsonify({"error": "oauth_client_not_configured"}), 500
    redirect_uri = url_for("gmail_auth.oauth_callback", _external=True)
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    try:
        resp = requests.post(token_url, data=data, timeout=10)
    except Exception:
        current_app.logger.exception("token exchange request failed")
        return jsonify({"error": "token_request_failed"}), 500

    if resp.status_code != 200:
        current_app.logger.error("token exchange failed: %s", resp.text)
        return jsonify({"error": "token_exchange_failed", "details": resp.text}), 400

    token_json = resp.json()
    # Google may omit refresh_token if the user previously granted consent.
    # Ensure we have a refresh_token; if missing, inform the user so they can
    # re-run consent with prompt=consent (our start URL already sets prompt=consent,
    # but some flows may still not return refresh_token).
    if not token_json.get("refresh_token"):
        current_app.logger.warning("token exchange returned no refresh_token: %s", token_json)
        # persist what we have (access token) but surface a message
        path = _persist_token(token_json)
        current_app.config["GMAIL_TOKEN_JSON"] = token_json
        return jsonify({"status": "no_refresh_token", "message": "Consent completed but no refresh_token returned. Re-run consent ensuring you select an account and allow offline access.", "persisted_to": path}), 200
    # persist locally (instance folder) for development
    path = _persist_token(token_json)
    # also place into runtime config so subsequent calls can use it immediately
    try:
        current_app.config["GMAIL_TOKEN_JSON"] = token_json
    except Exception:
        pass

    # redirect to a simple UI page or root with query param so user knows it's connected
    redirect_to = url_for("main.index") + "?gmail_connected=1"
    return redirect(redirect_to)


@bp.route("/fetch-emails", methods=["POST"])
def fetch_emails():
    # In production require ADMIN_API_TOKEN; in development allow unauthenticated
    env = current_app.config.get('APP_CONFIG', 'development')
    if env == 'production':
        token = request.headers.get("Authorization")
        if token != f"Bearer {current_app.config.get('ADMIN_API_TOKEN')}":
            return jsonify({"error": "unauthorized"}), 401
    gmail_token_json = current_app.config.get("GMAIL_TOKEN_JSON")
    if not gmail_token_json:
        return jsonify({"error": "no_gmail_token_configured"}), 400
    try:
        messages = fetch_today_messages(gmail_token_json)
    except Exception as exc:
        # If the google API client raised a HttpError, return a clear JSON error so UI can show it
        if HttpError is not None and isinstance(exc, HttpError):
            current_app.logger.exception("gmail api http error")
            # try to surface the error payload
            details = None
            try:
                details = exc.content.decode('utf-8') if hasattr(exc, 'content') and isinstance(exc.content, (bytes, bytearray)) else str(exc)
            except Exception:
                details = str(exc)
            return jsonify({"error": "gmail_api_error", "details": details}), 502
        current_app.logger.exception("failed to fetch gmail messages")
        return jsonify({"error": "fetch_failed"}), 500
    # classify messages using existing classifier
    from app.nlp.classifier import classify_text_with_confidence

    results = []
    totals = {"productive": 0, "unproductive": 0}
    for m in messages:
        snippet = m.get("snippet") or ""
        # use the classifier that returns (decision, confidence, used_ml)
        try:
            cat, conf, _used_ml = classify_text_with_confidence(snippet)
        except Exception:
            # fall back to the simpler API if available
            try:
                from app.nlp.classifier import classify_text as _classify_simple
                cat = _classify_simple(snippet)
                conf = 1.0
            except Exception:
                cat = "Improdutivo"
                conf = 0.0

        item = {**m, "category": cat, "confidence": conf}
        # in development include classifier diagnostic info so we can see why decisions are made
        try:
            if current_app.config.get('APP_CONFIG', 'development') == 'development':
                try:
                    from app.nlp.classifier import get_last_decision_reason, classify_text_html
                    reason = get_last_decision_reason()
                    # classify_text_html returns (decision, html, details)
                    try:
                        _d_decision, _d_html, details = classify_text_html(snippet)
                    except Exception:
                        details = {}
                    item.update({"reason": reason, "details": details})
                except Exception:
                    # ignore diagnostic failures
                    pass
        except Exception:
            pass
        results.append(item)
        if cat == "Produtivo":
            totals["productive"] += 1
        else:
            totals["unproductive"] += 1
    return jsonify({"messages": results, "totals": totals})


@bp.route('/gmail/token-status')
def token_status():
    """Return whether a Gmail token is configured in runtime config (env or instance file).

    This endpoint is used by the UI to show a helpful message when no token is present.
    """
    try:
        gmail_token_json = current_app.config.get("GMAIL_TOKEN_JSON")
        configured = bool(gmail_token_json)
        source = None
        if configured:
            # If the value is a string it may be a path or raw JSON string stored in env.
            if isinstance(gmail_token_json, str):
                try:
                    if os.path.exists(gmail_token_json):
                        source = "file"
                    else:
                        source = "env"
                except Exception:
                    source = "env"
            else:
                source = "env"
        return jsonify({"configured": configured, "source": source}), 200
    except Exception:
        current_app.logger.exception('failed to determine gmail token status')
        return jsonify({"configured": False}), 200


@bp.route('/gmail/consent-url')
def consent_url():
    """Return the consent URL and redirect URI used by the app (diagnostic only)."""
    try:
        url = build_consent_url(state="diagnostic")
        redirect_uri = url_for("gmail_auth.oauth_callback", _external=True)
        return jsonify({"consent_url": url, "redirect_uri": redirect_uri, "client_id": CLIENT_ID}), 200
    except Exception:
        current_app.logger.exception('failed to build consent url')
        return jsonify({"error": "failed_to_build_consent_url"}), 500
