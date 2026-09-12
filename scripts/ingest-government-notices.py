#!/usr/bin/env python3
"""Discover official notice links and create review-only draft candidates."""
from __future__ import annotations
import hashlib, json, re, sys, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/'data/government-source-registry.json'
OUT=ROOT/'data/government-ingestion-candidates'
ADAPTER=ROOT/'scripts/government-source-adapters.py'
TIMEOUT=20
MAX_LINKS_PER_SOURCE=40
KEYWORDS=re.compile(r'(recruit|vacanc|career|job|advertisement|notification|admit|result|answer.?key|scholarship|admission|syllabus|engagement|consultant|apprentice|fellow|faculty|exam)',re.I)

# Load adapter functions without requiring a package install.
ns={}; exec(ADAPTER.read_text(encoding='utf-8'),ns)

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'ONESTOP-Government-Notice-Bot/1.0'})
    with urllib.request.urlopen(req,timeout=TIMEOUT) as r: return r.read()

def links(source_id,base,body):
    text=body.decode('utf-8','ignore')
    candidates=[]
    for raw in re.findall(r'href\\s*=\\s*["\\\']([^"\\\']+)',text,re.I):
        url=urllib.parse.urljoin(base,raw)
        if urllib.parse.urlparse(url).scheme not in ('http','https'): continue
        if KEYWORDS.search(url) or KEYWORDS.search(raw): candidates.append(url)
    for x in ns['discover'](source_id,base,text): candidates.append(x['url'])
    return list(dict.fromkeys(candidates))[:MAX_LINKS_PER_SOURCE]

def slug(v): return re.sub(r'[^a-z0-9]+','-',v.lower()).strip('-')[:80] or 'notice'

def main():
    registry=json.loads(REGISTRY.read_text(encoding='utf-8')); OUT.mkdir(parents=True,exist_ok=True)
    now=datetime.now(timezone.utc).isoformat(); count=failures=0
    for source in registry.get('sources',[]):
        if not source.get('enabled'): continue
        try:
            base=source['url']; body=fetch(base)
            for url in links(source['id'],base,body):
                key=hashlib.sha256(url.encode()).hexdigest()[:16]; path=OUT/f"{slug(source['id'])}-{key}.json"
                if path.exists(): continue
                payload={'schemaVersion':1,'reviewStatus':'draft','sourceId':source['id'],'sourceName':source['name'],'sourceUrl':base,'noticeUrl':url,'applyUrl':url,'discoveredAt':now,'verificationRequired':True,'verificationNote':'Candidate discovered from an official source. Verify every field against the official notice before review/approval/publication.','contentTypeHint':'pdf' if url.lower().split('?')[0].endswith('.pdf') else 'html'}
                path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); count+=1
        except Exception as exc:
            failures+=1; print(f'WARN {source.get("id")}: {exc}',file=sys.stderr)
    print(json.dumps({'createdCandidates':count,'sourceFailures':failures})); return 1 if failures else 0

if __name__=='__main__': raise SystemExit(main())
