from typing import Dict
from flask import Blueprint, request, render_template, jsonify
from app.nlp.preprocess import preprocess_text
from app.nlp.classifier import classify_text
from app.ai.client import generate_response

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
def process_email_endpoint():
    data = request.get_json() or {}
    text = data.get("text") or request.form.get("text", "")
    if not text:
        return jsonify({"error": "no text provided"}), 400
    result = process_email_pipeline(text)
    return jsonify(result)