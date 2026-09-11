#!/usr/bin/env python3
import hashlib, json, os, sys, urllib.request
from datetime import datetime, timezone

SOURCES = {
    "ssc": "https://ssc.gov.in/",
    "upsc_highlights": "https://www.upsc.gov.in/highlight",
    "upsc_results": "https://www.upsc.gov.in/recruitment/recruitment-test/results/final-result",
    "upsc_interviews": "https://www.upsc.gov.in/exams-related-info/interview-schedule",
    "upsc_cds2_2026": "https://www.upsc.gov.in/examinations/Combined%20Defence%20Services%20Examination%20%28II%29%2C%202026",
    "employment_news": "https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All",
    "nsp_students": "https://scholarships.gov.in/Students",
    "nsp_schemes": "https://scholarships.gov.in/All-Scholarships",
}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "government-source-snapshots.json")
QUEUE = os.path.join(ROOT, "data", "government-update-review-queue.json")
MAX_HISTORY = 30

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ONESTOP-Government-Source-Monitor/1.0"})
    with urllib.request.urlopen(req, timeout=35) as r:
        body = r.read()
        return r.status, hashlib.sha256(body).hexdigest(), len(body)

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default

def main():
    old_data = load_json(OUT, {})
    old = old_data.get("sources", {})
    now = datetime.now(timezone.utc).isoformat()
    result = {"checkedAt": now, "sources": {}, "changed": [], "failed": []}
    for name, url in SOURCES.items():
        try:
            status, digest, size = fetch(url)
            previous = old.get(name, {}).get("sha256")
            state = "changed" if previous and previous != digest else ("baseline" if not previous else "unchanged")
            result["sources"][name] = {"url": url, "httpStatus": status, "sha256": digest, "bytes": size, "state": state}
            if state == "changed": result["changed"].append(name)
            print(f"{name}: HTTP {status} {state}")
        except Exception as e:
            result["failed"].append(name)
            result["sources"][name] = {"url": url, "state": "failed", "error": str(e)[:300]}
            print(f"{name}: FAILED — {e}")

    previous_history = old_data.get("history", [])
    entry = {"checkedAt": now, "changed": result["changed"], "failed": result["failed"], "states": {k: v.get("state") for k, v in result["sources"].items()}}
    result["history"] = ([entry] + previous_history)[:MAX_HISTORY]

    queue = load_json(QUEUE, {"version": 1, "updatedAt": None, "items": []})
    items = queue.get("items", [])
    existing_keys = {i.get("key") for i in items}
    for name in result["changed"]:
        source = result["sources"][name]
        key = f"{name}:{source.get('sha256')}"
        if key not in existing_keys:
            items.insert(0, {
                "key": key,
                "source": name,
                "detectedAt": now,
                "status": "pending",
                "verificationUrl": source.get("url"),
                "sourceSha256": source.get("sha256"),
                "note": "Official source changed; verify the specific notice before publishing any update."
            })
    queue["version"] = 1
    queue["updatedAt"] = now
    queue["items"] = items[:100]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(QUEUE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)
        f.write("\n")

    if result["failed"]:
        print("One or more official sources failed.")
        return 1
    if result["changed"]:
        print("Official source content changed:", ", ".join(result["changed"]))
    else:
        print("No official source content changes detected.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
