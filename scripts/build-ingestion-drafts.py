#!/usr/bin/env python3
"""Build draft-only records from discovered official notices."""
from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CAND=ROOT/'data/government-ingestion-candidates'
DRAFT=ROOT/'data/government-ingestion-drafts'
EXTRACT=ROOT/'scripts/extract-government-job-draft.py'

def main():
    CAND.mkdir(parents=True,exist_ok=True); DRAFT.mkdir(parents=True,exist_ok=True)
    processed=0
    for p in sorted(CAND.glob('*.json')):
        item=json.loads(p.read_text(encoding='utf-8'))
        if item.get('extractionStatus')=='processed': continue
        url=item.get('noticeUrl')
        if not url: continue
        with tempfile.TemporaryDirectory() as td:
            text=Path(td)/'notice.txt'; out=Path(td)/'draft.json'
            r=subprocess.run([sys.executable,str(ROOT/'scripts/extract-notice-content.py'),url,'--out',str(text)],capture_output=True,text=True,timeout=60)
            if r.returncode!=0:
                item['extractionStatus']='failed'; item['extractionError']=r.stderr[-500:]
            else:
                r2=subprocess.run([sys.executable,str(EXTRACT),url,str(text),'--output',str(out)],capture_output=True,text=True,timeout=30)
                if r2.returncode==0 and out.exists():
                    draft=json.loads(out.read_text(encoding='utf-8'))
                    draft['sourceId']=item.get('sourceId'); draft['sourceName']=item.get('sourceName')
                    draft['noticeUrl']=url; draft['applyUrl']=url
                    draft['reviewStatus']='draft'; draft['verificationRequired']=True
                    draft['verificationNote']='Automatically extracted candidate. Verify every field against the official notice before publication.'
                    target=DRAFT/(p.stem+'-draft.json')
                    target.write_text(json.dumps(draft,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                    item['extractionStatus']='processed'; item['draftPath']=str(target.relative_to(ROOT))
                else:
                    item['extractionStatus']='failed'; item['extractionError']=r2.stderr[-500:]
        p.write_text(json.dumps(item,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); processed+=1
    print(json.dumps({'processed':processed}))
if __name__=='__main__': main()
