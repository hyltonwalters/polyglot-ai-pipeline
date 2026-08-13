from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

def test_health():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_validation_rejects_empty_batch():
    response = client.post("/api/v1/ingest", json={"products": []})
    assert response.status_code == 422
