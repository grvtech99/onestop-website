#!/usr/bin/env python3
"""Source-aware notice discovery helpers. Discovery only; never verifies/publishes."""
from __future__ import annotations
import re
from urllib.parse import urljoin

COMMON = re.compile(r"(recruit|vacanc|career|job|advertisement|notification|admit|result|answer.?key|scholarship|admission|syllabus|engagement|consultant|apprentice|fellow|faculty|exam|tender)", re.I)
KEYWORDS = {
    "ssc": re.compile(r"(notice|recruit|vacanc|admit|result|answer|calendar|exam|candidate|selection)", re.I),
    "upsc": re.compile(r"(recruit|vacanc|examination|admit|result|answer|calendar|notice|candidate|interview)", re.I),
    "employment_news": re.compile(r"(job|recruit|vacanc|employment|advertisement|notification|career|post)", re.I),
}

def classify(source_id: str, url: str, label: str = "") -> str:
    rx = KEYWORDS.get(source_id, COMMON)
    return "high" if rx.search(url) or rx.search(label) else "low"

def discover(source_id: str, base_url: str, html: str):
    """Return high-priority links with anchor text for better title discovery."""
    results = []
    # Capture href plus nearby visible anchor text without requiring an HTML package.
    pattern = re.compile(r'<a\b[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
    for m in pattern.finditer(html):
        raw = re.sub(r"<[^>]+>", " ", m.group(2))
        label = re.sub(r"\s+", " ", raw).strip()
        url = urljoin(base_url, m.group(1).strip())
        if not url.startswith(("http://", "https://")):
            continue
        priority = classify(source_id, url, label)
        if priority == "high":
            results.append({"url": url, "label": label[:240], "priority": priority, "sourceId": source_id})
    seen = set(); out = []
    for x in results:
        if x["url"] not in seen:
            seen.add(x["url"]); out.append(x)
    return out
