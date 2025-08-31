import os
from typing import Dict, Any, cast, Tuple, Union, List
import logging
from flask import Blueprint, render_template, request, Response, jsonify, current_app
try:
    import bleach
    _BLEACH_AVAILABLE = True
except Exception:
    _BLEACH_AVAILABLE = False
from app.nlp.preprocess import preprocess_text
from app.nlp.classifier import classify_text_html, classify_email, get_last_decision_reason, classify_text_with_confidence
# Tenta importar a função real do cliente de AI; fornece um fallback tipado
# para que a análise estática e erros em tempo de execução sejam evitados
# caso o símbolo não esteja presente.
try:
    from app.ai.client import generate_response
except Exception:
    def generate_response(category: str, original_text: str) -> str:
        # Fallback implementation used when the AI client or the symbol is missing.
        # Keep this simple and non-blocking: return an empty string or a short canned reply.
        return ""
from io import BytesIO
import html as _html
import re
import time
from flask import stream_with_context, Response

bp = Blueprint("main", __name__)
# alias expected by app.main
main = bp

logger = logging.getLogger(__name__)

@bp.route("/", methods=["GET"])
def index():
    # Provide a safe gmail start URL for the template so rendering does not
    # fail if the optional gmail blueprint wasn't registered at runtime.
    try:
        from flask import url_for
        gmail_start = url_for('gmail_auth.start_oauth')
    except Exception:
        gmail_start = '/gmail/start'
    return render_template("index.html", gmail_start_url=gmail_start)


@bp.route("/classify-llm", methods=["POST"])
def classify_llm():
    """Endpoint para invocar o LLM sob demanda para uma única instância de classificação.
    Respeita as flags de configuração do servidor `ENABLE_LLM` e `ALLOW_UI_LLM_TOGGLE`.
    """
    if not (bool(current_app.config.get("ENABLE_LLM")) and bool(current_app.config.get("ALLOW_UI_LLM_TOGGLE", False))):
        return jsonify({"error": "LLM not enabled"}), 403

    data = cast(Dict[str, Any], request.get_json(silent=True) or {})
    text = data.get("text") or request.form.get("text") or ""
    if not text:
        return jsonify({"error": "no text provided"}), 400

    # optionally redact or trim text before sending to LLM (keep minimal for privacy)
    # here we send a short prefix + max 4096 characters to avoid huge payloads
    snippet = text if len(text) <= 4096 else text[:4096]
    try:
        # compute a heuristics-backed decision to pass as category to LLM so it can
        # produce a context-aware reply (Produtivo/Improdutivo)
        try:
            decision_label, _, _ = classify_text_with_confidence(text)
        except Exception:
            decision_label = classify_email(text)
        llm_reply = generate_response(decision_label, snippet)
    except Exception:
        logger.exception("llm call failed")
        return jsonify({"error": "llm call failed"}), 500

    return jsonify({"llm_reply": llm_reply, "llm_used": True})


@bp.route("/classify-llm-stream", methods=["POST"])
def classify_llm_stream():
    """Transmite a resposta do LLM em pedaços (streaming).
    Para desenvolvimento/local, simula streaming gerando a resposta via
    `generate_response` e emitindo pequenos trechos com pequenos atrasos.
    """
    if not (bool(current_app.config.get("ENABLE_LLM")) and bool(current_app.config.get("ALLOW_UI_LLM_TOGGLE", False))):
        return jsonify({"error": "LLM not enabled"}), 403

    data = cast(Dict[str, Any], request.get_json(silent=True) or {})
    text = data.get("text") or request.form.get("text") or ""
    if not text:
        return jsonify({"error": "no text provided"}), 400

    # generate full reply (synchronously) then stream it in small chunks
    try:
        try:
            decision_label, _, _ = classify_text_with_confidence(text)
        except Exception:
            decision_label = classify_email(text)
        full_reply = generate_response(decision_label, text)
    except Exception:
        logger.exception("llm call failed")
        return jsonify({"error": "llm call failed"}), 500

    def generator():
        # prefix with a simple JSON-like preface so the client can format
        # We'll stream plain text chunks
        words = (full_reply or "").split()
        for w in words:
            yield w + ' '
            # brief delay to simulate streaming
            time.sleep(0.03)

    return Response(stream_with_context(generator()), mimetype='text/plain; charset=utf-8')
def process_email_pipeline(raw_text: str) -> Dict[str, str]:
    text = preprocess_text(raw_text)
    label: str = classify_email(text)
    suggestion = generate_response(label, text)
    return {"category": label, "suggested_reply": suggestion, "text": text}

@bp.route("/process-email", methods=["POST"])
def process_email_endpoint() -> Response:
    # cast the JSON payload to a typed dict so static checkers know the shape
    data = cast(Dict[str, Any], request.get_json(silent=True) or {})
    # support text in JSON/form and file uploads
    text = data.get("text") or request.form.get("text", "")
    # if no text in payload, check uploaded file and extract text
    if not text and request.files:
        uploaded = request.files.get("file")
        if uploaded:
            file_text, status = _extract_text_from_file(uploaded)
            # accept extracted text if present, otherwise return an error mentioning status
            if file_text:
                text = file_text
            else:
                resp = jsonify({"error": "uploaded file contains no text", "status": status})
                resp.status_code = 400
                return resp
    if not text:
        resp = jsonify({"error": "no text provided"})
        resp.status_code = 400
        return resp
    result = process_email_pipeline(text)
    return jsonify(result)

def _extract_text_from_file(f: Any) -> Tuple[str, str]:
    try:
        payload: Union[bytes, str] = f.read()
    except Exception:
        return "", "file_read_error"

    # detect PDF by header or mimetype/filename
    is_pdf = False
    try:
        header = payload[:5]
        # be explicit about bytes vs str when checking the PDF header
        if (isinstance(header, (bytes, bytearray)) and header == b"%PDF-") or getattr(f, "mimetype", "") == "application/pdf" or (getattr(f, "filename", "") or "").lower().endswith(".pdf"):
            is_pdf = True
    except Exception:
        is_pdf = False

    if is_pdf:
        try:
            from PyPDF2 import PdfReader
            # ensure BytesIO gets bytes: handle bytes, bytearray, memoryview and fallback to encoding strings
            if isinstance(payload, bytes):
                bio_bytes = payload
            elif isinstance(payload, (bytearray, memoryview)):
                bio_bytes = bytes(payload)
            else:
                # fallback for str or other types
                bio_bytes = str(payload).encode()
            bio = BytesIO(bio_bytes)
            reader = PdfReader(bio)
            pages: List[str] = []
            for p in reader.pages:
                txt = p.extract_text() or ""
                pages.append(txt)
            content = "\n".join(pages).strip()
            if content:
                return content, "pdf_text_extracted"
            return "", "pdf_no_text_extracted"
        except Exception:
            return "", "pdf_extraction_failed"

    # non-pdf: try decode
    try:
        if isinstance(payload, (bytes, bytearray)):
            content = payload.decode(errors="ignore")
        else:
            content = str(payload)
        return content.strip(), "file_text_extracted" if content.strip() else "file_empty"
    except Exception:
        return "", "file_decode_failed"

@bp.route("/classify", methods=["GET", "POST"])
def classify():
    # If requested via GET, render the index page with the form
    if request.method == "GET":
        return render_template("index.html")

    if request.method == "POST":
        # accept multiple possible form field names (legacy and new)
        text = request.form.get("text") or request.form.get("email_text") or ""
        # safe defaults for template variables (avoid unbound locals on error paths)
        file_debug = ""
        decision = ""
        score_html = ""
        details: Dict[str, Any] = {}
        confidence = None
        debug = ""
        needs_review = False
        display_html = ""

        # if no text in form, try uploaded file(s)
        if not text and request.files:
            # prefer common field names but fall back to any uploaded file
            uploaded = request.files.get("email_file") or request.files.get("file")
            if not uploaded:
                # pick the first file in the files dict if present
                uploaded = next(iter(request.files.values()), None)
            if uploaded:
                file_text, file_debug = _extract_text_from_file(uploaded)
                if file_text:
                    text = file_text

        # use HTML-aware classifier so we can render the score fragment in the template
        try:
            # primary: heuristic decision, HTML fragment and structured details (no ML/LLM override)
            decision, score_html, details = classify_text_html(text)
        except Exception:
            decision = classify_email(text)
            score_html = ""
            details = {}

        # sanitize classifier HTML fragment before marking safe in templates
        if score_html and _BLEACH_AVAILABLE:
            # Allow the structural tags and preserve class attributes so the
            # classifier's markup (score-panel, score-card, score-count, etc.)
            # remains intact and can be styled by our CSS. Be conservative and
            # only allow the tags we generate.
            ALLOWED_TAGS = ['div', 'span', 'strong', 'em', 'code', 'pre', 'p', 'ul', 'li', 'br', 'h4']
            # Allow class on the tags so CSS selectors remain after cleaning.
            ALLOWED_ATTRS = {
                'div': ['class'],
                'span': ['class'],
                'h4': ['class'],
                'ul': ['class'],
                'li': ['class'],
                'code': ['class']
            }
            try:
                score_html = bleach.clean(score_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
            except Exception:
                # fallback: strip all tags
                score_html = re.sub(r'<[^>]+>', '', score_html)

        # compute confidence using the classifier helper but do NOT allow automatic ML fallback here
        try:
            # set ml_threshold=0.0 so classify_text_with_confidence computes confidence but will not call ML
            _decision_tmp, confidence, _used_ml = classify_text_with_confidence(text, ml_threshold=0.0)
        except Exception:
            confidence = 0.2

        # ambiguous if confidence below a configurable UI threshold
        amb_threshold = float(current_app.config.get("LLM_PROMPT_CONF_THRESHOLD", 0.6))
        ambiguous = (confidence is None) or (confidence < amb_threshold)

        # whether server allows UI-triggered LLM (global server enable + explicit allow toggle)
        llm_allowed = bool(current_app.config.get("ENABLE_LLM")) and bool(current_app.config.get("ALLOW_UI_LLM_TOGGLE", False))

        needs_review = (get_last_decision_reason() == "needs_human_review")
        debug = get_last_decision_reason()

        # prepare a display-friendly HTML version of the email text (keep original text for classification)
        def _format_text_for_display(s: str) -> str:
            if not s:
                return ""
            # unify newlines and normalize whitespace
            s2 = s.replace('\r\n', '\n').replace('\r', '\n')
            # mark paragraph breaks where there are 2+ newlines (or newline + spaces + newline)
            s2 = re.sub(r"\n\s*\n+", "\n\n", s2)
            # split into paragraphs
            paras = [p.strip() for p in s2.split('\n\n') if p.strip()]
            out_paras: List[str] = []
            for p in paras:
                # collapse any remaining whitespace (including single newlines) into a single space
                collapsed = re.sub(r"\s+", ' ', p).strip()
                out_paras.append(_html.escape(collapsed))
            if not out_paras:
                return _html.escape(re.sub(r"\s+", ' ', s2).strip())
            return '<p>' + '</p><p>'.join(out_paras) + '</p>'

        display_html = _format_text_for_display(text)

        return render_template(
            "result.html",
            # primary names used by new templates
            decision=decision,
            text=text,
            display_html=display_html,
            score_html=score_html,
            details=details,
            debug=debug,
            confidence=confidence,
            needs_review=needs_review,
            ambiguous=ambiguous,
            llm_allowed=llm_allowed,
            # aliases to keep backward-compatible templates working
            resposta_sugerida=decision,
            result=decision,
            category=decision,
            original=text,
            email=text,
            debug_reason=debug,
            file_debug=file_debug,
        )


@bp.route('/_health', methods=['GET'])
def _health():
    return jsonify({'status': 'ok'})

# Cria aliases para endpoints para que templates que usam main.index / main.classify
# resolvam corretamente
try:
    # if using a Blueprint named `main`
    bp.add_url_rule("/", endpoint="index", view_func=index)
    bp.add_url_rule("/classify", endpoint="classify", view_func=classify, methods=["POST"])
except Exception:
    # fallback if routes are registered on `app` instead of a blueprint
    try:
        # use current_app to reference the Flask application object when available
        current_app.add_url_rule("/", endpoint="index", view_func=index)
        current_app.add_url_rule("/classify", endpoint="classify", view_func=classify, methods=["POST"])
    except Exception:
        # ignore if already registered or if no application context is available
        pass


# Observação: endpoints de debug como '/_debug_llm_config' foram removidos para
# adequação à produção. Se você precisar inspecionar a configuração em tempo de
# execução do LLM, execute a aplicação localmente e use inspeção do ambiente ou
# uma sessão de depuração.