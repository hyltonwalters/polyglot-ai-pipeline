# Go worker build stage
FROM golang:1.23-alpine AS go-builder
WORKDIR /src
COPY go.mod ./
COPY ConcurrencyEngine ./ConcurrencyEngine
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/worker ./ConcurrencyEngine

# Python ingestion service
FROM python:3.12-slim AS ingestion
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN python -m pip install --disable-pip-version-check --no-cache-dir --retries 10 --timeout 60 -r requirements.txt
COPY IngestionService ./IngestionService
WORKDIR /app/IngestionService
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Go worker service
FROM alpine:3.21 AS worker
RUN addgroup -S app && adduser -S -G app app
COPY --from=go-builder /out/worker /usr/local/bin/worker
USER app
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/worker"]
