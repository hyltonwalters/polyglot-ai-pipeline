# Engineering Decisions

This document captures the main design choices in the Polyglot AI Integration Service and the trade-offs behind them.

## Python/FastAPI at the HTTP boundary

FastAPI owns the public ingestion endpoint because it provides concise request modelling, validation and asynchronous HTTP integration. Pydantic validation rejects malformed or oversized batches before work reaches the processing service.

The boundary is intentionally thin: validate input, forward a normalized payload, translate downstream failures, and return the worker response. Business processing stays out of the API layer.

## Go for bounded concurrent processing

The worker service uses Go to make concurrency explicit and easy to reason about. A fixed worker pool consumes jobs from a channel instead of starting an unbounded goroutine per product.

This provides a simple back-pressure mechanism and keeps concurrency bounded by `MAX_WORKERS`. The current demo allows 1-32 workers and falls back to 4 when configuration is outside that range.

## Stable ordering despite concurrent execution

Concurrent jobs can complete in any order, but callers should not need to reconstruct the original request ordering. Each job therefore carries its input index, and successful results are written back into that position before the response is returned.

## Per-job deadlines

Each enrichment call receives a context with a configurable timeout. This prevents one slow provider call from blocking a worker indefinitely. `JOB_TIMEOUT_MS` defaults to 5000 ms and is constrained to a reasonable range by configuration loading.

## Provider abstraction

The worker depends on a small `AIClient` interface instead of directly coupling batch processing to one provider. The default mock implementation is deterministic and makes local development, tests and CI independent of external credentials or network availability.

An OpenAI-compatible implementation is available for real provider calls. It is selected only when `AI_MODE=openai-compatible` and an API key is present.

## Failure handling

The FastAPI service distinguishes between a worker response error and worker unavailability, mapping those conditions to `502` and `503` respectively.

The Go service records per-product enrichment errors. If every product fails, the worker returns a bad-gateway response; partial successes retain the successful results plus error information.

## Why two services for a portfolio project?

A single service would be simpler to deploy. The split is deliberate because the project is meant to demonstrate service boundaries, HTTP contracts, bounded concurrency and polyglot integration rather than minimize component count.

For a small production workload, keeping the system in one runtime could be the better choice. The current architecture becomes more justifiable when processing has different scaling, runtime or operational characteristics from the public API layer.

## Current production-readiness limits

This repository intentionally stops short of claiming enterprise production readiness. A real production deployment would likely add authentication/authorization, persistent storage, structured observability, request correlation, metrics, tracing, retry policies, rate limiting, secrets management, deployment manifests, stronger provider-specific validation and load/performance testing.
