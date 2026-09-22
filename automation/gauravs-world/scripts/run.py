#!/usr/bin/env python3
"""Create review-only bilingual drafts from RSS candidates.

Text drafting requires OPENAI_API_KEY. Cover images are manual uploads only;
no image-generation API or image prompt generation is used.
Never publishes to the live blog.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("automation/gauravs-world")
OUT = ROOT / "output"
IMAGE_DIR = ROOT / "images"
CANDIDATES_FILE = OUT / "news-candidates.json"
OUT.mkdir(parents=True, exist_ok=True)
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
MAX_DRAFTS = max(1, min(int(os.getenv("MAX_DRAFTS_PER_RUN", "3")), 5))


def slugify(text):
    text = re.sub(r"[^a-zA-Z0-9\u0900-\u097f]+", "-", text.lower()).strip("-")
    return (text[:70].strip("-") or "news-draft")


def request_json(url, payload, headers=None, timeout=90):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req_headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        raise RuntimeError(f"OpenAI HTTP {exc.code}: {detail}") from exc


def responses_text(result):
    chunks = []
    for item in result.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in ("output_text", "text") and content.get("text"):
                chunks.append(content["text"])
    if chunks:
        return "\n".join(chunks).strip()
    if result.get("output_text"):
        return result["output_text"].strip()
    raise RuntimeError("OpenAI response did not contain output text")


def make_draft(candidate):
    prompt = f'''Create an editorial review draft based only on the supplied source metadata. Do not invent facts, quotes, dates, statistics, or details absent from the metadata. If information is insufficient, explicitly mark it as needing verification. Write useful original bilingual content: Hindi first, then English. Return ONLY valid JSON with keys: title_hi, title_en, slug, category, summary_hi, summary_en, body_hi, body_en, tags (array of 3-6 strings), verification_notes (array), sources (array of objects with title,url,published). Each body should be structured with short paragraphs and headings, not copied from the source. Include source URL exactly as provided. Do not claim independent verification. Keep each language body around 350-550 words when metadata supports it; otherwise make a concise draft and list missing facts.

SOURCE METADATA:
{json.dumps(candidate, ensure_ascii=False)}'''
    result = request_json("https://api.openai.com/v1/responses", {
        "model": MODEL,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        "text": {"format": {"type": "json_object"}},
        "max_output_tokens": 4500,
    })
    raw = responses_text(result)
    try:
        draft = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Model returned invalid JSON: {raw[:500]}") from exc
    required = ["title_hi", "title_en", "summary_hi", "summary_en", "body_hi", "body_en", "sources"]
    missing = [key for key in required if not draft.get(key)]
    if missing:
        raise RuntimeError("Draft missing required fields: " + ", ".join(missing))
    draft["slug"] = slugify(draft.get("slug") or draft["title_en"])
    draft["category"] = draft.get("category") or "Technology"
    draft["tags"] = draft.get("tags") if isinstance(draft.get("tags"), list) else []
    draft["verification_notes"] = draft.get("verification_notes") if isinstance(draft.get("verification_notes"), list) else []
    draft["source_candidate"] = candidate
    draft["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    draft["publication_status"] = "review_draft"
    draft["published"] = False
    return draft


def main():
    if not API_KEY:
        print("ERROR: OPENAI_API_KEY is missing. Add it as a GitHub Actions secret; never commit it.", file=sys.stderr)
        return 2
    if not CANDIDATES_FILE.exists():
        print("ERROR: RSS candidate file missing. Run rss_digest.py first.", file=sys.stderr)
        return 2
    candidates_payload = json.loads(CANDIDATES_FILE.read_text(encoding="utf-8"))
    candidates = candidates_payload.get("candidates", [])
    if not candidates:
        report = {"status": "no_candidates", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "draft_only": True, "publication_performed": False, "feed_errors": candidates_payload.get("feed_errors", [])}
        (OUT / "workflow-status.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("No RSS candidates available; nothing generated.")
        return 0

    drafts_dir = OUT / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    generated, failures = [], []
    for candidate in candidates[:MAX_DRAFTS]:
        try:
            draft = make_draft(candidate)
            slug = draft["slug"]
            target = drafts_dir / f"{slug}.json"
            if target.exists():
                slug = f"{slug}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
                draft["slug"] = slug
                target = drafts_dir / f"{slug}.json"
            # Editors upload the matching cover file manually: images/{slug}.png
            manual_image = IMAGE_DIR / f"{slug}.png"
            if manual_image.exists():
                draft["cover_image"] = f"images/{slug}.png"
                draft["image_status"] = "manual_uploaded"
            else:
                draft["cover_image"] = None
                draft["image_status"] = "manual_pending"
                draft["image_upload_filename"] = f"{slug}.png"
            target.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
            generated.append({"slug": slug, "file": str(target), "image": draft.get("cover_image"), "image_status": draft.get("image_status"), "image_upload_filename": draft.get("image_upload_filename"), "source_url": candidate.get("url")})
            print(f"Created review draft: {slug} (cover: {draft['image_status']})")
        except Exception as exc:
            failures.append({"stage": "draft", "source_url": candidate.get("url"), "error": str(exc)[:700]})
            print(f"Draft failed for candidate: {str(exc)[:250]}", file=sys.stderr)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "workflow": "Gaurav's World News Draft Builder",
        "status": "drafts_created" if generated else "generation_failed",
        "language": "Hindi-first + English",
        "candidate_count": len(candidates),
        "attempted": min(len(candidates), MAX_DRAFTS),
        "generated_count": len(generated),
        "generated": generated,
        "failures": failures,
        "cover_image_mode": "manual_upload",
        "draft_only": True,
        "publication_performed": False,
        "live_blog_modified": False,
        "requires_editorial_fact_check": True,
        "notes": "Drafts use RSS metadata and are not independently fact-checked. Review source links and verification_notes before use. Upload cover image as images/{slug}.png. No image-generation API is called and no live blog API is called."
    }
    (OUT / "workflow-status.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Finished: {len(generated)} draft(s); cover images are manual; publication remains disabled.")
    return 0 if generated else 1


if __name__ == "__main__":
    raise SystemExit(main())
