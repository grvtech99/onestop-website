import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "e2e-candidates.json"
REPORT = ROOT / "test-results" / "e2e-live-report.json"
V4 = ROOT.parent / "scripts" / "government-job-verifier-v4.1.py"


def load_v4():
    spec = importlib.util.spec_from_file_location("government_job_verifier_v41", V4)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_report(report):
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    started = datetime.now(timezone.utc).isoformat()
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    v4 = load_v4()

    # Current controlled live positive case: FreeJobAlert's RITES listing published
    # on 15 Sep 2026, with official RITES links in the article.
    positive = {
        "id": "e2e-rites-2026-v41",
        "url": "https://www.freejobalert.com/articles/rites-individual-consultant-recruitment-2026-apply-online-for-11-posts-3067773",
        "title": "RITES Individual Consultant Recruitment 2026 - Apply Online for 11 Posts",
        "description": "RITES Recruitment 2026 for 11 Individual Consultant posts; applications up to 11 October 2026 through the official RITES website.",
        "discoverySource": "FreeJobAlert",
    }
    negative = {
        "id": "e2e-negative-mismatch-v41",
        "url": positive["url"],
        "title": "UPSC Civil Services Examination 2026",
        "description": "Intentional mismatch: the discovery article is a RITES recruitment, not UPSC Civil Services.",
        "discoverySource": "FreeJobAlert",
    }

    positive_result = v4.verify_one(positive)
    negative_result = v4.verify_one(negative)
    passed = (
        positive_result.get("status") == "verified"
        and positive_result.get("publicationStatus") == "ready"
        and negative_result.get("status") == "hold"
        and negative_result.get("publicationStatus") == "hold"
    )
    report = {
        "schemaVersion": 3,
        "startedAt": started,
        "mode": "controlled-live-e2e-v4.1",
        "fixtureSource": fixture.get("sourceUrl"),
        "productionStateMutation": False,
        "positiveCase": positive_result,
        "negativeCase": negative_result,
        "overall": "PASS" if passed else "FAIL",
    }
    write_report(report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
