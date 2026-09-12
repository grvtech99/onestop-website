#!/usr/bin/env python3
"""Extract a conservative structured government-job draft from official notice text.

This tool is intentionally draft-only. It never publishes data and marks uncertain
fields for human verification. It can be fed text copied/extracted from an official
HTML page or PDF by a future ingestion workflow.
"""
import json
import re
import sys
from datetime import datetime, timezone

NA = "VERIFY FROM OFFICIAL NOTICE"

PATTERNS = {
    "vacancy": [r"(?:total\s+)?vacanc(?:y|ies)\s*[:\-]?\s*([0-9,]+)", r"(?:no\.\s*of|number\s+of)\s*(?:posts|vacancies)\s*[:\-]?\s*([0-9,]+)"],
    "fee": [r"(?:application|exam(?:ination)?)\s+fee\s*[:\-]?\s*(₹?\s*[0-9,]+(?:\s*/-)?|nil|no\s+fee)", r"fee\s*[:\-]?\s*(₹?\s*[0-9,]+(?:\s*/-)?|nil|no\s+fee)"],
    "age": [r"(?:age\s+limit|upper\s+age\s+limit|age)\s*[:\-]?\s*([0-9]{1,2}\s*(?:to|-|–)\s*[0-9]{1,2}\s*(?:years?|yrs?)?)"],
    "last_date": [r"(?:last\s+date|closing\s+date|apply\s+(?:online\s+)?by)\s*[:\-]?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{4})"],
    "start_date": [r"(?:start(?:ing)?\s+date|opening\s+date|application\s+(?:start|from))\s*[:\-]?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{4})"],
}


def first_match(text, patterns):
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip()
    return NA


def classify(text):
    t = text.lower()
    if any(x in t for x in ("admit card", "e-admit", "hall ticket")):
        return "admit"
    if any(x in t for x in ("answer key", "answer-key")):
        return "answer"
    if "result" in t:
        return "results"
    if "scholarship" in t:
        return "scholarship"
    if "admission" in t and "recruitment" not in t:
        return "admission"
    if any(x in t for x in ("syllabus", "exam scheme")) and "recruit" not in t:
        return "syllabus"
    return "jobs"


def extract(text, source_url, title=None):
    clean = re.sub(r"\s+", " ", text).strip()
    title = title or (clean[:140] if clean else "Government Update")
    category = classify(clean)
    draft = {
        "schemaVersion": 1,
        "reviewStatus": "draft",
        "sourceUrl": source_url,
        "extractedAt": datetime.now(timezone.utc).isoformat(),
        "category": category,
        "title": title,
        "vacancy": first_match(clean, PATTERNS["vacancy"]),
        "dates": first_match(clean, PATTERNS["start_date"]),
        "lastDate": first_match(clean, PATTERNS["last_date"]),
        "eligibility": NA,
        "fee": first_match(clean, PATTERNS["fee"]),
        "age": first_match(clean, PATTERNS["age"]),
        "selection": NA,
        "noticeUrl": source_url,
        "applyUrl": source_url,
        "verificationRequired": True,
        "verificationNote": "Extraction is a draft only. Verify every field against the official notice before publication."
    }
    if draft["dates"] == NA and draft["lastDate"] != NA:
        draft["dates"] = "Last date: " + draft["lastDate"]
    return draft


def main():
    if len(sys.argv) < 3:
        print("Usage: extract-government-job-draft.py <source-url> <text-file> [title]", file=sys.stderr)
        return 2
    source_url, path = sys.argv[1], sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else None
    with open(path, encoding="utf-8") as f:
        text = f.read()
    print(json.dumps(extract(text, source_url, title), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
