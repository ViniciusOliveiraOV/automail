import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env automatically so `flask run`
# picks them up without requiring the user to export them manually.
load_dotenv()
from typing import cast, MutableMapping, Any
from flask import Flask
from flask import send_from_directory
from app.routes import main as routes
from app.config import DevelopmentConfig, ProductionConfig, TestingConfig

def create_app():
    app = Flask(__name__)
    # load config by env var APP_CONFIG (development|production|testing)
    cfg = os.environ.get("APP_CONFIG", "development").lower()
    if cfg == "production":
        app.config.from_object(ProductionConfig)
    elif cfg == "testing":
        app.config.from_object(TestingConfig)
    else:
        app.config.from_object(DevelopmentConfig)
    # Ensure LLM-related flags reflect the current process environment at
    # startup. The config classes read os.environ at import time which can
    # be stale if the environment changes before create_app is called by
    # the Flask CLI. Overwrite here so setting $env:ENABLE_LLM = '1' just
    # before `flask run` takes effect.
    app.config['ENABLE_LLM'] = os.environ.get('ENABLE_LLM', '0') == '1'
    app.config['ALLOW_UI_LLM_TOGGLE'] = os.environ.get('ALLOW_UI_LLM_TOGGLE', '0') == '1'
    try:
        app.config['LLM_PROMPT_CONF_THRESHOLD'] = float(os.environ.get('LLM_PROMPT_CONF_THRESHOLD', app.config.get('LLM_PROMPT_CONF_THRESHOLD', 0.6)))
    except Exception:
        # keep existing value if conversion fails
        pass
    # logging
    # determine log level name from config (ensure it's a str for type checkers)
    # cast app.config to a typed mapping so .get overload resolves
    config: MutableMapping[str, Any] = cast(MutableMapping[str, Any], app.config)
    level_name = cast(str, config.get("LOG_LEVEL", "INFO"))
    # resolve to numeric level, default to logging.INFO if attribute not found
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level)
    app.logger.setLevel(level)

    # Register blueprints
    app.register_blueprint(routes)

    # Static assets (like tiled background) are served from app/static in production.
    return app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = create_app()
    # choose host via env; default to localhost for safety
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)