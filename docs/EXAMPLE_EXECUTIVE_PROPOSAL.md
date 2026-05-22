# Example Executive Proposal

This document shows the type of management-facing artifact generated after opportunity diagnosis.

The numbers are illustrative. In a real deployment, they should be validated against client volume, labor cost, error rate, system access, and risk tolerance.

## Client

Northwind Clinic Group

## Recommended initiative

Support agent with RAG over FAQs, tickets, and manuals.

## Priority problem

The clinic team spends repeated time answering similar patient and administrative questions. Some staff may be tempted to use public AI tools for speed, but patient-related context and internal documents require privacy controls.

## Recommended solution

Build a local-first support drafting assistant that retrieves answers from approved internal documents and generates draft responses for human review.

The system should:

- use tenant-scoped document retrieval,
- cite internal sources where possible,
- keep regulated content local,
- block premium escalation for sensitive contexts,
- and require human review before external replies.

## Expected financial profile

Estimated annual benefit:

```text
25,000-65,000 EUR
```

Estimated setup cost:

```text
3,000-9,000 EUR
```

Estimated monthly operating cost:

```text
300-1,200 EUR
```

## Deployment mode

Local-first with tightly controlled hybrid escalation.

For this sector, regulated or confidential content should not leave the local tenant environment by default.

## Pilot window

2-4 weeks.

## First experiment

Select 50-100 historical support questions. Build a retrieval set from approved FAQs and procedure documents. Generate draft answers and compare:

- answer accuracy,
- human edit distance,
- average handling time,
- privacy risk,
- number of cases requiring escalation.

## Quick wins

- Reduce repeated support drafting time.
- Standardize answers from approved content.
- Identify gaps in FAQs and internal procedures.
- Establish AI usage rules before uncontrolled adoption spreads.

## Main risk

The assistant could draft inaccurate or incomplete answers if the knowledge base is incomplete or stale.

Mitigation:

- source citations,
- human review,
- restricted knowledge sources,
- versioned content,
- sensitivity classification,
- clear rollback criteria.

## 90-day roadmap

### Weeks 1-2: discovery and governance

Deliverables:

- repeated-question inventory,
- approved document list,
- sensitivity policy,
- baseline support metrics.

### Weeks 3-4: prototype

Deliverables:

- local-first RAG prototype,
- draft answer workflow,
- human review checklist,
- first evaluation set.

### Weeks 5-8: pilot

Deliverables:

- controlled support pilot,
- weekly metrics,
- edit-rate analysis,
- risk and incident log.

### Weeks 9-12: rollout decision

Deliverables:

- baseline vs pilot comparison,
- financial estimate update,
- rollout, revise, or stop decision,
- governance update.

## Decision request

Approve a 30-day pilot for the support drafting assistant.

The pilot should not send regulated patient content to premium cloud models unless explicitly approved by the client and legally reviewed.
