import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "data" / "canonical-job-records.json"

SCHEMA_VERSION = 1
IDENTITY_FIELDS = ("organization", "advertisementNumber", "postName", "category")
COMPARISON_FIELDS = (
    "title", "organization", "department", "state", "jobType", "category",
    "vacancies", "qualification", "ageLimit", "applicationStartDate",
    "applicationLastDate", "examDate", "notificationUrl", "applyUrl",
)


def normalize(value):
    if value is None:
        return ""
    value = str(value).lower().strip()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def stable_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def fingerprint(record):
    payload = {field: normalize(record.get(field)) for field in COMPARISON_FIELDS}
    return hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()


def canonical_id(record):
    explicit = normalize(record.get("jobId"))
    if explicit:
        return explicit
    identity = "|".join(normalize(record.get(field)) for field in IDENTITY_FIELDS)
    if not identity.strip("|"):
        identity = "|".join(normalize(record.get(field)) for field in ("title", "notificationUrl"))
    return "job-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]


def canonicalize(raw):
    record = deepcopy(raw)
    record["jobId"] = canonical_id(record)
    record["recordVersion"] = int(record.get("recordVersion", 1))
    record["recordStatus"] = record.get("recordStatus", "draft")
    record["verificationStatus"] = record.get("verificationStatus", "pending_official_source")
    record["publicationStatus"] = record.get("publicationStatus", "hold")
    record["source"] = record.get("source", "SarkariResult")
    record["fingerprint"] = fingerprint(record)
    record["updatedAt"] = datetime.now(timezone.utc).isoformat()
    return record


def classify(old, new):
    if old is None:
        return "NEW"
    changed = [field for field in COMPARISON_FIELDS if normalize(old.get(field)) != normalize(new.get(field))]
    if not changed:
        return "UNCHANGED"
    return "CHANGED"


def merge(old, incoming):
    merged = deepcopy(old)
    for key, value in incoming.items():
        if value not in (None, "", [], {}):
            merged[key] = value
    merged["recordVersion"] = int(old.get("recordVersion", 1)) + 1
    merged["recordStatus"] = "draft"
    merged["verificationStatus"] = "pending_official_source"
    merged["publicationStatus"] = "hold"
    merged["fingerprint"] = fingerprint(merged)
    merged["updatedAt"] = datetime.now(timezone.utc).isoformat()
    return merged


def load_state():
    if not STATE_PATH.exists():
        return {"schemaVersion": SCHEMA_VERSION, "items": {}}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def upsert(incoming, state=None):
    state = state or load_state()
    record = canonicalize(incoming)
    old = state["items"].get(record["jobId"])
    event = classify(old, record)
    if event == "CHANGED":
        record = merge(old, record)
    elif event == "UNCHANGED":
        record = old
    state["items"][record["jobId"]] = record
    return state, {"event": event, "jobId": record["jobId"], "recordVersion": record["recordVersion"]}


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    print(json.dumps({"status": "READY", "schemaVersion": SCHEMA_VERSION, "identityFields": IDENTITY_FIELDS, "comparisonFields": COMPARISON_FIELDS}, indent=2))
