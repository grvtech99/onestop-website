import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
    v4 = load_v4()
    aggregator = b'<html><body><a href="https://www.rites.com/">Official Website</a></body></html>'
    official_home = b'<html><title>RITES</title><body>' + (b"RITES official corporate information. " * 20) + b'<a href="/careers/individual-consultant-recruitment-2026">Individual Consultant Recruitment 2026 Notification</a></body></html>'
    official_job = b'<html><title>RITES Individual Consultant Recruitment 2026</title><body>RITES Individual Consultant Recruitment 2026 Notification. Apply Online. 11 October 2026. Recruitment 11 posts. Official recruitment notification and application details.</body></html>'
    def fake_fetch(url, limit=8000000):
        if "freejobalert.com/article" in url: return 200, aggregator, url, "text/html"
        if url.rstrip("/") == "https://www.rites.com": return 200, official_home, url, "text/html"
        if "individual-consultant-recruitment-2026" in url: return 200, official_job, "https://www.rites.com/careers/individual-consultant-recruitment-2026", "text/html"
        return 404, b"", url, ""
    original_fetch = v4.fetch
    v4.fetch = fake_fetch
    try:
        positive = {"id":"e2e-positive-v41","url":"https://www.freejobalert.com/article","title":"RITES Individual Consultant Recruitment 2026 - Apply Online for 11 Posts","description":"RITES recruitment 2026 for 11 Individual Consultant posts; last date 11 October 2026.","discoverySource":"FreeJobAlert"}
        negative = {"id":"e2e-negative-v41","url":"https://www.freejobalert.com/article","title":"UPSC Civil Services Examination 2026","description":"Intentional mismatch against the RITES discovery article.","discoverySource":"FreeJobAlert"}
        positive_result = v4.verify_one(positive)
        negative_result = v4.verify_one(negative)
    finally:
        v4.fetch = original_fetch
    passed = positive_result.get("status") == "verified" and positive_result.get("publicationStatus") == "ready" and negative_result.get("status") == "hold" and negative_result.get("publicationStatus") == "hold"
    report = {"schemaVersion":4,"startedAt":started,"mode":"controlled-deterministic-e2e-v4.1","productionStateMutation":False,"positiveCase":positive_result,"negativeCase":negative_result,"overall":"PASS" if passed else "FAIL"}
    write_report(report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if passed else 1
if __name__ == "__main__": sys.exit(main())
