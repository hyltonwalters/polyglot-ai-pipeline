import httpx
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


class FakeAsyncClient:
    def __init__(self, response=None, error=None, capture=None, **_kwargs):
        self.response = response
        self.error = error
        self.capture = capture

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json):
        if self.capture is not None:
            self.capture["url"] = url
            self.capture["json"] = json
        if self.error is not None:
            raise self.error
        return self.response


def test_home_renders_browser_demo():
    response = client.get("/")
    assert response.status_code == 200
    assert "Polyglot AI Integration Service" in response.text
    assert "FastAPI in front. Go under load." in response.text
    assert "Run sample request" in response.text
    assert "Bounded worker pool" in response.text
    assert "Live response" in response.text
    assert 'href="/docs"' in response.text


def test_health():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_validation_rejects_empty_batch():
    response = client.post("/api/v1/ingest", json={"products": []})
    assert response.status_code == 422


def test_validation_rejects_invalid_product_fields():
    response = client.post(
        "/api/v1/ingest",
        json={"products": [{"id": 0, "title": " ", "raw_description": " "}]},
    )
    assert response.status_code == 422


def test_validation_rejects_more_than_100_products():
    products = [
        {"id": i + 1, "title": f"Product {i + 1}", "raw_description": "Valid description"}
        for i in range(101)
    ]
    response = client.post("/api/v1/ingest", json={"products": products})
    assert response.status_code == 422


def test_ingest_forwards_validated_payload_and_returns_worker_response(monkeypatch):
    capture = {}
    request = httpx.Request("POST", main.WORKER_URL)
    worker_response = httpx.Response(
        200,
        request=request,
        json={
            "status": "completed",
            "processed": 1,
            "failed": 0,
            "results": [
                {
                    "product": {
                        "id": 101,
                        "title": "Trail Boots",
                        "raw_description": "Waterproof hiking boots",
                    },
                    "enrichment": {"category": "footwear", "summary": "Trail Boots: Waterproof hiking boots"},
                    "worker_id": 1,
                    "duration_ms": 1,
                }
            ],
            "processing_ms": 1,
        },
    )
    monkeypatch.setattr(
        main.httpx,
        "AsyncClient",
        lambda **kwargs: FakeAsyncClient(response=worker_response, capture=capture, **kwargs),
    )

    response = client.post(
        "/api/v1/ingest",
        json={
            "products": [
                {
                    "id": 101,
                    "title": "  Trail Boots  ",
                    "raw_description": "  Waterproof hiking boots  ",
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["processed"] == 1
    assert capture["url"] == main.WORKER_URL
    assert capture["json"] == {
        "products": [
            {
                "id": 101,
                "title": "Trail Boots",
                "raw_description": "Waterproof hiking boots",
            }
        ]
    }


def test_ingest_maps_worker_http_error_to_502(monkeypatch):
    request = httpx.Request("POST", main.WORKER_URL)
    worker_response = httpx.Response(400, request=request, json={"error": "bad payload"})
    monkeypatch.setattr(
        main.httpx,
        "AsyncClient",
        lambda **kwargs: FakeAsyncClient(response=worker_response, **kwargs),
    )

    response = client.post(
        "/api/v1/ingest",
        json={"products": [{"id": 1, "title": "Boot", "raw_description": "Leather boot"}]},
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "Worker service rejected the request"}


def test_ingest_maps_worker_connection_error_to_503(monkeypatch):
    request = httpx.Request("POST", main.WORKER_URL)
    error = httpx.ConnectError("connection failed", request=request)
    monkeypatch.setattr(
        main.httpx,
        "AsyncClient",
        lambda **kwargs: FakeAsyncClient(error=error, **kwargs),
    )

    response = client.post(
        "/api/v1/ingest",
        json={"products": [{"id": 1, "title": "Boot", "raw_description": "Leather boot"}]},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Worker service is unavailable"}
