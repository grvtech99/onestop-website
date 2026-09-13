#!/usr/bin/env python3
"""Small deterministic smoke tests for Phase 2 government ingestion helpers."""
from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    adapters = load("government_source_adapters", ROOT / "scripts/government-source-adapters.py")
    extractor = load("extract_government_job_draft", ROOT / "scripts/extract-government-job-draft.py")

    html = '<a href="/notice/recruitment.pdf">Junior Engineer Recruitment 2026</a>'
    found = adapters.discover("ssc", "https://ssc.gov.in/", html)
    assert len(found) == 1, found
    assert found[0]["url"] == "https://ssc.gov.in/notice/recruitment.pdf", found[0]
    assert found[0]["label"] == "Junior Engineer Recruitment 2026", found[0]
    assert found[0]["priority"] == "high", found[0]
    assert found[0]["sourceId"] == "ssc", found[0]

    text = (
        "Recruitment 2026. Total Vacancy: 12 posts. "
        "Application Start Date: 01/09/2026. Last Date: 30/09/2026. "
        "Application Fee: Rs 250. Age Limit: 18 to 30 years."
    )
    draft = extractor.extract(text, "https://ssc.gov.in/notice/recruitment.pdf", "Junior Engineer Recruitment 2026")
    assert draft["schemaVersion"] == 3
    assert draft["reviewStatus"] == "draft"
    assert draft["verificationRequired"] is True
    assert draft["fieldConfidence"]["vacancy"]["level"] == "medium"
    assert draft["fieldConfidence"]["eligibility"]["level"] == "low"
    assert draft["noticeUrl"].startswith("https://")
    assert draft["applyUrl"].startswith("https://")

    # Architecture guard: automatic ingestion drafts must not be written to verified drafts.
    ingestion_dir = ROOT / "data/government-ingestion-drafts"
    verified_dir = ROOT / "data/government-verified-drafts"
    assert ingestion_dir.is_dir(), ingestion_dir
    assert verified_dir.is_dir(), verified_dir
    print("OK adapter discovery smoke test")
    print("OK extractor confidence/schema smoke test")
    print("OK draft/verified directory separation guard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
