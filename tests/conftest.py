import os
import sys
import pytest
from typing import Generator

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.main import create_app
from flask import Flask
from flask.testing import FlaskClient
@pytest.fixture
def app() -> Generator[Flask, None, None]:
    app = create_app()
    app.config["TESTING"] = True
    yield app
    yield app

@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()