from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


def test_message():
    resp = client.get("/api/message")
    assert resp.status_code == 200
    assert resp.json() == {"message": "Hello from FastAPI"}
