from typing import Dict, Any, cast, Tuple, Union, List
from flask import Blueprint, request, render_template, current_app, jsonify, Response
from app.nlp.preprocess import preprocess_text
from app.nlp.classifier import classify_text
from app.ai.client import generate_response
from io import BytesIO

main = Blueprint("main", __name__)

@main.route("/", methods=["GET"])
def index():
    return render_template("index.html")
def process_email_pipeline(raw_text: str) -> Dict[str, str]:
    text = preprocess_text(raw_text)
    label: str = classify_text(text)
    suggestion = generate_response(label, raw_text)
    return {"category": label, "suggested_reply": suggestion, "text": raw_text}

@main.route("/process-email", methods=["POST"])
def process_email_endpoint() -> Response:
    # cast the JSON payload to a typed dict so static checkers know the shape
    data = cast(Dict[str, Any], request.get_json(silent=True) or {})
    text = data.get("text") or request.form.get("text", "")
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

@main.route("/classify", methods=["POST"])
def classify_route():
    # extract text (keep your existing extraction logic)
    text = (request.form.get("email_text") or "").strip()
    file_debug = ""
    # if textarea empty, try other form fields
    if not text:
        for name in ("email", "text", "message", "content", "email_content", "body", "message_text"):
            val = request.form.get(name)
            if val and val.strip():
                text = val.strip()
                break

    # if still empty, try any non-empty form value
    if not text:
        for v in request.form.values():
            if v and str(v).strip():
                text = str(v).strip()
                break

    # if file uploaded, try to read it as text (txt or fallback decode)
    if not text and request.files:
        f = request.files.get("email_file") or next(iter(request.files.values()), None)
        if f:
            extracted, file_debug = _extract_text_from_file(f)
            if extracted:
                text = extracted
            else:
                # do not set text to raw binary; leave empty so classifier fallback runs
                text = ""

    text = text or ""

    # classify and fetch debug reason via getter
    from app.nlp.classifier import classify_email, get_last_decision_reason
    result = classify_email(text)
    debug_reason = get_last_decision_reason() or ""

    # pass file_debug so template can show extraction status
    return render_template(
        "result.html",
        result=result,
        category=result,
        resposta_sugerida=result,
        original=text,
        email=text,
        debug_reason=debug_reason,
        file_debug=file_debug,
    )

# create alias endpoints so templates using main.index / main.classify resolve correctly
try:
    # if using a Blueprint named `main`
    main.add_url_rule("/", endpoint="index", view_func=index)
    main.add_url_rule("/classify", endpoint="classify", view_func=classify_route, methods=["POST"])
except Exception:
    # fallback if routes are registered on `app` instead of a blueprint
    try:
        # use current_app to reference the Flask application object when available
        current_app.add_url_rule("/", endpoint="index", view_func=index)
        current_app.add_url_rule("/classify", endpoint="classify", view_func=classify_route, methods=["POST"])
    except Exception:
        # ignore if already registered or if no application context is available
        pass