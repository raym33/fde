from app.labs.schemas import LabDefinition


LAB_DEFINITIONS = [
    LabDefinition(
        id="rag_grounding",
        name="RAG Grounding Lab",
        mission="Improve retrieval quality, citations, factual grounding and tenant isolation.",
        capability="Knowledge retrieval and answer grounding",
        cadence="daily",
        threshold_pct=5.0,
        metrics=["recall_at_10", "citation_coverage", "answer_grounding", "tenant_leakage_rate"],
    ),
    LabDefinition(
        id="model_routing_cost",
        name="Model Routing & Cost Lab",
        mission="Optimize the open-source/frontier model mix without damaging strategic quality.",
        capability="Hybrid model routing and TCO control",
        cadence="daily",
        threshold_pct=4.0,
        metrics=["quality_score", "cost_per_1k_tasks", "latency_p95_ms", "premium_escalation_precision"],
    ),
    LabDefinition(
        id="agent_workflow",
        name="Agent Workflow Lab",
        mission="Test planner, verifier, tool-use and recovery patterns for higher task completion.",
        capability="Agent orchestration reliability",
        cadence="daily",
        threshold_pct=5.0,
        metrics=["task_completion_rate", "tool_recovery_rate", "avg_steps", "human_escalation_rate"],
    ),
    LabDefinition(
        id="roi_solutions",
        name="ROI & Solutions Lab",
        mission="Improve ranked recommendations, ROI estimates and budget-fit for Spanish SMEs.",
        capability="Solutions engine and business-case quality",
        cadence="daily",
        threshold_pct=5.0,
        metrics=["roi_calibration", "budget_fit", "catalog_coverage", "payback_accuracy"],
    ),
    LabDefinition(
        id="grc_eu_ai_act",
        name="GRC & EU AI Act Lab",
        mission="Improve EU AI Act readiness, risk classification and governance outputs.",
        capability="AI governance, risk and compliance",
        cadence="daily",
        threshold_pct=5.0,
        metrics=["obligation_coverage", "risk_classification_accuracy", "policy_completeness", "source_coverage"],
    ),
    LabDefinition(
        id="market_intelligence",
        name="Market Intelligence Lab",
        mission="Detect useful updates in models, vendors, regulation and practices for the core.",
        capability="Market and regulatory monitoring",
        cadence="twice_daily",
        threshold_pct=6.0,
        metrics=["freshness_score", "source_diversity", "signal_precision", "duplicate_rate"],
    ),
]


LABS_BY_ID = {lab.id: lab for lab in LAB_DEFINITIONS}

