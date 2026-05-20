# VirtuDirector IA - FDE Labs

Forward-deployed AI engineering lab for SME AI implementation: opportunity
diagnosis, tenant-scoped RAG, local/LAN model routing, continuous evaluation
and human-approved promotion of measured improvements.

This repository is the working lab behind **VirtuDirector IA**, an AI Operating
System / fractional CAIO for SMEs. It is designed around one core idea:

> AI systems for real companies should not change just because a model suggested
> a better answer. They should be measured, reviewed and promoted with evidence.

License: MIT. See [LICENSE](/Users/mac/Documents/Codex/2026-05-20/claude-ha-terminado-la-respuesta-quiero/LICENSE).

Default admin UI credentials in development:

- username: `admin`
- password: `change-me-admin`

## Why this exists

Most SMEs do not need a generic chatbot. They need a repeatable AI
implementation process that answers:

1. Where should we apply AI first?
2. Which tasks should stay local for privacy or cost?
3. How do we connect internal documents safely?
4. How do we compare RAG, agents and model-routing changes over time?
5. How do we keep humans in control before production changes?

This repo is that lab.

## What this proves

This project demonstrates the ability to:

- build FastAPI backends for AI products,
- diagnose AI opportunities for SMEs with deterministic scoring,
- run tenant-scoped RAG with document ingestion and retrieval evaluation,
- route workloads between local/LAN and frontier-style models,
- evaluate agent, GRC and market-intelligence improvements as measured labs,
- promote changes through `report -> approval -> feature flag -> implemented`,
- keep a curated intelligence layer available to the product at runtime.

## Current scope

This is a serious MVP / lab, not a finished SaaS platform. Some capabilities are
already measured end to end; others still use modeled proxies where full eval
infrastructure would be excessive for the current stage. That distinction is
called out explicitly below.

## Quick commands

```bash
make venv
make install
make smoke
make run
```

If the backend is already running locally, you can also verify the HTTP surface with:

```bash
make smoke-http
```

## Fast product walkthrough

1. Upload client documents into tenant-scoped RAG.
2. Ask the CAIO workbench where AI should be implemented first.
3. Review deterministic scorecards and a 90-day roadmap.
4. Run labs that compare baseline vs candidate behavior.
5. Approve only improvements backed by evidence.

## Labs

- `rag_grounding`: retrieval quality, citation coverage, hallucination controls, tenant isolation.
- `model_routing_cost`: hybrid model routing, open-source/frontier split, cost and latency tradeoffs.
- `agent_workflow`: planner/verifier/tooling patterns and task completion reliability.
- `roi_solutions`: solution-ranking quality, ROI calibration, budget-fit for Spanish SMEs.
- `grc_eu_ai_act`: EU AI Act readiness, GRC checklist quality, risk classification.
- `market_intelligence`: market/regulatory/model monitoring and freshness of signals.

### Measurement status

All labs now perform deterministic measured experiments. A lab may return
`no_material_improvement`; that is expected and desirable when the candidate
does not beat the measured baseline above threshold.

- `rag_grounding` and `model_routing_cost` perform **real measurement**:
  - `rag_grounding` ingests a golden set into an isolated tenant store and
    measures `recall@k`, first-citation precision and MRR for vector-only vs.
    hybrid (BM25+vector, RRF) retrieval, plus a real cross-tenant leakage check.
  - `model_routing_cost` computes cost, modeled quality, latency and
    premium-escalation precision from an editable price table and workload mix
    (`PRICE_EUR_PER_1M`, `WORKLOAD` in `evaluators/model_routing_cost.py`).
    Quality is a modeled proxy until real evals (LLM-judge/Ragas) are wired.
- `agent_workflow` executes a golden set of multi-step tasks against baseline
  linear orchestration vs. bounded planner/verifier/retry policy.
- `roi_solutions` runs real `solutions_engine.propose()` over Spanish SME cases
  and compares it with a naive catalog ranking baseline.
- `grc_eu_ai_act` evaluates role-specific EU AI Act/RGPD readiness rules against
  expected risk classes, obligations, policies and source requirements.
- `market_intelligence` measures clustering, dedupe and novelty filtering over a
  corpus of useful signals, duplicates and noise before updates enter the core.

## Run a Smoke Test

```bash
make smoke
```

This creates a local SQLite DB at `./data/virtudirector_labs.sqlite3`, runs all labs, stores runs and proposed reports, then approves one report.

Expected output shape:

```text
Catalog: 6 labs
Runs: 6
Reports proposed: N
- rag_grounding: ...
- model_routing_cost: ...
OK
```

## Run the API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Useful endpoints:

- `GET /health`
- `GET /app`
- `GET /admin/labs`
- `POST /chat`
- `POST /opportunities/diagnose`
- `POST /documents`
- `GET /knowledge/use-cases`
- `POST /knowledge/solutions`
- `GET /tools/web-search/status`
- `GET /tools/web-search/test?q=EU+AI+Act+Spain`
- `GET /tools/lm-studio/status`
- `GET /tools/lm-studio/test`
- `GET /documents/status`
- `GET /labs/catalog`
- `GET /labs/schedule/preview`
- `POST /labs/experiments/run`
- `GET /labs/runs?limit=20`
- `GET /labs/reports`
- `GET /labs/reports/{report_id}`
- `POST /labs/reports/{report_id}/decision`
- `GET /labs/changes`
- `GET /labs/feature-flags`
- `POST /labs/changes/{change_id}/apply`

## Admin UI

The app UI and Labs admin panel are served directly by FastAPI, so no Node or frontend build is required:

[http://127.0.0.1:8000/app](http://127.0.0.1:8000/app)

[http://127.0.0.1:8000/admin/labs](http://127.0.0.1:8000/admin/labs)

Security note:

- `/app` is the operator/user workspace.
- `/admin/labs` and `/labs/*` require admin Basic auth.
- `/tools/*` and `/documents/status` require tenant/user authentication headers or a valid JWT.

The CAIO chat supports:

- Streaming chat via `/chat`.
- Intent routing into strategy, GRC, research, build, solution and opportunity-discovery flows.
- AI opportunity diagnosis for questions like “dónde implementar IA primero”.
- Deterministic solution recommendations with scorecards and ROI.
- Tenant-scoped RAG in demo mode.

## Suggested demo flow

If you are reviewing this repo as a CTO, client or hiring team, the shortest
path to understanding it is:

1. `make smoke`
2. `make run`
3. Open `/app`
4. Ask: `dónde debería implementar IA primero en una pyme de 500 empleados`
5. Open `/admin/labs`
6. Run a lab and inspect the proposed report

## AI Opportunity Discovery

Many SMEs do not know where AI should be implemented first. The
`opportunity` workflow creates a deterministic consulting-style map:

`company question + client RAG + daily AI intelligence -> area opportunities -> scorecard -> 90-day roadmap`

The score is computed in code from impact, effort, data readiness, risk,
time-to-value and strategic fit. The LLM may add narrative in non-demo mode, but
it does not invent the ranking.

API:

```bash
curl -X POST http://127.0.0.1:8000/opportunities/diagnose \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-Id: demo-tenant' \
  -H 'X-User-Id: tester' \
  -H 'X-Client-Name: Demo SL' \
  -d '{"question":"dónde debería implementar IA primero en una pyme de 500 empleados","employee_count":500}'
```

Natural chat examples:

- “Dónde debería implementar IA primero en una pyme de 500 empleados.”
- “Hazme un mapa de oportunidades IA por departamentos.”
- “Qué procesos debería automatizar con IA antes de invertir fuerte.”

The Labs panel supports:

- Viewing all six labs and their cadence/threshold.
- Running one lab or all labs.
- Reviewing Core Reports with evidence, metrics, rollout and rollback plans.
- Approving, rejecting and marking approved reports as implemented.
- Converting approved reports into staged core changes.
- Applying staged changes as feature flags.
- Viewing recent measured lab runs.

## Labs-to-Core Promotion

Reports move through a controlled promotion path:

`proposed report -> approved report -> staged core change -> applied feature flag -> implemented report`

This keeps lab discoveries auditable. The app does not auto-mutate core behavior just because a lab found a better result; a human approval creates a staged change, and a separate apply step enables the corresponding feature flag.

## External Tools

The first concrete tool layer is web/market search. It is pluggable and server-side only:

- `SEARCH_PROVIDER=auto` chooses Brave, then Tavily, then Perplexity if a key exists.
- `SEARCH_PROVIDER=brave` uses Brave Search API.
- `SEARCH_PROVIDER=tavily` uses Tavily Search API.
- `SEARCH_PROVIDER=perplexity` uses Perplexity Search API.
- `DEMO_MODE=true` always returns clearly labeled demo results.

To activate real search:

```bash
cd backend
cp .env.example .env
# set DEMO_MODE=false and one provider key
uvicorn app.main:app --reload
```

Check readiness:

```bash
curl http://127.0.0.1:8000/tools/web-search/status
curl 'http://127.0.0.1:8000/tools/web-search/test?q=chatbot%20IA%20pyme%20Espana'
```

## Document Extraction

Clients can upload TXT/MD, DOCX and PDF files to tenant-scoped RAG:

```bash
curl -X POST http://127.0.0.1:8000/documents \
  -H 'X-Tenant-Id: demo-tenant' \
  -H 'X-User-Id: tester' \
  -F 'file=@policy.docx' \
  -F 'title=AI Policy'
```

Extraction stack:

- TXT/MD: native decoding with encoding fallback.
- DOCX: `python-docx`, including paragraphs and tables.
- PDF: `pypdf` text extraction.
- OCR fallback: `PyMuPDF + pytesseract + Pillow` when the PDF has little/no embedded text and the system `tesseract` binary is installed.

Check local parser readiness:

```bash
curl http://127.0.0.1:8000/documents/status
```

## LM Studio Local/LAN Models

LM Studio is supported through its OpenAI-compatible API (`/v1/chat/completions`,
`/v1/models`, and `/v1/embeddings` when an embedding model is loaded).

Local Mac example:

```env
DEMO_MODE=true
LOCAL_LLM_ENABLED=true
LOCAL_LLM_PROVIDER=lmstudio
LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
LM_STUDIO_CHAT_MODEL=gemma-4-26b-a4b-it-mlx
LM_STUDIO_MODEL_CHEAP=qwen3.6-27b
LM_STUDIO_MODEL_MEDIUM=gemma-4-26b-a4b-it-mlx
LM_STUDIO_MODEL_PREMIUM=gemma-4-26b-a4b-it-mlx
LM_STUDIO_EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5
```

LAN machines:

```env
LM_STUDIO_BASE_URL=http://192.168.1.50:1234/v1
LM_STUDIO_REMOTE_BASE_URLS=http://192.168.1.51:1234/v1,http://192.168.1.52:1234/v1
```

To let another computer on the same network open VirtuDirector IA, start the
backend on all interfaces:

```bash
cd backend
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open `http://<this-mac-lan-ip>:8000/app` from the other computer. On this
Mac the LAN IP will depend on the network you are on.

For each LM Studio worker machine, enable its local server and expose it on the
LAN, then add that machine to `LM_STUDIO_REMOTE_BASE_URLS`. Keep this on a
trusted private network only; do not expose LM Studio or this backend directly
to the public internet without auth, TLS, rate limits and network firewalling.

Check:

```bash
curl http://127.0.0.1:8000/tools/lm-studio/status
curl 'http://127.0.0.1:8000/tools/lm-studio/test?prompt=di%20listo'
```

## Daily AI Intelligence Knowledge Base

Technicians can upload `.txt`, `.md` or `.pdf` files with fresh AI information
from `/app` or via API. The system stores the raw extracted text for audit, then
creates a compact brief used by the CAIO core:

`raw document -> extracted text -> compact brief -> tags/relevance -> RAG chunk`

The compact brief is what the orchestrator retrieves, so long daily notes do not
flood the model context.

API:

```bash
curl -X POST http://127.0.0.1:8000/knowledge/updates \
  -H 'X-Tenant-Id: platform' \
  -H 'X-User-Id: technician' \
  -F 'file=@latest-ai-news.md' \
  -F 'title=Daily AI Update' \
  -F 'source_url=https://example.com/source' \
  -F 'source_type=daily_ai_update' \
  -F 'scope=global'

curl http://127.0.0.1:8000/knowledge/updates/status
curl 'http://127.0.0.1:8000/knowledge/briefs?q=rag%20costes%20modelos'
curl 'http://127.0.0.1:8000/knowledge/blocks?limit_per_block=4'
```

The `/app` workspace includes an **Explorador intel** panel that groups this
knowledge into practical blocks such as `intel`, `dolores`, `roadmaps`,
`stack` and sector-specific notes for health/public administration.

### Curated seed intel

Versioned curated intelligence can also live in the repo under:

`backend/app/data/curated_intel/<YYYY-MM-DD>/`

This is useful for importing analyst notes, pain-point research, roadmap
initiatives or stack summaries that we want available locally in the app from
day one. Import them into the local knowledge store with:

```bash
backend/.venv/bin/python scripts/import_curated_intel.py --date 2026-05-20
backend/.venv/bin/python scripts/recompact_knowledge_briefs.py
```

The importer marks these entries as `curated_operator_intel` so they remain
distinguishable from directly uploaded daily news or docs.

The recompact script is safe to run after improving the summarization logic; it
refreshes existing knowledge briefs in SQLite without duplicating source docs.

Example:

```bash
curl -X POST http://localhost:8000/labs/experiments/run \
  -H 'Content-Type: application/json' \
  -d '{"lab_id":"grc_eu_ai_act","triggered_by":"admin"}'
```

## Product Rule

Labs never auto-change production. They generate evidence-backed reports:

`experiment -> measured run -> Core Report -> human approval -> staging -> evals -> feature flag -> production`
