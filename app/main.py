import os
import logging
import json
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
    # expose chosen config name at runtime
    app.config['APP_CONFIG'] = cfg
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
    # Import and register optional gmail blueprint at runtime so import-time
    # failures (missing optional deps) don't leave the app in a state where
    # templates that call url_for('gmail_auth.*') fail with BuildError.
    try:
        from app.gmail_auth import bp as gmail_bp
        app.register_blueprint(gmail_bp)
    except Exception:
        try:
            from app.routes.gmail_auth import bp as gmail_bp
            app.register_blueprint(gmail_bp)
        except Exception:
            app.logger.debug('gmail_auth blueprint not available; skipping')

    # if a persisted gmail token exists in the instance folder, load it into config
    try:
        # First prefer explicit env var (useful for CI or when you set it in .env)
        gmail_env = os.environ.get("GMAIL_TOKEN_JSON")
        if gmail_env:
            try:
                app.config["GMAIL_TOKEN_JSON"] = json.loads(gmail_env)
            except Exception:
                # if it's not valid JSON, store the raw string (some users store a file path)
                app.config["GMAIL_TOKEN_JSON"] = gmail_env
        else:
            inst_path = app.instance_path
            token_path = os.path.join(inst_path, "gmail_token.json")
            if os.path.exists(token_path):
                with open(token_path, "r", encoding="utf-8") as f:
                    app.config["GMAIL_TOKEN_JSON"] = json.load(f)
    except Exception:
        # ignore if instance path doesn't exist or token can't be read
        pass

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