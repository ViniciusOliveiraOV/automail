from dotenv import load_dotenv
import json
import requests
import os
import concurrent.futures
import functools
import builtins
from typing import Any, cast
from app.nlp.classifier import classify_email as nlp_classify_email
import bleach

load_dotenv() 

class AIClient:
    from typing import Optional

    def __init__(self, api_url: str = "https://api.x.ai/v1/chat/completions", api_key: Optional[str] = None) -> None:
        # Campos legados mantidos por compatibilidade; o cliente agora prefere Hugging Face (HF)
        self.api_url = api_url or os.environ.get("GROK_API_URL", "https://api.x.ai/v1/chat/completions")
        self.api_key = api_key or os.environ.get("GROK_API_KEY")
        # Configuração do Hugging Face (provedor preferido)
        self.hf_token = os.environ.get("HF_API_TOKEN")
        self.hf_model = os.environ.get("HF_MODEL", "google/flan-t5-large")
        self.hf_api_base = os.environ.get("HF_API_URL", "https://api-inference.huggingface.co/models")

    def classify_email(self, email_content: str) -> str:
        """Classifica um e‑mail como 'Produtivo' ou 'Improdutivo'.

        Estratégia:
        - Tenta a API de inferência do Hugging Face primeiro (com cache + threadpool).
        - Se o HF expirar ou não estiver disponível, faz fallback para o classificador local.
        - Sempre retorna uma etiqueta curta ou 'Unknown' quando não for possível decidir.
        """
        # Caso especial: modelos zero-shot (ex.: facebook/bart-large-mnli) que
        # esperam `inputs` como string e `parameters` contendo `candidate_labels`.
        # Para modelos zero-shot / MNLI prefere-se um dict de inputs com chave `text`
        # (a API de inferência do HF aceita tanto uma string quanto um dict como {"text": "..."}).
        # HF config
        hf_token = os.environ.get("HF_API_TOKEN")
        hf_model = os.environ.get("HF_MODEL", "google/flan-t5-large")
        hf_api_base = os.environ.get("HF_API_URL", "https://api-inference.huggingface.co/models")
        hf_timeout = float(os.environ.get("HF_TIMEOUT", "12.0"))

        # Prepare thread pool executor for offloading HF calls (stored on instance)
        if not hasattr(self, "_hf_executor"):
            setattr(self, "_hf_executor", concurrent.futures.ThreadPoolExecutor(max_workers=int(os.environ.get("LLM_WORKERS", "2"))))
        executor = getattr(self, "_hf_executor")

        # Simple LRU cache for HF inference
        @functools.lru_cache(maxsize=256)
        def _hf_inference_cached(prompt: str, model_name: str, api_base: str, token: str, timeout: float) -> str:
            hf_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            # Caso especial: modelos zero-shot (ex.: facebook/bart-large-mnli) que
            # esperam `inputs` como string e `parameters` contendo `candidate_labels`.
            # Para modelos zero-shot / MNLI prefere-se um dict de inputs com chave `text`.
            if "bart-large-mnli" in model_name or "mnli" in model_name:
                payload: dict[str, Any] = {"inputs": {"text": prompt}, "parameters": {"candidate_labels": ["Produtivo", "Improdutivo"]}}
            else:
                payload: dict[str, Any] = {"inputs": prompt, "options": {"wait_for_model": True}}

            url = f"{api_base.rstrip('/')}/{model_name}"
            if os.environ.get("AI_DBG", "0") == "1":
                try:
                    pretty = json.dumps(payload, ensure_ascii=False)
                except Exception:
                    pretty = str(payload)
                print(f"[AI_DBG] HF SEND {url} payload={pretty}")

            r = requests.post(url, headers=hf_headers, json=payload, timeout=timeout)

            if os.environ.get("AI_DBG", "0") == "1":
                try:
                    short = r.text if os.environ.get("AI_DBG_RAW", "0") == "1" else r.text[:400]
                except Exception:
                    short = "<no body>"
                print(f"[AI_DBG] HF POST {url} -> status={r.status_code} body={short}")

            r.raise_for_status()
            body: Any = r.json()
            # If zero-shot classification output (labels + scores)
            if isinstance(body, dict) and "labels" in body:
                # Treat the JSON body as a typed dict for safe .get() usage
                body_dict = cast(dict[str, Any], body)
                # Be explicit about the expected type: coerce/validate into a list[str]
                raw_labels: Any = body_dict.get("labels", [])
                labels: list[str] = []
                # Normalize and validate labels to be a list of strings
                if isinstance(raw_labels, list):
                    for item in cast(list[Any], raw_labels):
                        if isinstance(item, str):
                            labels.append(item)
                        else:
                            # Coerce non-string items to string to keep a predictable type
                            try:
                                # Use builtins.str() to coerce items into a string (explicit for type checkers)
                                labels.append(builtins.str(cast(object, item)))
                            except Exception:
                                # Skip items that cannot be represented
                                continue
                elif isinstance(raw_labels, str):
                    # single-label string provided
                    labels.append(raw_labels)
                # otherwise ignore unexpected types
                if labels:
                    top = labels[0]
                    # top is guaranteed to be a string here
                    return top
            # Common generation formats
            if isinstance(body, list) and body:
                first: Any = cast(list[Any], body)[0]
                # Only call .get on actual dict objects to satisfy type checkers
                if isinstance(first, dict):
                    # Cast to a typed dict so .get has a known signature for the type checker
                    first_dict = cast(dict[str, Any], first)
                    gen = first_dict.get("generated_text") or first_dict.get("text")
                    if gen is not None:
                        return builtins.str(gen)
                    return builtins.str(cast(object, first))
                # Non-dict items: stringify
                return builtins.str(cast(object, first))
            if isinstance(body, dict) and "generated_text" in body:
                # Prefer generated_text or text fields, coerce to str and avoid returning None
                body_dict = cast(dict[str, Any], body)
                gen = body_dict.get("generated_text") or body_dict.get("text")
                if gen is not None:
                    return builtins.str(gen)
                # Fallback to stringifying the whole body to satisfy the declared return type
                return builtins.str(body_dict)
            return builtins.str(cast(object, body))

        def _dbg_wrap(text: str, source: str, raw: str | None = None) -> str:
            """Return text optionally annotated when AI_DBG=1."""
            if os.environ.get("AI_DBG", "0") != "1":
                return text
            parts = [f"src={source}"]
            if raw and os.environ.get("AI_DBG_RAW", "0") == "1":
                # include only first 200 chars of raw body (sanitize newlines)
                sanitized = raw[:200].replace("\n", " ")
                parts.append(f"raw={sanitized}")
            return f"{text} ({', '.join(parts)})"

        # Use the configured HF model first, then sensible hosted fallbacks.
        if hf_token:
            prompt = f"Classifique o seguinte email como 'Produtivo' ou 'Improdutivo':\n\n{email_content}"
            # sensible hosted fallbacks recommended: BART MNLI for zero-shot and Llama instruct models
            candidates = [hf_model] + [m for m in ("facebook/bart-large-mnli", "meta-llama/Llama-3.1-8B-Instruct", "meta-llama/Llama-3.1-70B-Instruct") if m != hf_model]
            last_exc = None
            normalized = " ".join(email_content.split()).strip()
            for model_try in candidates:
                if os.environ.get("AI_DBG", "0") == "1":
                    print(f"[AI_DBG] Trying HF model for classification: {model_try}")
                model_prompt = normalized if ("bart-large-mnli" in model_try or "mnli" in model_try) else prompt
                future = executor.submit(_hf_inference_cached, model_prompt, model_try, hf_api_base, hf_token, hf_timeout)
                try:
                    text = future.result(timeout=hf_timeout)
                except concurrent.futures.TimeoutError:
                    if os.environ.get("AI_DBG", "0") == "1":
                        print(f"[AI_DBG] HF timeout for model {model_try} after {hf_timeout}s")
                    last_exc = concurrent.futures.TimeoutError()
                    continue
                except Exception as e:
                    if os.environ.get("AI_DBG", "0") == "1":
                        print(f"[AI_DBG] HF exception for model {model_try}: {e}")
                    last_exc = e
                    continue

                raw_body = text
                text = (text or "").strip()
                if "improdut" in text.lower() or "improd" in text.lower():
                    return _dbg_wrap("Improdutivo", "hf", raw_body)
                if "produt" in text.lower():
                    return _dbg_wrap("Produtivo", "hf", raw_body)
                lowered = text.lower()
                if any(tok in lowered for tok in ("entailment", "contradiction", "neutral", "produtivo", "improdutivo")):
                    return _dbg_wrap(text or "Unknown", "hf", raw_body)
                # unrecognized HF output for this model -> try next candidate
            # All HF attempts failed or returned unrecognized output -> local fallback
            if os.environ.get("AI_DBG", "0") == "1":
                print(f"[AI_DBG] HF classification failed for all candidates: last_exception={last_exc}")
            try:
                return _dbg_wrap(nlp_classify_email(email_content), "local_fallback")
            except Exception:
                return _dbg_wrap("Unknown", "hf")

        # No HF token -> fall back to the local heuristic classifier
        try:
            local_label = nlp_classify_email(email_content)
            return _dbg_wrap(local_label, "local")
        except Exception:
            return _dbg_wrap("Unknown", "canned")

    def generate_response(self, data: dict[str, object], input_data: dict[str, object], category: str, original_text: str) -> str:
        # Prefer the configured Hugging Face model. If no HF token is available
        # or the request fails we fall back to a short canned reply.
        hf_token = self.hf_token
        hf_model = self.hf_model
        hf_api_base = self.hf_api_base

        if hf_token:
            hf_headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
            prompt = f"Categoria: {category}\nEmail: {original_text}\nGere uma resposta breve e adequada."
            hf_payload: dict[str, Any] = {"inputs": prompt, "options": {"wait_for_model": True}}
            # try configured model first, then a short fallback list of reasonable hosted candidates
            # Note: zero-shot MNLI models (facebook/bart-large-mnli) are for classification only
            # and should not be used for text generation; skip them in the generation path.
            raw_fallbacks = ("facebook/bart-large-mnli", "meta-llama/Llama-3.1-8B-Instruct", "meta-llama/Llama-3.1-70B-Instruct", "autoevaluate/natural-language-inference")
            candidates = [hf_model] + [m for m in raw_fallbacks if m != hf_model and "mnli" not in m.lower()]
            last_exc: Exception | None = None
            for model_try in candidates:
                hf_url = f"{hf_api_base.rstrip('/')}/{model_try}"
                # Skip MNLI-style models for generation attempts
                if "mnli" in model_try.lower() or "bart-large-mnli" in model_try.lower():
                    if os.environ.get("AI_DBG", "0") == "1":
                        print(f"[AI_DBG] Skipping MNLI model for generation: {model_try}")
                    continue

                try:
                    r = requests.post(hf_url, headers=hf_headers, json=hf_payload, timeout=float(os.environ.get("HF_TIMEOUT", "20")))
                    if os.environ.get("AI_DBG", "0") == "1":
                        try:
                            short = r.text if os.environ.get("AI_DBG_RAW", "0") == "1" else r.text[:400]
                        except Exception:
                            short = "<no body>"
                        print(f"[AI_DBG] HF POST {hf_url} -> status={r.status_code} body={short}")
                    if r.status_code == 404:
                        if os.environ.get("AI_DBG", "0") == "1":
                            print(f"[AI_DBG] HF model {model_try} not found (404), trying next candidate")
                        continue
                    r.raise_for_status()
                    body = r.json()
                    if isinstance(body, list) and body:
                        first_item = cast(dict[str, Any], body[0])
                        text = first_item.get("generated_text") or first_item.get("text") or builtins.str(first_item)
                    elif isinstance(body, dict) and ("generated_text" in body or "text" in body):
                        body_dict = cast(dict[str, Any], body)
                        gen = body_dict.get("generated_text") or body_dict.get("text")
                        text = builtins.str(gen) if gen is not None else builtins.str(body_dict)
                    else:
                        text = builtins.str(cast(object, body))
                    return (text or "").strip()
                except Exception as e:
                    last_exc = e
                    if os.environ.get("AI_DBG", "0") == "1":
                        print(f"[AI_DBG] HF attempt {model_try} failed: {e}")
                    continue
            if os.environ.get("AI_DBG", "0") == "1":
                print(f"[AI_DBG] All HF candidates failed: last_exception={last_exc}")

        # Fallback canned replies when HF is not available or fails
        if category == "Produtivo":
            return "Obrigado pelo contato. Recebi sua mensagem e vou analisar/acionar o responsável. Retorno em breve com uma atualização."
        return "Agradeço a mensagem. Registro-a e, caso seja necessário, entrarei em contato. Desejo um ótimo dia."

def generate_response(category: str, original_text: str) -> str:
    ai = AIClient()
    return ai.generate_response({}, {}, category=category, original_text=original_text)

if __name__ == "__main__":
    resposta = generate_response("Produtivo", "Preciso de suporte urgente.")
    print(resposta)