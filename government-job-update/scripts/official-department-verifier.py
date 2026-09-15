import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
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

UA = "ONESTOP-Government-Job-Update/2.0"
TIMEOUT = 5
WORKERS = 12
MAX_RECORDS = 120
MAX_LINKS = 12
JOB_WORDS = ("recruitment", "vacancy", "notification", "apply", "posts", "post", "admit card", "result", "answer key", "exam", "job", "career", "selection")
GOV_HINTS = ("gov.in", "nic.in", "ac.in", "edu.in", "govt.in")


def load_module(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

engine = load_module("canonical_engine", ROOT / "scripts" / "canonical-record-engine.py")
fields = load_module("job_fields", ROOT / "scripts" / "job-field-extractor.py")


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*;q=0.1"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read(700_000), r.geturl()
    except Exception as exc:
        return getattr(exc, "code", None), b"", url


def html_text(body):
    s = unescape(body.decode("utf-8", "replace"))
    s = re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def title_of(body):
    m = re.search(r"<title[^>]*>(.*?)</title>", body.decode("utf-8", "replace"), re.I | re.S)
    return html_text(m.group(1).encode())[:300] if m else ""


def official(url):
    host = urlparse(url).netloc.lower().split(":")[0]
    return any(host == h or host.endswith("." + h) for h in GOV_HINTS)


def links(body, base):
    html = body.decode("utf-8", "replace")
    out = []
    for href in re.findall(r'href=["\']([^"\']+)["\']', html, re.I):
        u = urljoin(base, unescape(href)).split("#", 1)[0]
        if not u.startswith(("http://", "https://")) or u in out:
            continue
        low = u.lower()
        if official(u) or any(k in low for k in ("recruit", "career", "vacan", "notice", "notification", "advert", "apply", "job", "result", "admit")):
            out.append(u)
        if len(out) >= MAX_LINKS:
            break
    return out


def score(title, official_title, body_text):
    a = set(re.findall(r"[a-z0-9]{4,}", title.lower()))
    b = set(re.findall(r"[a-z0-9]{4,}", (official_title + " " + body_text[:10000]).lower()))
    return round(len(a & b) / len(a), 3) if a else 0.0


def verify_one(item, old):
    item_id = item["id"]
    previous = old.get(item_id, {})
    if previous.get("status") == "verified" and previous.get("officialSource"):
        result = dict(previous)
        result["checkedAt"] = datetime.now(timezone.utc).isoformat()
        result["verificationReused"] = True
        return result

    now = datetime.now(timezone.utc).isoformat()
    title = item.get("title", "").strip()
    desc = item.get("description", "").strip()
    result = {
        "id": item_id, "discoveryUrl": item.get("url", ""), "status": "hold", "publicationStatus": "hold",
        "checkedAt": now, "officialSource": None, "checks": {},
        "discoveryAccess": "targeted_metadata", "discoveryMode": item.get("discoveryMode", "unknown")
    }
    result["fields"] = fields.normalize_record({"title": title, "text": desc, "notificationUrl": item.get("url", ""), "source": item.get("discoverySource", "MultiSource")})
    result["checks"]["nonempty_title"] = bool(title)
    result["checks"]["discovery_signal"] = bool(title or desc)

    # Do not crawl government portals blindly. First inspect only the discovery item page,
    # in parallel, and accept only an explicit government-domain link as an official candidate.
    discovery_url = item.get("url", "")
    status, body, final = get(discovery_url) if discovery_url.startswith(("http://", "https://")) else (None, b"", discovery_url)
    candidates = []
    if body and status == 200:
        candidates = [u for u in links(body, final) if official(u)][:MAX_LINKS]
        if official(final):
            candidates.insert(0, final)
    candidates = list(dict.fromkeys(candidates))[:MAX_LINKS]

    found = []
    # Official candidates are checked concurrently, with a hard per-record bound.
    if candidates:
        with ThreadPoolExecutor(max_workers=min(6, len(candidates))) as pool:
            futures = {pool.submit(get, u): u for u in candidates}
            for future in as_completed(futures):
                u = futures[future]
                try:
                    ps, page, resolved = future.result()
                except Exception:
                    continue
                if ps != 200 or not page:
                    continue
                ot = title_of(page)
                txt = html_text(page)
                low = txt.lower()
                sc = score(title, ot, txt)
                has_job_signal = any(k in (title + " " + txt[:12000]).lower() for k in JOB_WORDS)
                has_year = bool(re.search(r"\b20\d{2}\b", txt[:20000]))
                if len(txt) >= 120 and sc >= 0.15 and has_job_signal and has_year and official(resolved):
                    found.append((sc, resolved, ot))

    if found:
        sc, url, ot = max(found, key=lambda x: x[0])
        result["officialSource"] = {"sourceId": "official-government-domain", "url": url, "title": ot, "matchScore": sc}

    result["checks"]["official_notice_url"] = bool(result["officialSource"])
    result["checks"]["trusted_source"] = bool(result["officialSource"])
    result["checks"]["safe_http_urls"] = bool(result["officialSource"] and result["officialSource"]["url"].startswith(("http://", "https://")))
    result["checks"]["official_content_match"] = bool(result["officialSource"] and result["officialSource"]["matchScore"] >= 0.15)
    if all(result["checks"].values()):
        result["status"], result["publicationStatus"] = "verified", "ready"
        result["reason"] = "explicit_official_government_link_and_content_match"
    else:
        result["reason"] = "failed_checks:" + ",".join(k for k, v in result["checks"].items() if not v)
    return result


def main():
    now = datetime.now(timezone.utc).isoformat()
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"status": "source_unavailable", "items": {}}
    canonical = json.loads(CAN.read_text(encoding="utf-8")) if CAN.exists() else {"schemaVersion": 1, "items": {}}
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"items": {}}
    all_items = list(state.get("items", {}).items())

    # Fast path: prioritize likely job records and bound the amount of network work per run.
    def priority(pair):
        _, x = pair
        s = (x.get("title", "") + " " + x.get("description", "")).lower()
        return (0 if any(k in s for k in JOB_WORDS) else 1, -len(s))
    all_items.sort(key=priority)
    selected = all_items[:MAX_RECORDS]
    skipped = all_items[MAX_RECORDS:]

    results = {}
    counts = {"verified": 0, "hold": 0, "checked": 0, "new": 0, "changed": 0, "unchanged": 0, "reused": 0, "skipped": len(skipped)}

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(verify_one, item, previous.get("items", {})): (item_id, item) for item_id, item in selected}
        for future in as_completed(futures):
            item_id, item = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {"id": item_id, "discoveryUrl": item.get("url", ""), "status": "hold", "publicationStatus": "hold", "checkedAt": now, "officialSource": None, "checks": {"verifier_error": False}, "reason": "verifier_exception:" + type(exc).__name__}
            results[item_id] = result
            counts["checked"] += 1
            counts["reused"] += int(bool(result.get("verificationReused")))
            if result.get("status") == "verified": counts["verified"] += 1
            else: counts["hold"] += 1

            incoming = dict(result.get("fields", {}))
            incoming.update({"jobId": item_id, "notificationUrl": incoming.get("notificationUrl") or item.get("url", ""), "source": item.get("discoverySource", "MultiSource"), "verificationStatus": result.get("status", "hold"), "publicationStatus": result.get("publicationStatus", "hold"), "officialSource": result.get("officialSource"), "lastSeenAt": now})
            canonical, event = engine.upsert(incoming, canonical)
            ev = str(event.get("event", "unchanged")).lower()
            counts["new" if ev in ("created", "new") else "changed" if ev in ("updated", "changed") else "unchanged"] += 1
            result.update({"canonicalRecordId": event.get("jobId", item_id), "changeEvent": event.get("event", "unchanged"), "recordVersion": event.get("recordVersion")})

    # Skipped records are explicitly held, without network requests, so the run stays bounded.
    for item_id, item in skipped:
        result = {"id": item_id, "discoveryUrl": item.get("url", ""), "status": "hold", "publicationStatus": "hold", "checkedAt": now, "officialSource": None, "checks": {"deferred_due_to_run_bound": False}, "reason": "deferred_due_to_verification_run_bound"}
        result["fields"] = fields.normalize_record({"title": item.get("title", ""), "text": item.get("description", ""), "notificationUrl": item.get("url", ""), "source": item.get("discoverySource", "MultiSource")})
        results[item_id] = result

    save(CAN, canonical)
    save(OUT, {"schemaVersion": 4, "checkedAt": now, "sourceStatus": state.get("status"), "counts": counts, "items": results})
    save(LOG, {"checkedAt": now, "status": "ok", "counts": counts, "strategy": "Fast bounded verification: 12-way parallel discovery-page checks, explicit official-domain links only, no blind government crawling, verified-record reuse"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
