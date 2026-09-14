import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin
from importlib.util import spec_from_file_location, module_from_spec

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
STATE = DATA / "sarkariresult-monitor-state.json"
REGISTRY = DATA / "data" / "government-source-registry.json"
OUT = DATA / "official-verification-state.json"
LOG = DATA / "official-verification-log.json"
CAN = DATA / "canonical-job-records.json"


def load_module(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


engine = load_module("canonical_engine", ROOT / "scripts" / "canonical-record-engine.py")
fields = load_module("job_fields", ROOT / "scripts" / "job-field-extractor.py")

UA = "ONESTOP-Government-Job-Update/1.2"
KEYS = (
    "recruitment", "vacancy", "notification", "apply online", "career",
    "jobs", "application", "admit card", "result", "answer key",
)
DATE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b",
    re.I,
)


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get(url):
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.8,*/*;q=0.1",
            },
        )
        response = urllib.request.urlopen(request, timeout=20)
        return response.status, response.read(1_500_000), response.geturl()
    except Exception as exc:
        return getattr(exc, "code", None), b"", url


def clean(body):
    text = unescape(body.decode("utf-8", "replace"))
    text = re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", "\n", text, flags=re.I | re.S)
    text = re.sub(r"<(?:br|p|div|li|tr|td|th|h[1-6])[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines() if line.strip())


def title(body):
    match = re.search(r"<title[^>]*>(.*?)</title>", body.decode("utf-8", "replace"), re.I | re.S)
    if not match:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", match.group(1))).strip()[:300]


def links(body, base):
    html = body.decode("utf-8", "replace")
    return list(
        dict.fromkeys(
            urljoin(base, href).split("#", 1)[0]
            for href in re.findall(r'href=["\']([^"\']+)["\']', html, re.I)
            if urljoin(base, href).startswith(("http://", "https://"))
        )
    )


def score(a, b):
    left = set(re.findall(r"[a-z0-9]{4,}", a.lower()))
    right = set(re.findall(r"[a-z0-9]{4,}", b.lower()))
    return len(left & right) / len(left) if left else 0


def main():
    now = datetime.now(timezone.utc).isoformat()
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        state = {"status": "source_unavailable", "items": {}}
    try:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        registry = {"sources": []}
    try:
        canonical = json.loads(CAN.read_text(encoding="utf-8"))
    except Exception:
        canonical = {"schemaVersion": 1, "items": {}}

    sources = {item["id"]: item for item in registry.get("sources", []) if item.get("enabled")}
    results = {}
    counts = {"verified": 0, "hold": 0, "checked": 0, "new": 0, "changed": 0, "unchanged": 0}

    for item_id, item in state.get("items", {}).items():
        counts["checked"] += 1
        discovery_url = item.get("url", "")
        discovered_title = item.get("title", "").strip()
        description = item.get("description", "").strip()
        status, body, final_url = get(discovery_url)
        discovery_text = clean(body) if status == 200 and body else description
        discovered_title = title(body) or discovered_title if status == 200 and body else discovered_title

        extracted = fields.normalize_record(
            {
                "title": discovered_title,
                "text": discovery_text,
                "notificationUrl": discovery_url,
                "source": "SarkariResult",
            }
        )
        result = {
            "id": item_id,
            "discoveryUrl": discovery_url,
            "status": "hold",
            "publicationStatus": "hold",
            "checkedAt": now,
            "officialSource": None,
            "checks": {},
            "discoveryAccess": "ok" if status == 200 else "metadata_only",
            "discoveryMode": item.get("discoveryMode", "unknown"),
        }
        result["fields"] = extracted
        result["checks"]["nonempty_title"] = bool(discovered_title)
        result["checks"]["discovery_signal"] = bool(discovered_title or description)
        haystack = (discovered_title + " " + discovery_text).lower()

        candidates = []
        for source_id, source in sources.items():
            source_name = source.get("name", "").lower()
            source_tokens = set(re.findall(r"[a-z0-9]{4,}", source_name))
            haystack_tokens = set(re.findall(r"[a-z0-9]{4,}", haystack))
            overlap = len(source_tokens & haystack_tokens)
            exact = bool(source_name) and source_name in haystack
            if exact or overlap >= 1:
                candidates.append((100 if exact else overlap * 10, source))

        found = []
        for _, source in sorted(candidates, reverse=True, key=lambda pair: pair[0])[:4]:
            source_status, source_body, source_final = get(source["url"])
            if source_status != 200 or not source_body:
                continue
            pages = [(source["url"], source_body, source_final)]
            for page_url in links(source_body, source_final):
                if any(key in page_url.lower() for key in ("recruit", "career", "vacan", "job", "notice", "notification", "advert", "latest")):
                    pages.append((page_url, None, page_url))
            for page_url, page_body, page_base in pages[:18]:
                if page_body is None:
                    page_status, page_body, page_base = get(page_url)
                    if page_status != 200 or not page_body:
                        continue
                official_title = title(page_body)
                official_text = clean(page_body)
                low = official_text.lower()
                match_score = score(discovered_title, official_title + " " + official_text[:20_000])
                if (
                    len(official_text) >= 200
                    and match_score >= 0.25
                    and any(key in low for key in KEYS)
                    and DATE.search(low)
                ):
                    found.append((match_score, source, page_url, official_title))

        if found:
            match_score, source, official_url, official_title = max(found, key=lambda value: value[0])
            result["officialSource"] = {
                "sourceId": source["id"],
                "url": official_url,
                "title": official_title,
                "matchScore": round(match_score, 3),
            }

        result["checks"]["official_notice_url"] = bool(result["officialSource"])
        result["checks"]["trusted_source"] = bool(result["officialSource"])
        result["checks"]["safe_http_urls"] = bool(
            result["officialSource"] and result["officialSource"]["url"].startswith(("http://", "https://"))
        )
        result["checks"]["official_content_match"] = bool(
            result["officialSource"] and result["officialSource"]["matchScore"] >= 0.25
        )

        if all(result["checks"].values()):
            result["status"] = "verified"
            result["publicationStatus"] = "ready"
            result["reason"] = "official_department_match_and_required_checks_passed"
            counts["verified"] += 1
        else:
            failed = [key for key, value in result["checks"].items() if not value]
            result["reason"] = "failed_checks:" + ",".join(failed)
            counts["hold"] += 1

        incoming = dict(extracted)
        incoming.update(
            {
                "jobId": item_id,
                "notificationUrl": extracted.get("notificationUrl") or discovery_url,
                "source": "SarkariResult",
                "verificationStatus": result["status"],
                "publicationStatus": result["publicationStatus"],
                "officialSource": result["officialSource"],
                "lastSeenAt": now,
            }
        )
        canonical, event = engine.upsert(incoming, canonical)
        event_name = str(event.get("event", "unchanged")).lower()
        if event_name in {"created", "new"}:
            counts["new"] += 1
        elif event_name in {"updated", "changed"}:
            counts["changed"] += 1
        else:
            counts["unchanged"] += 1
        result.update(
            {
                "canonicalRecordId": event.get("jobId", item_id),
                "changeEvent": event.get("event", "unchanged"),
                "recordVersion": event.get("recordVersion"),
            }
        )
        results[item_id] = result

    save(CAN, canonical)
    save(
        OUT,
        {
            "schemaVersion": 2,
            "checkedAt": now,
            "sourceStatus": state.get("status"),
            "counts": counts,
            "items": results,
        },
    )
    save(
        LOG,
        {
            "checkedAt": now,
            "status": "ok",
            "counts": counts,
            "strategy": "SarkariResult metadata -> targeted official department verification",
        },
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
