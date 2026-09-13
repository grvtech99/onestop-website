#!/usr/bin/env python3
"""Source-aware government notice discovery helpers.

Discovery only; never verifies or publishes. The adapters intentionally remain
small and conservative because official portals change their markup often.
"""
from __future__ import annotations
import re
from urllib.parse import urljoin

COMMON = re.compile(r"(recruit|vacanc|career|job|advertisement|notification|admit|result|answer.?key|scholarship|admission|syllabus|engagement|consultant|apprentice|fellow|faculty|exam|tender)", re.I)
KEYWORDS = {
    "ssc": re.compile(r"(notice|recruit|vacanc|admit|result|answer|calendar|exam|candidate|selection|constable|sub.?inspector|cgl|chsl|je|mts|steno)", re.I),
    "upsc": re.compile(r"(recruit|vacanc|examination|admit|result|answer|calendar|notice|candidate|interview|nda|cds|civil|engineering|geo.?scientist)", re.I),
    "employment_news": re.compile(r"(job|recruit|vacanc|employment|advertisement|notification|career|post|engagement|consultant|apprentice|faculty|scientist)", re.I),
}

# Prefer anchors whose visible text is useful as the notice title. Ignore
# navigation/social links and obvious pagination controls.
IGNORE_LABEL = re.compile(r"^(home|login|register|menu|search|next|previous|back|read more|click here|apply online)$", re.I)


def clean_label(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value[:240]


def classify(source_id: str, url: str, label: str = "") -> str:
    rx = KEYWORDS.get(source_id, COMMON)
    if rx.search(label):
        return "high"
    if rx.search(url):
        return "high"
    return "low"


def source_kind(source_id: str) -> str:
    if source_id in {"ssc", "upsc", "employment_news"}:
        return source_id
    return "generic"


def discover(source_id: str, base_url: str, html: str):
    """Return de-duplicated high-priority official links with title hints."""
    results = []
    pattern = re.compile(r'<a\b[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
    kind = source_kind(source_id)
    for match in pattern.finditer(html):
        raw_href = match.group(1).strip()
        label = clean_label(match.group(2))
        if not raw_href or IGNORE_LABEL.match(label):
            continue
        url = urljoin(base_url, raw_href)
        if not url.startswith(("http://", "https://")):
            continue
        priority = classify(source_id, url, label)
        if priority != "high":
            continue

        # Source-specific signals make the discovery result more useful to
        # downstream extraction without hard-coding a portal's full markup.
        if kind == "ssc" and not (KEYWORDS["ssc"].search(label) or KEYWORDS["ssc"].search(url)):
            continue
        if kind == "upsc" and not (KEYWORDS["upsc"].search(label) or KEYWORDS["upsc"].search(url)):
            continue
        if kind == "employment_news" and not (KEYWORDS["employment_news"].search(label) or KEYWORDS["employment_news"].search(url)):
            continue

        results.append({
            "url": url,
            "label": label,
            "priority": priority,
            "sourceId": source_id,
            "sourceKind": kind,
        })

    seen = set(); out = []
    for item in results:
        key = item["url"].split("#", 1)[0]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out
