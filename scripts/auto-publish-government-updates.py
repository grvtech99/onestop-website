#!/usr/bin/env python3
"""Automatically publish high-confidence jobs from trusted official sources.

This is intentionally narrower than the manual publication path. It only
publishes jobs discovered from an allow-listed official source, after local
content/URL/date/title/duplicate checks. Anything ambiguous is left for the
existing review queue; no third-party source can authorize publication.
"""
from __future__ import annotations
import hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
POLICY=ROOT/'data/government-auto-verify-policy.json'
REGISTRY=ROOT/'data/government-source-registry.json'
DRAFT=ROOT/'data/government-ingestion-drafts'
DATA=ROOT/'onestop-updates-data.js'
LOG=ROOT/'data/government-auto-publication-log.json'
NA='VERIFY FROM OFFICIAL NOTICE'
RECRUIT=re.compile(r'(recruit|vacanc|career|job|advertisement|notification|appointment|engagement|apprentice|faculty|scientist|consultant|officer|engineer|professor|assistant|technician|clerk)',re.I)

def load(path, default):
    if not path.exists(): return default
    return json.loads(path.read_text(encoding='utf-8'))

def host_ok(source_url, notice_url):
    a=urlparse(source_url).hostname or ''; b=urlparse(notice_url).hostname or ''
    return bool(a and b and (b==a or b.endswith('.'+a) or a.endswith('.'+b)))

def safe_url(value):
    try: return urlparse(str(value)).scheme in ('http','https')
    except Exception: return False

def js(s): return json.dumps(str(s),ensure_ascii=False)

def main():
    policy=load(POLICY,{})
    registry=load(REGISTRY,{}); sources={x.get('id'):x for x in registry.get('sources',[])}
    trusted=set(policy.get('trustedSourceIds',[])); allowed=set(policy.get('autoPublishCategories',['jobs']))
    log=load(LOG,{'version':1,'updatedAt':None,'published':[],'held':[]})
    public=DATA.read_text(encoding='utf-8')
    published_titles={x.get('title') for x in log.get('published',[])}
    now=datetime.now(timezone.utc).isoformat(); changed=False; published=0; held=0
    for p in sorted(DRAFT.glob('*.json')):
        try: d=json.loads(p.read_text(encoding='utf-8'))
        except Exception: continue
        title=str(d.get('title','')).strip(); sid=str(d.get('sourceId','')).strip(); notice=str(d.get('noticeUrl','')).strip()
        reason=None
        src=sources.get(sid,{})
        if d.get('autoPublicationStatus') in ('published','held'): continue
        if sid not in trusted: reason='untrusted_source'
        elif d.get('category') not in allowed: reason='unsupported_category'
        elif not title or title.lower() in ('unknown',NA.lower()): reason='missing_title'
        elif not RECRUIT.search(title): reason='weak_recruitment_signal'
        elif not safe_url(notice) or not host_ok(src.get('url',''),notice): reason='invalid_or_nonofficial_notice_url'
        elif int(d.get('extractedChars') or 0) < 120: reason='notice_fetch_failed_or_empty'
        elif d.get('lastDate')==NA and d.get('dates')==NA: reason='missing_dates'
        elif title in public or title in published_titles: reason='duplicate'
        else:
            for field in ('vacancy','dates','eligibility','fee','age','selection'):
                if field not in d: reason='ambiguous_extraction'; break
        if reason:
            d['autoPublicationStatus']='held'; d['autoHoldReason']=reason; d['autoCheckedAt']=now
            p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            log.setdefault('held',[]).append({'title':title,'sourceId':sid,'reason':reason,'draftPath':str(p.relative_to(ROOT)),'checkedAt':now})
            held+=1; continue
        extra={k:d.get(k,NA) for k in ('vacancy','dates','eligibility','fee','age','selection')}
        extra.update({'noticeUrl':notice,'applyUrl':d.get('applyUrl') or notice,'verificationMode':'AUTO — TRUSTED OFFICIAL SOURCE + DATA VALIDATION','autoVerifiedAt':now,'sourceId':sid})
        meta=d.get('meta') or (('Last date: '+str(d.get('lastDate'))) if d.get('lastDate') and d.get('lastDate')!=NA else str(d.get('dates') or 'Official recruitment notice'))
        line='  d(%s,%s,%s,%s),'%(js(title),js(meta),js(notice),json.dumps(extra,ensure_ascii=False,separators=(',',':')))
        # Insert only into the jobs block and require exactly one block.
        matches=list(re.finditer(r'(\n\s*jobs:\[\n)([\s\S]*?)(\n \],)',public))
        if len(matches)!=1:
            raise RuntimeError('Expected exactly one jobs block')
        m=matches[0]; public=public[:m.end(2)]+(('\n' if m.group(2) and not m.group(2).endswith('\n') else ''))+line+public[m.end(2):]
        d['autoPublicationStatus']='published'; d['autoVerifiedAt']=now; d['publishedAt']=now
        p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        digest=hashlib.sha256((sid+'|'+notice+'|'+title).encode()).hexdigest()[:20]
        log.setdefault('published',[]).append({'id':'auto-'+digest,'title':title,'sourceId':sid,'noticeUrl':notice,'publishedAt':now,'verificationMode':'AUTO — TRUSTED OFFICIAL SOURCE + DATA VALIDATION','draftPath':str(p.relative_to(ROOT))})
        published_titles.add(title); published+=1; changed=True
    if changed: DATA.write_text(public,encoding='utf-8')
    log['published']=log.get('published',[])[-500:]; log['held']=log.get('held',[])[-500:]; log['updatedAt']=now; LOG.write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'autoPublished':published,'heldForReview':held,'changed':changed}))

if __name__=='__main__': main()
