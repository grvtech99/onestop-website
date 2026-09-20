#!/usr/bin/env python3
"""Collect candidate headlines from public RSS feeds; does not write to the live blog."""
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

FEEDS = [
    "https://news.google.com/rss/search?q=India+technology+OR+AI+OR+cybersecurity&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=भारत+तकनीक+OR+एआई+OR+साइबर+सुरक्षा&hl=hi&gl=IN&ceid=IN:hi",
    "https://news.google.com/rss/search?q=India+science+OR+education+OR+digital+services&hl=en-IN&gl=IN&ceid=IN:en",
]


def text(node, path):
    el = node.find(path)
    return (el.text or "").strip() if el is not None else ""


def main():
    items, errors = [], []
    for feed_url in FEEDS:
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "GauravsWorldDraftResearch/1.0"})
            with urllib.request.urlopen(req, timeout=20) as response:
                raw = response.read(2_000_000)
            root = ET.fromstring(raw)
            for item in root.findall(".//item"):
                title, link = text(item, "title"), text(item, "link")
                if not title or not link:
                    continue
                items.append({"title": title, "url": link, "published": text(item, "pubDate"),
                              "source": text(item, "source"), "feed": feed_url})
        except Exception as exc:
            errors.append({"feed": feed_url, "error": str(exc)[:300]})

    seen, unique = set(), []
    for item in items:
        key = re.sub(r"\W+", " ", item["title"].lower()).strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(item)

    out = Path("automation/gauravs-world/output")
    out.mkdir(parents=True, exist_ok=True)
    payload = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
               "status": "collected" if unique else "no_candidates",
               "count": len(unique), "candidates": unique[:100], "feed_errors": errors,
               "notice": "Headlines are research leads only. Verify original sources before writing; nothing is published."}
    (out / "news-candidates.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Collected {len(unique)} unique RSS candidates; live blog untouched.")


if __name__ == "__main__":
    main()
