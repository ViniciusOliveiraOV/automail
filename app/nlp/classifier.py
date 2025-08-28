from typing import List, Union, Any, Tuple, Dict, Set
import os
import re
import logging
from typing import Set

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
import joblib  # type: ignore
import numpy as np
from scipy.sparse import spmatrix  # type: ignore

MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "email_classifier_model.pkl"))

PRODUCTIVE_KEYWORDS: Set[str] = {
    "ajuda", "erro", "falha", "suporte", "incidente", "urgente", "status", "documento", "arquivo",
    "anexo", "reembolso", "pendente", "consulta",
    "issue", "error", "fail", "failure", "support", "help", "urgent", "status", "attachment", "invoice",
    "please", "update", "request", "attached", "attach", "send", "provide"
}
UNPRODUCTIVE_KEYWORDS: Set[str] = {
    "feliz", "parabéns", "obrigado", "obrigada", "bom natal", "feliz natal", "boa sorte",
    "happy", "congratulations", "thanks", "thank", "cheers", "regards", "best wishes", "holiday", "holidays", "hi", "hello", "greetings", "best"
}

logger = logging.getLogger(__name__)
LAST_DECISION_REASON: str = ""

def get_last_decision_reason() -> str:
    """Return the last decision reason set by classify_text."""
    return LAST_DECISION_REASON

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

def _keyword_fallback(text: str) -> str:
    t = (text or "").lower()
    tokens = re.findall(r"\w+", t)
    # short / empty emails => improdutivo
    if len(tokens) == 0 or len(tokens) <= 2:
        return "Improdutivo"
    score_p = sum(1 for k in PRODUCTIVE_KEYWORDS if k in t)
    score_u = sum(1 for k in UNPRODUCTIVE_KEYWORDS if k in t)
    if score_u > score_p:
        return "Improdutivo"
    if score_p > score_u and score_p > 0:
        return "Produtivo"
    return "Improdutivo"

def _looks_spammy(text: str) -> bool:
    t = (text or "").lower()
    # obvious spam: many urls/emails
    if re.search(r"https?://|www\.|[@]\w+\.", t):
        return True
    # long repeated chars (aaaaa)
    if re.search(r"(.)\1{4,}", t):
        return True
    # high non-alphanumeric ratio
    if len(t) > 0:
        non_alnum = sum(1 for c in t if not c.isalnum() and not c.isspace())
        if non_alnum / max(1, len(t)) > 0.3:
            return True
    # too many very short tokens
    tokens = re.findall(r"\w+", t)
    if tokens:
        short_ratio = sum(1 for w in tokens if len(w) <= 2) / len(tokens)
        if short_ratio > 0.5:
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
    if garbled_ratio > 0.4 or (digit_tokens / max(1, len(tokens))) > 0.4:
        return True
    return False

def classify_text(text: str) -> str:
    """
    Try to use saved model only when LOAD_MODEL=1; otherwise use fallback.
    This function sets LAST_DECISION_REASON with a short explanation of the rule used.
    """
    global LAST_DECISION_REASON
    LAST_DECISION_REASON = ""
    if not text or not text.strip():
        LAST_DECISION_REASON = "empty_or_whitespace"
        logger.info("classification: Improdutivo (%s)", LAST_DECISION_REASON)
        return "Improdutivo"

    txt = text.lower()
    words = set(re.findall(r"\w+", txt))

    greetings: Set[str] = {"hello", "hi", "hey", "greetings", "dear"}
    holiday: Set[str] = {"happy", "holidays", "merry", "congratulations", "congrats"}
    thanks: Set[str] = {"thanks", "thank", "ty", "gracias"}
    productive_indicators: Set[str] = {
        "please", "update", "status", "issue", "support", "attach", "attached",
        "ticket", "error", "problem", "urgent", "help", "request", "send", "provide"
    }

    # short greeting / check-in
    if len(txt) < 60 and (words & greetings):
        LAST_DECISION_REASON = "short_greeting"
        logger.info("classification: Improdutivo (%s)", LAST_DECISION_REASON)
        return "Improdutivo"

    # holiday / thanks without indicators
    if (words & holiday) or (words & thanks):
        if not (words & productive_indicators) and "?" not in text:
            LAST_DECISION_REASON = "holiday_or_thanks_no_action"
            logger.info("classification: Improdutivo (%s)", LAST_DECISION_REASON)
            return "Improdutivo"

    # explicit productive indicators
    if (words & productive_indicators):
        LAST_DECISION_REASON = "found_productive_indicator"
        logger.info("classification: Produtivo (%s)", LAST_DECISION_REASON)
        return "Produtivo"

    # '?' rule (require enough meaningful tokens)
    if "?" in text:
        try:
            from app.nlp.preprocess import _get_stopwords
            stopset = _get_stopwords()
            tokens = re.findall(r"\w+", txt)
            meaningful = [w for w in tokens if w not in stopset]
        except Exception:
            meaningful = re.findall(r"\w+", txt)
        if len(meaningful) >= 3:
            LAST_DECISION_REASON = "question_with_enough_meaningful_tokens"
            logger.info("classification: Produtivo (%s)", LAST_DECISION_REASON)
            return "Produtivo"

    # spam/garbled checks and meaningful-token heuristic
    try:
        from app.nlp.preprocess import _get_stopwords
        stopset = _get_stopwords()
        tokens = re.findall(r"\w+", txt)
        meaningful = [w for w in tokens if w not in stopset]
    except Exception:
        meaningful = re.findall(r"\w+", txt)

    # local helpers referenced in other patches; if not present, assume not spammy/garbled
    spammy = False
    garbled = False
    try:
        spammy = _looks_spammy(txt)  # defined elsewhere in this module when applied
    except Exception:
        spammy = False
    try:
        garbled = _looks_garbled(txt)
    except Exception:
        garbled = False

    if len(meaningful) >= 3 and not spammy and not garbled:
        LAST_DECISION_REASON = "many_meaningful_tokens_no_spam_garbled"
        logger.info("classification: Produtivo (%s)", LAST_DECISION_REASON)
        return "Produtivo"

    # Only load persisted model if explicitly enabled
    if os.getenv("LOAD_MODEL", "0") == "1":
        try:
            if os.path.exists(MODEL_PATH):
                logger.info("Loading persisted model for classification")
                clf = EmailClassifier()
                clf.load_model(MODEL_PATH)
                pred = clf.classify(text)
                LAST_DECISION_REASON = "model_loaded"
                logger.info("classification: %s (%s)", pred, LAST_DECISION_REASON)
                return pred
        except Exception:
            logger.exception("Model load failed, falling back to keyword rules")
            LAST_DECISION_REASON = "model_load_failed"

    # final fallback using preprocess + keyword rules
    try:
        from app.nlp.preprocess import preprocess_text  # local import
        cleaned = preprocess_text(text)
    except Exception:
        cleaned = (text or "").lower()

    result = _keyword_fallback(cleaned)
    LAST_DECISION_REASON = f"keyword_fallback ({len(re.findall(r'\\w+', cleaned))} tokens)"
    logger.info("classification: %s (%s)", result, LAST_DECISION_REASON)
    return result

def classify_email(text: str) -> str:
    return classify_text(text)