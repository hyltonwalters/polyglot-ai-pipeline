# Interview Walkthrough

Use this as a concise explanation of the system in a technical interview.

## 60-second overview

This project demonstrates a small polyglot backend architecture. A Python/FastAPI service owns the HTTP boundary and request validation. Validated batches are forwarded to a Go service that performs concurrent enrichment through a bounded worker pool. The Go service supports a deterministic mock provider by default and an optional OpenAI-compatible provider. The system is containerized with Docker Compose and covered by Python tests, Go tests, race detection, Docker builds, and an end-to-end CI integration test.

## Request flow

1. A client sends a batch of products to `POST /api/v1/ingest`.
2. FastAPI validates IDs, titles, descriptions, and batch size with Pydantic.
3. The ingestion service forwards the normalized payload to the Go worker service using HTTPX with explicit connect and request timeouts.
4. The Go service places jobs onto a channel and processes them with a bounded number of goroutines.
5. Each job receives its own context deadline.
6. The configured AI provider enriches the product.
7. Results are collected by original index so response ordering remains stable despite concurrent execution.
8. The FastAPI service returns the worker response to the client.

## Why FastAPI at the boundary?

FastAPI provides a concise API layer with strong schema validation through Pydantic, clear HTTP semantics, and async service-to-service communication. In this design it acts as the external contract boundary rather than carrying CPU- or concurrency-heavy processing logic.

## Why a Go worker service?

The Go service makes the concurrency model explicit. Goroutines and channels are used for bounded parallel processing, while the worker count prevents unbounded fan-out. The purpose is not that Go is inherently required for enrichment; it demonstrates a service boundary where workloads with different operational characteristics can be isolated behind a stable HTTP contract.

## Why bounded concurrency instead of one goroutine per product?

Unbounded goroutine creation can overwhelm downstream providers, sockets, memory, or rate limits as batch size grows. A fixed worker pool creates back-pressure and gives operators a simple concurrency control through `MAX_WORKERS`.

## How is result ordering preserved?

Jobs carry the input index. Workers can complete in any order, but the collector writes successful results into a pre-sized slice at their original indices. This separates execution order from response order.

## What happens when the Go service is unavailable?

The FastAPI layer distinguishes service availability failures from worker HTTP failures. Network/request errors map to `503 Service Unavailable`; worker HTTP rejection maps to `502 Bad Gateway`.

## What happens when AI enrichment times out?

Each Go job gets a context with `JOB_TIMEOUT_MS`. The provider request receives that context. If the deadline expires, the job returns an error rather than blocking the batch indefinitely.

## Why keep a deterministic mock AI provider?

The mock provider makes the complete architecture runnable without secrets or external network access. It makes tests and CI repeatable, avoids provider cost, and lets the service boundary and concurrency model be verified independently of a third-party API.

## Why use a provider abstraction?

`AIClient` separates orchestration from provider implementation. The worker pool only depends on an `Enrich` contract. That makes it possible to replace the mock or OpenAI-compatible implementation with another provider without rewriting the processing model.

## Why run `go test -race`?

Concurrency bugs can pass normal unit tests. The Go race detector adds runtime instrumentation to identify unsafe concurrent memory access, which is particularly relevant for a worker-pool demonstration.

## What does the integration test prove?

The integration test builds and starts the real Docker Compose services, waits for health, sends a request through FastAPI, and verifies the pipeline response. It checks service wiring, container networking, application startup, HTTP contracts, and end-to-end behavior in mock mode.

## What would change for production?

A production deployment would likely add authentication and authorization, structured logging, metrics and tracing, persistent storage or queues where durability is required, retry/backoff policies, provider rate-limit handling, secret management, stronger schema/version compatibility guarantees, deployment manifests, resource limits, and load/performance testing.

## Trade-offs

- HTTP between services is simple and inspectable, but introduces network overhead and partial-failure modes.
- A bounded in-process worker pool is appropriate for this demonstration, but a durable queue would be preferable for long-running or must-not-lose jobs.
- Stable ordering makes responses predictable, but retaining original positions means partial failures require a clear response contract.
- Mock mode improves deterministic testing, but does not model provider latency, rate limits, or content variability.

## Key files to discuss

- `IngestionService/main.py` — API boundary, validation, timeouts, upstream error mapping
- `ConcurrencyEngine/main.go` — configuration, provider abstraction, worker pool, ordering, deadlines, graceful shutdown
- `docker-compose.yml` — service topology and runtime configuration
- `.github/workflows/ci.yml` — automated quality gates and end-to-end integration test
- `docs/engineering-decisions.md` — architectural trade-offs
- `.env.example` — supported configuration
