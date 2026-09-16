import html
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "government-job-update" / "data"
OUT = DATA / "manual-job-review.json"
UA = "ONESTOP-Manual-Job-Review/1.0"
TIMEOUT = 20
MAX_BYTES = 12_000_000

AGGREGATORS = {
    "sarkariresult.com", "freejobalert.com", "fresherslive.com", "jagranjosh.com",
    "testbook.com", "careerpower.in", "indgovtjobs.net", "sarkarinaukriblog.com",
    "sarkariupdates.live", "exampix.com", "naukrichakri.in", "sarkarinaukari.it.com",
    "sarkari247.com", "sarkariscan.com", "naukriagent.com"
}
OFFICIAL_HINTS = re.compile(r"\b(official|notification|advertisement|advt|recruitment|career|vacancy|apply online|download)\b", re.I)
JOB_HINTS = re.compile(r"\b(recruitment|vacancy|vacancies|notification|advertisement|advt|posts?|job|appointment|apprentice|constable|teacher|engineer|assistant|officer|clerk|technician|trainee|professor|nurse|steno|driver|result|admit card|answer key|scholarship|fellowship|admission)\b", re.I)


def load_extractor():
    p = ROOT / "government-job-update" / "scripts" / "job-field-extractor.py"
    spec = spec_from_file_location("job_fields", p)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

FIELDS = load_extractor()


def host(url):
    return urllib.parse.urlparse(url).netloc.lower().split(":")[0].removeprefix("www.")


def same_domain(a, b):
    return a == b or a.endswith("." + b)


def is_aggregator(url):
    h = host(url)
    return any(same_domain(h, d) for d in AGGREGATORS)


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.1"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return {"ok": r.status == 200, "status": r.status, "body": r.read(MAX_BYTES), "final_url": r.geturl(), "content_type": r.headers.get("Content-Type", "")}
    except Exception as e:
        return {"ok": False, "status": getattr(e, "code", None), "body": b"", "final_url": url, "content_type": "", "error": f"{type(e).__name__}: {e}"}


def clean_html(body):
    text = body.decode("utf-8", "replace")
    text = re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>|<noscript[^>]*>.*?</noscript>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def page_title(body):
    m = re.search(r"<title[^>]*>(.*?)</title>", body.decode("utf-8", "replace"), re.I | re.S)
    return clean_html(m.group(1).encode("utf-8"))[:500] if m else ""


def pdf_text(body):
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(body))
        chunks = []
        for page in reader.pages[:60]:
            try:
                chunks.append(page.extract_text() or "")
            except Exception:
                pass
        return re.sub(r"\s+", " ", " ".join(chunks)).strip()
    except Exception:
        return ""


def content(result):
    if not result["ok"]:
        return "", "html"
    u = result["final_url"]
    ct = result["content_type"].lower()
    if "pdf" in ct or u.lower().split("?", 1)[0].endswith(".pdf"):
        return pdf_text(result["body"]), "pdf"
    return clean_html(result["body"]), "html"


def links(body, base):
    raw = body.decode("utf-8", "replace")
    found = []
    seen = set()
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", raw, re.I | re.S):
        hm = re.search(r'href\s*=\s*["\']([^"\']+)["\']', m.group(1), re.I)
        if not hm:
            continue
        u = urllib.parse.urljoin(base, html.unescape(hm.group(1))).split("#", 1)[0]
        if not u.startswith(("http://", "https://")) or u in seen:
            continue
        seen.add(u)
        label = clean_html(m.group(2).encode("utf-8", "replace"))[:300]
        score = (30 if OFFICIAL_HINTS.search(label) else 0) + (15 if JOB_HINTS.search(label) else 0)
        path_score = 15 if re.search(r"(recruit|career|vacan|notice|notification|advert|apply|job|download)", urllib.parse.urlparse(u).path, re.I) else 0
        if not is_aggregator(u):
            found.append({"url": u, "label": label, "score": score + path_score})
    return sorted(found, key=lambda x: x["score"], reverse=True)[:15]


def token_overlap(a, b):
    stop = {"the", "and", "for", "with", "online", "apply", "2024", "2025", "2026", "recruitment", "notification", "government", "govt", "posts", "post", "jobs", "job"}
    ta = {x for x in re.findall(r"[a-z0-9]{3,}", (a or "").lower()) if x not in stop}
    tb = {x for x in re.findall(r"[a-z0-9]{3,}", (b or "").lower()) if x not in stop}
    return len(ta & tb) / max(1, len(ta))


def official_score(job_title, discovery_text, candidate_url, candidate_title, candidate_text, explicit_score):
    score = explicit_score
    if candidate_url and re.search(r"(recruit|career|vacan|notice|notification|advert|apply|job|download)", urllib.parse.urlparse(candidate_url).path, re.I):
        score += 15
    overlap = token_overlap(job_title, candidate_title + " " + candidate_text[:50000])
    score += min(30, round(overlap * 30))
    if JOB_HINTS.search(candidate_title + " " + candidate_text[:50000]):
        score += 15
    if re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]20\d{2}\b|\b20\d{2}[/-]\d{1,2}[/-]\d{1,2}\b", candidate_text):
        score += 10
    if re.search(r"\b(vacanc(?:y|ies)|total posts?|number of posts?)\b", candidate_text, re.I):
        score += 10
    if re.search(r"\b(last date|closing date|apply online|important dates?)\b", candidate_text, re.I):
        score += 10
    if re.search(r"\b(eligibility|educational qualification|age limit|selection process|pay scale|salary|application fee)\b", candidate_text, re.I):
        score += 10
    return min(score, 130), overlap


def field_status(record):
    required = [
        "title", "organization", "vacancies", "qualification", "ageLimit", "fee",
        "selectionProcess", "salary", "jobLocation", "applicationStartDate",
        "applicationLastDate", "notificationUrl", "applyUrl"
    ]
    optional = ["department", "state", "jobType", "ageRelaxation", "examDate", "documentsRequired", "applicationMode", "vacancyDetails"]
    statuses = {}
    for key in required + optional:
        value = record.get(key)
        present = value not in (None, "", [], {})
        statuses[key] = "FOUND" if present else ("MISSING_REQUIRED" if key in required else "MISSING_OPTIONAL")
    return statuses


def main():
    url = (os.environ.get("JOB_URL") or "").strip()
    if not re.match(r"^https?://", url, re.I):
        print("JOB_URL must be a complete http(s) URL", file=sys.stderr)
        return 2

    checked = datetime.now(timezone.utc).isoformat()
    original = fetch(url)
    discovery_text, discovery_mode = content(original)
    final_url = original["final_url"]
    source_candidates = []
    if original["ok"]:
        source_candidates = links(original["body"], final_url)

    # If the supplied link itself is an official-looking page, evaluate it too.
    candidates = [{"url": final_url, "label": page_title(original["body"]), "score": 20}] if original["ok"] else []
    candidates.extend(source_candidates)
    dedup = []
    seen = set()
    for c in candidates:
        if c["url"] not in seen:
            seen.add(c["url"])
            dedup.append(c)
    candidates = dedup[:16]

    evaluated = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(fetch, c["url"]): c for c in candidates}
        for future in as_completed(futures):
            c = futures[future]
            r = future.result()
            if not r["ok"]:
                continue
            text, mode = content(r)
            if len(text) < 120:
                continue
            title = page_title(r["body"]) if mode == "html" else "Official PDF notification"
            score, overlap = official_score(page_title(original["body"]) or url, discovery_text, r["final_url"], title, text, c["score"])
            evaluated.append({"candidate": c, "result": r, "text": text, "mode": mode, "title": title, "score": score, "overlap": overlap})

    evaluated.sort(key=lambda x: x["score"], reverse=True)
    best = evaluated[0] if evaluated else None

    # A second hop is allowed only from the best HTML candidate: recruitment/career pages often link the real PDF.
    if best and best["mode"] == "html":
        hop_links = links(best["result"]["body"], best["result"]["final_url"])[:10]
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {pool.submit(fetch, c["url"]): c for c in hop_links}
            for future in as_completed(futures):
                c = futures[future]
                r = future.result()
                if not r["ok"]:
                    continue
                text, mode = content(r)
                if len(text) < 120:
                    continue
                title = page_title(r["body"]) if mode == "html" else "Official PDF notification"
                score, overlap = official_score(page_title(original["body"]) or url, discovery_text, r["final_url"], title, text, c["score"] + 20)
                evaluated.append({"candidate": c, "result": r, "text": text, "mode": mode, "title": title, "score": score, "overlap": overlap})
        evaluated.sort(key=lambda x: x["score"], reverse=True)
        best = evaluated[0] if evaluated else best

    official_url = best["result"]["final_url"] if best else (final_url if original["ok"] else "")
    official_text = best["text"] if best else discovery_text
    official_title = best["title"] if best else ""
    source_is_different = bool(best and official_url.rstrip("/") != final_url.rstrip("/"))

    raw = {
        "title": page_title(original["body"]) or official_title,
        "text": official_text,
        "notificationUrl": official_url if best else final_url,
        "source": host(url),
        "category": FIELDS.classify_update_type(page_title(original["body"]), official_text[:30000])
    }
    record = FIELDS.normalize_record(raw)
    if not record.get("notificationUrl"):
        record["notificationUrl"] = official_url
    if best and best["mode"] == "html":
        # Prefer a clearly labelled application URL over the notification page.
        for c in links(best["result"]["body"], official_url):
            if re.search(r"apply|online application|application", c["label"] + " " + c["url"], re.I):
                record["applyUrl"] = c["url"]
                break
    statuses = field_status(record)
    missing_required = [k for k, v in statuses.items() if v == "MISSING_REQUIRED"]
    verification_ok = bool(best and best["score"] >= 70 and best["overlap"] >= 0.08 and len(official_text) >= 1200)
    status = "VERIFIED_NEEDS_INPUT" if verification_ok and missing_required else ("VERIFIED_READY" if verification_ok else "VERIFICATION_REQUIRED")

    output = {
        "schemaVersion": 1,
        "reviewId": checked.replace(":", "").replace(".", ""),
        "checkedAt": checked,
        "inputUrl": url,
        "inputHost": host(url),
        "inputWasAggregator": is_aggregator(url),
        "discoveryFetch": {"ok": original["ok"], "status": original["status"], "finalUrl": final_url, "mode": discovery_mode, "title": page_title(original["body"]), "error": original.get("error")},
        "officialResolution": {
            "status": "RESOLVED" if best else "NOT_RESOLVED",
            "officialUrl": official_url,
            "officialTitle": official_title,
            "mode": best["mode"] if best else None,
            "score": best["score"] if best else 0,
            "titleOverlap": round(best["overlap"], 3) if best else 0,
            "sourceIsDifferentFromInput": source_is_different,
            "candidateCount": len(evaluated)
        },
        "record": record,
        "fieldStatus": statuses,
        "missingRequiredFields": missing_required,
        "status": status,
        "actionRequired": bool(missing_required or not verification_ok),
        "verificationNotes": (
            "Official source resolved and the extracted record is ready except for the listed missing fields."
            if verification_ok and missing_required else
            "Official source and content evidence are sufficient; all required fields were extracted."
            if verification_ok else
            "Do not publish. Official-source evidence is insufficient; inspect the supplied URL and official notification manually."
        )
    }
    DATA.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print("::notice title=ONESTOP Manual Job Review::Status: " + status)
    if missing_required:
        print("::warning title=Fields need admin input::Missing required fields: " + ", ".join(missing_required))
    if not verification_ok:
        print("::warning title=Official verification not sufficient::Do not publish this record yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
