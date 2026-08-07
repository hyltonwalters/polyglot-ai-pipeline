# Stage 1: Build the Go binary securely
FROM golang:1.22-alpine AS go-builder
WORKDIR /build
COPY ConcurrencyEngine/main.go .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o go-pipeline main.go

# Stage 2: Create the final minimal runtime mesh
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic

COPY --from=go-builder /build/go-pipeline /usr/local/bin/go-pipeline
COPY IngestionService/main.py .

EXPOSE 8000 8080

CMD ["sh", "-c", "go-pipeline & uvicorn main:app --host 0.0.0.0 --port 8000"]
