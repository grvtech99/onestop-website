import json, os, re, sys, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "government-job-update" / "data"
STATE = DATA / "sarkariresult-monitor-state.json"
REGISTRY = DATA / "data" / "government-source-registry.json"
OUT = DATA / "official-verification-state.json"
LOG = DATA / "official-verification-log.json"
CAN = DATA / "canonical-job-records.json"

UA = "ONESTOP-Government-Job-Update/4.0"
TIMEOUT = 10
WORKERS = 12
MAX_RECORDS = int(os.environ.get("ONESTOP_VERIFY_MAX_RECORDS", "100"))
MAX_CANDIDATES = 8
MAX_BODY = 1400000

AGGREGATOR_HOSTS = {
    "freejobalert.com", "sarkariresult.com", "fresherslive.com", "jagranjosh.com",
    "testbook.com", "careerpower.in", "sarkarinaukriblog.com", "indgovtjobs.net",
    "sarkariupdates.live", "exampix.com", "inrgovtjobs.com", "sarkarinaukari.it.com",
    "sarkari247.com", "sarkarinaukarisetu.com", "sarkari-naukri.in", "naukriagent.com",
    "naukripatrika.in", "nayawork.in", "naukrichakri.in", "sarkariscan.com",
}
OFFICIAL_TEXT = re.compile(r"\b(official|notification|advertisement|advt|detailed notification|apply online|online application|career|recruitment|vacancy|download)\b", re.I)
JOB_SIGNAL = re.compile(r"\b(recruit|vacan|job|appointment|apprent|notification|constable|teacher|engineer|assistant|officer|clerk|group\s*[abc]|technician|trainee|professor|nurse|steno|driver|advt|employment|admit card|result|answer key|selection|scholarship|fellowship|admission|notice|corrigendum|addendum)\b", re.I)
DATE_RE = re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]20\d{2}|20\d{2}[/-]\d{1,2}[/-]\d{1,2})\b")
ADVT_RE = re.compile(r"\b(?:advt?\.?|advertisement|notification|cen|ref(?:erence)?|file)\s*(?:no\.?|number)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9./_-]{2,})\b", re.I)

def load_module(name, path):
    spec = spec_from_file_location(name, path)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

engine = load_module("canonical_engine", ROOT / "scripts" / "canonical-record-engine.py")
fields = load_module("job_fields", ROOT / "scripts" / "job-field-extractor.py")

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def fetch(url):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "application/pdf,text/html,application/xhtml+xml,*/*;q=0.1",
        })
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read(MAX_BODY), r.geturl(), r.headers.get("Content-Type", "")
    except Exception as exc:
        return getattr(exc, "code", None), b"", url, ""

def clean_html(body):
    text = unescape(body.decode("utf-8", "replace"))
    text = re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>|<noscript[^>]*>.*?</noscript>", " ", text, flags=re.I|re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()

def page_title(body):
    m = re.search(r"<title[^>]*>(.*?)</title>", body.decode("utf-8", "replace"), re.I|re.S)
    return clean_html(m.group(1).encode())[:400] if m else ""

def host(url):
    return urllib.parse.urlparse(url).netloc.lower().split(":")[0].removeprefix("www.")

def domain_matches(h, trusted):
    return h == trusted or h.endswith("." + trusted)

def load_registry():
    trusted, aliases = set(), {}
    try:
        obj = json.loads(REGISTRY.read_text(encoding="utf-8"))
        for src in obj.get("sources", []):
            url, name, sid = src.get("url", ""), (src.get("name") or "").strip().lower(), (src.get("id") or "").strip().lower()
            h = host(url)
            if h: trusted.add(h)
            if name and h: aliases[name] = h
            if sid and h: aliases[sid] = h
    except Exception:
        pass
    trusted.update({
        "sbi.co.in", "rites.com", "hurl.net.in", "concorindia.co.in", "bhel.com",
        "bel-india.in", "hal-india.co.in", "ongcindia.com", "ntpc.co.in", "iocl.com",
        "gailonline.com", "licindia.in", "powergrid.in", "pfcindia.com", "coalindia.in",
        "hpcl.co.in", "bpcl.in", "rcfltd.com", "balmerlawrie.com", "mecl.co.in",
        "ibps.in", "nabard.org",
    })
    return trusted, aliases

TRUSTED_DOMAINS, ORG_ALIASES = load_registry()

def is_trusted_domain(url):
    h = host(url)
    return any(domain_matches(h, d) for d in TRUSTED_DOMAINS)

def is_aggregator(url):
    h = host(url)
    return any(domain_matches(h, d) for d in AGGREGATOR_HOSTS)

def html_links(body, base):
    html = body.decode("utf-8", "replace")
    out, seen = [], set()
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html, re.I|re.S):
        attrs, label = m.group(1), clean_html(m.group(2))
        hm = re.search(r'href\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        if not hm: continue
        u = urllib.parse.urljoin(base, unescape(hm.group(1))).split("#", 1)[0]
        if not u.startswith(("http://", "https://")) or u in seen or is_aggregator(u): continue
        seen.add(u)
        explicit = bool(OFFICIAL_TEXT.search(label))
        trusted = is_trusted_domain(u)
        if explicit or trusted:
            out.append({"url": u, "label": label[:300], "explicit": explicit, "trusted": trusted})
    return out

def source_text(url, body, content_type):
    if "pdf" in (content_type or "").lower() or url.lower().split("?", 1)[0].endswith(".pdf"):
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(body))
            chunks = []
            for page in reader.pages[:40]:
                try: chunks.append(page.extract_text() or "")
                except Exception: pass
            return re.sub(r"\s+", " ", "\n".join(chunks)).strip(), "pdf"
        except Exception:
            return "", "pdf"
    return clean_html(body), "html"

def tokens(s):
    return {x for x in re.findall(r"[a-z0-9]{3,}", (s or "").lower()) if x not in {"the","and","for","online","apply","2024","2025","2026","recruitment","notification","government","govt","posts","post","jobs","job"}}

def org_candidates(title, desc):
    hay = (title + " " + desc).lower()
    out = []
    for name, dom in ORG_ALIASES.items():
        if re.search(r"(?<![a-z])" + re.escape(name) + r"(?![a-z])", hay, re.I): out.append(dom)
    return list(dict.fromkeys(out))[:6]

def match_evidence(candidate_title, candidate_text, item_title, item_desc):
    a, b = tokens(item_title), tokens(candidate_title + " " + candidate_text[:50000])
    overlap = len(a & b) / max(1, len(a))
    job_signal = bool(JOB_SIGNAL.search(candidate_title + " " + candidate_text[:50000]))
    date_signal = bool(DATE_RE.search(candidate_text[:50000]))
    advt = ADVT_RE.findall(candidate_text[:50000]); item_advt = ADVT_RE.findall(item_title + " " + item_desc)
    advt_match = bool(advt and item_advt and any(a.lower() == b.lower() for a in advt for b in item_advt))
    return overlap, job_signal, date_signal, advt_match

def build_fields(item, text, title, notification_url, official_url):
    base = {"title": item.get("title") or title, "text": text[:80000], "notificationUrl": notification_url or official_url or item.get("url", ""), "source": item.get("discoverySource") or "MultiSource", "category": fields.classify_update_type(item.get("title", ""), text[:30000])}
    record = fields.normalize_record(base)
    record["title"] = record.get("title") or item.get("title") or title
    record["source"] = item.get("discoverySource") or "MultiSource"
    record["category"] = base["category"]
    record["updateType"] = base["category"]
    record["officialSource"] = official_url
    return record

def verify_one(item):
    now = datetime.now(timezone.utc).isoformat(); title = (item.get("title") or "").strip(); desc = (item.get("description") or "").strip()
    result = {"id": item["id"], "discoveryUrl": item.get("url", ""), "status": "hold", "publicationStatus": "hold", "checkedAt": now, "officialSource": None, "checks": {}, "evidence": {}, "reason": "not_verified"}
    ds, db, df, dct = fetch(item.get("url", "")) if item.get("url", "").startswith(("http://", "https://")) else (None, b"", item.get("url", ""), "")
    dtext, _ = source_text(df, db, dct)
    candidates = []
    if is_trusted_domain(item.get("url", "")): candidates.append({"url": item.get("url", ""), "label": "discovery source", "explicit": True, "trusted": True})
    if db: candidates.extend(html_links(db, df))
    for dom in org_candidates(title, desc): candidates.append({"url": "https://" + dom + "/", "label": "registry organization domain", "explicit": False, "trusted": True})
    unique, seen = [], set()
    for c in candidates:
        if c["url"] in seen or is_aggregator(c["url"]): continue
        seen.add(c["url"]); unique.append(c)
    unique = unique[:MAX_CANDIDATES]
    fetched = []
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(unique)))) as pool:
        futs = {pool.submit(fetch, c["url"]): c for c in unique}
        for fut in as_completed(futs):
            c = futs[fut]
            try: status, body, final, ctype = fut.result()
            except Exception: continue
            if status != 200 or not body: continue
            text, mode = source_text(final, body, ctype)
            if len(text) >= 120: fetched.append((c, final, text, mode, page_title(body) if mode == "html" else ""))
    best = None
    for c, final, text, mode, ptitle in fetched:
        overlap, job_signal, date_signal, advt_match = match_evidence(ptitle, text, title, desc)
        trusted = bool(c.get("trusted") or is_trusted_domain(final) or c.get("explicit"))
        explicit = bool(c.get("explicit")); score = (40 if trusted else 0) + (20 if explicit else 0) + min(25, round(overlap * 25)) + (10 if job_signal else 0) + (5 if date_signal else 0) + (15 if advt_match else 0)
        specific_path = bool(re.search(r"(recruit|career|vacan|notice|notification|advert|apply|job|result|admit|answer|syllabus|admission)", urllib.parse.urlparse(final).path, re.I))
        if specific_path: score += 5
        evidence = {"score": min(score, 120), "trustedDomain": trusted, "explicitOfficialLink": explicit, "titleOverlap": round(overlap, 3), "jobSignal": job_signal, "dateSignal": date_signal, "advertisementMatch": advt_match, "specificOfficialPath": specific_path, "mode": mode}
        if best is None or evidence["score"] > best[0]["score"]: best = (evidence, final, text, ptitle)
    if best:
        evidence, official_url, official_text, official_title = best; result["evidence"] = evidence
        verified = evidence["score"] >= 65 and evidence["trustedDomain"] and evidence["jobSignal"] and evidence["titleOverlap"] >= 0.12 and (evidence["advertisementMatch"] or evidence["specificOfficialPath"] or evidence["explicitOfficialLink"])
        result["officialSource"] = {"sourceId": "official-source-v4", "url": official_url, "title": official_title, "sourceType": "official_pdf" if evidence["mode"] == "pdf" else "official_html", "matchScore": evidence["score"]}
        result["fields"] = build_fields(item, official_text, official_title, official_url, official_url)
        result["checks"] = {"nonempty_title": bool(title), "discovery_fetched": bool(dtext or desc), "official_source_resolved": bool(official_url), "trusted_official_domain": bool(evidence["trustedDomain"]), "content_match": bool(evidence["titleOverlap"] >= 0.12), "job_signal": bool(evidence["jobSignal"]), "publication_evidence": bool(evidence["advertisementMatch"] or evidence["specificOfficialPath"] or evidence["explicitOfficialLink"])}
        if verified and all(result["checks"].values()): result["status"], result["publicationStatus"], result["reason"] = "verified", "ready", "v4_official_source_and_content_verified"
        else: result["reason"] = "v4_hold_insufficient_official_evidence"
    else:
        result["fields"] = build_fields(item, dtext or desc, title, item.get("url", ""), "")
        result["checks"] = {"nonempty_title": bool(title), "discovery_fetched": bool(dtext or desc), "official_source_resolved": False, "trusted_official_domain": False, "content_match": False, "job_signal": False, "publication_evidence": False}
        result["reason"] = "v4_no_official_source_resolved"
    return result

def main():
    now = datetime.now(timezone.utc).isoformat(); state = json.loads(STATE.read_text(encoding="utf-8"))
    try: canonical = json.loads(CAN.read_text(encoding="utf-8"))
    except Exception: canonical = {"schemaVersion": 1, "items": {}}
    try: previous = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception: previous = {}
    items = list(state.get("items", {}).items()); items.sort(key=lambda p: p[1].get("lastSeenAt") or p[1].get("lastDiscoveredAt") or p[1].get("discoveredAt") or "", reverse=True)
    prev_items = previous.get("items", {}) if isinstance(previous.get("items", {}), dict) else {}
    items.sort(key=lambda p: 0 if prev_items.get(p[0], {}).get("status") != "verified" else 1)
    selected, skipped = items[:MAX_RECORDS], items[MAX_RECORDS:]
    results = {}; counts = {"verified": 0, "hold": 0, "checked": 0, "new": 0, "changed": 0, "unchanged": 0, "skipped": len(skipped), "selectionLimit": MAX_RECORDS}
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(verify_one, item): (item_id, item) for item_id, item in selected}
        for fut in as_completed(futs):
            item_id, item = futs[fut]
            try: result = fut.result()
            except Exception as exc:
                result = {"id": item_id, "discoveryUrl": item.get("url", ""), "status": "hold", "publicationStatus": "hold", "checkedAt": now, "officialSource": None, "checks": {"verifier_error": False}, "reason": "v4_verifier_exception:" + type(exc).__name__, "fields": build_fields(item, item.get("description", ""), item.get("title", ""), item.get("url", ""), "")}
            results[item_id] = result; counts["checked"] += 1; counts["verified"] += int(result.get("status") == "verified"); counts["hold"] += int(result.get("status") != "verified")
            incoming = dict(result.get("fields", {})); incoming.update({"jobId": item_id, "notificationUrl": incoming.get("notificationUrl") or item.get("url", ""), "source": item.get("discoverySource") or "MultiSource", "verificationStatus": result.get("status", "hold"), "publicationStatus": result.get("publicationStatus", "hold"), "officialSource": result.get("officialSource"), "lastSeenAt": now})
            canonical, event = engine.upsert(incoming, canonical); ev = str(event.get("event", "unchanged")).lower(); counts["new" if ev in ("created", "new") else "changed" if ev in ("updated", "changed") else "unchanged"] += 1; result["canonicalRecordId"] = event.get("jobId", item_id); result["changeEvent"] = event.get("event", "unchanged")
    for item_id, item in skipped:
        results[item_id] = {"id": item_id, "discoveryUrl": item.get("url", ""), "status": "hold", "publicationStatus": "hold", "checkedAt": now, "officialSource": None, "checks": {"deferred_due_to_run_bound": False}, "reason": "deferred_due_to_v4_verification_run_bound", "fields": build_fields(item, item.get("description", ""), item.get("title", ""), item.get("url", ""), "")}
    save(CAN, canonical); save(OUT, {"schemaVersion": 8, "engine": "official-verification-v4", "checkedAt": now, "sourceStatus": state.get("status"), "counts": counts, "items": results}); save(LOG, {"checkedAt": now, "status": "ok", "engine": "official-verification-v4", "counts": counts, "strategy": "Resolve official sources from trusted registry, explicit official links, organization-domain mappings and official HTML/PDF content; aggregators are discovery-only."})
    print(json.dumps({"status": "PASS", "engine": "official-verification-v4", **counts}, indent=2))

if __name__ == "__main__": sys.exit(main())
