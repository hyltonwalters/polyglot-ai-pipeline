import os
import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List

app = FastAPI(title="Polyglot Ingestion Gateway", version="1.0.0")

class ProductPayload(BaseModel):
    id: int = Field(..., example=101)
    title: str = Field(..., max_length=255, example="Leather Boots")
    raw_description: str = Field(..., example="Handcrafted leather goods...")

class BatchExtractionRequest(BaseModel):
    products: List[ProductPayload]

GO_WORKER_POOL_URL = os.getenv("GO_WORKER_POOL_URL", "http://localhost:8080/v1/process-batch")

@app.post("/api/v1/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_legacy_records(payload: BatchExtractionRequest):
    if not payload.products:
        raise HTTPException(status_code=400, detail="Data payload cannot be empty")
        
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(GO_WORKER_POOL_URL, json=payload.model_dump())
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY, 
                    detail="Go infrastructure execution pool rejected data processing stream"
                )
            return {"status": "success", "processed_records": len(payload.products)}
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to communicate with underlying compilation thread mesh: {exc}"
            )
