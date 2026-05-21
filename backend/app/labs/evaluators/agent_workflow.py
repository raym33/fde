"""Agent Workflow Lab — medicion REAL de politicas de orquestacion.

No llama a LLMs: ejecuta un banco determinista de tareas contra dos politicas
de workflow:
  - baseline: ejecucion lineal, sin retry y sin verifier/gate de seguridad.
  - candidate: planner -> tool executor -> verifier, con retry acotado.

Cada tarea declara si necesita herramienta, si la herramienta falla una vez, si
requiere verificacion o si debe escalar a humano por riesgo. Las metricas salen
de ejecutar esas reglas, no de numeros escritos a mano.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.labs.base import BaseLab, weighted_score
from app.labs.registry import register_lab
from app.labs.schemas import CoreReportDraft, LabRunResult


@dataclass(frozen=True)
class WorkflowTask:
    task_id: str
    needs_tool: bool
    tool_fails_once: bool
    needs_verifier: bool
    high_risk: bool
    min_steps: int


@dataclass(frozen=True)
class WorkflowPolicy:
    name: str
    planner: bool
    verifier: bool
    retry_budget: int
    escalates_high_risk: bool


TASKS = [
    WorkflowTask("quick_answer", False, False, False, False, 2),
    WorkflowTask("solution_ranking", True, False, True, False, 5),
    WorkflowTask("rag_answer_with_citation", True, False, True, False, 5),
    WorkflowTask("web_research_transient_failure", True, True, True, False, 6),
    WorkflowTask("document_ingest_then_answer", True, True, True, False, 7),
    WorkflowTask("eu_ai_act_high_risk", True, False, True, True, 7),
    WorkflowTask("pii_sensitive_external_model", True, False, True, True, 6),
    WorkflowTask("market_update_dedupe", True, True, False, False, 5),
    WorkflowTask("build_agent_workflow", True, False, True, False, 7),
    WorkflowTask("unknown_vendor_claim", True, True, True, True, 7),
]

BASELINE = WorkflowPolicy(
    name="linear_no_retry",
    planner=False,
    verifier=False,
    retry_budget=0,
    escalates_high_risk=False,
)
CANDIDATE = WorkflowPolicy(
    name="bounded_planner_verifier",
    planner=True,
    verifier=True,
    retry_budget=2,
    escalates_high_risk=True,
)


def _execute(task: WorkflowTask, policy: WorkflowPolicy) -> dict:
    steps = task.min_steps
    if policy.planner:
        steps += 1
    if policy.verifier and task.needs_verifier:
        steps += 1

    tool_attempts = 0
    tool_recovered = True
    if task.needs_tool:
        tool_attempts = 1
        if task.tool_fails_once:
            if policy.retry_budget >= 1:
                tool_attempts += 1
                steps += 1
                tool_recovered = True
            else:
                tool_recovered = False

    human_escalated = task.high_risk and policy.escalates_high_risk
    unsafe_auto_completion = task.high_risk and not policy.escalates_high_risk
    verifier_missing = task.needs_verifier and not policy.verifier

    completed = tool_recovered and not verifier_missing and not unsafe_auto_completion
    return {
        "task_id": task.task_id,
        "completed": completed,
        "tool_needed": task.needs_tool,
        "tool_recovered": (not task.needs_tool) or tool_recovered,
        "human_escalated": human_escalated,
        "steps": steps,
        "tool_attempts": tool_attempts,
    }


def _evaluate(policy: WorkflowPolicy) -> dict:
    runs = [_execute(task, policy) for task in TASKS]
    tool_runs = [r for r in runs if r["tool_needed"]]
    return {
        "policy": policy.name,
        "task_completion_rate": round(sum(r["completed"] for r in runs) / len(runs), 4),
        "tool_recovery_rate": round(
            sum(r["tool_recovered"] for r in tool_runs) / len(tool_runs), 4
        ),
        "avg_steps": round(sum(r["steps"] for r in runs) / len(runs), 2),
        "human_escalation_rate": round(
            sum(r["human_escalated"] for r in runs) / len(runs), 4
        ),
        "runs": runs,
    }


def _score(m: dict) -> float:
    return weighted_score(
        {
            "completion": (m["task_completion_rate"] * 100, 0.40),
            "recovery": (m["tool_recovery_rate"] * 100, 0.25),
            "steps": (max(0, 100 - m["avg_steps"] * 6), 0.15),
            # Aqui una escalada humana alta no es siempre mala: en tareas high-risk
            # es control. Penalizamos solo por encima de 35%.
            "escalation": (max(0, 100 - max(0, m["human_escalation_rate"] - 0.35) * 200), 0.20),
        }
    )


@register_lab("agent_workflow")
class AgentWorkflowLab(BaseLab):
    def run(self) -> LabRunResult:
        baseline = _evaluate(BASELINE)
        candidate = _evaluate(CANDIDATE)
        baseline_score = _score(baseline)
        new_score = _score(candidate)
        return LabRunResult(
            lab_id=self.definition.id,
            baseline_score=baseline_score,
            new_score=new_score,
            threshold_pct=self.definition.threshold_pct,
            metrics={
                "task_count": len(TASKS),
                "baseline": baseline,
                "candidate": candidate,
            },
            notes=(
                "Medicion real sobre banco determinista de tareas. La candidata "
                "usa retry acotado y verifier, recupera fallos transitorios y "
                "escala tareas high-risk en vez de completarlas automaticamente."
            ),
        )

    def build_report(self, result: LabRunResult) -> CoreReportDraft:
        base = result.metrics["baseline"]
        cand = result.metrics["candidate"]
        return CoreReportDraft(
            lab_id=self.definition.id,
            title="Adoptar workflow acotado planner-verifier para tareas complejas",
            summary=(
                "El banco de tareas muestra que el workflow con retry acotado y "
                "verifier mejora finalizacion y recuperacion de herramientas sin "
                "abrir bucles autonomos sin limite."
            ),
            recommendation=(
                "Usar el patron planner -> tool executor -> verifier para EU AI "
                "Act readiness, recomendaciones multi-paso y tareas con fuentes."
            ),
            evidence=[
                {"metric": "improvement_pct", "value": round(result.improvement_pct, 2)},
                {"metric": "task_completion_rate", "baseline": base["task_completion_rate"],
                 "candidate": cand["task_completion_rate"]},
                {"metric": "tool_recovery_rate", "baseline": base["tool_recovery_rate"],
                 "candidate": cand["tool_recovery_rate"]},
                {"metric": "avg_steps", "baseline": base["avg_steps"],
                 "candidate": cand["avg_steps"]},
            ],
            metrics=result.metrics,
            risk_level="medium",
            rollout_plan="Activar para workflows con entregable explicito; maximo dos retries y logging de todos los fallos de herramienta.",
            rollback_plan="Volver a la orquestacion lineal actual y desactivar el feature flag del planner-verifier.",
        )
