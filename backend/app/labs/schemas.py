from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class LabDefinition:
    id: str
    name: str
    mission: str
    capability: str
    cadence: str
    threshold_pct: float
    metrics: List[str]


@dataclass
class LabRunResult:
    lab_id: str
    baseline_score: float
    new_score: float
    threshold_pct: float
    metrics: Dict[str, Any]
    notes: str = ""

    @property
    def improvement_pct(self) -> float:
        if self.baseline_score <= 0:
            return 0.0
        return ((self.new_score - self.baseline_score) / self.baseline_score) * 100

    @property
    def produces_report(self) -> bool:
        return self.improvement_pct >= self.threshold_pct


@dataclass
class CoreReportDraft:
    lab_id: str
    title: str
    summary: str
    recommendation: str
    evidence: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    risk_level: str
    rollout_plan: str
    rollback_plan: str
    status: str = "proposed"


def to_dict(value: Any) -> Dict[str, Any]:
    return asdict(value)

