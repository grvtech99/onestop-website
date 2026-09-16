import html
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "government-job-update" / "data"
OUT = DATA / "manual-job-review.json"
UA = "ONESTOP-Manual-Job-Review/2.0"
TIMEOUT = 25
MAX_BYTES = 15_000_000


def load_extractor():
    p = ROOT / "government-job-update" / "scripts" / "job-field-extractor.py"
    spec = spec_from_file_location("job_fields", p)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FIELDS = load_extractor()


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts = []
        self.headings = []
        self.anchors = []
        self.row_cells = []
        self.rows = []
        self.in_row = False
        self.in_cell = False
        self.cell_text = []
        self.in_title = False
        self.title_text = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in ("script", "style", "noscript", "svg"):
            self.skip += 1
            return
        if self.skip:
            return
        attrs = dict(attrs)
        if tag in ("h1", "h2", "h3"):
            self.headings.append([])
        if tag == "title":
            self.in_title = True
        if tag == "tr":
            self.in_row = True
            self.row_cells = []
        if tag in ("td", "th") and self.in_row:
            self.in_cell = True
            self.cell_text = []
        if tag == "a" and attrs.get("href"):
            self.anchors.append({"href": attrs.get("href"), "label": []})

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("script", "style", "noscript", "svg"):
            if self.skip:
                self.skip -= 1
            return
        if self.skip:
            return
        if tag in ("td", "th") and self.in_cell:
            value = clean_text(" ".join(self.cell_text))
            self.row_cells.append(value)
            self.in_cell = False
        if tag == "tr" and self.in_row:
            if any(self.row_cells):
                self.rows.append(self.row_cells[:])
            self.in_row = False
            self.row_cells = []
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.skip:
            return
        value = clean_text(data)
        if not value:
            return
        self.parts.append(value)
        if self.in_cell:
            self.cell_text.append(value)
        if self.in_title:
            self.title_text.append(value)
        if self.headings:
            self.headings[-1].append(value)
        if self.anchors:
            self.anchors[-1]["label"].append(value)


def clean_text(value):
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def host(url):
    return urllib.parse.urlparse(url).netloc.lower().split(":")[0].removeprefix("www.")


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.1",
        })
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return {
                "ok": r.status == 200,
                "status": r.status,
                "body": r.read(MAX_BYTES),
                "final_url": r.geturl(),
                "content_type": r.headers.get("Content-Type", ""),
            }
    except Exception as e:
        return {
            "ok": False,
            "status": getattr(e, "code", None),
            "body": b"",
            "final_url": url,
            "content_type": "",
            "error": f"{type(e).__name__}: {e}",
        }


def pdf_text(body):
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(body))
        chunks = []
        for page in reader.pages[:80]:
            try:
                chunks.append(page.extract_text() or "")
            except Exception:
                pass
        return clean_text(" ".join(chunks))
    except Exception:
        return ""


def parse_page(result):
    if not result["ok"]:
        return {"text": "", "title": "", "headings": [], "links": [], "rows": [], "mode": "html"}
    ct = result["content_type"].lower()
    url = result["final_url"]
    if "pdf" in ct or url.lower().split("?", 1)[0].endswith(".pdf"):
        return {"text": pdf_text(result["body"]), "title": "PDF Notification", "headings": [], "links": [], "rows": [], "mode": "pdf"}

    parser = PageParser()
    parser.feed(result["body"].decode("utf-8", "replace"))
    links = []
    seen = set()
    for item in parser.anchors:
        u = urllib.parse.urljoin(url, html.unescape(item["href"])).split("#", 1)[0]
        if not u.startswith(("http://", "https://")) or u in seen:
            continue
        seen.add(u)
        links.append({"url": u, "label": clean_text(" ".join(item["label"]))})

    heading_values = [clean_text(" ".join(x)) for x in parser.headings if clean_text(" ".join(x))]
    title = clean_text(" ".join(parser.title_text)) or (heading_values[0] if heading_values else "")
    row_lines = [" | ".join(x for x in row if x) for row in parser.rows if any(row)]
    # Keeping table rows in the extraction text is important: vacancy/category tables often contain the actual post data.
    text = clean_text(" ".join(parser.parts) + " " + " ".join(row_lines))
    return {"text": text, "title": title, "headings": heading_values, "links": links, "rows": parser.rows, "mode": "html"}


def pick_title(parsed, fallback_url):
    candidates = parsed.get("headings", [])
    for value in candidates:
        if re.search(r"(recruitment|vacancy|online form|notification|posts?|job|officer|teacher|engineer|assistant|constable|admission|scholarship)", value, re.I):
            return value[:500]
    return (parsed.get("title") or fallback_url)[:500]


def classify_links(links):
    notification = ""
    apply = ""
    website = ""
    useful = []
    for item in links:
        label = item["label"]
        url = item["url"]
        hay = f"{label} {url}".lower()
        is_pdf = ".pdf" in urllib.parse.urlparse(url).path.lower()
        if re.search(r"apply|online application|application form|registration", hay) and not apply:
            apply = url
        elif re.search(r"notification|advertisement|advt|notice|download", hay) or is_pdf:
            if not notification:
                notification = url
        elif re.search(r"official website|official site|department website", hay) and not website:
            website = url
        if re.search(r"apply|notification|advert|advt|download|official website|official site|pdf", hay, re.I):
            useful.append(item)
    return notification, apply, website, useful[:30]


def table_summary(rows):
    useful = []
    for row in rows:
        cells = [clean_text(x) for x in row if clean_text(x)]
        if len(cells) >= 2:
            useful.append(" | ".join(cells))
    return useful[:200]


def field_status(record):
    required = [
        "title", "organization", "vacancies", "qualification", "ageLimit", "fee",
        "selectionProcess", "salary", "jobLocation", "applicationStartDate",
        "applicationLastDate", "notificationUrl", "applyUrl"
    ]
    optional = [
        "department", "state", "jobType", "ageRelaxation", "examDate",
        "documentsRequired", "applicationMode", "vacancyDetails"
    ]
    statuses = {}
    for key in required + optional:
        value = record.get(key)
        present = value not in (None, "", [], {})
        statuses[key] = "FOUND" if present else ("MISSING_REQUIRED" if key in required else "MISSING_OPTIONAL")
    return statuses


def main():
    url = (os.environ.get("JOB_URL") or "").strip()
    if not re.match(r"^https?://", url, re.I):
        print("JOB_URL must be a complete http(s) URL", file=sys.stderr)
        return 2

    checked = datetime.now(timezone.utc).isoformat()
    source = fetch(url)
    parsed = parse_page(source)
    final_url = source["final_url"]
    title = pick_title(parsed, final_url)
    notification_url, apply_url, official_site_url, useful_links = classify_links(parsed.get("links", []))

    raw = {
        "title": title,
        "text": parsed.get("text", ""),
        "notificationUrl": notification_url,
        "applyUrl": apply_url,
        "source": host(url),
        "category": FIELDS.classify_update_type(title, parsed.get("text", "")),
    }
    record = FIELDS.normalize_record(raw)
    record["title"] = title
    record["notificationUrl"] = notification_url
    record["applyUrl"] = apply_url
    if official_site_url:
        record["officialWebsiteUrl"] = official_site_url

    statuses = field_status(record)
    missing_required = [k for k, v in statuses.items() if v == "MISSING_REQUIRED"]

    if not source["ok"]:
        status = "FETCH_FAILED"
    elif missing_required:
        status = "NEEDS_ADMIN_INPUT"
    else:
        status = "READY_FOR_REVIEW"

    output = {
        "schemaVersion": 2,
        "reviewId": checked.replace(":", "").replace(".", ""),
        "checkedAt": checked,
        "inputUrl": url,
        "finalUrl": final_url,
        "sourceHost": host(url),
        "fetch": {
            "ok": source["ok"],
            "status": source["status"],
            "contentType": source["content_type"],
            "mode": parsed.get("mode"),
            "error": source.get("error"),
        },
        "record": record,
        "fieldStatus": statuses,
        "missingRequiredFields": missing_required,
        "status": status,
        "actionRequired": bool(missing_required or not source["ok"]),
        "sourceLinks": useful_links,
        "sourceTableRows": table_summary(parsed.get("rows", [])),
        "notes": "Information is copied/extracted from the supplied page. Direct notification/apply links are retained when present. Admin should use the notification PDF/source links for cross-checking before publication.",
    }

    DATA.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print("::notice title=ONESTOP Manual Job Review::Status: " + status)
    if missing_required:
        print("::warning title=Admin input needed::Missing required fields: " + ", ".join(missing_required))
    if not source["ok"]:
        print("::error title=Source page could not be fetched::Check the URL and run again.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
