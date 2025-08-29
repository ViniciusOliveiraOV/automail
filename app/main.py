import os
import logging
from typing import cast, MutableMapping, Any
from flask import Flask
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
    return app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = create_app()
    # choose host via env; default to localhost for safety
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)