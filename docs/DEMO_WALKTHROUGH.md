# Demo Walkthrough

This document is a text-only demo script for showing VirtuDirector IA without screenshots, videos, or external assets.

The goal is to demonstrate the product as a practical AI consulting and prototyping workflow for SMEs:

```text
diagnosis -> proposal -> implementation bundle -> pilot -> runtime policy -> labs
```

## Demo scenario

Use this fictional client:

- Client: `Northwind Clinic Group`
- Sector: healthcare / clinics
- Size: 120 employees
- Pain: repetitive patient emails, document search, invoice handling, privacy concerns
- Data sensitivity: high
- Goal: first useful pilot in 30 days without sending patient data to cloud tools

## 1. Start the application

```bash
make run
```

Open:

```text
http://127.0.0.1:8000/app
```

Use these development headers automatically through the UI:

- Tenant: `northwind-clinic`
- Company: `Northwind Clinic Group`

## 2. Run a guided SME diagnosis

In `/app`, choose:

- Mode: `SME`
- Sector: `Clinic`
- Size: `101-500 employees`
- Main pain: `Too much time in support and emails`
- Data sensitivity: `High`
- Goal: `Keep data inside the company`

Expected output:

- one recommended opportunity,
- estimated annual benefit,
- first pilot window,
- local-first or tightly controlled hybrid deployment mode,
- initial executive proposal content.

## 3. Run the same diagnosis through the API

```bash
curl -X POST http://127.0.0.1:8000/opportunities/diagnose \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-Id: northwind-clinic' \
  -H 'X-User-Id: demo-operator' \
  -H 'X-Client-Name: Northwind Clinic Group' \
  -d '{
    "question": "Where should we implement AI first in a 120-employee clinic group with repetitive patient emails, invoices, internal document search, and high privacy requirements?",
    "employee_count": 120,
    "top_k": 5
  }'
```

Expected result:

- `diagnosis.top_opportunities`
- `diagnosis.quick_wins`
- `diagnosis.roadmap_90_days`
- a markdown version of the diagnosis

## 4. Generate an executive proposal

Use the diagnosis JSON from step 3 as the `diagnosis` field.

```bash
curl -X POST http://127.0.0.1:8000/opportunities/executive-proposal \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-Id: northwind-clinic' \
  -H 'X-User-Id: demo-operator' \
  -H 'X-Client-Name: Northwind Clinic Group' \
  -d @/absolute/path/to/executive-proposal-request.json
```

Expected result:

- `proposal.problem_statement`
- `proposal.recommended_solution`
- `proposal.annual_benefit_eur`
- `proposal.deployment_mode`
- `proposal.pilot_window`
- `proposal.quick_wins`
- `proposal.roadmap_90_days`
- `html`
- persisted `proposal.json` and `proposal.html` when `persist=true`

## 5. Generate an implementation bundle

From the UI:

1. Switch to `Consultant` mode.
2. Pick the top ranked opportunity.
3. Click `Generate bundle`.

Through the API:

```bash
curl -X POST http://127.0.0.1:8000/opportunities/implementation-bundle \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-Id: northwind-clinic' \
  -H 'X-User-Id: demo-operator' \
  -H 'X-Client-Name: Northwind Clinic Group' \
  -d '{
    "question": "Where should we implement AI first in a 120-employee clinic group with repetitive patient emails, invoices, internal document search, and high privacy requirements?",
    "employee_count": 120,
    "opportunity_id": "support_knowledge_agent",
    "top_k": 5,
    "review": true
  }'
```

Expected files:

- `swarm_input.md`
- `execution_request.json`
- `review_checklist.md`
- `command.txt`

## 6. Create a pilot

From the UI:

1. Stay in `Consultant` mode.
2. Click `Create pilot` on the selected opportunity.
3. Open the `Active pilots` section.
4. Move the pilot from `draft` to `approved`, then to `in_progress`.
5. Complete the next task.

Through the API:

```bash
curl -X POST http://127.0.0.1:8000/pilots \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-Id: northwind-clinic' \
  -H 'X-User-Id: demo-operator' \
  -H 'X-Client-Name: Northwind Clinic Group' \
  -d @/absolute/path/to/create-pilot-request.json
```

Expected result:

- persistent pilot ID,
- status `draft`,
- success metrics,
- risks,
- implementation tasks.

## 7. Check runtime policy

```bash
curl http://127.0.0.1:8000/tools/runtime-policy \
  -H 'X-Tenant-Id: northwind-clinic' \
  -H 'X-User-Id: demo-operator'
```

For this clinic scenario, the expected operating posture is:

- local-first,
- premium escalation disabled by default,
- sensitive content blocked from escalation,
- LM Studio or another local backend preferred for internal documents.

## 8. Test sensitivity analysis

```bash
curl -X POST http://127.0.0.1:8000/tools/sensitivity/analyze \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-Id: northwind-clinic' \
  -H 'X-User-Id: demo-operator' \
  -d '{
    "text": "Summarize appointment emails",
    "context_chunks": [
      "Patient name Maria Lopez, clinical record, appointment reason and email address."
    ]
  }'
```

Expected result:

- sensitivity level should be `regulated` or `confidential`,
- premium escalation should not be allowed unless explicitly overridden by policy.

## 9. Run Labs

```bash
make smoke
```

Expected result:

- registered labs run deterministically,
- material improvements create proposed reports,
- human approval is required before staged changes are applied.

## Demo close

The demo should make this clear:

- VirtuDirector IA starts from a business problem, not a prompt.
- It turns that problem into a ranked AI opportunity.
- It creates an executive proposal and implementation package.
- It tracks the work as a pilot with success metrics.
- It keeps runtime choices local-first and tenant-controlled.
- It validates future product changes through Labs.
