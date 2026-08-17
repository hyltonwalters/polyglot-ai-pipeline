![Polyglot AI Pipeline banner](https://raw.githubusercontent.com/hyltonwalters/polyglot-ai-pipeline/main/docs/social-preview.png)

# Polyglot AI Integration Service

[![CI](https://github.com/hyltonwalters/polyglot-ai-pipeline/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/hyltonwalters/polyglot-ai-pipeline/actions/workflows/ci.yml?query=branch%3Amain)

A portfolio-grade backend system demonstrating a practical polyglot architecture: **Python/FastAPI** validates and accepts structured records, then delegates batch processing to a **Go worker pool**. Each Go worker can perform deterministic local enrichment or call an **OpenAI-compatible AI endpoint** concurrently.

The project is intentionally runnable without an API key. `AI_MODE=mock` is the default so the complete pipeline can be tested locally, in CI and in the public demo without external AI services.

## Live demo

- **Live application:** https://polyglot-ai-pipeline.onrender.com
- **Interactive API docs:** https://polyglot-ai-pipeline.onrender.com/docs
- **Health check:** https://polyglot-ai-pipeline.onrender.com/healthz
- **Source:** https://github.com/hyltonwalters/polyglot-ai-pipeline

The landing page includes a one-click sample request that exercises the complete public-demo path: **FastAPI → Go worker → deterministic mock enrichment**. The hosted demo intentionally uses mock AI mode so it requires no external API key or paid provider.

## Architecture

```text
Client
  |
  v
Python / FastAPI :8000
  |  validation + HTTP boundary
  v
Go Worker Pool :8080
  |  bounded concurrency
  +----> Mock enrichment (default)
  |
  +----> OpenAI-compatible /chat/completions (optional)
```

## What it demonstrates

- FastAPI request validation with Pydantic v2
- Service-to-service HTTP communication with explicit timeouts
- Go goroutines, channels and a bounded worker pool
- Context-based per-job deadlines
- Stable result ordering despite concurrent execution
- Provider abstraction with a no-network mock implementation
- Optional OpenAI-compatible AI integration
- Docker multi-stage builds and Docker Compose service separation
- Health endpoints, automated tests and GitHub Actions CI
- Basic request-size and batch-size protection
- End-to-end container integration testing without external AI dependencies
- Browser-accessible deployment using a dedicated single-container Render adapter while preserving the local two-service architecture

## Run locally

### Option A: Python + Go directly

```bash
# terminal 1
cd IngestionService
pip install -r ../requirements.txt
uvicorn main:app --reload --port 8000

# terminal 2
go run ./ConcurrencyEngine
```

For direct local execution, set `WORKER_URL=http://localhost:8080/v1/process-batch` before starting FastAPI.

### Option B: Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

The API is then available at `http://localhost:8000`.

## Configuration

The repository includes [`.env.example`](.env.example) with safe defaults for local development.

| Variable | Default | Purpose |
| --- | --- | --- |
| `AI_MODE` | `mock` | Selects deterministic local enrichment or `openai-compatible` mode |
| `AI_API_KEY` | empty | Provider credential; required only for real AI calls |
| `AI_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible API base URL |
| `AI_MODEL` | `gpt-4o-mini` | Model name passed to the provider |
| `MAX_WORKERS` | `4` | Bounded Go worker-pool size; values outside 1-32 fall back to 4 |
| `JOB_TIMEOUT_MS` | `5000` | Per-job deadline; invalid values fall back to 5000 ms |
| `PORT` | `8080` | Optional Go worker port when running it directly |
| `WORKER_URL` | `http://worker:8080/v1/process-batch` | FastAPI-to-worker endpoint; use localhost when running directly |

Do **not** commit secrets. Keep real provider keys in environment variables or a local `.env` file that remains ignored by Git.

## Test the pipeline

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H 'Content-Type: application/json' \
  -d '{
    "products": [
      {"id":101,"title":"Table Mountain Leather Boot","raw_description":"Handcrafted premium footwear."},
      {"id":102,"title":"Kruger Utility Jacket","raw_description":"Rugged double-stitched canvas jacket."},
      {"id":103,"title":"Karoo Merino Jersey","raw_description":"Technical wool knit."}
    ]
  }'
```

Expected response contains `processed: 3`, three ordered results, worker IDs and enrichment data.

Health checks:

```bash
curl http://localhost:8000/healthz
curl http://localhost:8080/healthz
```

## Enable a real AI provider

The worker supports an OpenAI-compatible chat-completions endpoint. The default is mock mode; no secret is required for the demo.

```bash
AI_MODE=openai-compatible \
AI_API_KEY=your-key \
AI_BASE_URL=https://api.openai.com/v1 \
AI_MODEL=gpt-4o-mini \
docker compose up --build
```

## Tests

Run the application-level test suites from the repository root:

```bash
python -m pytest -q IngestionService
go test -race -cover ./ConcurrencyEngine
```

The tests cover:

- FastAPI health and Pydantic request validation
- Browser-demo landing page availability
- Payload normalization before service-to-service forwarding
- Worker HTTP failure mapping (`502`) and availability failure mapping (`503`)
- Go worker result ordering and deterministic mock categorization
- Per-job deadline handling
- Worker HTTP handler validation and all-job failure behavior
- OpenAI-compatible provider request/response handling using a local mock HTTP server

## Continuous integration

`.github/workflows/ci.yml` runs automatically for pushes and pull requests targeting `main`.

The CI pipeline performs:

1. Python dependency installation and `pytest`
2. Go formatting validation, `go vet`, race-enabled tests and coverage
3. Docker Compose image builds plus the dedicated Render demo image build
4. A full containerized end-to-end test through FastAPI and the Go worker

The integration test uses `AI_MODE=mock`, making it deterministic and safe to run without secrets or network access to an AI provider.

## Further documentation

- [`docs/engineering-decisions.md`](docs/engineering-decisions.md) — architecture choices, trade-offs and current production-readiness limits
- [`docs/interview-walkthrough.md`](docs/interview-walkthrough.md) — concise technical walkthrough and interview discussion points
- [`docs/project-history.md`](docs/project-history.md) — retrospective project timeline and the distinction between early work and dated public Git activity

## Engineering decisions

The architecture intentionally separates the FastAPI HTTP boundary from the Go processing worker so the project can demonstrate service contracts, bounded concurrency, provider abstraction and explicit failure handling.

See [`docs/engineering-decisions.md`](docs/engineering-decisions.md) for the reasoning, trade-offs and current production-readiness limits.

## Project history

This project began in **January 2026** as part of independent backend engineering work focused on Python/FastAPI, Go concurrency and AI-enabled service integration. Early experimentation was not preserved as a complete public Git commit history; the public repository records the later consolidation, testing, CI and hardening work.

See [`docs/project-history.md`](docs/project-history.md) for the retrospective timeline and the distinction between early project work and dated public Git activity.

## Engineering notes

This project is a focused portfolio demonstration with a public demo deployment rather than a claim of enterprise-scale production use. The design emphasizes clear boundaries, failure handling, testability and explainable concurrency patterns that can be extended with persistent storage, authentication, observability and provider-specific adapters when required.
