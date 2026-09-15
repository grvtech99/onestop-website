import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from html import unescape
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
STATE = DATA / "sarkariresult-monitor-state.json"
REGISTRY = DATA / "data" / "government-source-registry.json"
OUT = DATA / "official-verification-state.json"
LOG = DATA / "official-verification-log.json"
CAN = DATA / "canonical-job-records.json"
UA = "ONESTOP-Government-Job-Update/1.3"
TIMEOUT = 6
MAX_LINKS = 6


def load_module(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


engine = load_module("canonical_engine", ROOT / "scripts" / "canonical-record-engine.py")
fields = load_module("job_fields", ROOT / "scripts" / "job-field-extractor.py")

ALIASES = {
    "ssc": ("ssc", "staff selection commission"), "upsc": ("upsc", "union public service commission"),
    "rrb": ("rrb", "railway recruitment board"), "nta": ("nta", "national testing agency"),
    "drdo": ("drdo",), "isro": ("isro",), "csir": ("csir",), "icmr": ("icmr",),
    "aiims": ("aiims",), "ugc": ("ugc",), "ibps": ("ibps",), "rbi": ("rbi",),
    "sbi": ("sbi",), "nabard": ("nabard",), "sebi": ("sebi",), "epfo": ("epfo",),
    "esic": ("esic",), "bhel": ("bhel",), "bel": ("bel",), "hal": ("hal",),
    "ongc": ("ongc",), "ntpc": ("ntpc",), "iocl": ("iocl",), "gail": ("gail",),
    "lic": ("lic",), "uppsc": ("uppsc",), "upsssc": ("upsssc",), "bpsc": ("bpsc",),
    "rpsc": ("rpsc",), "mppsc": ("mppsc",), "hpsc": ("hpsc",), "psc_wb": ("wbpsc",),
    "mpsc_maha": ("mpsc",), "tnpsc": ("tnpsc",), "kpsc": ("kpsc",),
    "employment_news": ("employment news",),
}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*;q=0.1"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read(900_000), r.geturl()
    except Exception as exc:
        return getattr(exc, "code", None), b"", url


def text(body):
    s = unescape(body.decode("utf-8", "replace"))
    s = re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", "\n", s, flags=re.I | re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def page_title(body):
    m = re.search(r"<title[^>]*>(.*?)</title>", body.decode("utf-8", "replace"), re.I | re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()[:300] if m else ""


def page_links(body, base):
    html = body.decode("utf-8", "replace")
    urls = []
    for href in re.findall(r'href=["\']([^"\']+)["\']', html, re.I):
        u = urljoin(base, href).split("#", 1)[0]
        if u.startswith(("http://", "https://")) and any(k in u.lower() for k in ("recruit", "career", "vacan", "job", "notice", "notification", "advert", "latest")):
            if u not in urls:
                urls.append(u)
        if len(urls) >= MAX_LINKS:
            break
    return urls


def token_score(a, b):
    left = set(re.findall(r"[a-z0-9]{4,}", a.lower()))
    right = set(re.findall(r"[a-z0-9]{4,}", b.lower()))
    return len(left & right) / len(left) if left else 0


def candidates(title, description, sources, discovery_url):
    low = (title + " " + description).lower()
    host = urlparse(discovery_url).netloc.lower()
    direct = []
    for sid, src in sources.items():
        if urlparse(src.get("url", "")).netloc.lower() == host and host:
            direct.append(src)
    if direct:
        return direct[:2]
    found = []
    for sid, src in sources.items():
        aliases = ALIASES.get(sid, (src.get("name", ""),))
        hits = [a for a in aliases if a and a in low]
        if hits:
            found.append((max(map(len, hits)), src))
    return [src for _, src in sorted(found, reverse=True, key=lambda x: x[0])[:2]]


def verify(item, sources, old_items):
    item_id = item["id"]
    old = old_items.get(item_id, {})
    if old.get("status") == "verified" and old.get("officialSource"):
        old = dict(old)
        old["checkedAt"] = datetime.now(timezone.utc).isoformat()
        old["verificationReused"] = True
        return old

    title = item.get("title", "").strip()
    desc = item.get("description", "").strip()
    result = {
        "id": item_id, "discoveryUrl": item.get("url", ""), "status": "hold",
        "publicationStatus": "hold", "checkedAt": datetime.now(timezone.utc).isoformat(),
        "officialSource": None, "checks": {}, "discoveryAccess": "metadata_only",
        "discoveryMode": item.get("discoveryMode", "unknown"),
    }
    result["fields"] = fields.normalize_record({"title": title, "text": desc, "notificationUrl": item.get("url", ""), "source": item.get("discoverySource", "MultiSource")})
    result["checks"]["nonempty_title"] = bool(title)
    result["checks"]["discovery_signal"] = bool(title or desc)

    found = []
    for src in candidates(title, desc, sources, item.get("url", "")):
        status, body, final = get(src["url"])
        if status != 200 or not body:
            continue
        pages = [(src["url"], body, final)] + [(u, None, u) for u in page_links(body, final)]
        for url, page, base in pages[:MAX_LINKS + 1]:
            if page is None:
                ps, page, base = get(url)
                if ps != 200 or not page:
                    continue
            official_title = page_title(page)
            official_text = text(page)
            low = official_text.lower()
            score = token_score(title, official_title + " " + official_text[:12000])
            if len(official_text) >= 120 and score >= 0.20 and any(k in low for k in ("recruitment", "vacancy", "notification", "apply online", "career", "jobs", "application", "admit card", "result", "answer key")) and re.search(r"\b(?:20\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", low):
                found.append((score, src, url, official_title))

    if found:
        score, src, url, official_title = max(found, key=lambda x: x[0])
        result["officialSource"] = {"sourceId": src["id"], "url": url, "title": official_title, "matchScore": round(score, 3)}
    result["checks"]["official_notice_url"] = bool(result["officialSource"])
    result["checks"]["trusted_source"] = bool(result["officialSource"])
    result["checks"]["safe_http_urls"] = bool(result["officialSource"] and result["officialSource"]["url"].startswith(("http://", "https://")))
    result["checks"]["official_content_match"] = bool(result["officialSource"] and result["officialSource"]["matchScore"] >= 0.20)
    if all(result["checks"].values()):
        result["status"], result["publicationStatus"] = "verified", "ready"
        result["reason"] = "official_department_match_and_required_checks_passed"
    else:
        result["reason"] = "failed_checks:" + ",".join(k for k, v in result["checks"].items() if not v)
    return result


def main():
    now = datetime.now(timezone.utc).isoformat()
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"status": "source_unavailable", "items": {}}
    registry = json.loads(REGISTRY.read_text(encoding="utf-8")) if REGISTRY.exists() else {"sources": []}
    canonical = json.loads(CAN.read_text(encoding="utf-8")) if CAN.exists() else {"schemaVersion": 1, "items": {}}
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"items": {}}
    sources = {x["id"]: x for x in registry.get("sources", []) if x.get("enabled")}
    results = {}
    counts = {"verified": 0, "hold": 0, "checked": 0, "new": 0, "changed": 0, "unchanged": 0, "reused": 0}

    for item_id, item in state.get("items", {}).items():
        counts["checked"] += 1
        result = verify(item, sources, previous.get("items", {}))
        results[item_id] = result
        if result.get("verificationReused"): counts["reused"] += 1
        if result.get("status") == "verified": counts["verified"] += 1
        else: counts["hold"] += 1
        incoming = dict(result.get("fields", {}))
        incoming.update({"jobId": item_id, "notificationUrl": incoming.get("notificationUrl") or item.get("url", ""), "source": item.get("discoverySource", "MultiSource"), "verificationStatus": result.get("status", "hold"), "publicationStatus": result.get("publicationStatus", "hold"), "officialSource": result.get("officialSource"), "lastSeenAt": now})
        canonical, event = engine.upsert(incoming, canonical)
        ev = str(event.get("event", "unchanged")).lower()
        counts["new" if ev in ("created", "new") else "changed" if ev in ("updated", "changed") else "unchanged"] += 1
        result.update({"canonicalRecordId": event.get("jobId", item_id), "changeEvent": event.get("event", "unchanged"), "recordVersion": event.get("recordVersion")})

    save(CAN, canonical)
    save(OUT, {"schemaVersion": 3, "checkedAt": now, "sourceStatus": state.get("status"), "counts": counts, "items": results})
    save(LOG, {"checkedAt": now, "status": "ok", "counts": counts, "strategy": "Targeted official verification with 6-second request timeout and verified-record reuse"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
