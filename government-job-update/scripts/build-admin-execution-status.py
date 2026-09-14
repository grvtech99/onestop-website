#!/usr/bin/env python3
"""Build a public, read-only snapshot of this workflow's step execution state.

Only non-sensitive GitHub Actions metadata and step outcomes supplied by the
workflow are written. Secrets and tokens are never included.
"""
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
    "officialVerification": outcome("STEP_VERIFICATION_OUTCOME"),
    "controlledE2E": outcome("STEP_E2E_OUTCOME"),
    "publicationRegression": outcome("STEP_PUBLICATION_REGRESSION_OUTCOME"),
    "publicationQueue": outcome("STEP_PUBLICATION_QUEUE_OUTCOME"),
    "adminSnapshot": outcome("STEP_ADMIN_SNAPSHOT_OUTCOME"),
}

out = {
    "schemaVersion": 1,
    "generatedAt": now,
    "workflow": os.environ.get("GITHUB_WORKFLOW"),
    "runId": os.environ.get("GITHUB_RUN_ID"),
    "runNumber": os.environ.get("GITHUB_RUN_NUMBER"),
    "runAttempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
    "commitSha": os.environ.get("GITHUB_SHA"),
    "runUrl": run_url(),
    "steps": steps,
    "note": "Step outcomes are workflow execution status only. Production discovery remains dependent on live SarkariResult access; controlled E2E is not production discovery.",
}

OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {OUT}")
