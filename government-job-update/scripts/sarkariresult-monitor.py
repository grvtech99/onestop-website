import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BASE = "https://www.sarkariresult.com/"
UA = "ONESTOP-Government-Job-Update/1.2"
STATE = DATA / "sarkariresult-monitor-state.json"
LOG = DATA / "sarkariresult-monitor-log.json"

INDEXED_QUERIES = (
    "site:sarkariresult.com recruitment vacancy",
    "site:sarkariresult.com government job notification",
    "site:sarkariresult.com latest jobs",
    "site:sarkariresult.com admit card result",
)


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get(url):
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": UA,
                "Accept": "application/xml,text/xml,text/html;q=0.9,*/*;q=0.1",
            },
        )
        response = urllib.request.urlopen(req, timeout=20)
        return response.status, response.read(2_000_000), response.geturl(), None
    except urllib.error.HTTPError as exc:
        return exc.code, b"", url, f"HTTP {exc.code}"
    except Exception as exc:
        return None, b"", url, str(exc)[:300]


def rss_items(body):
    rows = []
    try:
        root = ET.fromstring(body)
        for item in root.iter():
            if item.tag.rsplit("}", 1)[-1] != "item":
                continue
            row = {}
            for child in item:
                tag = child.tag.rsplit("}", 1)[-1]
                if child.text and tag in {"link", "title", "description", "pubDate", "guid"}:
                    row[tag] = child.text.strip()
            if row.get("link"):
                rows.append(row)
    except Exception:
        pass
    return rows


def sitemap_entries(body):
    rows = []
    try:
        root = ET.fromstring(body)
        kind = root.tag.rsplit("}", 1)[-1]
        if kind == "sitemapindex":
            for element in root.iter():
                if element.tag.rsplit("}", 1)[-1] == "loc" and element.text:
                    rows.append({"url": element.text.strip()})
        elif kind == "urlset":
            current = None
            for element in root.iter():
                tag = element.tag.rsplit("}", 1)[-1]
                if tag == "url":
                    current = {}
                elif current is not None and tag in {"loc", "lastmod"} and element.text:
                    current[tag] = element.text.strip()
                if tag == "url" and current is not None and current.get("loc"):
                    rows.append(current)
                    current = None
    except Exception:
        pass
    return rows


def resolve_google_news_link(url):
    try:
        status, body, final, _ = get(url)
        candidate = final
        if candidate.startswith(BASE):
            return candidate
        text = body.decode("utf-8", "replace")
        urls = re.findall(r'https?://[^"\'<>\\s]+', text)
        for found in urls:
            found = urllib.parse.unquote(found).rstrip(".,)")
            if found.startswith(BASE):
                return found
        return None
    except Exception:
        return None


def indexed_sarkariresult_items():
    rows = []
    channels = []
    for query in INDEXED_QUERIES:
        rss_url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
            {"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
        )
        status, body, _, _ = get(rss_url)
        if status != 200 or not body:
            continue
        for item in rss_items(body):
            original = item.get("link", "")
            resolved = resolve_google_news_link(original)
            if resolved and resolved.startswith(BASE):
                item["link"] = resolved
                item["discoveryMode"] = "public-indexed-signal"
                rows.append(item)
        if rows:
            channels.append("public-indexed-signal-google-news-rss")
    return rows, channels


def write_state(status, checked_at, error, items):
    save(
        STATE,
        {
            "schemaVersion": 3,
            "source": "sarkariresult",
            "sourceUrl": BASE,
            "status": status,
            "lastCheckedAt": checked_at,
            "lastSuccessfulDiscoveryAt": checked_at if status == "ok" else None,
            "lastError": error,
            "items": items,
        },
    )


def main():
    checked_at = datetime.now(timezone.utc).isoformat()
    try:
        old = json.loads(STATE.read_text(encoding="utf-8")).get("items", {})
    except Exception:
        old = {}

    log = {
        "checkedAt": checked_at,
        "source": BASE,
        "status": "unknown",
        "new": 0,
        "changed": 0,
        "error": None,
        "discoveryChannels": [],
        "directAccess": "unknown",
    }

    status, body, final, error = get(urllib.parse.urljoin(BASE, "robots.txt"))
    log["directAccess"] = "available" if status == 200 else "unavailable"
    if status == 200:
        rules = body.decode("utf-8", "replace").lower()
        if "user-agent: *" in rules and re.search(r"user-agent:\s*\*.*?disallow:\s*/(?:\s|$)", rules, re.S):
            log.update(status="robots_blocked", error="robots.txt disallows generic crawling")
            write_state("robots_blocked", checked_at, log["error"], old)
            save(LOG, log)
            return 0

    discovered = []

    status, body, _, _ = get(urllib.parse.urljoin(BASE, "feed_rss.xml"))
    if status == 200:
        discovered.extend(
            {
                "url": row["link"],
                "title": row.get("title", ""),
                "description": row.get("description", ""),
                "publishedAt": row.get("pubDate", ""),
                "discoveryMode": "public-rss",
            }
            for row in rss_items(body)
        )
        if discovered:
            log["discoveryChannels"].append("public-rss")

    status, body, final, _ = get(urllib.parse.urljoin(BASE, "sitemap.xml"))
    if status == 200:
        entries = sitemap_entries(body)
        if entries and entries[0].get("url", "").endswith("sitemap.xml"):
            for sitemap in entries[:5]:
                sitemap_status, sitemap_body, _, _ = get(sitemap["url"])
                if sitemap_status == 200:
                    entries = sitemap_entries(sitemap_body)
                    break
        if entries:
            discovered.extend({**entry, "discoveryMode": "public-sitemap"} for entry in entries)
            log["discoveryChannels"].append("public-sitemap")
        elif final.rstrip("/") == BASE.rstrip("/"):
            html = body.decode("utf-8", "replace")
            urls = [urllib.parse.urljoin(BASE, u) for u in re.findall(r'href=["\']([^"\']+)["\']', html, re.I)]
            urls = [u for u in urls if u.startswith(BASE)]
            discovered.extend({"url": u, "discoveryMode": "public-sitemap-redirect-html"} for u in urls)
            if urls:
                log["discoveryChannels"].append("public-sitemap-redirect-html")

    # If direct SarkariResult discovery is unavailable, use only a public indexed
    # signal that resolves back to SarkariResult. This is discovery metadata,
    # not a replacement source and does not bypass access controls.
    if not discovered:
        fallback, channels = indexed_sarkariresult_items()
        discovered.extend(fallback)
        log["discoveryChannels"].extend(channels)

    if not discovered:
        log.update(status="source_unavailable", error="No accessible SarkariResult discovery signal")
        write_state("source_unavailable", checked_at, log["error"], old)
        save(LOG, log)
        return 0

    output = {}
    for row in discovered[:1000]:
        url = row.get("url", "").split("#", 1)[0]
        if not url.startswith(BASE):
            continue
        metadata = "|".join(
            [
                url,
                row.get("title", ""),
                row.get("description", ""),
                row.get("publishedAt", ""),
                row.get("lastmod", ""),
                row.get("discoveryMode", ""),
            ]
        )
        key = hashlib.sha256(url.encode()).hexdigest()[:24]
        fingerprint = hashlib.sha256(metadata.encode()).hexdigest()
        previous = old.get(key, {})
        output[key] = {
            "id": key,
            "url": url,
            "title": row.get("title", ""),
            "description": row.get("description", ""),
            "publishedAt": row.get("publishedAt", ""),
            "lastmod": row.get("lastmod", ""),
            "discoveryMode": row.get("discoveryMode", "public-rss"),
            "fingerprint": fingerprint,
            "discoveredAt": previous.get("discoveredAt", checked_at),
            "lastSeenAt": checked_at,
            "verificationStatus": "pending_official_source",
            "publicationStatus": "hold",
        }
        if key not in old:
            log["new"] += 1
        elif previous.get("fingerprint") != fingerprint:
            log["changed"] += 1

    write_state("ok", checked_at, None, output)
    log["status"] = "ok"
    save(LOG, log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
