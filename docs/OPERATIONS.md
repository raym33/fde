# Operations

## Start the backend

From the repository root:

```bash
make run
```

For LAN access:

```bash
make run-lan
```

## Required checks

Use these commands before pushing changes:

```bash
make compile
make labs-quality
make test
make smoke
```

## Common operational tasks

### Inspect health

```bash
curl http://127.0.0.1:8000/healthz
```

### Inspect runtime tool status

```bash
curl http://127.0.0.1:8000/tools/web-search/status \
  -H 'X-Tenant-Id: demo-tenant' \
  -H 'X-User-Id: ops'
```

```bash
curl http://127.0.0.1:8000/tools/lm-studio/status \
  -H 'X-Tenant-Id: demo-tenant' \
  -H 'X-User-Id: ops'
```

```bash
curl http://127.0.0.1:8000/tools/premium/status \
  -H 'X-Tenant-Id: demo-tenant' \
  -H 'X-User-Id: ops'
```

### Inspect or update tenant runtime policy

```bash
curl http://127.0.0.1:8000/tools/runtime-policy \
  -H 'X-Tenant-Id: demo-tenant' \
  -H 'X-User-Id: ops'
```

```bash
curl -X POST http://127.0.0.1:8000/tools/runtime-policy \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-Id: demo-tenant' \
  -H 'X-User-Id: ops' \
  -d '{
    "premium_provider": "codex_cli",
    "escalation_enabled": true,
    "escalation_allow_sensitive": false,
    "escalation_allowed_intents": "strategy,grc,deliverable"
  }'
```

### Generate an executive proposal from a diagnosis

The usual sequence is:

1. call `/opportunities/diagnose`,
2. pass the returned diagnosis payload into `/opportunities/executive-proposal`,
3. optionally persist the resulting HTML and JSON artifacts.

```bash
curl -X POST http://127.0.0.1:8000/opportunities/executive-proposal \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-Id: demo-tenant' \
  -H 'X-User-Id: ops' \
  -H 'X-Client-Name: Demo SL' \
  -d @/absolute/path/to/executive-proposal-request.json
```

Expected behavior:

- the response includes a normalized proposal payload,
- the response includes HTML for immediate rendering or download,
- and, when `persist=true`, the backend writes the artifact set under `data/executive_proposals/`.

### Generate an implementation bundle from a ranked opportunity

```bash
curl -X POST http://127.0.0.1:8000/opportunities/implementation-bundle \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-Id: demo-tenant' \
  -H 'X-User-Id: ops' \
  -H 'X-Client-Name: Demo SL' \
  -d @/absolute/path/to/implementation-bundle-request.json
```

Expected behavior:

- the response includes the generated files and paths,
- the backend writes a deterministic bundle under `data/implementation_bundles/`,
- and the selected service blueprint reflects the chosen opportunity type.

### Analyze whether content is safe to escalate

```bash
curl -X POST http://127.0.0.1:8000/tools/sensitivity/analyze \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-Id: demo-tenant' \
  -H 'X-User-Id: ops' \
  -d '{
    "text": "Review this clinic workflow",
    "context_chunks": [
      "Historia clínica del paciente con email maria@example.com y expediente asociado."
    ]
  }'
```

### Import curated knowledge

```bash
backend/.venv/bin/python scripts/import_curated_intel.py --date 2026-05-21
```

### Recompute compact briefs after changing compaction logic

```bash
make recompact-intel
```

### Run HTTP smoke tests against a running backend

```bash
make smoke-http
```

## Labs operations

### Run all labs from the CLI

```bash
make smoke
```

### Run all labs from the API

```bash
curl -X POST http://127.0.0.1:8000/labs/experiments/run \
  -u admin:change-me-admin \
  -H 'Content-Type: application/json' \
  -d '{"triggered_by":"manual"}'
```

### List reports

```bash
curl http://127.0.0.1:8000/labs/reports \
  -u admin:change-me-admin
```

### Approve a report

```bash
curl -X POST http://127.0.0.1:8000/labs/reports/<report_id>/decision \
  -u admin:change-me-admin \
  -H 'Content-Type: application/json' \
  -d '{"decision":"approve","decided_by":"admin","notes":"Approved after review"}'
```

### Apply a staged change

```bash
curl -X POST http://127.0.0.1:8000/labs/changes/<change_id>/apply \
  -u admin:change-me-admin \
  -H 'Content-Type: application/json' \
  -d '{"applied_by":"admin"}'
```

## Operator workflow

Recommended operator sequence:

1. set the tenant and company in `/app`,
2. upload client documents,
3. upload new curated intelligence,
4. choose the product mode:
   - `SME`
   - `Consultant`
   - `Technical`
5. ask a diagnosis or roadmap question,
6. inspect search-backed intelligence in the explorer,
7. generate an executive proposal or implementation bundle,
8. if needed, set a tenant runtime policy override for premium escalation,
9. evaluate implementation changes through Labs.

## Failure handling

### One lab fails during a batch

Expected behavior:

- the failed run is persisted with failure status,
- the remaining labs continue,
- the batch does not crash as a whole.

### OCR is not installed

Expected behavior:

- PDF text extraction still works for text-based PDFs,
- scanned PDFs may lose content until Tesseract is installed.

### LM Studio is unavailable

Expected behavior:

- the app falls back to demo or non-local behavior,
- `/tools/lm-studio/status` will show the failure,
- the operator UI will reflect that local inference is not active.

### Premium CLI or API backend is unavailable

Expected behavior:

- `/tools/premium/status` reports the selected premium backend status,
- the application does not crash,
- premium escalation falls back to the local answer path,
- and the failure remains visible through status and audit trails.

### A route touches runtime policy before the database exists

Expected behavior:

- the runtime policy layer initializes the local SQLite schema on demand,
- route-level tests do not depend on startup order,
- and tenant policy resolution falls back to defaults when no override exists.
