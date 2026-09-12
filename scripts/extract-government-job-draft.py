#!/usr/bin/env python3
"""Extract a conservative structured government-update draft from notice text.

Draft-only: uncertain fields are explicitly flagged for human verification.
"""
from __future__ import annotations
import argparse, json, re, sys
from datetime import datetime, timezone

NA = "VERIFY FROM OFFICIAL NOTICE"
PATTERNS = {
    "vacancy": [r"(?:total\s+)?vacanc(?:y|ies)\s*[:\-]?\s*([0-9,]+)", r"(?:no\.\s*of|number\s+of)\s*(?:posts|vacancies)\s*[:\-]?\s*([0-9,]+)"],
    "fee": [r"(?:application|exam(?:ination)?)\s+fee\s*[:\-]?\s*(₹?\s*[0-9,]+(?:\s*/-)?|nil|no\s+fee)", r"fee\s*[:\-]?\s*(₹?\s*[0-9,]+(?:\s*/-)?|nil|no\s+fee)"],
    "age": [r"(?:age\s+limit|upper\s+age\s+limit|age)\s*[:\-]?\s*([0-9]{1,2}\s*(?:to|-|–)\s*[0-9]{1,2}\s*(?:years?|yrs?)?)"],
    "last_date": [r"(?:last\s+date|closing\s+date|apply\s+(?:online\s+)?by)\s*[:\-]?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{4})"],
    "start_date": [r"(?:start(?:ing)?\s+date|opening\s+date|application\s+(?:start|from))\s*[:\-]?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{4})"],
}

def first_match(text, patterns):
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m: return re.sub(r"\s+", " ", m.group(1)).strip()
    return NA

def field(value):
    return {"value": value, "confidence": "high" if value != NA else "low", "verificationRequired": value == NA}

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
    clean=re.sub(r"\s+"," ",text).strip()
    title=title or (clean[:140] if clean else "Government Update")
    values={"vacancy":first_match(clean,PATTERNS["vacancy"]),"lastDate":first_match(clean,PATTERNS["last_date"]),"fee":first_match(clean,PATTERNS["fee"]),"age":first_match(clean,PATTERNS["age"])}
    start=first_match(clean,PATTERNS["start_date"])
    values["dates"] = start if start != NA else ("Last date: "+values["lastDate"] if values["lastDate"] != NA else NA)
    draft={"schemaVersion":2,"reviewStatus":"draft","sourceUrl":source_url,"extractedAt":datetime.now(timezone.utc).isoformat(),"category":classify(clean),"title":title,"vacancy":values["vacancy"],"dates":values["dates"],"lastDate":values["lastDate"],"eligibility":NA,"fee":values["fee"],"age":values["age"],"selection":NA,"noticeUrl":source_url,"applyUrl":source_url,"verificationRequired":True,"verificationNote":"Automatic extraction is draft-only. Verify every field against the official notice before publication.","fieldConfidence":{k:field(v) for k,v in values.items()} | {"eligibility":field(NA),"selection":field(NA)}}
    return draft

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("source_url"); ap.add_argument("text_file"); ap.add_argument("--output"); ap.add_argument("--title"); args=ap.parse_args()
    with open(args.text_file,encoding="utf-8") as f: draft=extract(f.read(),args.source_url,args.title)
    data=json.dumps(draft,indent=2,ensure_ascii=False)
    if args.output: open(args.output,"w",encoding="utf-8").write(data+"\n")
    else: print(data)
    return 0
if __name__ == "__main__": raise SystemExit(main())
