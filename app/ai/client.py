from dotenv import load_dotenv
import requests
import os
import concurrent.futures
import functools
import builtins
from typing import Any, cast
from app.config import BaseConfig

load_dotenv() 

class AIClient:
    from typing import Optional

    def __init__(self, api_url: str = "https://api.x.ai/v1/chat/completions", api_key: Optional[str] = None) -> None:
        self.api_url = api_url or os.environ.get("GROK_API_URL", "https://api.x.ai/v1/chat/completions")
        self.api_key = api_key or os.environ.get("GROK_API_KEY")

    def classify_email(self, email_content: str) -> str:
        """Classify an email as 'Produtivo' or 'Improdutivo'.

        Strategy:
        - Try Hugging Face Inference API first (cached + threadpool).
        - If HF times out or is unavailable, fall back to Grok (if configured).
        - Always return a short string label or 'Unknown'.
        """
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        # Grok payload (used as fallback)
        grok_payload: dict[str, object] = {
            "model": "grok-4-latest",
            "messages": [
                {"role": "system", "content": "Você é um assistente que classifica emails como 'Produtivo' ou 'Improdutivo'. Responda apenas com uma das duas palavras."},
                {"role": "user", "content": f"Classifique o seguinte email:\n\n{email_content}"}
            ],
            "temperature": 0.0,
            "max_tokens": 16
        }

        # HF config
        hf_token = os.environ.get("HF_API_TOKEN")
        hf_model = os.environ.get("HF_MODEL", "google/flan-t5-large")
        hf_api_base = os.environ.get("HF_API_URL", "https://api-inference.huggingface.co/models")
        hf_timeout = float(os.environ.get("HF_TIMEOUT", "12.0"))
        hf_async = os.environ.get("HF_ASYNC", "0") == "1"

        # Prepare thread pool executor for offloading HF calls (stored on instance)
        if not hasattr(self, "_hf_executor"):
            setattr(self, "_hf_executor", concurrent.futures.ThreadPoolExecutor(max_workers=int(os.environ.get("LLM_WORKERS", "2"))))
        executor = getattr(self, "_hf_executor")

        # Simple LRU cache for HF inference
        @functools.lru_cache(maxsize=256)
        def _hf_inference_cached(prompt: str, model_name: str, api_base: str, token: str, timeout: float) -> str:
            hf_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            # Special-case zero-shot models like facebook/bart-large-mnli which expect
            # `inputs` to be a string and `parameters` to include `candidate_labels`.
            if "bart-large-mnli" in model_name:
                payload: dict[str, Any] = {"inputs": prompt, "parameters": {"candidate_labels": ["Produtivo", "Improdutivo"]}}
            else:
                payload: dict[str, Any] = {"inputs": prompt, "options": {"wait_for_model": True}}
                payload = {"inputs": prompt, "options": {"wait_for_model": True}}
            url = f"{api_base.rstrip('/')}/{model_name}"
            r = requests.post(url, headers=hf_headers, json=payload, timeout=timeout)
            # Verbose debug print
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

        # Try HF first if token present — try multiple HF models (user model, then BART MNLI for classification)
        if hf_token:
            prompt = f"Classifique o seguinte email como 'Produtivo' ou 'Improdutivo':\n\n{email_content}"
            # Allow config-driven candidate list (comma-separated)
            cfg_candidates = os.environ.get("HF_MODEL_CANDIDATES") or BaseConfig.HF_MODEL_CANDIDATES
            hf_candidates = [c.strip() for c in cfg_candidates.split(",") if c.strip()]
            # Ensure the explicit HF_MODEL (hf_model) is used first when provided to avoid it being ignored
            if hf_model and hf_model not in hf_candidates:
                hf_candidates.insert(0, hf_model)
            if hf_async:
                # Non-blocking mode: return Unknown immediately and allow cached result to populate
                return "Unknown"

            for model_try in hf_candidates:
                if os.environ.get("AI_DBG", "0") == "1":
                    print(f"[AI_DBG] Trying HF model for classification: {model_try}")
                # Avoid priming zero-shot classifiers: send raw email text instead of an instruction
                # Also perform light normalization: lower whitespace and strip
                normalized = " ".join(email_content.split()).strip()
                model_prompt = normalized if "bart-large-mnli" in model_try else prompt
                future = executor.submit(_hf_inference_cached, model_prompt, model_try, hf_api_base, hf_token, hf_timeout)
                try:
                    text = future.result(timeout=hf_timeout)
                except concurrent.futures.TimeoutError:
                    if os.environ.get("AI_DBG", "0") == "1":
                        print(f"[AI_DBG] HF timeout for model {model_try} after {hf_timeout}s")
                    continue
                except Exception as e:
                    if os.environ.get("AI_DBG", "0") == "1":
                        print(f"[AI_DBG] HF exception for model {model_try}: {e}")
                    continue

                raw_body = text
                text = (text or "").strip()
                # If model produced a clear label, return it. Check 'improd' first to avoid
                # accidental substring matches (e.g. 'Improdutivo' contains 'produt').
                if "improdut" in text.lower() or "improd" in text.lower():
                    return _dbg_wrap("Improdutivo", "hf", raw_body)
                if "produt" in text.lower():
                    return _dbg_wrap("Produtivo", "hf", raw_body)
                # If BART (MNLI) returns an entailment-like label, accept common outputs
                lowered = text.lower()
                if any(tok in lowered for tok in ("entailment", "contradiction", "neutral", "produtivo", "improdutivo")):
                    return _dbg_wrap(text or "Unknown", "hf", raw_body)
                # otherwise try next model

            # All HF attempts failed or produced no clear label — fall back to canned
            if os.environ.get("AI_DBG", "0") == "1":
                print("[AI_DBG] All HF classification candidates failed to produce a label")
            return _dbg_wrap("Unknown", "canned")

        # If no HF token available, try Grok if available
        if self.api_key:
            try:
                resp = requests.post(self.api_url, headers=headers, json=grok_payload, timeout=5)
                if os.environ.get("AI_DBG", "0") == "1":
                    try:
                        short = resp.text if os.environ.get("AI_DBG_RAW", "0") == "1" else resp.text[:400]
                    except Exception:
                        short = "<no body>"
                    print(f"[AI_DBG] Grok POST {self.api_url} -> status={resp.status_code} body={short}")
                resp.raise_for_status()
                body = resp.json()
                grok_text = body.get("choices", [{}])[0].get("message", {}).get("content", "").strip() or "Unknown"
                return _dbg_wrap(grok_text, "grok", str(body))
            except Exception as e:
                if os.environ.get("AI_DBG", "0") == "1":
                    print(f"[AI_DBG] Grok exception: {e}")
                return _dbg_wrap("Unknown", "canned")

        return _dbg_wrap("Unknown", "canned")

    def generate_response(self, data: dict[str, object], input_data: dict[str, object], category: str, original_text: str) -> str:
        # If there's no Grok API key and no HF token, return canned reply
        hf_token = os.environ.get("HF_API_TOKEN")
        hf_model = os.environ.get("HF_MODEL", "google/flan-t5-small")
        hf_api_base = os.environ.get("HF_API_URL", "https://api-inference.huggingface.co/models")

        # If HF token is available, try HF Inference API first (works with public models)
        if hf_token:
            hf_headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
            prompt = f"Categoria: {category}\nEmail: {original_text}\nGere uma resposta breve e adequada."
            hf_payload: dict[str, Any] = {"inputs": prompt, "options": {"wait_for_model": True}}
            candidates = [hf_model, "facebook/bart-large-mnli", "bigscience/bloom", "gpt2"]
            last_exception = None
            for model_try in candidates:
                hf_url = f"{hf_api_base}/{model_try}"
                try:
                    r = requests.post(hf_url, headers=hf_headers, json=hf_payload, timeout=20)
                    if os.environ.get("AI_DBG", "0") == "1":
                        try:
                            short = r.text if os.environ.get("AI_DBG_RAW", "0") == "1" else r.text[:400]
                        except Exception:
                            short = "<no body>"
                        print(f"[AI_DBG] HF POST {hf_url} -> status={r.status_code} body={short}")
                    if r.status_code == 404:
                        # try next candidate
                        if os.environ.get("AI_DBG", "0") == "1":
                            print(f"[AI_DBG] HF model {model_try} not found (404), trying next model")
                        continue
                    r.raise_for_status()
                    body = r.json()
                    # HF may return list or dict — try common fields
                    # Use truthiness check for lists to avoid calling len() on list[Unknown]
                    if isinstance(body, list) and body:
                        first_item = cast(dict[str, Any], body[0])
                        text = first_item.get("generated_text") or first_item.get("text") or builtins.str(first_item)
                    elif isinstance(body, dict) and ("generated_text" in body or "text" in body):
                        # Cast to a typed dict so .get() has a known signature for the type checker,
                        # then coerce the found value to str (safely handling None).
                        body_dict = cast(dict[str, Any], body)
                        gen = body_dict.get("generated_text") or body_dict.get("text")
                        text = builtins.str(gen) if gen is not None else builtins.str(body_dict)
                    else:
                        text = builtins.str(cast(object, body))
                    return (text or "").strip()
                except Exception as e:
                    last_exception = e
                    if os.environ.get("AI_DBG", "0") == "1":
                        print(f"[AI_DBG] HF attempt {model_try} failed: {e}")
                    continue
            # All HF attempts failed — log and fall back to canned reply
            if os.environ.get("AI_DBG", "0") == "1":
                print(f"[AI_DBG] All HF candidates failed: last_exception={last_exception}")
            if category == "Produtivo":
                return "Obrigado pelo contato. Recebi sua mensagem e vou analisar/acionar o responsável. Retorno em breve com uma atualização."
            return "Agradeço a mensagem. Registro-a e, caso seja necessário, entrarei em contato. Desejo um ótimo dia."

        # Next: try Grok if API key present
        if not self.api_key:
            if category == "Produtivo":
                return "Obrigado pelo contato. Recebi sua mensagem e vou analisar/acionar o responsável. Retorno em breve com uma atualização."
            return "Agradeço a mensagem. Registro-a e, caso seja necessário, entrarei em contato. Desejo um ótimo dia."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        messages = [
            {
                "role": "system",
                "content": "Você é um assistente profissional que responde emails de acordo com a categoria informada."
            },
            {
                "role": "user",
                "content": f"Categoria: {category}\nEmail: {original_text}\nGere uma resposta breve e adequada."
            }
        ]
        data = {
            "model": "grok-4-latest",
            "messages": messages,
            "stream": False,
            "temperature": 0.2,
            "max_tokens": 120
        }
        try:
            resp = requests.post(self.api_url, headers=headers, json=data, timeout=15)
            if os.environ.get("AI_DBG", "0") == "1":
                try:
                    short = resp.text if os.environ.get("AI_DBG_RAW", "0") == "1" else resp.text[:400]
                except Exception:
                    short = "<no body>"
                print(f"[AI_DBG] Grok POST {self.api_url} -> status={resp.status_code} body={short}")
            try:
                resp.raise_for_status()
            except requests.HTTPError:
                body_text = "<no body>"
                try:
                    body_text = resp.text
                except Exception:
                    pass
                if resp.status_code == 403 and ("no credits" in body_text.lower() or "doesn't have any credits" in body_text.lower() or "does not have permission" in body_text.lower()):
                    if category == "Produtivo":
                        return "Obrigado pelo contato. Recebi sua mensagem e vou analisar/acionar o responsável. Retorno em breve com uma atualização. (Grok indisponível: conta sem créditos)"
                    return "Agradeço a mensagem. Registro-a e, caso seja necessário, entrarei em contato. Desejo um ótimo dia. (Grok indisponível: conta sem créditos)"
                return f"Erro ao gerar via Grok: {resp.status_code} {resp.reason} - {body_text}"

            result = resp.json()
            return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"Erro ao gerar via Grok: {e}"

def generate_response(category: str, original_text: str) -> str:
    ai = AIClient()
    return ai.generate_response({}, {}, category=category, original_text=original_text)

if __name__ == "__main__":
    resposta = generate_response("Produtivo", "Preciso de suporte urgente.")
    print(resposta)