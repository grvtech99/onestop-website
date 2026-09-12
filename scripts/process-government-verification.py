#!/usr/bin/env python3
import json, os, re, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "data", "government-update-review-queue.json")
OUT_DIR = os.path.join(ROOT, "data", "government-verified-drafts")

comment = os.environ.get("VERIFICATION_COMMENT", "")
issue_number = os.environ.get("ISSUE_NUMBER", "")
issue_title = os.environ.get("ISSUE_TITLE", "Government update verification")
comment_author = os.environ.get("COMMENT_AUTHOR", "grvtech99")

verified = bool(re.search(r"\bVERIFIED\b", comment, re.IGNORECASE))
rejected = bool(re.search(r"\bREJECTED\b", comment, re.IGNORECASE))
if verified and rejected:
    print("ERROR: Comment cannot contain both VERIFIED and REJECTED.")
    sys.exit(2)
if not verified and not rejected:
    print("No VERIFIED or REJECTED marker found; nothing to process.")
    sys.exit(0)

now = datetime.now(timezone.utc).isoformat()

# Update the matching queue item so the review lifecycle is visible and auditable.
queue_changed = False
if os.path.exists(QUEUE):
    try:
        with open(QUEUE, encoding="utf-8") as f:
            queue = json.load(f)
    except (OSError, json.JSONDecodeError):
        queue = {"version": 1, "updatedAt": None, "items": []}
    for item in queue.get("items", []):
        if str(item.get("reviewIssue", "")) == str(issue_number):
            item["status"] = "verified" if verified else "rejected"
            item["statusAt"] = now
            item["statusBy"] = comment_author
            if verified:
                item.pop("rejectionReason", None)
            else:
                reason = re.sub(r"\bREJECTED\b", "", comment, flags=re.IGNORECASE).strip()
                item["rejectionReason"] = reason[:500] if reason else "Rejected during official-source review."
            queue_changed = True
            break
    if queue_changed:
        queue["updatedAt"] = now
        with open(QUEUE, "w", encoding="utf-8") as f:
            json.dump(queue, f, indent=2, ensure_ascii=False)
            f.write("\n")

if rejected:
    print(f"Review issue #{issue_number} marked rejected.")
    sys.exit(0)

match = re.search(r"```json\s*(\{.*?\})\s*```", comment, re.IGNORECASE | re.DOTALL)
if not match:
    print("VERIFIED marker found but no JSON draft block was supplied.")
    sys.exit(2)

try:
    draft = json.loads(match.group(1))
except json.JSONDecodeError as exc:
    print(f"Invalid JSON draft: {exc}")
    sys.exit(2)

required = ["category", "title", "meta", "url", "vacancy", "dates", "eligibility", "fee", "age", "selection", "noticeUrl", "applyUrl"]
missing = [key for key in required if not str(draft.get(key, "")).strip()]
if missing:
    print("Missing required fields:", ", ".join(missing))
    sys.exit(2)

category = str(draft["category"]).strip().lower()
allowed = {"jobs", "admit", "results", "answer", "admission", "scholarship", "syllabus", "important", "local"}
if category not in allowed:
    print("Invalid category:", category)
    sys.exit(2)

for key in ("url", "noticeUrl", "applyUrl"):
    if not re.match(r"^https?://", str(draft[key])):
        print(f"Invalid URL in {key}.")
        sys.exit(2)

draft["reviewStatus"] = "verified"
draft["verifiedAt"] = now
draft["verificationIssue"] = int(issue_number) if issue_number.isdigit() else issue_number
draft["verificationIssueTitle"] = issue_title
draft["verificationBy"] = comment_author
draft["verificationNote"] = "Verified by repository owner against the official source. This is a draft for final publication review; it is not auto-published."

slug = re.sub(r"[^a-z0-9]+", "-", str(draft["title"]).lower()).strip("-")[:60] or "government-update"
os.makedirs(OUT_DIR, exist_ok=True)
out = os.path.join(OUT_DIR, f"{slug}-issue-{issue_number}.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(draft, f, indent=2, ensure_ascii=False)
    f.write("\n")

print("Verified draft written to", out)
if not queue_changed:
    print(f"WARNING: no queue item matched review issue #{issue_number}; draft was still created.")
