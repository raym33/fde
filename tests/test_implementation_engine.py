from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "extensions" / "implementation-engine"

if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

from skill_injector import load_skill_documents, render_skill_bundle


def test_skill_injector_loads_named_skills() -> None:
    docs = load_skill_documents(
        [
            ENGINE / "skills" / "base",
            ENGINE / "skills" / "verticals",
        ],
        ["general", "shopify-ecommerce"],
    )

    names = [doc.name for doc in docs]
    assert "general" in names
    assert "shopify-ecommerce" in names
    bundle = render_skill_bundle(docs)
    assert "## Skill: general" in bundle
    assert "## Skill: shopify-ecommerce" in bundle


def test_swarm_launcher_generates_output_package(tmp_path: Path) -> None:
    output_dir = tmp_path / "bundle"
    result = subprocess.run(
        [
            sys.executable,
            str(ENGINE / "swarm_launcher.py"),
            "--client-config",
            str(ENGINE / "config" / "example-client.json"),
            "--service-file",
            str(ENGINE / "services" / "customer-support-automation.md"),
            "--skill-dir",
            str(ENGINE / "skills" / "base"),
            "--skill-dir",
            str(ENGINE / "skills" / "verticals"),
            "--skill",
            "general",
            "--skill",
            "shopify-ecommerce",
            "--output-dir",
            str(output_dir),
            "--review",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["output_dir"] == str(output_dir)
    assert (output_dir / "swarm_input.md").exists()
    assert (output_dir / "execution_request.json").exists()
    assert (output_dir / "review_checklist.md").exists()
