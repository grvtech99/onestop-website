#!/usr/bin/env python3
import json, os, re, sys
from datetime import datetime, timezone

comment = os.environ.get("VERIFICATION_COMMENT", "")
issue_number = os.environ.get("ISSUE_NUMBER", "")
issue_title = os.environ.get("ISSUE_TITLE", "Government update verification")

if not re.search(r"\bVERIFIED\b", comment, re.IGNORECASE):
    print("No VERIFIED marker found; nothing to process.")
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

now = datetime.now(timezone.utc).isoformat()
draft["reviewStatus"] = "verified"
draft["verifiedAt"] = now
draft["verificationIssue"] = int(issue_number) if issue_number.isdigit() else issue_number
draft["verificationIssueTitle"] = issue_title
draft["verificationNote"] = "Verified by authorized GitHub issue comment. This is a draft for final publication review; it is not auto-published."

slug = re.sub(r"[^a-z0-9]+", "-", str(draft["title"]).lower()).strip("-")[:60] or "government-update"
out_dir = os.path.join("data", "government-verified-drafts")
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, f"{slug}-issue-{issue_number}.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(draft, f, indent=2, ensure_ascii=False)
    f.write("\n")
print("Verified draft written to", out)
