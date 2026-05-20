import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from app.core.db import init_db
from app.labs.service import LabsService


def main() -> None:
    os.environ.setdefault("LABS_SQLITE_PATH", str(ROOT / "data" / "virtudirector_labs.sqlite3"))
    init_db()
    service = LabsService()

    print("Catalog:", len(service.list_catalog()), "labs")
    result = service.run_experiment(triggered_by="smoke_test")
    print("Runs:", len(result["runs"]))
    print("Reports proposed:", len(result["reports"]))

    for run in result["runs"]:
        print(
            f"- {run['lab_id']}: {run['baseline_score']} -> {run['new_score']} "
            f"({run['improvement_pct']}%) [{run['status']}]"
        )

    proposed = service.list_reports(status="proposed")
    print("Total proposed reports in DB:", len(proposed))

    if proposed:
        approved = service.decide_report(
            proposed[0]["id"],
            decision="approve",
            decided_by="smoke_test",
            notes="Approved during smoke test.",
        )
        print("Approved report:", approved["id"], approved["status"])

    print("OK")


if __name__ == "__main__":
    main()
