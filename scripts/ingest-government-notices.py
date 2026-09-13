#!/usr/bin/env python3
"""Discover official notice links and create ingestion candidates.

Employment News' All Jobs page is a table containing many independent jobs.
Those rows are converted into separate candidates so one source page can never
collapse multiple organisations/posts into one ONESTOP notification.
"""
from __future__ import annotations
import hashlib, html, json, re, sys, urllib.parse, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; REGISTRY=ROOT/'data/government-source-registry.json'; OUT=ROOT/'data/government-ingestion-candidates'; ADAPTER=ROOT/'scripts/government-source-adapters.py'
TIMEOUT=20; MAX_LINKS_PER_SOURCE=40
KEYWORDS=re.compile(r'(recruit|vacanc|career|job|advertisement|notification|admit|result|answer.?key|scholarship|admission|syllabus|engagement|consultant|apprentice|fellow|faculty|exam)',re.I)
ns={}; exec(ADAPTER.read_text(encoding='utf-8'),ns)

class TableParser(HTMLParser):
    """Extract simple HTML table rows while preserving cell boundaries."""
    def __init__(self):
        super().__init__(convert_charrefs=True); self.rows=[]; self.cells=[]; self.parts=[]; self.in_row=False; self.in_cell=False
    def handle_starttag(self,tag,attrs):
        tag=tag.lower()
        if tag=='tr':
            self.in_row=True; self.cells=[]; self.parts=[]
        elif self.in_row and tag in ('td','th'):
            self.in_cell=True; self.parts=[]
        elif self.in_cell and tag=='br': self.parts.append(' ')
    def handle_data(self,data):
        if self.in_cell: self.parts.append(data)
    def handle_endtag(self,tag):
        tag=tag.lower()
        if tag in ('td','th') and self.in_cell:
            value=re.sub(r'\s+',' ',html.unescape(''.join(self.parts))).strip(' |[]')
            self.cells.append(value); self.in_cell=False; self.parts=[]
        elif tag=='tr' and self.in_row:
            if self.cells: self.rows.append(self.cells[:])
            self.in_row=False; self.in_cell=False; self.cells=[]; self.parts=[]

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'ONESTOP-Government-Notice-Bot/1.2','Accept':'text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8'})
    with urllib.request.urlopen(req,timeout=TIMEOUT) as r: return r.read()

def employment_news_rows(base,body):
    parser=TableParser(); parser.feed(body.decode('utf-8','ignore'))
    rows=[]
    for cells in parser.rows:
        if len(cells)<5: continue
        joined=' | '.join(cells[:5]).lower()
        if 'issued date' in joined and 'organisation' in joined and 'last date' in joined: continue
        issued,organisation,post,method,last_date=(cells+["","","","",""])[:5]
        if not organisation or not post or not last_date: continue
        if not re.search(r'\b\d{1,2}/\d{1,2}/\d{4}\b',issued) or not re.search(r'\b\d{1,2}/\d{1,2}/\d{4}\b',last_date): continue
        row={'issuedDate':issued,'organisation':organisation,'post':post,'method':method or 'Recruitment','lastDate':last_date}
        row['rowKey']=hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:20]
        row['noticeTitleHint']=f"{organisation} — {post}"[:240]
        row['url']=base; row['label']=row['noticeTitleHint']; row['priority']='high'; row['sourceId']='employment_news'; row['sourceKind']='employment_news'; rows.append(row)
    return rows

def links(source_id,base,body):
    if source_id=='employment_news':
        return employment_news_rows(base,body)[:MAX_LINKS_PER_SOURCE]
    text=body.decode('utf-8','ignore'); candidates=[]
    for x in ns['discover'](source_id,base,text): candidates.append(x)
    for raw in re.findall(r'href\s*=\s*["\']([^"\']+)',text,re.I):
        url=urllib.parse.urljoin(base,raw)
        if urllib.parse.urlparse(url).scheme in ('http','https') and KEYWORDS.search(url):
            candidates.append({'url':url,'label':raw,'priority':'high','sourceId':source_id,'sourceKind':ns.get('source_kind',lambda _: 'generic')(source_id)})
    out=[]; seen=set()
    for x in candidates:
        key=x['url'].split('#',1)[0]
        if key in seen: continue
        seen.add(key); out.append(x)
    return out[:MAX_LINKS_PER_SOURCE]

def slug(v): return re.sub(r'[^a-z0-9]+','-',v.lower()).strip('-')[:80] or 'notice'

def main():
    registry=json.loads(REGISTRY.read_text(encoding='utf-8')); OUT.mkdir(parents=True,exist_ok=True); now=datetime.now(timezone.utc).isoformat(); count=failures=0
    for source in registry.get('sources',[]):
        if not source.get('enabled'): continue
        try:
            base=source['url']; body=fetch(base)
            for hit in links(source['id'],base,body):
                url=hit['url'];
                identity=(url+'|'+hit['rowKey']) if hit.get('rowKey') else url
                key=hashlib.sha256(identity.encode()).hexdigest()[:16]; path=OUT/f"{slug(source['id'])}-{key}.json"
                if path.exists(): continue
                label=hit.get('noticeTitleHint') or hit.get('label','').strip()
                payload={'schemaVersion':3,'reviewStatus':'draft','sourceId':source['id'],'sourceName':source['name'],'sourceUrl':base,'noticeUrl':url,'applyUrl':url,'discoveredAt':now,'noticeTitleHint':label[:240] if label else '', 'discoveryPriority':hit.get('priority','high'),'sourceKind':hit.get('sourceKind',ns.get('source_kind',lambda _: 'generic')(source['id'])),'verificationRequired':True,'verificationNote':'Candidate discovered from an official source. Automatic publication is allowed only after trusted-source and data validation checks pass.','contentTypeHint':'pdf' if url.lower().split('?')[0].endswith('.pdf') else 'html'}
                if hit.get('rowKey'): payload['employmentNewsRow']={k:hit[k] for k in ('rowKey','issuedDate','organisation','post','method','lastDate')}
                path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); count+=1
        except Exception as exc:
            failures+=1; print(f'WARN {source.get("id")}: {exc}',file=sys.stderr)
    print(json.dumps({'createdCandidates':count,'sourceFailures':failures})); return 0
if __name__=='__main__': raise SystemExit(main())
