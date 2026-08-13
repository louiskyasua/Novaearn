import importlib
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-long-enough")
os.environ.setdefault("DATABASE_PATH", ":memory:")


def test_app_imports():
    app_module = importlib.import_module("app")
    assert app_module.app is not None


def test_bank_api_exists():
    app_module = importlib.import_module("app")
    client = app_module.app.test_client()
    response = client.get("/api/banks")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert "banks" in payload
    assert isinstance(payload["banks"], list)
