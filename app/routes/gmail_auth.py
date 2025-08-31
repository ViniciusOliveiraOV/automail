from flask import Blueprint, current_app, jsonify, redirect, request
from app.utils.gmail_oauth import build_consent_url
from app.utils.gmail_reader import fetch_today_messages

bp = Blueprint("gmail_auth", __name__)


@bp.route("/gmail/start")
def start_oauth():
    url = build_consent_url(state="fetch_today")
    return redirect(url)


@bp.route("/gmail/callback")
def oauth_callback():
    # Exchange code for token using google token endpoint. We keep this
    # minimal: caller must persist refresh_token from returned payload.
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "no_code"}), 400
    # In a full implementation you'd exchange the code here and persist
    # the refresh token. For now, return a notice asking the user to save
    # the code and perform the exchange server-side with client secrets.
    return jsonify({"status": "received_code", "code": code})


@bp.route("/fetch-emails", methods=["POST"])
def fetch_emails():
    # Require a simple admin token to avoid open endpoint (read from env)
    token = request.headers.get("Authorization")
    if token != f"Bearer {current_app.config.get('ADMIN_API_TOKEN')}":
        return jsonify({"error": "unauthorized"}), 401
    # Expect the server to have a stored token made available via env JSON
    gmail_token_json = current_app.config.get("GMAIL_TOKEN_JSON")
    if not gmail_token_json:
        return jsonify({"error": "no_gmail_token_configured"}), 400
    messages = fetch_today_messages(gmail_token_json)
    # classify messages using existing classifier
    from app.nlp.classifier import classify_text

    results = []
    totals = {"productive": 0, "unproductive": 0}
    for m in messages:
        cat, conf = classify_text(m.get("snippet", ""))
        results.append({**m, "category": cat, "confidence": conf})
        if cat == "Produtivo":
            totals["productive"] += 1
        else:
            totals["unproductive"] += 1
    return jsonify({"messages": results, "totals": totals})
