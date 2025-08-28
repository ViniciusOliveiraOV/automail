import os
import logging
from flask import Flask
from app.routes import main as routes

def create_app():
    app = Flask(__name__)
    # logging for flask-run (ensure visible when using `flask run`)
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app.logger.setLevel(logging.INFO)

    # Use env var em produção; fallback para um valor de desenvolvimento
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')

    # Register blueprints
    app.register_blueprint(routes)

    return app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = create_app()
    host = '0.0.0.0'
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    app.run(host=host, port=port, debug=debug)