import os

class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
    ENABLE_OCR = os.environ.get("ENABLE_OCR", "0") == "1"
    LOAD_MODEL = os.environ.get("LOAD_MODEL", "0") == "1"
    MODEL_PATH = os.environ.get("MODEL_PATH", "model.pkl")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))  # 5MB
    # HF/LLM configuration
    HF_API_URL = os.environ.get("HF_API_URL", "https://api-inference.huggingface.co/models")
    HF_DEFAULT_MODEL = os.environ.get("HF_MODEL", "google/flan-t5-large")
    HF_MODEL_CANDIDATES = os.environ.get("HF_MODEL_CANDIDATES", ",".join([HF_DEFAULT_MODEL, "facebook/bart-large-mnli", "google/flan-t5-large"]))
    # LLM toggles: server-wide enable and whether the UI toggle is allowed
    ENABLE_LLM = os.environ.get("ENABLE_LLM", "0") == "1"
    # allow the frontend to ask for per-request LLM calls (opt-in for safety)
    ALLOW_UI_LLM_TOGGLE = os.environ.get("ALLOW_UI_LLM_TOGGLE", "0") == "1"
    # confidence below which the UI will show the 'ask assistant' button
    LLM_PROMPT_CONF_THRESHOLD = float(os.environ.get("LLM_PROMPT_CONF_THRESHOLD", "0.6"))

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = False
    LOG_LEVEL = "DEBUG"

class TestingConfig(BaseConfig):
    DEBUG = False
    TESTING = True
    LOG_LEVEL = "WARNING"

class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False
    LOG_LEVEL = "INFO"