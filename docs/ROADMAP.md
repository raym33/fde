# Repository Roadmap

This document is a continuation guide for developers and AI coding agents working on VirtuDirector IA.

The goal is to make the next engineering steps explicit: where the repository is today, what is already implemented, what should be built next, and what acceptance criteria should be used before merging future work.

## Product direction

VirtuDirector IA is moving toward a local-first AI consulting and prototyping operating layer for SMEs.

The target workflow is:

```text
SME intake
-> AI opportunity diagnosis
-> executive proposal
-> implementation bundle
-> pilot execution
-> measurement
-> governance
-> lab-validated product improvement
```

The product should remain practical, self-hostable, and understandable by SMEs. Technical power should exist behind the scenes, while the main user flow should stay focused on business outcomes, ROI, privacy, and the next pilot.

## Current state

### Implemented product surfaces

- FastAPI backend with static web application served at `/app`.
- Labs admin interface served at `/admin/labs`.
- Three `/app` product modes:
  - `SME`
  - `Consultant`
  - `Technical`
- Guided SME diagnosis flow.
- Structured opportunity diagnosis through `POST /opportunities/diagnose`.
- Executive proposal generation through `POST /opportunities/executive-proposal`.
- Implementation bundle generation through `POST /opportunities/implementation-bundle`.
- Process scanner through `POST /process-scanner/analyze`.
- Tenant-scoped document ingestion through `POST /documents`.
- Curated knowledge ingestion and ranked retrieval through `/knowledge/*`.
- Explainable knowledge ranking with intent, block, score breakdown, and ranking reasons.
- Runtime policy per tenant through `/tools/runtime-policy`.
- LM Studio local/LAN status and test routes.
- Optional premium escalation through customer-owned API keys or local CLIs.
- Sensitivity analysis through `POST /tools/sensitivity/analyze`.
- FDE Labs for measured evaluation and human-approved promotion.

### Implemented backend modules

- `backend/app/core/opportunities.py`
  - deterministic opportunity diagnosis.
- `backend/app/core/executive_proposals.py`
  - proposal construction and persisted HTML/JSON artifacts.
- `backend/app/core/implementation_engine.py`
  - delivery bundle generation from ranked opportunities.
- `backend/app/core/runtime_policy.py`
  - tenant runtime overrides for premium provider and escalation policy.
- `backend/app/core/escalation.py`
  - local-to-premium escalation decision logic.
- `backend/app/security/sensitivity.py`
  - content classification into `public`, `internal`, `confidential`, or `regulated`.
- `backend/app/knowledge/updates.py`
  - curated intelligence ingestion, brief generation, ranking, and explanations.
- `backend/app/labs/*`
  - lab catalog, registry, evaluators, reports, changes, and feature flags.

### Implemented test coverage

Current tests cover:

- executive proposal generation,
- implementation bundle templates,
- optional implementation engine,
- knowledge ranking,
- lab quality gates,
- labs service persistence and report lifecycle,
- opportunity-to-bundle generation,
- premium integration,
- tenant runtime policy,
- sensitivity classification.

Run the core checks before pushing:

```bash
make compile
make labs-quality
make test
make smoke
```

## Near-term engineering priorities

### P0.1: Proposal-to-pilot pipeline

Current state:

- The system can generate an executive proposal and an implementation bundle.
- There is no first-class pilot object or state machine.

Build:

- A persistent `pilot_projects` table.
- A backend module, for example `backend/app/core/pilots.py`.
- API routes:
  - `POST /pilots`
  - `GET /pilots`
  - `GET /pilots/{pilot_id}`
  - `POST /pilots/{pilot_id}/status`
  - `POST /pilots/{pilot_id}/tasks/{task_id}/complete`
- A pilot should be creatable from:
  - an executive proposal,
  - an implementation bundle,
  - or a selected diagnosis opportunity.

Minimum pilot fields:

- `id`
- `tenant_id`
- `client_name`
- `source_type`
- `source_id`
- `title`
- `status`
- `owner`
- `start_date`
- `target_end_date`
- `success_metrics_json`
- `tasks_json`
- `risks_json`
- `created_at`
- `updated_at`

Suggested statuses:

- `draft`
- `approved`
- `in_progress`
- `blocked`
- `completed`
- `cancelled`

Acceptance criteria:

- A user can turn the top diagnosis opportunity into a pilot.
- The pilot persists across requests.
- The pilot has measurable success criteria.
- Tests cover creation, listing, status transition, and invalid transition handling.

### P0.2: Sector-specific proposal logic

Current state:

- Executive proposals are useful but generic.

Build:

- Sector-specific proposal profiles for:
  - clinics,
  - legal offices,
  - real estate agencies,
  - accounting firms,
  - industrial SMEs,
  - municipalities.
- Each profile should tune:
  - problem language,
  - risks,
  - quick wins,
  - cost assumptions,
  - expected benefit ranges,
  - pilot window,
  - compliance notes.

Suggested files:

- `backend/app/core/sector_profiles.py`
- `tests/test_sector_profiles.py`

Acceptance criteria:

- The same diagnosis produces different proposal framing for a clinic and a real estate agency.
- Regulated sectors surface privacy and governance earlier.
- Tests assert deterministic outputs for at least three sectors.

### P0.3: PDF proposal export

Current state:

- Proposals are persisted as JSON and HTML.

Build:

- A server-side export path for PDF generation.
- Keep HTML as the source of truth where possible.
- Add route:
  - `GET /opportunities/executive-proposal/{proposal_id}/pdf`

Implementation options:

- Playwright or a lightweight HTML-to-PDF tool.
- If external binaries are unavailable, return a clear `501` with setup guidance instead of failing silently.

Acceptance criteria:

- Existing proposal HTML can be rendered into a PDF artifact.
- The route returns a stable file response.
- Tests cover success when renderer is available and graceful fallback when it is not.

### P0.4: UI workflow for pilots

Current state:

- `/app` can diagnose, propose, and generate bundles.
- It does not yet show a pilot pipeline.

Build:

- A `Pilot` section in Consultant mode.
- One-click conversion from:
  - selected opportunity,
  - executive proposal,
  - implementation bundle.
- A compact status board:
  - draft,
  - approved,
  - in progress,
  - blocked,
  - completed.

Acceptance criteria:

- SME mode remains simple.
- Consultant mode can manage pilots.
- Technical mode can inspect runtime details.
- No product mode should expose unrelated controls by default.

## Mid-term engineering priorities

### P1.1: Ingestion source connectors

Current state:

- Manual upload and local scheduled ingestion exist.

Build:

- Source connector abstraction.
- Initial connectors:
  - local folder,
  - SharePoint or Microsoft Graph,
  - Google Drive,
  - Notion,
  - Git repository.

Acceptance criteria:

- Each connector supports dry-run mode.
- Each connector supports allowlisted paths.
- Each connector reports files discovered, skipped, ingested, and failed.
- Sensitive content classification is applied during ingestion.

### P1.2: Knowledge deduplication and versioning

Current state:

- Knowledge updates use content hashes.
- There is no rich version history per source document.

Build:

- Source-level version tracking.
- Better duplicate grouping.
- Brief invalidation when compaction logic changes.
- A route to inspect versions for a source file.

Acceptance criteria:

- Re-ingesting the same document does not create noisy duplicates.
- Updating a document creates a visible version.
- Search results can identify the latest version.

### P1.3: Runtime audit dashboard

Current state:

- Escalation decisions are made and audit helpers exist.
- Operators need a clearer view of local vs premium behavior.

Build:

- Persisted runtime events:
  - local answer,
  - premium escalation attempted,
  - premium escalation blocked,
  - premium unavailable fallback,
  - sensitivity classification result.
- API routes:
  - `GET /tools/runtime-events`
  - `GET /tools/runtime-events/summary`
- UI section in Technical mode.

Acceptance criteria:

- Operators can see why a task stayed local or escalated.
- Regulated content blocks are visible without exposing sensitive text.
- Tests cover event creation and summary aggregation.

### P1.4: Bundle quality checks

Current state:

- Bundles are generated and persisted.

Build:

- A bundle validation layer.
- Checks:
  - required files exist,
  - selected service blueprint matches opportunity type,
  - review checklist includes success metrics,
  - command file is safe and non-destructive,
  - sensitive data is not written into generated prompts.

Acceptance criteria:

- Invalid bundles fail loudly in tests.
- Bundle generation returns validation status.
- The UI shows whether a bundle is ready for review.

## Labs roadmap

### L1: Add pilot outcome lab

Purpose:

- Evaluate whether generated pilots produce measurable business outcomes.

Inputs:

- completed pilot records,
- planned success metrics,
- actual outcome metrics,
- implementation notes.

Outputs:

- recommendation on proposal heuristics,
- suggested changes to sector profiles,
- suggested changes to ROI assumptions.

Acceptance criteria:

- Lab is deterministic.
- Lab produces a report only when outcome deltas are material.
- Report includes evidence from completed pilots.

### L2: Add sensitivity and escalation lab

Purpose:

- Calibrate when local answers should escalate to premium and when escalation should be blocked.

Inputs:

- synthetic queries across sensitivity levels,
- expected escalation decisions,
- expected redaction behavior.

Outputs:

- suggested threshold changes,
- policy recommendations,
- failure examples.

Acceptance criteria:

- Lab catches accidental escalation of regulated content.
- Lab catches missed escalation for difficult but non-sensitive strategic work.
- Lab integrates with `make labs-quality`.

### L3: Add proposal quality lab

Purpose:

- Evaluate executive proposals for completeness, clarity, and sector fit.

Inputs:

- fixed diagnosis scenarios,
- expected proposal properties,
- sector profile expectations.

Outputs:

- proposal completeness score,
- sector fit score,
- missing field analysis.

Acceptance criteria:

- Lab checks at least five sectors.
- Lab fails if proposals omit ROI, risks, pilot window, or next step.
- Lab is deterministic and does not require external models.

## Product hardening roadmap

### H1: Move from local SQLite-only assumptions to explicit persistence modes

Current state:

- SQLite is the working persistence path used by tests and local operation.
- `DATABASE_URL` exists but is not the main active persistence path.

Build:

- Explicit persistence mode setting:
  - `sqlite`
  - `postgres`
- Migration strategy for PostgreSQL.
- Integration tests for the selected mode.

Acceptance criteria:

- Local development remains simple.
- Production deployment has a clear persistence path.
- Migrations are repeatable.

### H2: Authentication and role hardening

Current state:

- Development headers are accepted for tenant routes.
- Admin routes use Basic auth.

Build:

- Role model:
  - SME user,
  - consultant,
  - technical operator,
  - admin.
- JWT claims mapped to these roles.
- Optional development-header mode gated behind environment.

Acceptance criteria:

- Production mode rejects development headers.
- Sensitive runtime policy routes require technical or admin role.
- Labs admin routes require admin role.

### H3: Frontend regression checks

Current state:

- Static UI exists without a frontend build.

Build:

- Browser smoke checks for:
  - `/app`,
  - `/admin/labs`,
  - product mode switching,
  - diagnosis form rendering,
  - runtime panel rendering,
  - executive proposal rendering.

Acceptance criteria:

- CI can detect broken static UI references.
- Tests do not require external model providers.

## Agent instructions for future work

When continuing this repository:

1. Prefer backend functionality over documentation-only changes unless the task explicitly asks for docs.
2. Preserve local-first behavior as the default.
3. Do not make premium escalation automatic unless tenant policy enables it.
4. Keep SME mode simple; move technical controls into Consultant or Technical mode.
5. Add tests for every new route or persistent object.
6. Keep Labs deterministic.
7. Do not introduce a separate frontend build unless there is a strong reason.
8. Do not commit generated runtime artifacts from `data/executive_proposals/` or `data/implementation_bundles/`.
9. Keep curated Spanish intelligence in `backend/app/data/curated_intel/`; repository docs should remain English.
10. Run `make compile`, `make test`, and any relevant smoke or labs checks before pushing.

## Recommended next commit sequence

The most useful next sequence is:

1. Add pilot persistence and API routes.
2. Connect executive proposals and implementation bundles to pilot creation.
3. Add sector-specific proposal profiles.
4. Add PDF export for proposals.
5. Add a Consultant-mode pilot pipeline UI.
6. Add the proposal quality lab.
7. Add runtime audit event persistence and UI.

This sequence turns the repository from a diagnosis and packaging system into a fuller consulting operations product: diagnosis, proposal, pilot, measurement, governance, and continuous improvement.
