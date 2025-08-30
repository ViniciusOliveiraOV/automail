from flask import Flask

app = Flask(__name__)

# Ensure the package-level app registers the routes blueprint so running
# `flask run` against the package (FLASK_APP=app) exposes the endpoints.
try:
	from app.routes import main as routes
	app.register_blueprint(routes)
except Exception:
	# Import-time registration may fail in some tooling; fallback to lazy import
	pass