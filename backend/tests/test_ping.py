import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.main import app  # type: ignore
from fastapi.testclient import TestClient

client = TestClient(app)

def test_ping() -> None:
    response = client.get('/ping')
    
    assert response.status_code == 200  # nosec
    assert response.json() == {"ping": "pong"}  # nosec
