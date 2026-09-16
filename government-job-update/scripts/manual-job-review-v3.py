import importlib.util
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "government-job-update" / "scripts" / "manual-job-review.py"

spec = importlib.util.spec_from_file_location("manual_review", BASE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def reader_fetch(url):
    """Use the normal direct fetch first; use Jina Reader only when the source rejects it."""
    direct = mod.fetch(url)
    if direct.get("ok"):
        return direct

    status = direct.get("status")
    if status not in (403, 429, 451, 500, 502, 503, 504):
        return direct

    reader_url = "https://r.jina.ai/" + url
    try:
        req = urllib.request.Request(
            reader_url,
            headers={
                "User-Agent": "ONESTOP-Manual-Job-Review/3.0",
                "Accept": "text/plain,text/markdown,*/*;q=0.1",
            },
        )
        with urllib.request.urlopen(req, timeout=40) as r:
            body = r.read(mod.MAX_BYTES)
            return {
                "ok": r.status == 200 and bool(body),
                "status": r.status,
                "body": body,
                "final_url": url,
                "content_type": "text/markdown; reader-fallback=1",
                "error": None if r.status == 200 else f"Reader HTTP {r.status}",
                "fetchMethod": "jina-reader-fallback",
                "directStatus": status,
            }
    except Exception as e:
        direct["readerFallbackError"] = f"{type(e).__name__}: {e}"
        return direct


def parse_markdown(result):
    text = result["body"].decode("utf-8", "replace")
    lines = text.splitlines()
    headings = []
    rows = []
    links = []
    seen_links = set()

    for line in lines:
        stripped = line.strip()
        hm = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
        if hm:
            value = mod.clean_text(re.sub(r"[*_`]+", "", hm.group(1)))
            if value:
                headings.append(value)

        lm = re.findall(r"\[([^\]]+)\]\((https?://[^)\s]+)(?:\s+[^)]*)?\)", stripped)
        for label, href in lm:
            href = href.rstrip(".,;)")
            if href in seen_links:
                continue
            seen_links.add(href)
            links.append({"url": href, "label": mod.clean_text(label)})

        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [mod.clean_text(x) for x in stripped.strip("|").split("|")]
            if cells and not all(re.fullmatch(r"[-: ]+", x or "-") for x in cells):
                rows.append(cells)

    # Remove markdown table separators and formatting while preserving the original page text.
    clean = re.sub(r"^\s*\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)+\|?\s*$", " ", text, flags=re.M)
    clean = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 \2", clean)
    clean = re.sub(r"[`*_>#]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    title = headings[0] if headings else ""
    return {
        "text": clean,
        "title": title,
        "headings": headings,
        "links": links,
        "rows": rows,
        "mode": "reader-markdown",
    }


def parse_with_reader(result):
    if result.get("fetchMethod") == "jina-reader-fallback":
        return parse_markdown(result)
    return mod.parse_page(result)


mod.fetch = reader_fetch
mod.parse_page = parse_with_reader

if __name__ == "__main__":
    raise SystemExit(mod.main())
