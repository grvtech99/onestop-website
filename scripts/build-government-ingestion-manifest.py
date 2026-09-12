#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CAND=ROOT/'data/government-ingestion-candidates'
OUT=ROOT/'data/government-ingestion-manifest.json'
DRAFT=ROOT/'data/government-verified-drafts'

def main():
    items=[]
    for p in sorted(CAND.glob('*.json')):
        try: x=json.loads(p.read_text(encoding='utf-8'))
        except Exception: continue
        items.append({'title':x.get('title') or x.get('noticeTitle') or p.stem,'sourceName':x.get('sourceName'),'sourceId':x.get('sourceId'),'noticeUrl':x.get('noticeUrl'),'discoveredAt':x.get('discoveredAt'),'status':'failed' if x.get('extractionStatus')=='failed' else ('verified' if x.get('reviewStatus')=='verified' else 'pending'),'category':x.get('category'),'candidatePath':str(p.relative_to(ROOT)),'draftPath':x.get('draftPath')})
    OUT.write_text(json.dumps({'version':1,'generatedAt':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'items':items[:500]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'manifest_items={len(items[:500])}')
if __name__=='__main__': main()
