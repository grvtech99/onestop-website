import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "e2e-candidates.json"
UA = "ONESTOP-Government-Job-Update-E2E/1.0"


def fetch(url):
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.8,*/*;q=0.1",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, response.read(1500000), response.geturl(), None
    except urllib.error.HTTPError as exc:
        return exc.code, b"", url, f"HTTP {exc.code}"
    except Exception as exc:
        return None, b"", url, str(exc)[:300]


def clean_html(body):
    raw = body.decode("utf-8", "replace")
    raw = re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def page_title(body):
    raw = body.decode("utf-8", "replace")
    match = re.search(r"<title[^>]*>(.*?)</title>", raw, flags=re.I | re.S)
    if not match:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", match.group(1))).strip()


def token_set(value):
    return set(re.findall(r"[a-z0-9]{4,}", value.lower()))


def verify(candidate, official_body, official_final_url):
    text = clean_html(official_body)
    official_title = page_title(official_body)
    candidate_tokens = token_set(candidate["title"])
    target_tokens = token_set(official_title + " " + text[:12000])
    score = len(candidate_tokens & target_tokens) / len(candidate_tokens) if candidate_tokens else 0
    host = (urlparse(official_final_url).hostname or "").lower()
    trusted_host = host == "ntpc.co.in" or host.endswith(".ntpc.co.in")
    recruitment_signal = "recruitment" in text.lower() or "advt" in text.lower()
    content_ok = len(text) >= 200
    title_ok = bool(candidate["title"])
    date_ok = bool(candidate.get("dateEvidence"))
    match_ok = score >= 0.25
    checks = {
        "trusted_source": trusted_host,
        "official_notice_url": trusted_host,
        "nonempty_title": title_ok,
        "recruitment_signal": recruitment_signal,
        "extractable_notice_content": content_ok,
        "last_date_or_valid_dates": date_ok,
        "safe_http_urls": official_final_url.startswith(("http://", "https://")),
        "candidate_official_match": match_ok,
    }
    passed = all(checks.values())
    return {
        "id": candidate["id"],
        "discoverySource": candidate["discoveryUrl"],
        "officialSource": official_final_url,
        "officialTitle": official_title,
        "matchScore": round(score, 3),
        "status": "verified" if passed else "hold",
        "publicationStatus": "ready" if passed else "hold",
        "checks": checks,
        "reason": "all_required_checks_passed" if passed else "failed_checks:" + ",".join(k for k, v in checks.items() if not v),
    }


def main():
    started = datetime.now(timezone.utc).isoformat()
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    candidates = fixture["candidates"]
    positive, negative = candidates

    status, body, final_url, error = fetch(positive["officialUrl"])
    if status != 200 or not body:
        print(json.dumps({"status": "FAIL", "stage": "official_source_fetch", "error": error or f"HTTP {status}"}, indent=2))
        return 1

    positive_result = verify(positive, body, final_url)
    negative_result = verify(negative, body, final_url)
    negative_expected_hold = negative_result["status"] == "hold" and negative_result["publicationStatus"] == "hold"
    positive_expected_ready = positive_result["status"] == "verified" and positive_result["publicationStatus"] == "ready"

    report = {
        "schemaVersion": 1,
        "startedAt": started,
        "mode": "controlled-live-e2e",
        "discoverySource": fixture["discoverySource"],
        "discoveryFixtureOnly": True,
        "productionStateMutation": False,
        "officialSourceLiveFetch": positive["officialUrl"],
        "positiveCase": positive_result,
        "negativeCase": negative_result,
        "overall": "PASS" if positive_expected_ready and negative_expected_hold else "FAIL",
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
