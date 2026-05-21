# Service blueprint: document search copilot

Objective: deliver an internal document search copilot with retrieval, access controls, citations, and measurable quality gates.

Required outputs:
- target architecture for ingestion, indexing, retrieval, and answer generation
- permission boundary model
- document freshness and re-indexing plan
- evaluation plan with a golden question set
- rollout plan with human review checkpoints

Implementation requirements:
- Use a tenant-scoped knowledge base with explicit source citations.
- Respect document-level permissions and never leak cross-team content.
- Keep retrieval and answer generation separate so retrieval quality can be measured independently.
- Define a compact ingestion policy for PDF, DOCX, Markdown, and plain text.
- Include fallback behavior when no grounded answer is available.

Technical checklist:
1. Identify source systems: shared drive, SharePoint, Google Drive, Notion, or exported folders.
2. Define chunking strategy by document type and expected question style.
3. Define embedding runtime: local-first when privacy matters, hybrid only if approved.
4. Define retrieval evaluation: recall@k, citation coverage, tenant isolation, freshness.
5. Define answer policy: cite first, answer second, escalate to human when confidence is low.

Expected delivery artifact:
- architecture diagram
- implementation sequence
- access requirements
- ingestion checklist
- test plan
- production guardrails
