import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "publication-gate.py"
REPORT = ROOT / "test-results" / "publication-gate-test-report.json"


def ready_item():
    return {
        "status": "verified",
        "publicationStatus": "ready",
        "officialSource": {"url": "https://ntpc.co.in/node/266"},
        "fields": {
            "title": "NTPC Assistant Executive (Operation) Recruitment 2026",
            "notificationUrl": "https://www.sarkariresult.com/",
            "source": "SarkariResult",
        },
    }


def run_gate(payload, previous_payload=None, history_payload=None):
    verification = ROOT / "data" / "official-verification-state.json"
    output = ROOT / "data" / "publication-queue.json"
    history = ROOT / "data" / "publication-history.json"
    original_verification = verification.read_text(encoding="utf-8") if verification.exists() else None
    original_output = output.read_text(encoding="utf-8") if output.exists() else None
    original_history = history.read_text(encoding="utf-8") if history.exists() else None
    try:
        verification.parent.mkdir(parents=True, exist_ok=True)
        verification.write_text(json.dumps(payload), encoding="utf-8")
        if previous_payload is None:
            output.unlink(missing_ok=True)
        else:
            output.write_text(json.dumps(previous_payload), encoding="utf-8")
        if history_payload is None:
            history.unlink(missing_ok=True)
        else:
            history.write_text(json.dumps(history_payload), encoding="utf-8")
        completed = subprocess.run([sys.executable, str(GATE)], capture_output=True, text=True)
        queue = json.loads(output.read_text(encoding="utf-8"))
        return completed.returncode, queue
    finally:
        if original_verification is None: verification.unlink(missing_ok=True)
        else: verification.write_text(original_verification, encoding="utf-8")
        if original_output is None: output.unlink(missing_ok=True)
        else: output.write_text(original_output, encoding="utf-8")
        if original_history is None: history.unlink(missing_ok=True)
        else: history.write_text(original_history, encoding="utf-8")


def main():
    ready = {"schemaVersion": 1, "checkedAt": "test", "items": {"pass": ready_item()}}
    hold = {"schemaVersion": 1, "checkedAt": "test", "items": {"hold": {"status": "hold", "publicationStatus": "hold", "officialSource": None}}}
    mixed = {"schemaVersion": 1, "checkedAt": "test", "items": {"pass": ready_item(), "hold": {"status": "hold", "publicationStatus": "hold", "officialSource": None}}}
    rc1, q1 = run_gate(ready)
    rc2, q2 = run_gate(hold)
    rc3, q3 = run_gate(mixed)

    # A previously published active record must survive a temporary source rotation.
    retained = ready_item()
    retained["fields"]["title"] = "Previously Published Active Vacancy"
    retained["fields"]["notificationUrl"] = "https://example.gov.in/recruitment/active"
    retained["fields"]["applicationLastDate"] = "2026-10-30"
    history_payload = {"schemaVersion": 1, "items": [{**retained["fields"], "jobId": "historical-1", "verificationStatus": "verified", "publicationStatus": "ready", "applicationLastDate": "2026-10-30"}]}
    rc4, q4 = run_gate({"schemaVersion": 1, "checkedAt": "test", "items": {}}, history_payload=None, previous_payload=None, history_payload=history_payload)

    passed = (
        rc1 == 0 and q1["readyCount"] == 1 and q1["blockedCount"] == 0
        and rc2 == 0 and q2["readyCount"] == 0 and q2["blockedCount"] == 1
        and rc3 == 0 and q3["readyCount"] == 1 and q3["blockedCount"] == 1
        and rc4 == 0 and q4["readyCount"] == 1 and q4["reusedActiveCount"] == 1
    )
    report = {"schemaVersion": 2, "status": "PASS" if passed else "FAIL", "tests": {
        "verified_is_published": q1,
        "hold_is_blocked": q2,
        "mixed_only_verified_is_published": q3,
        "active_history_is_retained": q4,
    }}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__": sys.exit(main())