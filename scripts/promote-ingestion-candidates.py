#!/usr/bin/env python3
"""Promote discovered/extracted candidates into the review queue.

Candidates remain unverified. This script only creates queue metadata and never
modifies public government-update data.
"""
from __future__ import annotations
import hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CAND=ROOT/'data/government-ingestion-candidates'
DRAFT=ROOT/'data/government-verified-drafts'
QUEUE=ROOT/'data/government-update-review-queue.json'
PUBLIC=ROOT/'onestop-updates-data.js'

def key(item):
    raw='|'.join(str(item.get(x,'')) for x in ('sourceId','noticeUrl','title'))
    return 'ingest-'+hashlib.sha256(raw.encode()).hexdigest()[:20]

def main():
    q=json.loads(QUEUE.read_text(encoding='utf-8')) if QUEUE.exists() else {'version':1,'updatedAt':None,'items':[]}
    existing={x.get('key') for x in q.get('items',[])}
    public=PUBLIC.read_text(encoding='utf-8') if PUBLIC.exists() else ''
    now=datetime.now(timezone.utc).isoformat(); added=0
    for p in sorted(DRAFT.glob('*.json')):
        try: item=json.loads(p.read_text(encoding='utf-8'))
        except Exception: continue
        title=str(item.get('title','')).strip()
        if not title or title.lower() in ('unknown','verify from official notice'): continue
        k=key(item)
        if k in existing: continue
        duplicate=title in public
        q['items'].append({'key':k,'source':item.get('sourceId'),'sourceName':item.get('sourceName'),'detectedAt':item.get('extractedAt') or item.get('discoveredAt') or now,'sourceSha256':item.get('contentSha256',''),'verificationUrl':item.get('noticeUrl'),'noticeUrl':item.get('noticeUrl'),'draftPath':str(p.relative_to(ROOT)),'title':title,'status':'rejected' if duplicate else 'pending','duplicateOfPublic':duplicate,'verificationRequired':True,'verificationNote':'Automatically extracted candidate. Verify every field against the official notice before publication.'})
        existing.add(k); added+=1
    q['items']=q.get('items',[])[-100:]
    q['updatedAt']=now
    QUEUE.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'added':added,'queueItems':len(q['items'])}))

if __name__=='__main__': main()
