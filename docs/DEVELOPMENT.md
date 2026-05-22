# Development

## Local development loop

### Install

```bash
make venv
make install
cp backend/.env.example backend/.env
```

### Run

```bash
make run
```

### Validate

```bash
make compile
make labs-quality
make test
make smoke
```

## File-level guide

### Add or change an API route

- route definitions: `backend/app/api/`
- app registration: `backend/app/main.py`

### Change opportunity diagnosis behavior

- `backend/app/core/opportunities.py`
- `backend/app/core/orchestrator.py`
- `backend/app/api/routes_opportunities.py`

### Change executive proposal generation

- `backend/app/core/executive_proposals.py`
- `backend/app/api/routes_opportunities.py`
- `tests/test_executive_proposals.py`

Typical reasons to change this layer:

- revise proposal field mapping,
- adjust cost or benefit heuristics,
- change persisted artifact formats,
- or alter how the UI consumes backend-generated proposal output.

### Change knowledge ingestion, compaction, or ranking

- `backend/app/knowledge/updates.py`
- `tests/test_knowledge_ranking.py`

After ranking changes:

```bash
make test
make recompact-intel
```

### Change document parsing

- `backend/app/ingest/document_parser.py`
- `backend/app/api/routes_documents.py`

### Change RAG behavior

- `backend/app/rag/store.py`
- `backend/app/rag/ingest.py`
- `backend/app/rag/retriever.py`

### Change the operator UI

- `backend/app/static/caio-chat.html`
- `backend/app/static/caio-chat.css`
- `backend/app/static/caio-chat.js`

Important UI surfaces inside `/app`:

- product mode switching (`SME`, `Consultant`, `Technical`),
- guided diagnosis intake,
- executive proposal panel,
- implementation bundle actions,
- runtime policy controls,
- explainable intelligence explorer.

### Change runtime policy or premium escalation

- `backend/app/core/runtime_policy.py`
- `backend/app/core/model_router.py`
- `backend/app/core/escalation.py`
- `backend/app/security/sensitivity.py`
- `backend/app/tools/cli_provider.py`
- `tests/test_premium_integration.py`
- `tests/test_runtime_policy.py`
- `tests/test_sensitivity.py`

### Change the Labs admin UI

- `backend/app/static/admin-labs.html`
- `backend/app/static/admin-labs.css`
- `backend/app/static/admin-labs.js`

### Add a new lab

1. Add the lab definition in `backend/app/labs/catalog.py`.
2. Implement the evaluator under `backend/app/labs/evaluators/`.
3. Register it with `@register_lab(...)`.
4. Validate:

```bash
make labs-quality
make test
make smoke
```

## Test strategy

### `make labs-quality`

Use this when changing lab logic or introducing a new lab.

### `make test`

Use this for:

- ranking changes,
- proposal and bundle generation changes,
- runtime policy changes,
- premium escalation changes,
- persistence changes,
- report lifecycle changes,
- route and service behavior covered by tests.

### `make smoke`

Use this when you need an end-to-end sanity check of the labs runtime and local persistence.

### `make smoke-http`

Use this when the backend is already running and you want to verify the actual HTTP surface.

## Development assumptions

The repository currently assumes:

- Python dependencies are installed in `backend/.venv`,
- the backend is run from the repository root through the `Makefile`,
- local persistence is acceptable for development and testing,
- operator intelligence content can remain versioned as markdown and imported on demand.
