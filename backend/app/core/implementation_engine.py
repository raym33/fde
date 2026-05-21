from __future__ import annotations

import json
import logging
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app.core.opportunities import Opportunity, OpportunityDiagnosis


LOG = logging.getLogger("implementation_engine")

ROOT = Path(__file__).resolve().parents[3]
ENGINE_DIR = ROOT / "extensions" / "implementation-engine"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "implementation_bundles"


SERVICE_FILE_MAP = {
    "support_knowledge_agent": ENGINE_DIR / "services" / "customer-support-automation.md",
    "document_search_copilot": ENGINE_DIR / "services" / "document-search-copilot.md",
    "finance_invoice_automation": ENGINE_DIR / "services" / "invoice-automation.md",
    "executive_ai_governance": ENGINE_DIR / "services" / "ai-governance-rollout.md",
}


def load_skill_documents(skill_dirs: list[Path], selected_skills: list[str] | None = None) -> list[dict]:
    selected = {name.strip().lower() for name in (selected_skills or []) if name.strip()}
    documents: list[dict] = []
    for skill_dir in skill_dirs:
        if not skill_dir.exists():
            continue
        for path in sorted(skill_dir.rglob("*.md")):
            name = path.stem.lower()
            if selected and name not in selected:
                continue
            documents.append(
                {
                    "name": name,
                    "path": path,
                    "content": path.read_text(encoding="utf-8").strip(),
                }
            )
    return documents


def render_skill_bundle(skill_docs: list[dict]) -> str:
    if not skill_docs:
        return "No extra skill files were injected."
    return "\n\n".join(
        "\n".join(
            [
                f"## Skill: {doc['name']}",
                f"Source: {doc['path']}",
                "",
                doc["content"],
            ]
        )
        for doc in skill_docs
    )


def generate_bundle(
    *,
    tenant_id: str,
    client_name: str,
    diagnosis: OpportunityDiagnosis,
    opportunity: Opportunity,
    review: bool = True,
) -> dict:
    output_dir = _make_output_dir(tenant_id, opportunity.id)
    output_dir.mkdir(parents=True, exist_ok=True)

    service_file = SERVICE_FILE_MAP.get(opportunity.id, SERVICE_FILE_MAP["support_knowledge_agent"])
    service_prompt = service_file.read_text(encoding="utf-8")

    skill_names = _default_skill_selection(opportunity)
    skill_dirs = [
        ENGINE_DIR / "skills" / "base",
        ENGINE_DIR / "skills" / "verticals",
    ]
    skill_docs = load_skill_documents(skill_dirs, skill_names)
    skill_bundle = render_skill_bundle(skill_docs)

    request_payload = {
        "generated_at": _timestamp(),
        "tenant_id": tenant_id,
        "client_name": client_name,
        "question": diagnosis.question,
        "company_size": diagnosis.company_size,
        "employee_count": diagnosis.assumed_employee_count,
        "selected_opportunity": opportunity.model_dump(),
        "quick_wins": diagnosis.quick_wins,
        "strategic_bets": diagnosis.strategic_bets,
        "not_now": diagnosis.not_now,
        "roadmap_90_days": diagnosis.roadmap_90_days,
        "missing_context": diagnosis.missing_context,
        "skill_names": skill_names,
        "service_file": str(service_file),
    }

    swarm_input = _build_swarm_input(
        client_name=client_name,
        diagnosis=diagnosis,
        opportunity=opportunity,
        service_prompt=service_prompt,
        skill_bundle=skill_bundle,
    )

    swarm_input_path = output_dir / "swarm_input.md"
    execution_request_path = output_dir / "execution_request.json"
    review_checklist_path = output_dir / "review_checklist.md"
    command_path = output_dir / "command.txt"

    swarm_input_path.write_text(swarm_input, encoding="utf-8")
    execution_request_path.write_text(json.dumps(request_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    command_path.write_text(os.environ.get("IMPLEMENTATION_SWARM_COMMAND", "<not configured>"), encoding="utf-8")

    if review:
        review_checklist_path.write_text(_review_checklist(client_name, opportunity), encoding="utf-8")

    external_execution = _run_external_command(output_dir, swarm_input_path)
    return {
        "output_dir": str(output_dir),
        "service_file": str(service_file),
        "skill_names": skill_names,
        "files": {
            "swarm_input": str(swarm_input_path),
            "execution_request": str(execution_request_path),
            "review_checklist": str(review_checklist_path) if review else None,
            "command": str(command_path),
        },
        "external_execution": external_execution,
    }


def _make_output_dir(tenant_id: str, opportunity_id: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_tenant = tenant_id.replace("/", "-").replace(" ", "-")
    return DEFAULT_OUTPUT_DIR / f"{stamp}-{safe_tenant}-{opportunity_id}"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_skill_selection(opportunity: Opportunity) -> list[str]:
    selected = ["general"]
    haystack = " ".join([opportunity.area, opportunity.title, opportunity.problem, opportunity.ai_solution]).lower()
    if "shopify" in haystack or "ecommerce" in haystack:
        selected.append("shopify-ecommerce")
    return selected


def _build_swarm_input(
    *,
    client_name: str,
    diagnosis: OpportunityDiagnosis,
    opportunity: Opportunity,
    service_prompt: str,
    skill_bundle: str,
) -> str:
    return "\n".join(
        [
            "# VirtuDirector IA Implementation Bundle",
            "",
            f"Client: {client_name}",
            f"Question: {diagnosis.question}",
            f"Selected opportunity: {opportunity.title}",
            "",
            "## Opportunity summary",
            f"- Area: {opportunity.area}",
            f"- Problem: {opportunity.problem}",
            f"- AI solution: {opportunity.ai_solution}",
            f"- Expected value: {opportunity.expected_value}",
            f"- Recommended phase: {opportunity.recommended_phase}",
            f"- Owner: {opportunity.owner}",
            f"- Annual benefit estimate (EUR): {opportunity.annual_benefit_eur}",
            f"- Setup cost estimate (EUR): {opportunity.setup_cost_eur}",
            f"- Monthly cost estimate (EUR): {opportunity.monthly_cost_eur}",
            "",
            "## First experiment",
            opportunity.first_experiment,
            "",
            "## Required data",
            *[f"- {item}" for item in opportunity.data_needed],
            "",
            "## Risks",
            *[f"- {item}" for item in opportunity.risks],
            "",
            "## 90-day roadmap context",
            json.dumps(diagnosis.roadmap_90_days, indent=2, ensure_ascii=False),
            "",
            "## Service blueprint",
            service_prompt.strip(),
            "",
            "## Injected skills",
            skill_bundle,
            "",
            "## Required output",
            "- target architecture",
            "- integration sequence",
            "- required permissions",
            "- data flow and boundary notes",
            "- human review points",
            "- rollout plan",
            "- rollback plan",
            "- KPI definitions",
        ]
    )


def _review_checklist(client_name: str, opportunity: Opportunity) -> str:
    return "\n".join(
        [
            "# Human review checklist",
            "",
            f"Client: {client_name}",
            f"Opportunity: {opportunity.title}",
            "",
            "- Confirm the business owner and implementation owner.",
            "- Confirm the source systems and access model.",
            "- Confirm whether the selected runtime must be local, cloud, or hybrid.",
            "- Confirm approval checkpoints before any production write action.",
            "- Confirm KPI definitions and rollback criteria.",
        ]
    )


def _run_external_command(output_dir: Path, swarm_input_path: Path) -> dict:
    command = os.environ.get("IMPLEMENTATION_SWARM_COMMAND", "").strip()
    if not command:
        return {"executed": False, "reason": "IMPLEMENTATION_SWARM_COMMAND is not set"}

    args = shlex.split(command) + [str(swarm_input_path)]
    LOG.info("Running external implementation command: %s", args)
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    (output_dir / "stdout.txt").write_text(result.stdout or "", encoding="utf-8")
    (output_dir / "stderr.txt").write_text(result.stderr or "", encoding="utf-8")
    return {
        "executed": True,
        "returncode": result.returncode,
        "command": args,
    }
