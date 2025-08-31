import json
import os
from app.main import create_app


def test_llm_endpoint_forbidden_when_disabled(monkeypatch):
    os.environ.pop("APP_CONFIG", None)
    app = create_app()
    app.config["ENABLE_LLM"] = False
    app.config["ALLOW_UI_LLM_TOGGLE"] = False
    client = app.test_client()

    resp = client.post("/classify-llm", json={"text": "Please confirm the meeting"})
    assert resp.status_code == 403


def test_llm_endpoint_success_with_mocked_llm(monkeypatch):
    os.environ["APP_CONFIG"] = "testing"
    app = create_app()
    # enable LLM for this test
    app.config["ENABLE_LLM"] = True
    app.config["ALLOW_UI_LLM_TOGGLE"] = True

    # monkeypatch the generate_response symbol in app.routes where it's used
    import importlib
    routes_mod = importlib.import_module('app.routes')

    def fake_generate_response(category, text):
        return "Assistant reply: classified as Produtivo"

    monkeypatch.setattr(routes_mod, "generate_response", fake_generate_response, raising=False)

    client = app.test_client()
    resp = client.post("/classify-llm", json={"text": "Please confirm the meeting"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("llm_used") is True
    assert "Assistant reply" in data.get("llm_reply", "")


def test_llm_endpoint_bad_request_no_text(monkeypatch):
    os.environ["APP_CONFIG"] = "testing"
    app = create_app()
    app.config["ENABLE_LLM"] = True
    app.config["ALLOW_UI_LLM_TOGGLE"] = True

    import importlib
    routes_mod = importlib.import_module('app.routes')
    monkeypatch.setattr(routes_mod, "generate_response", lambda c, t: "x", raising=False)

    client = app.test_client()
    resp = client.post("/classify-llm", json={})
    assert resp.status_code == 400
