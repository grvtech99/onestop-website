#!/usr/bin/env python3
"""Fetch public RSS feeds and produce source-linked candidate digest.

This stage never publishes. It writes candidate data for later editorial review.
"""
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://www.theguardian.com/world/rss",
    "https://www.theguardian.com/technology/rss",
    "https://techcrunch.com/feed/",
    # Google News RSS queries add Hindi-first India coverage and topical variety.
    "https://news.google.com/rss/search?q=AI+OR+cybersecurity+OR+technology+India&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=AI+OR+cyber+security+OR+technology+India&hl=hi&gl=IN&ceid=IN:hi",
    "https://news.google.com/rss/search?q=science+OR+space+OR+education+India&hl=hi&gl=IN&ceid=IN:hi",
]
OUT = Path("automation/gauravs-world/output")
OUT.mkdir(parents=True, exist_ok=True)


def clean(value):
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def parse_feed(url):
    req = urllib.request.Request(url, headers={"User-Agent": "GauravsWorldDraftBot/1.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        root = ET.fromstring(response.read())
    entries = []
    for item in root.findall(".//item"):
        title = clean(item.findtext("title"))
        link = clean(item.findtext("link"))
        desc = clean(re.sub(r"<[^>]+>", " ", item.findtext("description") or ""))
        pub = clean(item.findtext("pubDate"))
        if title and link:
            entries.append({"title": title, "url": link, "summary": desc, "published": pub, "feed": url})
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for item in root.findall("a:entry", ns):
        title = clean(item.findtext("a:title", namespaces=ns))
        link_el = item.find("a:link", ns)
        link = link_el.get("href", "") if link_el is not None else ""
        summary = clean(item.findtext("a:summary", namespaces=ns))
        pub = clean(item.findtext("a:updated", namespaces=ns))
        if title and link:
            entries.append({"title": title, "url": link, "summary": summary, "published": pub, "feed": url})
    return entries


items, errors = [], []
for feed in FEEDS:
    try:
        items.extend(parse_feed(feed))
    except Exception as exc:
        errors.append({"feed": feed, "error": str(exc)[:300]})

seen, unique = set(), []
for item in items:
    key = item["url"].split("?")[0].rstrip("/").lower()
    if key and key not in seen:
        seen.add(key)
        unique.append(item)

payload = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "feeds_collected" if unique else "no_feed_items",
    "draft_only": True,
    "publication_performed": False,
    "candidate_count": len(unique),
    "feed_errors": errors,
    "candidates": unique[:60],
    "next_step": "Editorial selection and bilingual original drafting are still required; no blog endpoint is called.",
}
(OUT / "news-candidates.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Collected {len(unique)} unique RSS candidates; publication disabled.")
if errors:
    print(f"{len(errors)} feed(s) failed; see feed_errors in artifact.")
if not unique:
    print("No candidates collected. Check feed/network availability in Actions logs.")
