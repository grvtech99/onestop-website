#!/usr/bin/env python3
"""Discover official notice links and create review-only draft candidates.

This is intentionally conservative: it never edits public job data and never
marks a notice verified. Government sites differ widely, so this generic
adapter discovers likely HTML/PDF links and lets the existing extractor do
field parsing from text supplied by the notice page.
"""
from __future__ import annotations

import hashlib, json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "government-source-registry.json"
OUT = ROOT / "data" / "government-ingestion-candidates"
TIMEOUT = 20
MAX_LINKS_PER_SOURCE = 40
KEYWORDS = re.compile(r"(recruit|vacanc|career|job|advertisement|notification|admit|result|answer.?key|scholarship|admission|syllabus|engagement|consultant|apprentice|fellow|faculty|exam)", re.I)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "ONESTOP-Government-Notice-Bot/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def links(base: str, body: bytes):
    text = body.decode("utf-8", "ignore")
    found = []
    for raw in re.findall(r'href\\s*=\\s*["\\\']([^"\\\']+)', text, re.I):
        url = urllib.parse.urljoin(base, raw)
        p = urllib.parse.urlparse(url)
        if p.scheme not in ("http", "https"):
            continue
        label = re.sub(r"<[^>]+>", " ", raw)
        if KEYWORDS.search(url) or KEYWORDS.search(label):
            found.append(url)
    return list(dict.fromkeys(found))[:MAX_LINKS_PER_SOURCE]


def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:80] or "notice"


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    count = 0
    failures = 0
    for source in registry.get("sources", []):
        if not source.get("enabled"):
            continue
        base = source.get("url", "")
        try:
            body = fetch(base)
            for url in links(base, body):
                key = hashlib.sha256(url.encode()).hexdigest()[:16]
                path = OUT / f"{slug(source['id'])}-{key}.json"
                if path.exists():
                    continue
                payload = {
                    "schemaVersion": 1,
                    "reviewStatus": "draft",
                    "sourceId": source["id"],
                    "sourceName": source["name"],
                    "sourceUrl": base,
                    "noticeUrl": url,
                    "applyUrl": url,
                    "discoveredAt": now,
                    "verificationRequired": True,
                    "verificationNote": "Candidate discovered from an official source. Open the notice and verify every field before review/approval/publication.",
                    "contentTypeHint": "pdf" if url.lower().split("?")[0].endswith(".pdf") else "html"
                }
                path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                count += 1
        except Exception as exc:
            failures += 1
            print(f"WARN {source.get('id')}: {exc}", file=sys.stderr)
    print(json.dumps({"createdCandidates": count, "sourceFailures": failures}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
