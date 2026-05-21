#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE_DIR = ROOT / "extensions" / "implementation-engine"

if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from skill_injector import load_skill_documents, render_skill_bundle


LOG = logging.getLogger("implementation_engine")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_swarm_input(
    *,
    client_config: dict,
    service_prompt: str,
    skill_bundle: str,
    question: str | None,
) -> str:
    return "\n".join(
        [
            "# VirtuDirector IA Implementation Request",
            "",
            "## Client configuration",
            "```json",
            json.dumps(client_config, indent=2, ensure_ascii=False),
            "```",
            "",
            "## Service blueprint",
            service_prompt.strip(),
            "",
            "## Injected skills",
            skill_bundle,
            "",
            "## Operator request",
            question.strip() if question else "Generate an implementation-ready package based on the client configuration and service blueprint.",
            "",
            "## Required output",
            "- proposed architecture",
            "- data flow",
            "- implementation steps",
            "- risk and control list",
            "- integration checklist",
            "- rollout plan",
            "- rollback plan",
            "- measurable success criteria",
        ]
    )


def _write_review_checklist(output_dir: Path, client_config: dict) -> None:
    checklist = "\n".join(
        [
            "# Human Review Checklist",
            "",
            f"Client: {client_config.get('client_name', 'unknown')}",
            "",
            "- Confirm the target process and business owner.",
            "- Confirm data sensitivity and whether local runtime is mandatory.",
            "- Confirm the proposed integrations actually exist in the client environment.",
            "- Confirm required approvals before any production action.",
            "- Confirm success metrics, rollback criteria, and human escalation path.",
        ]
    )
    (output_dir / "review_checklist.md").write_text(checklist, encoding="utf-8")


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and optionally launch a VirtuDirector implementation swarm package.")
    parser.add_argument("--client-config", required=True, help="Path to a client JSON configuration file.")
    parser.add_argument("--service-file", required=True, help="Path to a markdown service blueprint.")
    parser.add_argument("--skill-dir", action="append", default=[], help="Directory containing skill markdown files. Can be passed multiple times.")
    parser.add_argument("--skill", action="append", default=[], help="Skill basename to inject, without extension. Can be passed multiple times.")
    parser.add_argument("--question", default="", help="Optional operator request to append to the generated swarm input.")
    parser.add_argument("--output-dir", required=True, help="Directory where generated files will be written.")
    parser.add_argument("--review", action="store_true", help="Write a human review checklist into the output directory.")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s %(name)s: %(message)s")

    client_config_path = Path(args.client_config).resolve()
    service_file_path = Path(args.service_file).resolve()
    output_dir = Path(args.output_dir).resolve()
    skill_dirs = [Path(item).resolve() for item in args.skill_dir]

    if not client_config_path.exists():
        raise SystemExit(f"Client config not found: {client_config_path}")
    if not service_file_path.exists():
        raise SystemExit(f"Service file not found: {service_file_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    client_config = _read_json(client_config_path)
    service_prompt = service_file_path.read_text(encoding="utf-8")
    skill_docs = load_skill_documents(skill_dirs, args.skill)
    skill_bundle = render_skill_bundle(skill_docs)

    swarm_input = _build_swarm_input(
        client_config=client_config,
        service_prompt=service_prompt,
        skill_bundle=skill_bundle,
        question=args.question,
    )

    swarm_input_path = output_dir / "swarm_input.md"
    execution_request_path = output_dir / "execution_request.json"
    command_path = output_dir / "command.txt"

    swarm_input_path.write_text(swarm_input, encoding="utf-8")
    execution_request_path.write_text(
        json.dumps(
            {
                "generated_at": _timestamp(),
                "client_config_path": str(client_config_path),
                "service_file_path": str(service_file_path),
                "skills": [doc.name for doc in skill_docs],
                "question": args.question,
                "review_required": args.review,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    command_path.write_text(
        os.environ.get("IMPLEMENTATION_SWARM_COMMAND", "<not configured>"),
        encoding="utf-8",
    )

    if args.review:
        _write_review_checklist(output_dir, client_config)

    result = _run_external_command(output_dir, swarm_input_path)
    print(json.dumps({"output_dir": str(output_dir), "external_execution": result}, indent=2))
    return 0 if not result.get("executed") or result.get("returncode", 0) == 0 else result["returncode"]


if __name__ == "__main__":
    raise SystemExit(main())
