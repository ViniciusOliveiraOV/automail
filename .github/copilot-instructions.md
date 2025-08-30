# Copilot instructions for the automail repository

Objective
- Help contributors be immediately productive by describing the project's structure, important entry points, test and run workflows, and conventions that repeat across the codebase.

Quick orientation
- This is a small Flask app in `app/` that classifies email text as `Produtivo` / `Improdutivo` using a rule-based engine with an optional sklearn ML fallback and an LLM inference fallback.
- Key runtime entry points:
  - `app/main.py` — application factory `create_app()` and CLI entry when run as `python -m app.main`.
  - `app/__init__.py` — simple Flask app instance used by some dev flows.
  - `app/routes.py` — HTTP routes and web UI handlers (`/`, `/classify`, `/process-email`).

Where the logic lives
- Rule-based classifier: `app/nlp/classifier.py` — central scoring, hard filters (`_looks_spammy`, `_looks_garbled`), overrides (`_apply_overrides`), and HTML fragment builder (`_render_score_html`).
- Preprocessing: `app/nlp/preprocess.py` — normalizes and strips signatures/quoted text before scoring.
- PDF parsing and utils: `app/utils/pdf_parser.py` and `app/utils/mail_client.py` (used for file extraction and optional email fetching).
- AI/LLM integration: `app/ai/client.py` — wrappers to call HF Inference API (primary), Grok/x.ai (fallback), and a BART zero-shot path; has caching and debug toggles.

Important patterns & conventions
- Labels are Portuguese: `Produtivo` and `Improdutivo` (exact strings used across tests and templates). Don't change these strings without updating tests and templates.
- The classifier exposes both programmatic functions and HTML helpers:
  - `classify_text(text: str) -> str` — canonical API used by tests and routes.
  - `classify_text_with_confidence(text, ml_threshold=0.45) -> (label, confidence, used_ml)` — returns confidence and whether ML fallback was used.
  - `classify_text_html(text) -> (label, html_fragment)` — used by the `/classify` UI; the HTML fragment must avoid inline styles (the repo's CSS controls look-and-feel).
- CSS control: `app/static/css/styles.css` holds project palette and badges. Keep `_render_score_html` semantic (use classes like `.score-card`, `.score-good`, `.score-bad`) so front-end can restyle without changing Python.
- Env-driven optional behaviour:
  - `LOAD_MODEL=1` loads `app/email_classifier_model.pkl` (path configured in `classifier.py`) to enable sklearn ML fallback.
  - AI API keys are read by `app/ai/client.py` from env vars (see `app/config.py` for defaults).

Dev/run/test workflows
- Local (fast edit-iterate): activate your venv and run Flask dev server from repo root `email-classifier-app`:

```powershell
& .\.venv\Scripts\Activate.ps1
flask run --host 127.0.0.1 --port 5000
```

- Run the app module directly (uses app factory):

```powershell
python -m app.main
```

- Tests: run pytest from repo root `email-classifier-app` (venv activated):

```powershell
pytest -q
```

- Docker: see `Dockerfile` and `docker-compose.yml` for containerized runs. There's a `Makefile` with convenience targets; inspect `Makefile` for `make build` / `make up`.

Debugging gotchas & tips
- Import path: many scripts expect working directory to be the repo root `email-classifier-app` so that `app` is importable. Run Python commands from that folder.
- When editing `_render_score_html`, avoid embedding colors or layout inline — use CSS classes in `app/static/css/styles.css`.
- The classifier sets `last_decision_reason` for debugging; tests and routes read it — keep its possible values consistent when changing logic.
- PDF extraction uses `PyPDF2.PdfReader` in `routes.py` — errors in environments without `PyPDF2` will cause routes reading PDFs to fail; ensure `requirements.txt` contains all needed packages for CI.

Cross-component integration points
- Routes -> NLP: `app/routes.py` imports `classify_text_html`, `classify_email`, `classify_text_with_confidence` and `get_last_decision_reason` from `app/nlp/classifier.py` — changes to these signatures break the web UI.
- Routes -> AI: `app/routes.py` calls `generate_response` from `app/ai/client.py` to generate suggested replies; AI client has its own cache and debug toggles.

Files to inspect when changing behavior
- `app/nlp/classifier.py` — scoring rules and hard filters
- `app/nlp/preprocess.py` — text normalization and signature removal
- `app/static/css/styles.css` + `app/templates/result.html` — visual presentation of classification fragments
- `app/ai/client.py` — LLM fallbacks, caching, and environment flags
- `tests/` — contains unit tests that validate classifier behavior; run them frequently when changing heuristics

Minimal examples (useful snippets)
- How to get a classification and HTML fragment in Python REPL:

```python
from app.nlp.classifier import classify_text_html
label, html = classify_text_html(open('sample_emails/productive_example.txt').read())
```

- How the HTML fragment should expose classes (example excerpt expected):

```html
<div class="score-panel">
  <div class="score-card"><h4>Produtivo</h4><div class="score-count">2</div></div>
  <div class="score-card"><h4>Improdutivo</h4><div class="score-count">0</div></div>
</div>
<ul class="score-list"><li class="score-details"><code>action_verb</code> <span class="score-good">+1</span></li></ul>
```

When to prefer heuristics vs ML/LLM
- Heuristics are primary; ML fallback is used only when confidence < `ml_threshold` and `LOAD_MODEL=1`.
- LLM (HF/Grok) is used by `generate_response` to craft suggested replies, not for label assignment unless explicitly wired in the routes.

If anything is unclear or you want the file to preserve a different tone/format, tell me what to change and I'll iterate the `.github/copilot-instructions.md` accordingly.
