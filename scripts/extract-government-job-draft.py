#!/usr/bin/env python3
"""Extract conservative field-level government-update drafts from notice text.

Draft-only: extraction never verifies or publishes information.
"""
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone

NA = "VERIFY FROM OFFICIAL NOTICE"
DATE = r"[0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{4}"
PATTERNS = {
    "vacancy": [
        r"(?:total\s+)?vacanc(?:y|ies)\s*[:\-]?\s*([0-9,]+)",
        r"(?:no\.\s*of|number\s+of)\s*(?:posts|vacancies)\s*[:\-]?\s*([0-9,]+)",
        r"(?:total\s+)?(?:number\s+of\s+)?posts\s*[:\-]?\s*([0-9,]+)",
        r"(?:posts|vacancies)\s*[:\-]\s*([0-9,]+)",
    ],
    "fee": [
        r"(?:application|exam(?:ination)?|online)\s+fee\s*[:\-]?\s*(₹?\s*[0-9,]+(?:\s*/-)?|nil|no\s+fee|not?\s+applicable)",
        r"fee\s*[:\-]?\s*(₹?\s*[0-9,]+(?:\s*/-)?|nil|no\s+fee|not?\s+applicable)",
        r"(?:ur|general|gen)\s*(?:category)?\s*(?:application\s+)?fee\s*[:\-]?\s*(₹?\s*[0-9,]+(?:\s*/-)?)",
    ],
    "age": [
        r"(?:age\s+limit|upper\s+age\s+limit|maximum\s+age)\s*[:\-]?\s*([0-9]{1,2}\s*(?:to|-|–)\s*[0-9]{1,2}\s*(?:years?|yrs?)?)",
        r"(?:age\s+limit|upper\s+age\s+limit)\s*[:\-]?\s*(?:up\s+to\s*)?([0-9]{1,2}\s*(?:years?|yrs?)?)",
        r"born\s+(?:on\s+or\s+after|between)\s+([^.;]{5,50})",
    ],
    "last_date": [
        rf"(?:last\s+date|closing\s+date|last\s+date\s+for\s+(?:submission|application)|apply\s+(?:online\s+)?by)\s*[:\-]?\s*({DATE})",
        rf"(?:applications?\s+)?(?:close|closes|closed)\s+(?:on\s+)?({DATE})",
    ],
    "start_date": [
        rf"(?:start(?:ing)?\s+date|opening\s+date|application\s+(?:start|from)|applications?\s+open)\s*[:\-]?\s*({DATE})",
        rf"(?:applications?\s+)?(?:open|opens|opened)\s+(?:on\s+)?({DATE})",
    ],
    "eligibility": [
        r"(?:educational\s+qualification|essential\s+qualification|minimum\s+qualification|eligibility)\s*[:\-]?\s*([^.;]{8,240})",
        r"(?:qualification|eligible\s+candidate)\s*[:\-]?\s*([^.;]{8,240})",
    ],
    "selection": [
        r"(?:mode\s+of\s+selection|selection\s+process|method\s+of\s+selection)\s*[:\-]?\s*([^.;]{8,240})",
        r"(?:selection\s+will\s+be\s+based\s+on)\s*([^.;]{8,240})",
    ],
}

def first_match(text, patterns):
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip(" .;:")
    return NA

def confidence(value, field_name):
    if value == NA:
        return {"level":"low","verificationRequired":True,"reason":"Not confidently extracted"}
    return {"level":"medium","verificationRequired":True,"reason":f"Pattern matched for {field_name}; confirm against official notice"}

def classify(text):
    t=text.lower()
    if any(x in t for x in ("admit card","e-admit","hall ticket")): return "admit"
    if "answer key" in t or "answer-key" in t: return "answer"
    if "result" in t: return "results"
    if "scholarship" in t: return "scholarship"
    if "admission" in t and "recruitment" not in t: return "admission"
    if any(x in t for x in ("syllabus","exam scheme")) and "recruit" not in t: return "syllabus"
    return "jobs"

def extract(text, source_url, title=None):
    clean = re.sub(r"\s+", " ", text).strip()
    title = title or (clean[:140] if clean else "Government Update")
    values = {
        "vacancy": first_match(clean, PATTERNS["vacancy"]),
        "lastDate": first_match(clean, PATTERNS["last_date"]),
        "fee": first_match(clean, PATTERNS["fee"]),
        "age": first_match(clean, PATTERNS["age"]),
        "eligibility": first_match(clean, PATTERNS["eligibility"]),
        "selection": first_match(clean, PATTERNS["selection"]),
    }
    start = first_match(clean, PATTERNS["start_date"])
    values["dates"] = start if start != NA else ("Last date: " + values["lastDate"] if values["lastDate"] != NA else NA)
    field_conf = {k: {"value": v, **confidence(v, k)} for k, v in values.items()}
    return {
        "schemaVersion": 4, "reviewStatus": "draft", "sourceUrl": source_url,
        "extractedAt": datetime.now(timezone.utc).isoformat(), "category": classify(clean),
        "title": title, "vacancy": values["vacancy"], "dates": values["dates"],
        "lastDate": values["lastDate"], "eligibility": values["eligibility"],
        "fee": values["fee"], "age": values["age"], "selection": values["selection"],
        "noticeUrl": source_url, "applyUrl": source_url, "verificationRequired": True,
        "verificationNote": "Automatic extraction is draft-only. Verify every field against the official notice before publication.",
        "fieldConfidence": field_conf
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("source_url"); ap.add_argument("text_file"); ap.add_argument("--output"); ap.add_argument("--title"); args=ap.parse_args()
    with open(args.text_file, encoding="utf-8") as f: draft=extract(f.read(), args.source_url, args.title)
    data=json.dumps(draft, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f: f.write(data + "\n")
    else: print(data)
    return 0

if __name__ == "__main__": raise SystemExit(main())
