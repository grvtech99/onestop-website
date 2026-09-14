import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "publication-gate.py"


def run_gate(payload):
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp)
        verification = ROOT / "data" / "official-verification-state.json"
        original = verification.read_text(encoding="utf-8") if verification.exists() else None
        try:
            verification.parent.mkdir(parents=True, exist_ok=True)
            verification.write_text(json.dumps(payload), encoding="utf-8")
            completed = subprocess.run([sys.executable, str(GATE)], capture_output=True, text=True)
            queue = json.loads((ROOT / "data" / "publication-queue.json").read_text(encoding="utf-8"))
            return completed.returncode, queue
        finally:
            if original is None:
                verification.unlink(missing_ok=True)
            else:
                verification.write_text(original, encoding="utf-8")
            (ROOT / "data" / "publication-queue.json").unlink(missing_ok=True)


def main():
    ready = {"schemaVersion": 1, "checkedAt": "test", "items": {"pass": {"status": "verified", "publicationStatus": "ready", "officialSource": {"url": "https://ntpc.co.in/node/266"}}}}
    hold = {"schemaVersion": 1, "checkedAt": "test", "items": {"hold": {"status": "hold", "publicationStatus": "hold", "officialSource": None}}}
    mixed = {"schemaVersion": 1, "checkedAt": "test", "items": {"pass": {"status": "verified", "publicationStatus": "ready", "officialSource": {"url": "https://ntpc.co.in/node/266"}}, "hold": {"status": "hold", "publicationStatus": "hold", "officialSource": None}}}

    rc1, q1 = run_gate(ready)
    rc2, q2 = run_gate(hold)
    rc3, q3 = run_gate(mixed)
    passed = rc1 == 0 and q1["readyCount"] == 1 and q1["blockedCount"] == 0 and rc2 == 0 and q2["readyCount"] == 0 and q2["blockedCount"] == 1 and rc3 == 0 and q3["readyCount"] == 1 and q3["blockedCount"] == 1
    report = {"status": "PASS" if passed else "FAIL", "tests": {"verified_is_published": q1, "hold_is_blocked": q2, "mixed_only_verified_is_published": q3}}
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
