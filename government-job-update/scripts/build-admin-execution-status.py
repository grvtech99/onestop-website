#!/usr/bin/env python3
"""Build a public, read-only snapshot of this workflow's step execution state."""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "data" / "admin-execution-status.json"

def outcome(name: str) -> str:
    value = os.environ.get(name, "unknown").strip().lower()
    return value.upper() if value else "UNKNOWN"

def run_url() -> str | None:
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if not repo or not run_id:
        return None
    return f"{server}/{repo}/actions/runs/{run_id}"

now = datetime.now(timezone.utc).isoformat()
steps = {
    "discovery": outcome("STEP_DISCOVERY_OUTCOME"),
    "buffer": outcome("STEP_BUFFER_OUTCOME"),
    "officialVerification": outcome("STEP_VERIFICATION_OUTCOME"),
    "verificationRecovery": outcome("STEP_VERIFICATION_RECOVERY_OUTCOME"),
    "enrichment": outcome("STEP_ENRICHMENT_OUTCOME"),
    "controlledE2E": outcome("STEP_E2E_OUTCOME"),
    "publicationRegression": outcome("STEP_PUBLICATION_REGRESSION_OUTCOME"),
    "publicationQueue": outcome("STEP_PUBLICATION_QUEUE_OUTCOME"),
    "executionStatus": "PASS",
    "adminSnapshot": outcome("STEP_ADMIN_SNAPSHOT_OUTCOME"),
    "stateSave": "PENDING",
}

ordered = list(steps)
failed = [name for name in ordered if steps[name] in {"FAILURE", "CANCELLED", "TIMED_OUT"}]
blocked = [name for name in ordered if steps[name] in {"SKIPPED", "UNKNOWN"}]
current = next((name for name in ordered if steps[name] in {"IN_PROGRESS", "QUEUED"}), None)
if failed:
    overall = "FAILURE"
elif current:
    overall = "IN_PROGRESS"
elif blocked:
    overall = "CHECK"
else:
    overall = "SUCCESS"

out = {
    "schemaVersion": 3,
    "generatedAt": now,
    "workflow": os.environ.get("GITHUB_WORKFLOW"),
    "runId": os.environ.get("GITHUB_RUN_ID"),
    "runNumber": os.environ.get("GITHUB_RUN_NUMBER"),
    "runAttempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
    "commitSha": os.environ.get("GITHUB_SHA"),
    "runUrl": run_url(),
    "overall": overall,
    "currentStep": current,
    "failedSteps": failed,
    "blockedSteps": blocked,
    "steps": steps,
    "note": "Execution status is workflow telemetry only. Discovery uses alternate sources for signals; official government/recruitment sources remain the final authority. Controlled E2E is not production discovery.",
}

OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {OUT}")
