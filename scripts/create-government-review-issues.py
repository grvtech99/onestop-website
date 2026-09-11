#!/usr/bin/env python3
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "data", "government-update-review-queue.json")
REPO = os.environ.get("GITHUB_REPOSITORY", "grvtech99/onestop-website")

NAMES = {
    "ssc": "Staff Selection Commission (SSC)",
    "upsc_highlights": "UPSC Highlights",
    "upsc_results": "UPSC Final Results",
    "upsc_interviews": "UPSC Interview Schedules",
    "upsc_cds2_2026": "UPSC CDS II 2026",
    "employment_news": "Employment News — All Jobs",
    "nsp_students": "National Scholarship Portal — Students",
    "nsp_schemes": "National Scholarship Portal — Scholarships",
}

def run(*args):
    return subprocess.check_output(args, text=True).strip()

def main():
    if not os.path.exists(QUEUE):
        print("Review queue does not exist; nothing to notify.")
        return 0
    with open(QUEUE, encoding="utf-8") as f:
        queue = json.load(f)
    items = queue.get("items", [])
    for item in items:
        if item.get("status") != "pending":
            continue
        key = item.get("key")
        if not key:
            continue
        marker = f"ONESTOP-REVIEW-KEY: {key}"
        try:
            existing = run("gh", "issue", "list", "--repo", REPO, "--state", "all", "--search", f'"{marker}"', "--json", "number", "--jq", ".[].number")
        except subprocess.CalledProcessError as e:
            print(f"Issue lookup failed for {key}: {e}", file=sys.stderr)
            continue
        if existing:
            print(f"Review issue already exists for {key}: #{existing.splitlines()[0]}")
            continue
        source = NAMES.get(item.get("source"), item.get("source", "Official source"))
        url = item.get("verificationUrl", "")
        body = f"""## ONESTOP Government Update Review\n\n**Source:** {source}\n**Detected:** {item.get('detectedAt', '—')}\n**Source hash:** `{item.get('sourceSha256', '—')}`\n\n### Verification required\nOpen the official source and verify the exact notice details before any public update is prepared. A webpage hash change is **not** evidence of a new vacancy by itself.\n\nPlease verify:\n- Exact notice / recruitment title\n- Vacancy / post count (if applicable)\n- Important dates and closing date\n- Eligibility / qualification\n- Fee (if applicable)\n- Age limit (if applicable)\n- Selection process\n- Official notification / PDF link\n- Official application link\n\n**Official source:** {url}\n\n### Approval protocol\nAfter completing the checks, add a comment containing `VERIFIED` only when every required detail has been checked against the official notice. Use `REJECTED` if the change is irrelevant, duplicated, or cannot be verified.\n\n`{marker}`\n"""
        title = f"[ONESTOP REVIEW] {source} changed"
        try:
            number = run("gh", "issue", "create", "--repo", REPO, "--title", title, "--body", body)
            print(f"Created review issue for {key}: {number}")
        except subprocess.CalledProcessError as e:
            print(f"Issue creation failed for {key}: {e}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
