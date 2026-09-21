#!/usr/bin/env python3
"""Validate the RSS candidate artifact without publishing or calling the blog API."""
import json
import re
from pathlib import Path

ROOT = Path("automation/gauravs-world/output")
SOURCE = ROOT / "news-candidates.json"
TARGET = ROOT / "candidate-validation.json"


def normalized_title(value):
    value = value.casefold()
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def main():
    if not SOURCE.exists():
        raise SystemExit("Missing news-candidates.json; run RSS collection first.")
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    candidates = payload.get("candidates", [])
    seen_urls, seen_titles, accepted, rejected = set(), set(), [], []
    for item in candidates:
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        key_url = url.split("?")[0].rstrip("/").casefold()
        key_title = normalized_title(title)
        reasons = []
        if not title:
            reasons.append("missing_title")
        if not url.startswith(("https://", "http://")):
            reasons.append("invalid_url")
        if key_url and key_url in seen_urls:
            reasons.append("duplicate_url")
        if key_title and key_title in seen_titles:
            reasons.append("duplicate_title")
        if reasons:
            rejected.append({"title": title, "url": url, "reasons": reasons})
            continue
        seen_urls.add(key_url)
        seen_titles.add(key_title)
        accepted.append(item)
    result = {
        "generated_at_utc": payload.get("generated_at_utc"),
        "status": "validated_candidates" if accepted else "no_valid_candidates",
        "draft_only": True,
        "publication_performed": False,
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "accepted": accepted[:40],
        "rejected": rejected[:100],
        "editorial_review_required": True,
        "article_generation_enabled": False,
        "image_generation_enabled": False,
        "blog_api_called": False,
    }
    TARGET.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Validation complete: {len(accepted)} accepted, {len(rejected)} rejected; no publishing.")


if __name__ == "__main__":
    main()
