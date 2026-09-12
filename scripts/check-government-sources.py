#!/usr/bin/env python3
import hashlib, json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(ROOT, "data", "government-source-registry.json")
OUT = os.path.join(ROOT, "data", "government-source-snapshots.json")
QUEUE = os.path.join(ROOT, "data", "government-update-review-queue.json")
MAX_HISTORY = 30
MAX_WORKERS = 8
TIMEOUT = 20
RETRIES = 2


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def load_sources():
    registry = load_json(REGISTRY, {})
    sources = registry.get("sources", [])
    enabled = {}
    for item in sources:
        if not item.get("enabled", True):
            continue
        source_id = str(item.get("id", "")).strip()
        url = str(item.get("url", "")).strip()
        if source_id and url.startswith(("http://", "https://")):
            enabled[source_id] = item
    if not enabled:
        raise RuntimeError("No enabled official sources found in government-source-registry.json")
    return enabled


def fetch(source):
    url = source["url"]
    last_error = None
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ONESTOP-Government-Source-Monitor/2.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                body = r.read()
                return {
                    "httpStatus": r.status,
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "bytes": len(body),
                    "attempts": attempt,
                }
        except Exception as exc:
            last_error = exc
            if attempt < RETRIES:
                time.sleep(1.5 * attempt)
    raise last_error


def main():
    sources = load_sources()
    old_data = load_json(OUT, {})
    old = old_data.get("sources", {})
    now = datetime.now(timezone.utc).isoformat()
    result = {"checkedAt": now, "registryVersion": load_json(REGISTRY, {}).get("version", 1), "sources": {}, "changed": [], "failed": []}

    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(sources))) as pool:
        futures = {pool.submit(fetch, source): (name, source) for name, source in sources.items()}
        for future in as_completed(futures):
            name, source = futures[future]
            try:
                fetched = future.result()
                previous = old.get(name, {}).get("sha256")
                state = "changed" if previous and previous != fetched["sha256"] else ("baseline" if not previous else "unchanged")
                result["sources"][name] = {
                    "name": source.get("name", name),
                    "type": source.get("type", "Government"),
                    "category": source.get("category", "Government Updates"),
                    "url": source["url"],
                    **fetched,
                    "state": state,
                }
                if state == "changed":
                    result["changed"].append(name)
                print(f"{name}: HTTP {fetched['httpStatus']} {state}")
            except Exception as exc:
                result["failed"].append(name)
                result["sources"][name] = {
                    "name": source.get("name", name),
                    "type": source.get("type", "Government"),
                    "category": source.get("category", "Government Updates"),
                    "url": source["url"],
                    "state": "failed",
                    "error": str(exc)[:300],
                }
                print(f"{name}: FAILED — {exc}")

    result["changed"].sort()
    result["failed"].sort()
    previous_history = old_data.get("history", [])
    entry = {
        "checkedAt": now,
        "changed": result["changed"],
        "failed": result["failed"],
        "states": {k: v.get("state") for k, v in sorted(result["sources"].items())},
    }
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
                "sourceName": source.get("name"),
                "sourceType": source.get("type"),
                "category": source.get("category"),
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
        print(f"No official source content changes detected across {len(sources)} enabled sources.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
