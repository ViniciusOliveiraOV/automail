from typing import Dict, Any, cast, Tuple, Union, List
from flask import Blueprint, render_template, request, Response, jsonify, current_app
from app.nlp.preprocess import preprocess_text
from app.nlp.classifier import classify_text_html, classify_email, get_last_decision_reason
from app.ai.client import generate_response
from io import BytesIO

bp = Blueprint("main", __name__)
# alias expected by app.main
main = bp

@bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")
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
    if request.method == "POST":
        # accept multiple possible form field names (legacy and new)
        text = request.form.get("text") or request.form.get("email_text") or ""
        file_debug = ""

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
            decision, score_html = classify_text_html(text)
        except Exception:
            decision = classify_email(text)
            score_html = ""
        debug = get_last_decision_reason()
        return render_template(
            "result.html",
            # primary names used by new templates
            decision=decision,
            text=text,
            score_html=score_html,
            debug=debug,
            # aliases to keep backward-compatible templates working
            resposta_sugerida=decision,
            result=decision,
            category=decision,
            original=text,
            email=text,
            debug_reason=debug,
            file_debug=file_debug,
        )

    # GET: render the index page which contains the form (classify.html was missing)
    return render_template("index.html")

# create alias endpoints so templates using main.index / main.classify resolve correctly
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