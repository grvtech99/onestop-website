#!/usr/bin/env python3
"""Starter runner. It intentionally does not claim to fetch or publish news."""
import json
from datetime import datetime, timezone
from pathlib import Path

out = Path('automation/gauravs-world/output')
out.mkdir(parents=True, exist_ok=True)
report = {
    'generated_at_utc': datetime.now(timezone.utc).isoformat(),
    'workflow': "Gaurav's World News Draft Builder",
    'status': 'setup_required',
    'schedule': '6 times daily (UTC; scheduled execution may be delayed)',
    'language': 'Hindi-first + English',
    'publication_mode': 'draft_only',
    'live_blog_modified': False,
    'news_search': 'not_connected',
    'article_generation': 'not_connected',
    'image_generation': 'not_connected',
    'blog_draft_api': 'not_verified',
    'message': 'No provider adapters or credentials are configured. This run created a status report only; it did not search, generate an article, save a blog draft, or publish.'
}
(out / 'workflow-status.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('Setup-status artifact written; no live blog changes made.')
