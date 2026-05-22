# Example SME Diagnosis

This document shows a realistic text-only example of the diagnosis flow.

It is not a benchmark and does not claim production ROI. It is a practical example of the type of output the repository is designed to generate.

## Input

```json
{
  "client_name": "Northwind Clinic Group",
  "employee_count": 120,
  "question": "Where should we implement AI first in a 120-employee clinic group with repetitive patient emails, invoices, internal document search, and high privacy requirements?"
}
```

## Expected diagnosis shape

```json
{
  "company_size": "SME",
  "top_opportunities": [
    {
      "id": "support_knowledge_agent",
      "title": "Support agent with RAG over FAQs, tickets, and manuals",
      "area": "customer support",
      "problem": "The team spends repeated time answering similar patient or client questions.",
      "ai_solution": "Build a retrieval-augmented assistant that drafts answers from approved internal content.",
      "expected_value": "Reduce repetitive response time and improve consistency.",
      "recommended_phase": "weeks 1-4",
      "annual_benefit_eur": [25000, 65000],
      "setup_cost_eur": [3000, 9000],
      "monthly_cost_eur": [300, 1200]
    },
    {
      "id": "document_search_copilot",
      "title": "Private document search copilot",
      "area": "knowledge management",
      "problem": "Staff lose time searching policies, procedures, invoices, and internal documents.",
      "ai_solution": "Index approved documents into a tenant-scoped RAG store with citation-first answers.",
      "expected_value": "Reduce search time and improve document reuse.",
      "recommended_phase": "weeks 3-8"
    },
    {
      "id": "executive_ai_governance",
      "title": "AI governance rollout",
      "area": "governance",
      "problem": "Employees may use public AI tools without clear rules or privacy boundaries.",
      "ai_solution": "Create a local-first AI usage policy, sensitivity checks, and runtime escalation rules.",
      "expected_value": "Lower privacy and compliance risk before broader rollout.",
      "recommended_phase": "weeks 1-4"
    }
  ],
  "quick_wins": [
    "support_knowledge_agent",
    "executive_ai_governance"
  ],
  "strategic_bets": [
    "document_search_copilot"
  ],
  "roadmap_90_days": [
    {
      "name": "Weeks 1-2: discovery and data boundaries",
      "deliverable": "Confirm high-volume support topics, approved knowledge sources, and sensitivity rules."
    },
    {
      "name": "Weeks 3-4: first prototype",
      "deliverable": "Build a local-first support drafting assistant over approved FAQs and procedures."
    },
    {
      "name": "Weeks 5-8: pilot",
      "deliverable": "Run the assistant with human review and measure response time reduction."
    },
    {
      "name": "Weeks 9-12: rollout decision",
      "deliverable": "Compare baseline vs pilot metrics and decide whether to expand, revise, or stop."
    }
  ]
}
```

## Interpretation

For a clinic, the strongest first step is usually not full automation. It is a controlled assistant that drafts responses from approved internal knowledge while humans remain in the loop.

Recommended deployment posture:

- local-first,
- tenant-scoped RAG,
- no premium escalation for regulated content,
- explicit governance policy before production use.

## What a consultant should do next

1. Confirm the top 20 repeated questions.
2. Collect approved FAQ, policy, and procedure documents.
3. Define forbidden content categories.
4. Build a first RAG prototype.
5. Measure:
   - average handling time,
   - human edits per draft,
   - escalation rate,
   - privacy incidents,
   - staff satisfaction.

## What the system should generate next

After diagnosis, the repo should be able to generate:

- an executive proposal,
- an implementation bundle,
- a pilot project,
- and later a Labs report comparing expected vs actual outcome.
