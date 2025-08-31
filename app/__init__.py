from dotenv import load_dotenv
import os

# Load environment variables from .env so `flask run` picks them up.
load_dotenv()

from flask import Flask

app = Flask(__name__)

# Load configuration object based on APP_CONFIG and ensure LLM toggles
# reflect the actual environment at import time (useful for `flask run`).
try:
	from app.config import DevelopmentConfig, ProductionConfig, TestingConfig
	cfg = os.environ.get("APP_CONFIG", "development").lower()
	if cfg == "production":
		app.config.from_object(ProductionConfig)
	elif cfg == "testing":
		app.config.from_object(TestingConfig)
	else:
		app.config.from_object(DevelopmentConfig)
	# Overwrite LLM flags from the (loaded) environment to ensure CLI picks them up
	app.config['ENABLE_LLM'] = os.environ.get('ENABLE_LLM', '0') == '1'
	app.config['ALLOW_UI_LLM_TOGGLE'] = os.environ.get('ALLOW_UI_LLM_TOGGLE', '0') == '1'
except Exception:
	# If config import fails for any reason, continue with defaults.
	pass

# Ensure the package-level app registers the routes blueprint so running
# `flask run` against the package (FLASK_APP=app) exposes the endpoints.
try:
	from app.routes import main as routes
	app.register_blueprint(routes)
except Exception:
	# Import-time registration may fail in some tooling; fallback to lazy import
	pass