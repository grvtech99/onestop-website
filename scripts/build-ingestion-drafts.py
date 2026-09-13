#!/usr/bin/env python3
"""Build draft-only records from discovered official notices."""
from __future__ import annotations
import json, re, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; CAND=ROOT/'data/government-ingestion-candidates'; DRAFT=ROOT/'data/government-ingestion-drafts'; EXTRACT=ROOT/'scripts/extract-government-job-draft.py'
NA='VERIFY FROM OFFICIAL NOTICE'

def build_employment_row_draft(item, trace):
    row=item['employmentNewsRow']; org=str(row.get('organisation','')).strip(); post=str(row.get('post','')).strip(); method=str(row.get('method') or 'Recruitment').strip(); issued=str(row.get('issuedDate','')).strip(); last=str(row.get('lastDate','')).strip()
    title=f'{org} — {post}'.strip(' —')
    dates=f'Issued: {issued}; Last date: {last}' if issued and last else (f'Last date: {last}' if last else NA)
    return {'schemaVersion':4,'title':title,'category':'jobs','vacancy':post or NA,'dates':dates,'lastDate':last or NA,'eligibility':NA,'fee':NA,'age':NA,'selection':method or NA,'meta':f'Last date: {last}' if last else dates,'fieldConfidence':{'title':'high','vacancy':'high' if post else 'low','dates':'high' if last else 'low','lastDate':'high' if last else 'low','selection':'high' if method else 'medium','eligibility':'low','fee':'low','age':'low'},'reviewStatus':'draft','verificationRequired':True,'verificationNote':'Employment News All Jobs row parsed from the official table. Verify vacancy/eligibility/fee/age and the complete recruitment notice before any publication.'}

def main():
    CAND.mkdir(parents=True,exist_ok=True); DRAFT.mkdir(parents=True,exist_ok=True); processed=0
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
                trace_match=re.search(r'content_sha256=([0-9a-f]+)\s+content_type=([^\s]+)\s+chars=(\d+)',r.stdout)
                trace={'contentSha256':trace_match.group(1),'contentType':trace_match.group(2),'extractedChars':int(trace_match.group(3))} if trace_match else {'contentSha256':'','contentType':'','extractedChars':0}
                item.update(trace)
                if item.get('employmentNewsRow'):
                    draft=build_employment_row_draft(item,trace)
                    draft.update({'sourceId':item.get('sourceId'),'sourceName':item.get('sourceName'),'noticeUrl':url,'applyUrl':url,**trace,'discoveryPriority':item.get('discoveryPriority','high')})
                    target=DRAFT/(p.stem+'-draft.json'); target.write_text(json.dumps(draft,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); item['extractionStatus']='processed'; item['draftPath']=str(target.relative_to(ROOT))
                else:
                    r2=subprocess.run([sys.executable,str(EXTRACT),url,str(text),'--output',str(out),'--title',item.get('noticeTitleHint','')],capture_output=True,text=True,timeout=30)
                    if r2.returncode==0 and out.exists():
                        draft=json.loads(out.read_text(encoding='utf-8')); draft.update({'sourceId':item.get('sourceId'),'sourceName':item.get('sourceName'),'noticeUrl':url,'applyUrl':url,**trace,'discoveryPriority':item.get('discoveryPriority','high'),'reviewStatus':'draft','verificationRequired':True,'verificationNote':'Automatically extracted candidate. Verify every field against the official notice before publication.'})
                        target=DRAFT/(p.stem+'-draft.json'); target.write_text(json.dumps(draft,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); item['extractionStatus']='processed'; item['draftPath']=str(target.relative_to(ROOT))
                    else: item['extractionStatus']='failed'; item['extractionError']=r2.stderr[-500:]
        p.write_text(json.dumps(item,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); processed+=1
    print(json.dumps({'processed':processed}))
if __name__=='__main__': main()
