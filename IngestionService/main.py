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
  <meta name=\"description\" content=\"Interactive portfolio demo of a Python/FastAPI ingestion gateway and bounded-concurrency Go worker.\">
  <title>Polyglot AI Integration Service</title>
  <style>
    * { box-sizing: border-box; }
    :root {
      color-scheme: dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif;
      --bg: #07111f;
      --panel: #0c192a;
      --panel-2: #101f33;
      --border: #20364f;
      --text: #edf4ff;
      --muted: #9fb0c5;
      --accent: #66d9ef;
      --accent-2: #8b9dff;
      --success: #72e6a1;
      --danger: #ff8b8b;
    }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at 15% -10%, rgba(102,217,239,.14), transparent 28%),
        radial-gradient(circle at 90% 5%, rgba(139,157,255,.12), transparent 25%),
        var(--bg);
      color: var(--text);
    }
    a { color: inherit; }
    main { max-width: 1120px; margin: 0 auto; padding: 34px 24px 72px; }
    nav { display:flex; align-items:center; justify-content:space-between; gap:18px; margin-bottom:64px; }
    .brand { font-weight:800; letter-spacing:-.02em; }
    .nav-links { display:flex; gap:10px; flex-wrap:wrap; }
    .nav-links a { color:var(--muted); text-decoration:none; font-size:.92rem; }
    .nav-links a:hover { color:var(--text); }
    .hero { display:grid; grid-template-columns: 1.35fr .65fr; gap:32px; align-items:end; }
    .eyebrow { color: var(--accent); font-weight: 800; letter-spacing: .11em; text-transform: uppercase; font-size:.78rem; }
    h1 { font-size: clamp(2.7rem, 7vw, 5.6rem); line-height: .95; letter-spacing:-.055em; margin: 14px 0 22px; max-width:900px; }
    .lead { max-width: 760px; color: #b9c6d8; font-size: 1.15rem; line-height: 1.75; margin:0; }
    .status-card { background:rgba(12,25,42,.76); border:1px solid var(--border); border-radius:18px; padding:22px; backdrop-filter:blur(8px); }
    .status-line { display:flex; align-items:center; gap:10px; font-weight:800; }
    .dot { width:9px; height:9px; border-radius:50%; background:var(--success); box-shadow:0 0 16px rgba(114,230,161,.8); }
    .status-card p { color:var(--muted); line-height:1.55; margin:10px 0 0; font-size:.94rem; }
    .actions { display:flex; flex-wrap:wrap; gap:12px; margin:30px 0 0; }
    button, .btn { border-radius:11px; padding:12px 17px; font-weight:800; text-decoration:none; cursor:pointer; font:inherit; }
    button, .btn.primary { color:#06111e; background:var(--accent); border:0; }
    button:hover, .btn.primary:hover { filter:brightness(1.06); }
    .btn.secondary { color:#dbe8f8; border:1px solid #365777; background:transparent; }
    section { margin-top:70px; }
    .section-kicker { color:var(--accent); font-size:.76rem; font-weight:800; text-transform:uppercase; letter-spacing:.1em; }
    h2 { font-size:clamp(1.8rem, 4vw, 2.7rem); letter-spacing:-.035em; margin:9px 0 12px; }
    .section-copy { color:var(--muted); line-height:1.65; max-width:740px; }
    .pipeline { display:grid; grid-template-columns:repeat(7,1fr); gap:10px; align-items:center; margin-top:28px; }
    .node { grid-column:span 1; min-height:132px; background:linear-gradient(180deg,var(--panel-2),var(--panel)); border:1px solid var(--border); border-radius:16px; padding:18px; display:flex; flex-direction:column; justify-content:space-between; }
    .node.wide { grid-column:span 2; }
    .node small { color:var(--accent); text-transform:uppercase; letter-spacing:.08em; font-weight:800; }
    .node strong { font-size:1.02rem; }
    .node span { color:var(--muted); font-size:.9rem; line-height:1.45; }
    .arrow { text-align:center; color:#5d7694; font-size:1.4rem; }
    .demo-shell { display:grid; grid-template-columns:.9fr 1.1fr; gap:18px; margin-top:28px; }
    .panel { background:rgba(12,25,42,.88); border:1px solid var(--border); border-radius:18px; padding:22px; }
    .panel-head { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:18px; }
    .panel-head strong { font-size:1.05rem; }
    .badge { border:1px solid #2d526d; border-radius:999px; padding:5px 9px; color:var(--accent); font-size:.72rem; font-weight:800; letter-spacing:.05em; text-transform:uppercase; }
    .sample-list { display:grid; gap:10px; }
    .sample { border:1px solid #1b334d; background:#091524; border-radius:13px; padding:14px; }
    .sample-top { display:flex; justify-content:space-between; gap:12px; margin-bottom:5px; }
    .sample-id { color:#6e849c; font-size:.8rem; }
    .sample p { margin:0; color:var(--muted); font-size:.9rem; line-height:1.5; }
    .run-row { margin-top:16px; display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
    .hint { color:#71859d; font-size:.82rem; }
    .metrics { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-bottom:14px; }
    .metric { border:1px solid #1b334d; background:#091524; border-radius:13px; padding:13px; }
    .metric span { display:block; color:#7e93aa; font-size:.74rem; text-transform:uppercase; letter-spacing:.07em; font-weight:800; }
    .metric strong { display:block; margin-top:5px; font-size:1.35rem; }
    #result-cards { display:grid; gap:10px; }
    .result { border:1px solid #1b334d; background:#091524; border-radius:13px; padding:14px; }
    .result-head { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; }
    .result h3 { margin:0; font-size:1rem; }
    .category { color:#06111e; background:var(--success); border-radius:999px; padding:4px 9px; font-size:.72rem; font-weight:900; text-transform:uppercase; }
    .result p { color:var(--muted); margin:9px 0 0; line-height:1.5; font-size:.9rem; }
    .meta { display:flex; gap:14px; flex-wrap:wrap; margin-top:11px; color:#748aa2; font-size:.78rem; }
    .empty { color:#73879e; border:1px dashed #29435e; border-radius:13px; padding:26px 18px; text-align:center; line-height:1.55; }
    .error { color:var(--danger); }
    details { margin-top:12px; }
    summary { color:#8fa5bd; cursor:pointer; font-size:.84rem; }
    pre { white-space:pre-wrap; word-break:break-word; background:#030a13; border:1px solid #1b334d; border-radius:12px; padding:14px; color:#b9fbc0; overflow:auto; font-size:.82rem; max-height:320px; }
    .signals { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-top:28px; }
    .signal { background:var(--panel); border:1px solid var(--border); border-radius:15px; padding:18px; }
    .signal strong { display:block; margin-bottom:8px; }
    .signal span { color:var(--muted); line-height:1.5; font-size:.9rem; }
    footer { color:#71859d; margin-top:72px; border-top:1px solid #172b42; padding-top:22px; font-size:.88rem; display:flex; justify-content:space-between; gap:16px; flex-wrap:wrap; }
    @media (max-width:900px) {
      .hero, .demo-shell { grid-template-columns:1fr; }
      .pipeline { grid-template-columns:1fr; }
      .node, .node.wide { grid-column:span 1; min-height:auto; }
      .arrow { transform:rotate(90deg); }
      .signals { grid-template-columns:repeat(2,1fr); }
    }
    @media (max-width:560px) {
      main { padding:24px 16px 52px; }
      nav { margin-bottom:44px; }
      .nav-links { display:none; }
      .metrics, .signals { grid-template-columns:1fr; }
      h1 { font-size:3rem; }
    }
  </style>
</head>
<body>
<main>
  <nav>
    <div class=\"brand\">Polyglot AI Integration Service</div>
    <div class=\"nav-links\">
      <a href=\"#architecture\">Architecture</a>
      <a href=\"#demo\">Live demo</a>
      <a href=\"/docs\">API docs</a>
      <a href=\"https://github.com/hyltonwalters/polyglot-ai-pipeline\">GitHub</a>
    </div>
  </nav>

  <div class=\"hero\">
    <div>
      <div class=\"eyebrow\">Backend Engineering Portfolio Demo</div>
      <h1>FastAPI in front. Go under load.</h1>
      <p class=\"lead\">A browser-accessible demonstration of typed API validation, service-to-service communication, bounded concurrency, deterministic AI-style enrichment and production-oriented testing.</p>
      <div class=\"actions\">
        <a class=\"btn primary\" href=\"#demo\">Try the live pipeline</a>
        <a class=\"btn secondary\" href=\"/docs\">Open Swagger docs</a>
        <a class=\"btn secondary\" href=\"https://github.com/hyltonwalters/polyglot-ai-pipeline\">View source</a>
      </div>
    </div>
    <div class=\"status-card\">
      <div class=\"status-line\"><span class=\"dot\"></span> Live demo online</div>
      <p><strong>Mock AI mode</strong> is enabled for the hosted demo, making results deterministic and keeping the public environment free of paid API credentials.</p>
    </div>
  </div>

  <section id=\"architecture\">
    <div class=\"section-kicker\">Architecture</div>
    <h2>One request, two runtimes, bounded work.</h2>
    <p class=\"section-copy\">The public request enters through FastAPI, is validated with Pydantic, then crosses an explicit HTTP service boundary into a Go worker pool before enrichment results are returned in stable input order.</p>
    <div class=\"pipeline\">
      <div class=\"node\"><small>01</small><strong>Browser / API client</strong><span>JSON batch request</span></div>
      <div class=\"arrow\">→</div>
      <div class=\"node wide\"><small>02 · Python</small><strong>FastAPI gateway</strong><span>Pydantic validation · HTTPX · timeout/error mapping</span></div>
      <div class=\"arrow\">→</div>
      <div class=\"node wide\"><small>03 · Go</small><strong>Bounded worker pool</strong><span>Goroutines · channels · per-job deadlines · ordered results</span></div>
      <div class=\"arrow\">→</div>
      <div class=\"node\"><small>04</small><strong>Enrichment provider</strong><span>Deterministic mock or OpenAI-compatible adapter</span></div>
    </div>
  </section>

  <section id=\"demo\">
    <div class=\"section-kicker\">Interactive demo</div>
    <h2>Run the pipeline in the browser.</h2>
    <p class=\"section-copy\">This sends three products through the real hosted FastAPI endpoint and internal Go worker. The response below is rendered from the live API result, not hard-coded UI data.</p>

    <div class=\"demo-shell\">
      <div class=\"panel\">
        <div class=\"panel-head\"><strong>Request batch</strong><span class=\"badge\">3 products</span></div>
        <div class=\"sample-list\">
          <div class=\"sample\"><div class=\"sample-top\"><strong>Trail Boots</strong><span class=\"sample-id\">#101</span></div><p>Waterproof hiking boots for rough terrain.</p></div>
          <div class=\"sample\"><div class=\"sample-top\"><strong>Laptop</strong><span class=\"sample-id\">#102</span></div><p>Portable computer for software development.</p></div>
          <div class=\"sample\"><div class=\"sample-top\"><strong>Jacket</strong><span class=\"sample-id\">#103</span></div><p>Lightweight outdoor jacket for changing weather.</p></div>
        </div>
        <div class=\"run-row\">
          <button id=\"run-demo\">Run sample request</button>
          <span class=\"hint\">FastAPI → Go → mock enrichment</span>
        </div>
      </div>

      <div class=\"panel\">
        <div class=\"panel-head\"><strong>Live response</strong><span id=\"response-status\" class=\"badge\">Ready</span></div>
        <div class=\"metrics\">
          <div class=\"metric\"><span>Processed</span><strong id=\"processed\">—</strong></div>
          <div class=\"metric\"><span>Failed</span><strong id=\"failed\">—</strong></div>
          <div class=\"metric\"><span>Processing</span><strong id=\"processing\">—</strong></div>
        </div>
        <div id=\"result-cards\"><div class=\"empty\">Click <strong>Run sample request</strong> to exercise the live backend and render the worker results here.</div></div>
        <details id=\"raw-wrap\" hidden>
          <summary>View raw JSON response</summary>
          <pre id=\"raw-output\"></pre>
        </details>
      </div>
    </div>
  </section>

  <section>
    <div class=\"section-kicker\">Engineering signals</div>
    <h2>What this project is meant to demonstrate.</h2>
    <div class=\"signals\">
      <div class=\"signal\"><strong>Typed API boundary</strong><span>FastAPI and Pydantic normalize and reject invalid requests before downstream work begins.</span></div>
      <div class=\"signal\"><strong>Explicit failure handling</strong><span>Connection and worker failures are mapped to deliberate 503 and 502 responses.</span></div>
      <div class=\"signal\"><strong>Concurrency with limits</strong><span>The Go service uses a bounded worker pool rather than unbounded goroutine creation.</span></div>
      <div class=\"signal\"><strong>Verification</strong><span>Python tests, Go vet/race tests, Docker builds and containerized end-to-end CI protect the architecture.</span></div>
    </div>
  </section>

  <footer>
    <span>Portfolio demonstration · Python 3.12 · FastAPI · Go · Docker · GitHub Actions</span>
    <span>Free hosting may cold-start after inactivity.</span>
  </footer>
</main>
<script>
  const output = document.getElementById('raw-output');
  const rawWrap = document.getElementById('raw-wrap');
  const results = document.getElementById('result-cards');
  const statusBadge = document.getElementById('response-status');
  const runButton = document.getElementById('run-demo');
  const processed = document.getElementById('processed');
  const failed = document.getElementById('failed');
  const processing = document.getElementById('processing');

  const samplePayload = {products: [
    {id: 101, title: 'Trail Boots', raw_description: 'Waterproof hiking boots for rough terrain.'},
    {id: 102, title: 'Laptop', raw_description: 'Portable computer for software development.'},
    {id: 103, title: 'Jacket', raw_description: 'Lightweight outdoor jacket for changing weather.'}
  ]};

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'\"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',\"'\":'&#39;','\"':'&quot;'}[char]));
  }

  runButton.addEventListener('click', async () => {
    runButton.disabled = true;
    runButton.textContent = 'Running…';
    statusBadge.textContent = 'Processing';
    results.innerHTML = '<div class=\"empty\">Validating request and dispatching work to the Go worker pool…</div>';
    rawWrap.hidden = true;
    processed.textContent = failed.textContent = processing.textContent = '—';

    try {
      const response = await fetch('/api/v1/ingest', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(samplePayload)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);

      processed.textContent = data.processed ?? 0;
      failed.textContent = data.failed ?? 0;
      processing.textContent = `${data.processing_ms ?? 0} ms`;
      statusBadge.textContent = data.status || 'Completed';

      results.innerHTML = (data.results || []).map(item => `
        <div class=\"result\">
          <div class=\"result-head\">
            <h3>${escapeHtml(item.product?.title)}</h3>
            <span class=\"category\">${escapeHtml(item.enrichment?.category || 'unknown')}</span>
          </div>
          <p>${escapeHtml(item.enrichment?.summary || 'No summary returned.')}</p>
          <div class=\"meta\"><span>Product #${escapeHtml(item.product?.id)}</span><span>Worker ${escapeHtml(item.worker_id)}</span><span>${escapeHtml(item.duration_ms)} ms</span></div>
        </div>`).join('') || '<div class=\"empty\">No result items returned.</div>';

      output.textContent = JSON.stringify(data, null, 2);
      rawWrap.hidden = false;
    } catch (error) {
      statusBadge.textContent = 'Failed';
      results.innerHTML = `<div class=\"empty error\">Demo request failed: ${escapeHtml(error.message || error)}</div>`;
    } finally {
      runButton.disabled = false;
      runButton.textContent = 'Run sample request';
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
