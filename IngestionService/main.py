import os
from typing import Annotated

import httpx
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, StringConstraints

app = FastAPI(title="Polyglot Ingestion Gateway", version="2.0.0")
WORKER_URL = os.getenv("WORKER_URL", "http://worker:8080/v1/process-batch")

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class ProductPayload(BaseModel):
    id: int = Field(gt=0, examples=[101])
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    raw_description: NonEmptyString


class BatchExtractionRequest(BaseModel):
    products: list[ProductPayload] = Field(min_length=1, max_length=100)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home() -> str:
    return """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Polyglot AI Integration Service</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
    body { margin: 0; background: #07111f; color: #e8eef7; }
    main { max-width: 960px; margin: 0 auto; padding: 64px 24px; }
    .eyebrow { color: #66d9ef; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
    h1 { font-size: clamp(2.4rem, 6vw, 4.6rem); line-height: 1; margin: 14px 0 20px; }
    .lead { max-width: 760px; color: #b9c6d8; font-size: 1.15rem; line-height: 1.7; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(210px,1fr)); gap: 16px; margin: 34px 0; }
    .card { background: #0c192a; border: 1px solid #20364f; border-radius: 14px; padding: 20px; }
    .card strong { display: block; margin-bottom: 8px; color: #fff; }
    .card span { color: #9fb0c5; line-height: 1.5; }
    .actions { display: flex; flex-wrap: wrap; gap: 12px; margin: 28px 0; }
    a, button { border-radius: 10px; padding: 12px 16px; font-weight: 700; text-decoration: none; cursor: pointer; }
    a.primary, button { color: #06111e; background: #66d9ef; border: 0; }
    a.secondary { color: #dbe8f8; border: 1px solid #365777; }
    pre { white-space: pre-wrap; background: #030a13; border: 1px solid #20364f; border-radius: 12px; padding: 18px; min-height: 96px; color: #b9fbc0; overflow: auto; }
    footer { color: #71859d; margin-top: 30px; font-size: .92rem; }
  </style>
</head>
<body>
<main>
  <div class=\"eyebrow\">Backend Engineering Demo</div>
  <h1>Polyglot AI Integration Service</h1>
  <p class=\"lead\">A Python/FastAPI ingestion gateway connected to a Go worker that demonstrates typed validation, bounded concurrency, stable result ordering, per-job deadlines, provider abstraction, Docker and automated testing.</p>

  <div class=\"grid\">
    <div class=\"card\"><strong>Python / FastAPI</strong><span>Validated HTTP ingestion using Pydantic and HTTPX.</span></div>
    <div class=\"card\"><strong>Go concurrency</strong><span>Bounded worker pool using goroutines and channels.</span></div>
    <div class=\"card\"><strong>Safe demo mode</strong><span>Deterministic mock enrichment; no external AI key required.</span></div>
    <div class=\"card\"><strong>Production practices</strong><span>Docker, tests, race detection, CI and end-to-end verification.</span></div>
  </div>

  <div class=\"actions\">
    <button id=\"run-demo\">Run sample request</button>
    <a class=\"secondary\" href=\"/docs\">Open API docs</a>
    <a class=\"secondary\" href=\"/healthz\">Health check</a>
    <a class=\"secondary\" href=\"https://github.com/hyltonwalters/polyglot-ai-pipeline\">View source</a>
  </div>

  <pre id=\"output\">Click “Run sample request” to exercise FastAPI → Go worker → mock enrichment.</pre>
  <footer>Portfolio demo. Free hosting may need a short cold start after inactivity.</footer>
</main>
<script>
  const output = document.getElementById('output');
  document.getElementById('run-demo').addEventListener('click', async () => {
    output.textContent = 'Running…';
    try {
      const response = await fetch('/api/v1/ingest', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({products: [
          {id: 101, title: 'Trail Boots', raw_description: 'Waterproof hiking boots'},
          {id: 102, title: 'Laptop', raw_description: 'Portable computer'},
          {id: 103, title: 'Jacket', raw_description: 'Lightweight outdoor jacket'}
        ]})
      });
      const data = await response.json();
      output.textContent = JSON.stringify(data, null, 2);
    } catch (error) {
      output.textContent = 'Demo request failed: ' + error;
    }
  });
</script>
</body>
</html>"""


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/ingest", status_code=status.HTTP_200_OK)
async def ingest(payload: BatchExtractionRequest):
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=2.0)) as client:
            response = await client.post(WORKER_URL, json=payload.model_dump())
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Worker service rejected the request") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Worker service is unavailable") from exc
