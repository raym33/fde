#!/usr/bin/env python3
"""Recompacta briefs de conocimiento ya ingeridos con la lógica actual."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.knowledge import updates  # noqa: E402


def main() -> int:
    result = updates.recompact_all_briefs()
    print(
        f"Knowledge briefs recompactados: refreshed={result.refreshed} skipped={result.skipped}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
