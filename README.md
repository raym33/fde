# VirtuDirector IA

VirtuDirector IA is a FastAPI-based backend and local web application for running an AI operating layer for SMEs. It combines:

- a CAIO-style chat workspace,
- tenant-scoped document ingestion and retrieval,
- deterministic opportunity diagnosis,
- curated intelligence ingestion,
- local/LAN model routing through LM Studio,
- and an FDE Labs subsystem that evaluates changes before they are promoted.

This repository is not a generic chatbot template. It is an operational lab and backend for testing how AI should be introduced, evaluated, and governed inside small and medium-sized businesses.

License: MIT. See [LICENSE](/Users/mac/Documents/Codex/2026-05-20/claude-ha-terminado-la-respuesta-quiero/LICENSE).

## Repository purpose

The repository solves four practical problems:

1. Ingest client documents into a tenant-scoped knowledge layer.
2. Answer AI implementation questions using deterministic scoring plus curated knowledge.
3. Run measured lab experiments on RAG, routing, workflows, GRC, ROI, and market intelligence.
4. Require human approval before promoting a measured improvement.

## What is included

### Core application

- `backend/app/main.py`: FastAPI entrypoint.
- `backend/app/api/`: HTTP routes.
- `backend/app/core/`: orchestration, opportunity scoring, process scanner, routing.
- `backend/app/rag/`: embeddings, ingestion, retriever, local store.
- `backend/app/knowledge/`: curated knowledge ingestion, compaction, retrieval, ranking.
- `backend/app/tools/`: web search and LM Studio integration.
- `backend/app/static/`: operator UI and Labs admin UI.

### FDE Labs

- `backend/app/labs/`: lab definitions, schemas, service, registry, change promotion.
- `backend/app/api/labs.py`: HTTP surface for labs.
- `scripts/smoke_labs.py`: local smoke test.
- `scripts/labs_quality_gate.py`: deterministic validation gate for labs.

### Data and curated knowledge

- `backend/app/data/solutions_catalog.json`: base catalog used by the solutions engine.
- `backend/app/data/curated_intel/`: versioned curated knowledge loaded into the local knowledge store.

### Tests and utilities

- `tests/`: pytest suite.
- `scripts/import_curated_intel.py`: imports curated markdown into the local knowledge DB.
- `scripts/recompact_knowledge_briefs.py`: recomputes compact knowledge briefs with current logic.
- `scripts/smoke_tests.py`: HTTP smoke tests against a running backend.

## Runtime model

The product can run in three modes:

1. `demo_mode=true`: deterministic/demo behavior where external services are optional.
2. Cloud-assisted mode: external web search and hosted model APIs enabled.
3. Local/LAN mode: LM Studio provides OpenAI-compatible inference from the local machine or other machines on the LAN.

## Authentication model

There are two authentication paths:

### Operator and tenant routes

For most application routes, requests are resolved to a tenant principal.

- In production: use `Authorization: Bearer <jwt>`.
- In development: `X-Tenant-Id` and `X-User-Id` headers are accepted.

### Labs admin routes

Labs routes and the Labs admin UI use HTTP Basic auth.

Development defaults:

- username: `admin`
- password: `change-me-admin`

Change these values in `.env` before exposing the service outside local development.

## Requirements

Minimum requirements for local development:

- Python 3.11 or newer
- `venv`
- `pip`

Optional but recommended:

- PostgreSQL, if you want to match the configured `DATABASE_URL`
- Redis, if you plan to extend the runtime to use it
- Tesseract OCR, for scanned PDFs
- LM Studio, for local/LAN inference

The current labs persistence uses SQLite through `LABS_SQLITE_PATH` when set, or `data/virtudirector_labs.sqlite3` by default.

## Quick start

From the repository root:

```bash
make venv
make install
cp backend/.env.example backend/.env
make run
```

Open:

- [http://127.0.0.1:8000/app](http://127.0.0.1:8000/app)
- [http://127.0.0.1:8000/admin/labs](http://127.0.0.1:8000/admin/labs)
- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Exact setup steps

### 1. Create the virtual environment

```bash
python3 -m venv backend/.venv
```

or:

```bash
make venv
```

### 2. Install dependencies

```bash
backend/.venv/bin/pip install -r backend/requirements.txt
```

or:

```bash
make install
```

### 3. Create the environment file

```bash
cp backend/.env.example backend/.env
```

### 4. Start the backend

```bash
make run
```

For LAN access:

```bash
make run-lan
```

or:

```bash
./scripts/run_backend_lan.sh
```

## Make targets

The repository exposes these `make` targets:

- `make help`: print available targets.
- `make venv`: create `backend/.venv`.
- `make install`: install backend dependencies into `backend/.venv`.
- `make run`: start FastAPI on `127.0.0.1:8000`.
- `make run-lan`: start FastAPI on `0.0.0.0:8000`.
- `make smoke`: run `scripts/smoke_labs.py`.
- `make smoke-http`: run `scripts/smoke_tests.py` against a running backend.
- `make compile`: run Python bytecode compilation over `backend/app` and `scripts`.
- `make test`: run pytest.
- `make labs-quality`: run deterministic lab validation.
- `make recompact-intel`: recompute all knowledge briefs with current compaction logic.

## Environment variables

Environment variables are loaded from `backend/.env`.

Important variables:

### Core runtime

- `DEMO_MODE`
- `ENVIRONMENT`
- `DATA_REGION`

### Search provider

- `SEARCH_PROVIDER`
- `BRAVE_SEARCH_API_KEY`
- `TAVILY_API_KEY`
- `PERPLEXITY_API_KEY`
- `WEB_SEARCH_TIMEOUT_SECONDS`
- `WEB_SEARCH_CACHE_TTL_SECONDS`
- `WEB_SEARCH_DEFAULT_COUNTRY`
- `WEB_SEARCH_DEFAULT_LANGUAGE`

### Hosted model routing

- `DEEPINFRA_API_KEY`
- `TOGETHER_API_KEY`
- `FIREWORKS_API_KEY`
- `GROQ_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `MODEL_ROUTER_CHEAP`
- `MODEL_ROUTER_MEDIUM`
- `MODEL_ROUTER_PREMIUM`
- `MODEL_EMBEDDINGS`

### Local/LAN LM Studio

- `LOCAL_LLM_ENABLED`
- `LOCAL_LLM_PROVIDER`
- `LM_STUDIO_BASE_URL`
- `LM_STUDIO_API_KEY`
- `LM_STUDIO_TIMEOUT_SECONDS`
- `LM_STUDIO_CHAT_MODEL`
- `LM_STUDIO_MODEL_CHEAP`
- `LM_STUDIO_MODEL_MEDIUM`
- `LM_STUDIO_MODEL_PREMIUM`
- `LM_STUDIO_EMBEDDING_MODEL`
- `LM_STUDIO_REMOTE_BASE_URLS`
- `LOCAL_EMBEDDING_FALLBACK`

### Persistence and auth

- `DATABASE_URL`
- `REDIS_URL`
- `LABS_SQLITE_PATH`
- `JWT_SECRET`
- `ADMIN_BASIC_USERNAME`
- `ADMIN_BASIC_PASSWORD`

See [backend/.env.example](/Users/mac/Documents/Codex/2026-05-20/claude-ha-terminado-la-respuesta-quiero/backend/.env.example) for defaults and comments.

## Main HTTP routes

### Public or development-friendly routes

- `GET /`
- `GET /healthz`
- `GET /app`
- `GET /docs`

### Chat and operator workflows

- `POST /chat`
- `POST /opportunities/diagnose`
- `POST /opportunities/implementation-bundle`
- `POST /process-scanner/analyze`

### Document ingestion

- `POST /documents`
- `GET /documents/status`

### Knowledge ingestion and retrieval

- `GET /knowledge/updates/status`
- `POST /knowledge/updates`
- `GET /knowledge/updates`
- `GET /knowledge/briefs`
- `GET /knowledge/blocks`
- `GET /knowledge/use-cases`
- `POST /knowledge/solutions`

### Tool status

- `GET /tools/web-search/status`
- `GET /tools/web-search/test`
- `GET /tools/lm-studio/status`
- `GET /tools/lm-studio/test`

### Labs admin routes

- `GET /labs/catalog`
- `GET /labs/schedule/preview`
- `POST /labs/experiments/run`
- `GET /labs/runs`
- `GET /labs/reports`
- `GET /labs/reports/{report_id}`
- `POST /labs/reports/{report_id}/decision`
- `GET /labs/changes`
- `GET /labs/changes/{change_id}`
- `POST /labs/changes/{change_id}/apply`
- `GET /labs/feature-flags`

## How to use the web application

### Operator workspace: `/app`

The `/app` interface is the main workspace for day-to-day usage.

Typical usage flow:

1. Set `Tenant` and `Company`.
2. Upload client documents under `Documentos cliente`.
3. Upload curated intelligence under `Intel IA diaria`.
4. Use one of the preset prompts or write a custom question.
5. Use `Opportunity workbench` to run a structured diagnosis and generate an implementation bundle from a ranked opportunity.
6. Use `Explorador intel` to inspect:
   - curated blocks,
   - direct searches,
   - detected query intent,
   - ranking reasons.
7. Use `Process scanner` to submit structured process descriptions and review candidate automations.

### Labs admin: `/admin/labs`

The Labs admin panel is for measured evaluation and change promotion.

Typical usage flow:

1. Log in with admin Basic auth.
2. Review available labs.
3. Run a full experiment batch or a single lab.
4. Inspect reports with baseline vs candidate evidence.
5. Approve or reject reports.
6. Apply approved staged changes.
7. Inspect resulting feature flags.

## How to use the repository from the command line

### Run the local labs smoke test

```bash
make smoke
```

This command:

1. initializes the local labs database,
2. runs every registered lab,
3. stores run records,
4. stores proposed reports,
5. approves one report as part of the smoke flow.

Expected output shape:

```text
Catalog: 6 labs
Runs: 6
Reports proposed: N
...
OK
```

### Run the lab quality gate

```bash
make labs-quality
```

This command validates that:

1. every lab defined in the catalog is registered,
2. every lab is deterministic across two consecutive runs,
3. scores and metrics are well-formed,
4. report-producing labs generate valid report drafts.

### Run the test suite

```bash
make test
```

The test suite covers:

- knowledge ranking behavior,
- explainable search metadata,
- lab quality gate behavior,
- lab persistence,
- report approval and change application flow.

### Rebuild all knowledge briefs

```bash
make recompact-intel
```

Use this after changing knowledge compaction logic in `backend/app/knowledge/updates.py`.

### Import curated intelligence from versioned markdown

```bash
backend/.venv/bin/python scripts/import_curated_intel.py --date 2026-05-21
```

Common options:

- `--date <folder>`: import only one dated folder under `backend/app/data/curated_intel/`
- `--uploaded-by <name>`
- `--scope global|internal`
- `--source-type <value>`

## How the knowledge layer works

The knowledge subsystem stores two related records:

1. `knowledge_updates`: raw ingested documents and metadata.
2. `knowledge_briefs`: compacted summaries used for retrieval.

The workflow is:

1. ingest markdown, text, PDF, or DOCX,
2. parse and normalize,
3. compact into summary, tags, key points, and relevance fields,
4. store a retrieval-ready brief,
5. rank briefs for future operator questions.

The ranking layer currently supports:

- accent-insensitive matching,
- token expansion,
- field weighting,
- phrase boosts,
- sector boosts,
- query-intent detection,
- explainable search output.

## How the labs subsystem works

The labs subsystem uses a fixed lifecycle:

1. a lab definition exists in `backend/app/labs/catalog.py`,
2. a concrete evaluator class is registered in `backend/app/labs/registry.py`,
3. the lab runs a deterministic experiment,
4. the service stores a `lab_run`,
5. if the threshold is exceeded, the lab generates a `CoreReportDraft`,
6. a human approves or rejects the report,
7. approved reports create staged changes,
8. staged changes can be applied,
9. applied changes create or update feature flags.

Current labs:

- `rag_grounding`
- `model_routing_cost`
- `agent_workflow`
- `roi_solutions`
- `grc_eu_ai_act`
- `market_intelligence`

## How to add a new lab

1. Add a catalog entry in [backend/app/labs/catalog.py](/Users/mac/Documents/Codex/2026-05-20/claude-ha-terminado-la-respuesta-quiero/backend/app/labs/catalog.py).
2. Create an evaluator in `backend/app/labs/evaluators/`.
3. Inherit from the base lab contract.
4. Register the evaluator with `@register_lab("your_lab_id")`.
5. Ensure `run()` is deterministic.
6. Ensure `build_report()` returns a valid reviewable draft.
7. Run:

```bash
make labs-quality
make test
make smoke
```

## How to use LM Studio

### Local machine

1. Start LM Studio.
2. Enable its OpenAI-compatible server.
3. Set:

```env
LOCAL_LLM_ENABLED=true
LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
```

4. Configure chat and embedding model names in `.env`.

### Other machines on the LAN

1. Enable network serving in LM Studio on the remote machine.
2. Add its URL to:

```env
LM_STUDIO_REMOTE_BASE_URLS=http://192.168.x.y:1234/v1,http://192.168.x.z:1234/v1
```

3. Restart the backend.
4. Inspect:

- `GET /tools/lm-studio/status`
- the `Runtime` panel in `/app`

## Minimal end-to-end usage example

### 1. Start the backend

```bash
make run
```

### 2. Upload a text document into RAG

```bash
curl -X POST http://127.0.0.1:8000/documents \
  -H 'X-Tenant-Id: demo-tenant' \
  -H 'X-User-Id: tester' \
  -H 'X-Client-Name: Demo SL' \
  -F 'file=@/absolute/path/to/file.txt'
```

### 3. Ask for an opportunity diagnosis

```bash
curl -X POST http://127.0.0.1:8000/opportunities/diagnose \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-Id: demo-tenant' \
  -H 'X-User-Id: tester' \
  -H 'X-Client-Name: Demo SL' \
  -d '{"question":"Where should we implement AI first in a 500-employee SME?","employee_count":500}'
```

### 4. Run a lab batch as admin

```bash
curl -X POST http://127.0.0.1:8000/labs/experiments/run \
  -u admin:change-me-admin \
  -H 'Content-Type: application/json' \
  -d '{"triggered_by":"manual"}'
```

## CI

GitHub Actions currently runs:

1. `make compile`
2. `make labs-quality VENV_PYTHON=python`
3. `make test VENV_PYTHON=python`
4. `make smoke VENV_PYTHON=python`

CI definition: [.github/workflows/ci.yml](/Users/mac/Documents/Codex/2026-05-20/claude-ha-terminado-la-respuesta-quiero/.github/workflows/ci.yml)

## Documentation map

Additional repository documentation:

- [docs/ARCHITECTURE.md](/Users/mac/Documents/Codex/2026-05-20/claude-ha-terminado-la-respuesta-quiero/docs/ARCHITECTURE.md)
- [docs/OPERATIONS.md](/Users/mac/Documents/Codex/2026-05-20/claude-ha-terminado-la-respuesta-quiero/docs/OPERATIONS.md)
- [docs/DEVELOPMENT.md](/Users/mac/Documents/Codex/2026-05-20/claude-ha-terminado-la-respuesta-quiero/docs/DEVELOPMENT.md)
- [docs/IMPLEMENTATION_ENGINE_EXTENSION.md](/Users/mac/Documents/Codex/2026-05-20/claude-ha-terminado-la-respuesta-quiero/docs/IMPLEMENTATION_ENGINE_EXTENSION.md)

## Scope note

Repository-facing documentation is in English.

Curated intelligence datasets under `backend/app/data/curated_intel/` intentionally remain in Spanish because they are runtime product content for Spanish-language retrieval and operator workflows.

An optional execution scaffold is also available under:

- [extensions/implementation-engine/README.md](/Users/mac/Documents/Codex/2026-05-20/claude-ha-terminado-la-respuesta-quiero/extensions/implementation-engine/README.md)
