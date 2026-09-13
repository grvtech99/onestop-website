#!/usr/bin/env python3
"""Build a lightweight lifecycle index from the public government data layer.

This does not alter public listings. It only classifies published records as
ACTIVE, CLOSING_SOON, LAST_DATE_TODAY, or EXPIRED for admin/reporting use.
"""
from __future__ import annotations
import json,re
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'onestop-updates-data.js'; OUT=ROOT/'data/government-job-lifecycle.json'
DATE=re.compile(r'(?:last date|application(?:s)? close(?:s)?|closes)\s*[:\-]?\s*(\d{2})/(\d{2})/(\d{4})',re.I)

def records(text):
    # Public data uses d('title','meta','url',...) consistently for its static records.
    pat=re.compile(r"d\('((?:\\'|[^'])*)','((?:\\'|[^'])*)','(https?://[^']+)'",re.I)
    for m in pat.finditer(text):
        yield tuple(x.replace("\\'","'") for x in m.groups())

def status(meta,now):
    m=DATE.search(meta)
    if not m:return 'NO_DEADLINE',None
    dt=datetime(int(m.group(3)),int(m.group(2)),int(m.group(1)),23,59,59,tzinfo=timezone.utc)
    days=(dt-now).total_seconds()/86400
    if days<0:return 'EXPIRED',dt.date().isoformat()
    if days<=1:return 'LAST_DATE_TODAY',dt.date().isoformat()
    if days<=7:return 'CLOSING_SOON',dt.date().isoformat()
    return 'ACTIVE',dt.date().isoformat()

def main():
    text=DATA.read_text(encoding='utf-8'); now=datetime.now(timezone.utc); items=[]
    for title,meta,url in records(text):
        st,deadline=status(meta,now); items.append({'title':title,'meta':meta,'url':url,'status':st,'deadline':deadline})
    counts={k:sum(1 for x in items if x['status']==k) for k in ('ACTIVE','CLOSING_SOON','LAST_DATE_TODAY','EXPIRED','NO_DEADLINE')}
    OUT.write_text(json.dumps({'version':1,'generatedAt':now.isoformat(),'counts':counts,'items':items},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'records':len(items),'counts':counts}))
if __name__=='__main__':main()
