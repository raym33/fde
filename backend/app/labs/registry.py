from app.labs.catalog import LABS_BY_ID
from app.labs.evaluators.agent_workflow import AgentWorkflowLab
from app.labs.evaluators.grc_eu_ai_act import GrcEuAiActLab
from app.labs.evaluators.market_intelligence import MarketIntelligenceLab
from app.labs.evaluators.model_routing_cost import ModelRoutingCostLab
from app.labs.evaluators.rag_grounding import RagGroundingLab
from app.labs.evaluators.roi_solutions import RoiSolutionsLab


LAB_CLASSES = {
    "rag_grounding": RagGroundingLab,
    "model_routing_cost": ModelRoutingCostLab,
    "agent_workflow": AgentWorkflowLab,
    "roi_solutions": RoiSolutionsLab,
    "grc_eu_ai_act": GrcEuAiActLab,
    "market_intelligence": MarketIntelligenceLab,
}


def make_lab(lab_id: str):
    if lab_id not in LAB_CLASSES:
        raise KeyError(f"Unknown lab_id: {lab_id}")
    return LAB_CLASSES[lab_id](LABS_BY_ID[lab_id])

