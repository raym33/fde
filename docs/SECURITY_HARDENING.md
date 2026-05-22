# Security Hardening

This repository is local-first and self-hostable, but the default development configuration is not suitable for public exposure.

Do not expose this service to the internet until the checklist below is complete.

## Critical production checklist

### 1. Change development credentials

Required changes:

- set a strong `JWT_SECRET`,
- change `ADMIN_BASIC_USERNAME`,
- change `ADMIN_BASIC_PASSWORD`,
- disable or restrict development header authentication,
- do not keep `admin` / `change-me-admin` in any exposed environment.

Relevant settings:

```env
JWT_SECRET=replace-with-long-random-secret
ADMIN_BASIC_USERNAME=replace-me
ADMIN_BASIC_PASSWORD=replace-me
ENVIRONMENT=production
```

### 2. Keep the service behind a trusted network boundary

Recommended:

- run behind a reverse proxy,
- terminate TLS at the proxy,
- restrict inbound IP ranges,
- avoid exposing `/admin/labs` publicly,
- place local model servers on a private network only.

### 3. Enforce tenant isolation

Every tenant route depends on tenant identity.

Before production use:

- use JWT-based tenant identity,
- reject development `X-Tenant-Id` headers in production,
- review every new route for tenant filtering,
- verify document and knowledge retrieval always receives `tenant_id`.

### 4. Treat premium escalation as opt-in

Default posture:

- local-first,
- premium escalation disabled,
- sensitive content blocked,
- tenant-specific policy required before any escalation.

Relevant routes:

- `GET /tools/runtime-policy`
- `POST /tools/runtime-policy`
- `GET /tools/premium/status`
- `POST /tools/sensitivity/analyze`

Recommended production behavior:

- only technical operators or admins should change runtime policy,
- regulated content should not be escalated,
- audit every escalation attempt,
- fallback to local output if premium backend fails.

### 5. Protect local CLIs and external tools

Optional premium providers can call local CLIs such as Claude or Codex.

Controls:

- set `PREMIUM_SANDBOX_DIR`,
- enforce timeouts,
- do not run CLIs with broad filesystem access,
- keep CLI authentication owned by the self-hosting customer,
- document provider terms and rate limits for the customer.

### 6. Review document ingestion boundaries

For document ingestion:

- allowlist directories for scheduled ingestion,
- classify sensitivity before model escalation,
- do not ingest broad shared drives without scoping,
- keep raw document storage and vector storage tenant-scoped,
- avoid logging raw sensitive content.

### 7. Lock down Labs operations

Labs can create staged changes and feature flags.

Production controls:

- require admin authentication,
- keep human approval mandatory,
- do not auto-apply staged changes,
- log decisions and notes,
- review rollback plans before applying changes.

## Route risk levels

| Route family | Risk | Required control |
| --- | --- | --- |
| `/chat` | Medium | Tenant auth, sensitivity checks, model policy |
| `/documents` | High | Tenant isolation, file validation, storage policy |
| `/knowledge/*` | Medium | Source validation, tenant or scope controls |
| `/opportunities/*` | Medium | Tenant auth, artifact storage controls |
| `/pilots/*` | Medium | Tenant auth, status validation |
| `/tools/runtime-policy` | High | Technical/admin role required in production |
| `/tools/premium/status` | Medium | Tenant auth |
| `/tools/sensitivity/analyze` | Medium | Tenant auth, avoid raw sensitive logs |
| `/labs/*` | High | Admin auth, human approval |

## Deployment notes

The repository currently optimizes for local development and self-hosted prototypes.

Before production deployment, prioritize:

1. role-based access control,
2. explicit production rejection of development headers,
3. PostgreSQL migrations or a formally supported SQLite appliance mode,
4. audit event persistence,
5. backup and restore procedures,
6. file upload limits,
7. reverse proxy and TLS configuration.

## Minimum safe local appliance profile

For a private SME appliance:

- run on a machine inside the client network,
- bind FastAPI to private LAN only,
- use LM Studio or another local model backend,
- keep premium escalation disabled by default,
- restrict admin access to the operator machine,
- back up the SQLite database and uploaded document store,
- document who can change runtime policy.

## What not to do

- Do not expose development credentials.
- Do not mount unrestricted shared drives into ingestion agents.
- Do not allow regulated content to escalate to cloud models by default.
- Do not auto-apply Labs changes.
- Do not log raw patient, legal, payroll, or contract data.
- Do not treat generated proposals as verified financial advice without client validation.
