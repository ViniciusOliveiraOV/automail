from typing import List, Union, Any, Tuple, Dict, Set
import os
import re
import logging
import unicodedata
from typing import Set
import html as _html  # novo import para escapar texto em HTML

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
import joblib  # type: ignore
import numpy as np
from scipy.sparse import spmatrix  # type: ignore

MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "email_classifier_model.pkl"))

# consolidated, language-agnostic keyword sets (EN + PT)
# (Removed duplicate definition of _COMBINED_PRODUCTIVE_KEYWORDS and _COMBINED_UNPRODUCTIVE_KEYWORDS)

logger = logging.getLogger(__name__)
last_decision_reason: str = ""

# Removed duplicate definition of get_last_decision_reason

# (Removed duplicate definition of EmailClassifier)

# (Removed duplicate definition of _normalize_for_matching)

# (Removed duplicate definition of _contains_any_keyword)

# (Removed duplicate definition of _keyword_fallback)

# (Removed duplicate definition of _looks_spammy)

# (Removed duplicate definition of _looks_garbled)


# add modular scoring rule sets / weights
# --- added: simple date/time patterns used by co-occurrence checks ---
# _DATE_PATTERNS and _DATE_RE already defined above; duplicate definition removed.

# consolidated, language-agnostic keyword sets (EN + PT)
_COMBINED_PRODUCTIVE_KEYWORDS: Set[str] = {
    # English
    "please", "update", "status", "issue", "support", "attach", "attached", "ticket",
    "error", "problem", "urgent", "help", "request", "send", "provide", "confirm",
    "review", "meeting", "agenda", "schedule", "call", "followup", "follow-up",
    "invoice", "payment", "refund", "deadline", "due", "reply", "respond",
    # Portuguese
    "por favor", "atualizar", "status", "issue", "suporte", "anexo", "anexar", "ticket",
    "erro", "problema", "urgente", "ajuda", "pedido", "enviar", "fornecer", "confirmar",
    "revisar", "reunião", "agenda", "agendar", "chamada", "prazo", "vencimento",
    "responder", "resposta", "certificado", "avaliacao", "avaliar", "matrículas", "anexo"
}

_COMBINED_UNPRODUCTIVE_KEYWORDS: Set[str] = {
    # English
    "happy", "holidays", "merry", "congratulations", "congrats", "thanks", "thank",
    "cheers", "regards", "best wishes", "hi", "hello", "greetings",
    # Portuguese
    "feliz", "parabéns", "obrigado", "obrigada", "boa sorte", "saudações", "atenciosamente",
    "abraços", "bom dia", "boa tarde", "boa noite"
}

logger = logging.getLogger(__name__)
last_decision_reason: str = ""

def get_last_decision_reason() -> str:
    """Return the last decision reason set by classify_text."""
    return last_decision_reason

class EmailClassifier:
    vectorizer: CountVectorizer
    classifier: MultinomialNB
    is_trained: bool

    def __init__(self) -> None:
        self.vectorizer = CountVectorizer()
        self.classifier = MultinomialNB()
        self.is_trained = False

    def train(self, emails: List[str], labels: List[str]) -> None:
        email_vectors: Union[np.ndarray, spmatrix] = self.vectorizer.fit_transform(emails)
        self.classifier.fit(email_vectors, labels)
        self.is_trained = True

    def classify(self, email: str) -> str:
        if not getattr(self, "is_trained", False):
            raise RuntimeError("Classifier is not trained yet.")
        email_vector: spmatrix = self.vectorizer.transform([email])
        prediction = self.classifier.predict(email_vector)
        return str(prediction[0])

    def save_model(self, model_path: str = MODEL_PATH) -> None:
        os.makedirs(os.path.dirname(model_path) or ".", exist_ok=True)
        joblib.dump((self.vectorizer, self.classifier), model_path)

    def load_model(self, model_path: str = MODEL_PATH) -> None:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        loaded = joblib.load(model_path)
        if isinstance(loaded, (tuple, list)) and len(loaded) >= 2:
            self.vectorizer, self.classifier = loaded[0], loaded[1]
        elif isinstance(loaded, dict):
            self.vectorizer = loaded.get("vectorizer", self.vectorizer)
            self.classifier = loaded.get("classifier", self.classifier)
        else:
            raise RuntimeError("Unknown model format in file.")
        self.is_trained = True

def _normalize_for_matching(s: str) -> str:
    """Lowercase + remove diacritics, collapse whitespace for robust keyword matching."""
    if not s:
        return ""
    s = str(s).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # replace non-word with spaces to make simple substring/token checks safer
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# (Removed unused function _contains_any_keyword)

def _keyword_fallback(text: str) -> str:
    t_norm = _normalize_for_matching(text or "")
    tokens = re.findall(r"\w+", t_norm)
    # short / empty emails => improdutivo
    if len(tokens) == 0 or len(tokens) <= 2:
        return "Improdutivo"
    score_p = 0
    score_u = 0
    # count productive keywords occurrences (phrase-aware)
    for k in _COMBINED_PRODUCTIVE_KEYWORDS:
        kk = _normalize_for_matching(k)
        if " " in kk:
            if kk in t_norm:
                score_p += 1
        else:
            score_p += tokens.count(kk)
    for k in _COMBINED_UNPRODUCTIVE_KEYWORDS:
        kk = _normalize_for_matching(k)
        if " " in kk:
            if kk in t_norm:
                score_u += 1
        else:
            score_u += tokens.count(kk)

    if score_u > score_p:
        return "Improdutivo"
    if score_p > score_u and score_p > 0:
        return "Produtivo"
    return "Improdutivo"

def _looks_spammy(text: str) -> bool:
    t = (text or "").lower()

    # recognize full urls/emails more robustly
    email_url_re = re.compile(r"(https?://\S+|www\.\S+|[\w.+-]+@[\w.-]+\.\w+)")
    matches = email_url_re.findall(t)

    # require multiple URLs/emails to consider it spammy (single sender address is normal)
    if len(matches) >= 2:
        return True

    # long repeated chars (aaaaa)
    if re.search(r"(.)\1{4,}", t):
        return True

    # Remove detected emails/urls before computing non-alphanumeric ratio
    t_no_links = email_url_re.sub(" ", t)
    # count non-alphanumeric chars (excluding common punctuation used in email bodies)
    allowed_punct = set(".,:;()-\"'<>@/\\\n\r\t")
    non_alnum = sum(1 for c in t_no_links if not c.isalnum() and c not in allowed_punct and not c.isspace())
    total_len = max(1, len(t_no_links))
    # make threshold more permissive for normal emails
    if non_alnum / total_len > 0.5:
        return True

    # too many very short tokens
    tokens = re.findall(r"\w+", t_no_links)
    if tokens:
        short_ratio = sum(1 for w in tokens if len(w) <= 2) / len(tokens)
        if short_ratio > 0.6:
            return True

    return False

def _looks_garbled(text: str) -> bool:
    """
    Return True if text looks garbled/non‑linguistic:
    - many tokens with very low vowel ratio
    - tokens containing long consonant clusters (likely gibberish)
    - too many tokens with digits/symbols
    """
    t = (text or "").lower()
    # skip garbled detection for reasonably long texts (likely human-written prose)
    if len(text or "") > 200:
        return False

    tokens = re.findall(r"[a-zA-Zçáéíóúâêîôûãõàèìòù]+", t)  # include common accented letters
    if not tokens:
        return True

    vowels = set("aeiouáéíóúâêîôûãõàèìòù")
    garbled_count = 0
    digit_tokens = 0
    consonant_cluster_re = re.compile(r"[bcdfghjklmnpqrstvwxyz]{4,}", re.IGNORECASE)

    for w in tokens:
        # digit/alpha mix
        if any(ch.isdigit() for ch in w):
            digit_tokens += 1

        # vowel ratio
        vowel_chars = sum(1 for ch in w if ch in vowels)
        vowel_ratio = vowel_chars / max(1, len(w))
        if vowel_ratio < 0.35:
            garbled_count += 1
            continue

        # long consonant clusters (e.g., "sdfghjk")
        if consonant_cluster_re.search(w) and len(w) >= 5:
            garbled_count += 1
            continue

    garbled_ratio = garbled_count / len(tokens)

    # If many tokens are garbled, or many tokens contain digits, consider garbled
    # Use more conservative thresholds to avoid false positives on normal text
    if garbled_ratio > 0.6 or (digit_tokens / max(1, len(tokens))) > 0.5:
        return True
    return False


def _looks_like_feed(text: str) -> bool:
    """
    Heuristic to detect feed/news-like content (multiple short article snippets,
    newsletter dumps, or social feed exports). These often contain markers like
    'Ler mais', 'Voto positivo', 'Comentar', 'Postado', 'Quora', 'Leia mais', etc.
    Return True when multiple such markers or repeated article blocks are present.
    """
    if not text:
        return False
    t = text.lower()
    markers = [
        "ler mais", "leia mais", "voto positivo", "votos", "comentar", "postado",
        "quora", "notícias", "noticias", "leia também", "ver mais", "ler mais »"
    ]
    # simple marker count
    marker_count = sum(t.count(m) for m in markers)
    if marker_count >= 2:
        return True

    # count per-line markers (many feed exports have repeated short blocks)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    perline = 0
    for ln in lines:
        ln_l = ln.lower()
        if any(m in ln_l for m in ("ler mais", "leia mais", "voto positivo", "comentar")):
            perline += 1
    if perline >= 2:
        return True

    # heuristic: many short headline-like lines (>3 lines, each shorter than 120 chars)
    short_lines = [ln for ln in lines if 0 < len(ln) <= 140]
    if len(short_lines) >= 6 and len(lines) / max(1, len(short_lines)) < 3:
        return True

    return False

def _contains_actionable_elements(text: str) -> bool:
    """
    Detect if the email contains elements that require user interaction:
    - urls (http/https/www)
    - instructions like 'clique', 'click here', 'botão', 'button'
    - explicit order words near links (e.g., 'clique no botão', 'acesse o link')
    Returns True when an actionable element is present.
    """
    if not text:
        return False
    t = text.lower()
    # urls
    if re.search(r"https?://\S+|www\.\S+", t):
        return True
    # email/payment/order patterns with 'click' / 'clique' / 'botão' nearby
    if re.search(r"\bclick here\b|\bclique aqui\b|\bclique no botão\b|\bbotão\b|\bacesse o link\b|\bconsulte o pedido\b", t):
        return True
    # short 'click' + 'order' context
    if "clique" in t or "click" in t or "botão" in t or "button" in t:
        # ensure these mentions are not in a purely feed-like context by checking for 'ler mais' nearby
        if not re.search(r"ler mais|leia mais|voto positivo|comentar", t):
            return True
    return False


KEYWORDS_PT = {
    "revisar", "confirmar", "prazo", "reunião", "avaliacao", "avaliar",
    "responder", "responda", "certificado", "matrículas", "minhas matrículas",
    "inscrição", "confirmacao", "confirma", "anexo", "verificar"
}

# add modular scoring rule sets / weights
ACTION_VERBS: Set[str] = {
    "atualiz", "atualize", "atualizem", "revisar", "revisem", "revisao", "revisão", "confirmar", "confirme",
    "confiram", "enviar", "envie", "enviem", "abrir", "abram", "corrigir", "corrija", "responder", "responda",
    "respondam", "agendar", "agende", "comparecer", "compareçam", "participar", "participem", "fornecer",
    "submeter", "aprovar", "aprovação", "aprovar", "atualizem", "atualizar", "atualize"
}

REQUEST_PATTERNS: Set[str] = {
    "por favor", "favor", "peço que", "peço", "preciso que", "por gentileza", "could you", "please", "would you",
    "can you", "pode", "poderia", "poderia por favor", "please update", "please confirm", "confirm please"
}

# --- added: simple date/time patterns used by co-occurrence checks ---
_DATE_PATTERNS = [
    r"\b\d{1,2}/\d{1,2}\b",        # 12/05
    r"\b\d{1,2}-\d{1,2}\b",        # 12-05
    r"\bamanh[ãa]\b",              # amanhã / amanha
    r"\bhoje\b", r"\bontem\b",
    r"\bsegund[oa]\b", r"\bterc[ea]\b", r"\bquarta\b", r"\bquinta\b", r"\bsexta\b",
    r"\bàs?\b", r"\b\d{1,2}h\b",    # às, 15h
    r"\bdia\s+\d{1,2}\b"
]
_DATE_RE = re.compile("|".join(_DATE_PATTERNS), flags=re.IGNORECASE)


def _score_text(text: str) -> Tuple[int, int, Dict[str, int]]:
    """Compute simple rule-based productivity and unproductivity scores.
    Returns (prod_score, imp_score, details) where details is a dict of contributing counts.
    """
    t_norm = _normalize_for_matching(text or "")
    tokens = re.findall(r"\w+", t_norm)
    prod_score = 0
    imp_score = 0
    details: Dict[str, int] = {}

    # action verbs (stem matching)
    action_count = 0
    for stem in ACTION_VERBS:
        cnt = sum(1 for tok in tokens if stem in tok)
        if cnt:
            action_count += cnt
    if action_count:
        prod_score += action_count
        details["action_verb"] = action_count

    # request patterns (phrase matches)
    # tighten detection: only count a request if it appears in a sentence
    # that also contains an action-verb stem or an explicit interrogative marker ("?")
    req_count = 0
    # split into coarse sentences to avoid counting unrelated occurrences in feeds
    sentences = re.split(r"[\n\.!?]+", text or "")
    for p in REQUEST_PATTERNS:
        p_norm = _normalize_for_matching(p)
        for sent in sentences:
            s_norm = _normalize_for_matching(sent)
            if not s_norm:
                continue
            if p_norm in s_norm:
                # check for action verb presence in sentence
                has_action = any(stem in s_norm for stem in ACTION_VERBS)
                # or interrogative / polite marker
                if '?' in sent or has_action:
                    req_count += 1
    if req_count:
        prod_score += req_count
        details["request_pattern"] = req_count

    # productive/unproductive keyword counts
    prod_kw = 0
    imp_kw = 0
    for k in _COMBINED_PRODUCTIVE_KEYWORDS:
        kk = _normalize_for_matching(k)
        if not kk:
            continue
        if " " in kk:
            if kk in t_norm:
                prod_kw += 1
        else:
            prod_kw += tokens.count(kk)
    for k in _COMBINED_UNPRODUCTIVE_KEYWORDS:
        kk = _normalize_for_matching(k)
        if not kk:
            continue
        if " " in kk:
            if kk in t_norm:
                imp_kw += 1
        else:
            imp_kw += tokens.count(kk)
    if prod_kw:
        prod_score += prod_kw
        details["work_context"] = prod_kw
    if imp_kw:
        imp_score += imp_kw
        details["unproductive_keyword"] = imp_kw

    # co-occurrence boost: action/request with date/time mentions
    if (action_count or req_count or prod_kw) and _DATE_RE.search(t_norm):
        details["cooccurrence_boost"] = details.get("cooccurrence_boost", 0) + 2
        prod_score += 2

    # short messages bias towards improdutivo
    if len(tokens) <= 3:
        imp_score += 1
        details["short_message"] = details.get("short_message", 0) + 1

    return prod_score, imp_score, details


def _apply_overrides(prod_score: int, imp_score: int, details: Dict[str, int], text: str) -> Tuple[str, str]:
    """Decide final label based on scores and simple overrides.
    Returns (decision_label, reason_key).
    """
    # if no signals, fall back to keyword heuristic
    if (not details or (prod_score == 0 and imp_score == 0)):
        fb = _keyword_fallback(text)
        return fb, "no_score_fallback"

    # clear major majority
    # interaction detection: if the email contains actionable elements (links, buttons,
    # explicit 'clique' instructions or 'click here') treat as Produtivo since it
    # requires user interaction. This replaces the prior feed-like override which
    # was marking many legitimate transactional/actionable emails as improdutivo.
    try:
        if _contains_actionable_elements(text):
            return "Produtivo", "contains_action"
    except Exception:
        logger.debug("actionable element detection failed")

    if prod_score >= imp_score + 2:
        return "Produtivo", "score_majority"
    if imp_score >= prod_score + 2:
        return "Improdutivo", "score_majority"

    # tie or close: prefer productive if it has action/request/context signals
    if prod_score > imp_score:
        return "Produtivo", "score_close_prod"
    if imp_score > prod_score:
        return "Improdutivo", "score_close_imp"

    # exact tie: use keyword fallback
    fb = _keyword_fallback(text)
    return fb, "tie_fallback"


# -- confidence / ML fallback support --
_ml_clf = None

def _load_ml_model_if_requested():
    """Lazily load a saved sklearn model if environment requests it. Safe no-op otherwise."""
    global _ml_clf
    try:
        if _ml_clf is not None:
            return
        if os.environ.get("LOAD_MODEL", "0") != "1":
            return
        if not os.path.exists(MODEL_PATH):
            logger.info("ML model requested but MODEL_PATH not found: %s", MODEL_PATH)
            return
        clf = EmailClassifier()
        clf.load_model(MODEL_PATH)
        _ml_clf = clf
        logger.info("Loaded ML model from %s", MODEL_PATH)
    except Exception:
        logger.exception("failed loading ML model; proceeding without it")

def _try_ml_classify(text: str) -> Union[str, None]:
    """Return ML label or None if unavailable/error."""
    _load_ml_model_if_requested()
    if _ml_clf is None:
        return None
    try:
        return _ml_clf.classify(text)
    except Exception:
        logger.exception("ml classify failed")
        return None

def _compute_confidence(prod_score: int, imp_score: int, details: Dict[str, int]) -> float:
    """Compute a heuristic confidence in [0.0, 1.0] from scores/details.
    - large difference => higher confidence
    - presence of action/request/work_context increases confidence
    - no signals => low confidence
    """
    total = prod_score + imp_score
    if total <= 0:
        return 0.15
    base = abs(prod_score - imp_score) / float(total)
    # boost for strong signals
    boost = 0.0
    if details.get("action_verb"):
        boost += 0.15
    if details.get("request_pattern"):
        boost += 0.15
    if details.get("work_context"):
        boost += 0.1
    if details.get("cooccurrence_boost"):
        boost += 0.1
    conf = min(1.0, base + boost)
    # clamp low-confidence cases a bit higher if base is tiny but boost exists
    return round(conf, 3)

def classify_text_with_confidence(text: str, ml_threshold: float = 0.45) -> Tuple[str, float, bool]:
    """Return (decision_label, confidence, used_ml_flag).
    If confidence < ml_threshold and an ML model is available, use ML as a fallback.
    If ML not available and confidence low, returns heuristic decision with low confidence and needs_review True.
    """
    global last_decision_reason
    last_decision_reason = ""

    if not text or not text.strip():
        last_decision_reason = "empty_or_whitespace"
        return "Improdutivo", 0.0, False

    # hard filters
    try:
        if _looks_spammy(text) or _looks_garbled(text):
            last_decision_reason = "hard_filter_spam_or_garbled"
            return "Improdutivo", 1.0, False
    except Exception:
        logger.exception("error in hard filters; proceeding to scoring")

    try:
        prod_score, imp_score, details = _score_text(text)
        decision, reason = _apply_overrides(prod_score, imp_score, details, text)
        conf = _compute_confidence(prod_score, imp_score, details)
        last_decision_reason = reason

        used_ml = False
        if conf < ml_threshold:
            # low confidence: try ML fallback if available
            ml_label = _try_ml_classify(text)
            if ml_label:
                decision = ml_label
                last_decision_reason = "ml_fallback"
                conf = max(conf, 0.75)
                used_ml = True
            else:
                # mark for human review (routes can use this)
                last_decision_reason = "needs_human_review"

        return decision, conf, used_ml
    except Exception:
        logger.exception("error in scoring engine; falling back to keyword heuristic")
        fallback = _keyword_fallback(text)
        last_decision_reason = "keyword_fallback"
        return fallback, 0.25, False


def classify_text(text: str) -> str:
    """
    Main public classifier used by the app/tests.
    Layers:
      - hard filters (spam/garbled) -> always Improdutivo
      - scoring engine (_score_text + _apply_overrides) -> decision
      - fallback -> _keyword_fallback
    Sets last_decision_reason for debugging.
    """
    global last_decision_reason
    last_decision_reason = ""

    if not text or not text.strip():
        last_decision_reason = "empty_or_whitespace"
        logger.info("classification: Improdutivo (%s)", last_decision_reason)
        return "Improdutivo"

    # Hard filters
    try:
        if _looks_spammy(text) or _looks_garbled(text):
            last_decision_reason = "hard_filter_spam_or_garbled"
            logger.info("classification: Improdutivo (%s)", last_decision_reason)
            return "Improdutivo"
    except Exception:
        # on error, proceed to scoring/fallback
        logger.exception("error in hard filters; proceeding to scoring")

    # Scoring engine (preferred)
    try:
        prod_score, imp_score, details = _score_text(text)  # type: ignore
        decision: str
        reason: str
        result: Any = _apply_overrides(prod_score, imp_score, details, text)
        decision: str
        reason: str
        if isinstance(result, tuple) and len(result) == 2:
            decision, reason = result
        else:
            decision, reason = "Improdutivo", "override_error"
        last_decision_reason = reason
        logger.info("scoring details: prod=%d imp=%d details=%s", prod_score, imp_score, details)
        logger.info("classification: %s (%s)", decision, last_decision_reason)
        # ensure returned value is one of expected labels
        if decision in ("Produtivo", "Improdutivo"):
            return decision
    except NameError:
        # scoring helpers not defined — fall back
        logger.debug("scoring engine not available; using keyword fallback")
    except Exception:
        logger.exception("error in scoring engine; falling back to keyword heuristic")

    # Final fallback: keyword heuristic
    try:
        fallback = _keyword_fallback(text)
        # compute token count outside any f-string to avoid backslash-in-expression issues
        token_count = len(re.findall(r"\w+", (text or "")))
        last_decision_reason = f"keyword_fallback ({token_count} tokens)"
        logger.info("classification: %s (%s)", fallback, last_decision_reason)
        return fallback
    except Exception:
        logger.exception("fatal error in fallback; returning Improdutivo by default")
        last_decision_reason = "fatal_error"
        return "Improdutivo"


def classify_email(text: str) -> str:
    """Alias kept for backwards compatibility with tests/routes."""
    return classify_text(text)

def _render_score_html(prod_score: int, imp_score: int, details: Dict[str,int], reason: str | None = None) -> str:
        detail_items: list[str] = []
        for k, v in (details or {}).items():
                if v <= 0:
                        continue
                key_escaped = _html.escape(k)
                if k in ("action_verb", "request_pattern", "work_context", "cooccurrence_boost"):
                        detail_items.append(f"<li class=\"score-details\"><code>{key_escaped}</code> <span class=\"score-good\">+{v}</span></li>")
                else:
                        detail_items.append(f"<li class=\"score-details\"><code>{key_escaped}</code> <span class=\"score-bad\">+{v}</span></li>")

        details_html = "<ul class=\"score-list\">" + "".join(detail_items) + "</ul>" if detail_items else ""

        reason_html = f'<div class="score-details">reason: {_html.escape(str(reason or ""))}</div>'

        # semantic structure: two small score cards followed by details and reason
        html = f"""
        <div class="score-render">
            <div class="score-panel" role="group" aria-label="Pontuação">
                <div class="score-card">
                    <h4>Produtivo</h4>
                    <div class="score-count">{prod_score}</div>
                </div>
                <div class="score-card">
                    <h4>Improdutivo</h4>
                    <div class="score-count">{imp_score}</div>
                </div>
            </div>
            {details_html}
            {reason_html}
        </div>
        """
        return html

def classify_text_html(text: str) -> Tuple[str, str, Dict[str, int]]:
    """
    Run scoring and return (decision, html_fragment).
    Does not change existing classify_text behavior.
    """
    try:
        prod_score, imp_score, details = _score_text(text)
        decision, reason = _apply_overrides(prod_score, imp_score, details, text)
    except Exception:
        # fallback: safe degrade to keyword_fallback and empty details
        decision = _keyword_fallback(text)
        prod_score = 0
        imp_score = 0
        details = {}
        reason = "fallback_html"

    html = _render_score_html(prod_score, imp_score, details, reason)
    return decision, html, details

def classify_email_html(text: str) -> Tuple[str, str, Dict[str, int]]:
    """Alias for web UI to get (decision, html, details)."""
    return classify_text_html(text)