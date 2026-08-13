import os
from typing import Annotated

import httpx
from fastapi import FastAPI, HTTPException, status
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
