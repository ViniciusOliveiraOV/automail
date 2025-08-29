import os

class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
    ENABLE_OCR = os.environ.get("ENABLE_OCR", "0") == "1"
    LOAD_MODEL = os.environ.get("LOAD_MODEL", "0") == "1"
    MODEL_PATH = os.environ.get("MODEL_PATH", "model.pkl")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))  # 5MB

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