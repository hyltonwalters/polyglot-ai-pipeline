# Polyglot AI Integration Service 🚀

An enterprise-grade, concurrent backend data pipeline designed to solve data transformation bottlenecks at scale. This project demonstrates high-performance polyglot engineering, using a Python framework for strict schema parsing and a Go runtime to handle massive network I/O concurrency cleanly.

## 🏗️ Architectural Topology
```
[Legacy DB Client Nodes] 
          │ 
          │ (Bulk Unstructured Ingestion Payload)
          ▼
┌─────────────────────────────────┐
│  Python Ingestion Service       │ <-- FastAPI / Pydantic Data Safety Layer
└─────────────────────────────────┘
          │ 
          │ (Clean Validated Data Streams)
          ▼
┌─────────────────────────────────┐
│  Go Parallel Worker Pool        │ <-- Multi-threaded I/O (Goroutines/Channels)
└─────────────────────────────────┘
          │ 
          │ (Concurrent Batch Streams)
          ▼
[Secure Enterprise LLM Endpoint APIs]
```
## 🛠️ Tech Stack & Patterns
- **Ingestion Microservice:** Python 3.12, FastAPI, Pydantic v2, HTTPX.
- **Concurrency Microservice:** Go (Golang) 1.22, Native Net/HTTP, Multi-threading Workers.
- **Containerization & DevOps:** Multi-stage Docker Builds, Linux Alpine Security Hardening.
- **Engineering Patterns:** Shared Worker Pools, Thread Synchronization (Sync.WaitGroup), Buffered Channels, Context Deadlines.

## 📁 Source Implementation Directories

### 1. Python Ingestion Gateway (`IngestionService/main.py`)
Handles upstream connections safely. It applies rigorous typing metrics to filter out corrupted or missing data payloads before passing the stream down the deployment mesh.

### 2. Go Parallel Concurrency Engine (`ConcurrencyEngine/main.go`)
Leverages Go's native, lightweight threads (**Goroutines**) to distribute network execution loads concurrently, achieving significantly faster processing speeds than traditional, single-threaded architectures.

---

## 🚀 Rapid Deployment & Testing Guide

### Prerequisites
- Docker Engine installed locally.

### 1. Build and Run the Complete Infrastructure
Run the multi-stage container environment using your terminal:
```bash
docker build -t polyglot-ai-pipeline .
docker run -d -p 8000:8000 -p 8080:8080 --name pipeline-running polyglot-ai-pipeline
```

### 2. Run a Concurrent Bulk Load Test
Execute this `curl` script from your machine to pass mock e-commerce product structures into your local endpoints:
```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
-H "Content-Type: application/json" \
-d '{
  "products": [
    {"id": 101, "title": "Table Mountain Leather Boot", "raw_description": "Handcrafted premium footwear."},
    {"id": 102, "title": "Kruger Safari Utility Jacket", "raw_description": "Rugged double-stitched canvas canvas."},
    {"id": 103, "title": "Karoo Winter Merino Jersey", "raw_description": "100% organic local technical wool knit."}
  ]
}'
```

### 3. Review Concurrency Workload Logs
Inspect the internal thread tracking directly inside your runtime cluster logs:
```bash
docker logs pipeline-running
```
*Output verification will display individual threads executing jobs across multiple workers in parallel.*
