from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SkillDocument:
    name: str
    path: Path
    content: str


def load_skill_documents(skill_dirs: list[Path], selected_skills: list[str] | None = None) -> list[SkillDocument]:
    selected = {name.strip().lower() for name in (selected_skills or []) if name.strip()}
    documents: list[SkillDocument] = []

    for skill_dir in skill_dirs:
        if not skill_dir.exists():
            continue
        for path in sorted(skill_dir.rglob("*.md")):
            name = path.stem.lower()
            if selected and name not in selected:
                continue
            documents.append(
                SkillDocument(
                    name=name,
                    path=path,
                    content=path.read_text(encoding="utf-8").strip(),
                )
            )
    return documents


def render_skill_bundle(skill_docs: list[SkillDocument]) -> str:
    if not skill_docs:
        return "No extra skill files were injected."

    blocks = []
    for doc in skill_docs:
        blocks.append(
            "\n".join(
                [
                    f"## Skill: {doc.name}",
                    f"Source: {doc.path}",
                    "",
                    doc.content,
                ]
            )
        )
    return "\n\n".join(blocks)
