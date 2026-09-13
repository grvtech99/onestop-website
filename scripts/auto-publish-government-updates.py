#!/usr/bin/env python3
"""Auto-publish high-confidence jobs from trusted official sources.

Trusted official source + successful extraction + consistency checks can publish
without manual review. Ambiguous or expired records are held for review.
Third-party aggregators can discover candidates but can never authorize publication.
"""
from __future__ import annotations
import hashlib, json, re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
POLICY=ROOT/'data/government-auto-verify-policy.json'; REGISTRY=ROOT/'data/government-source-registry.json'; DRAFT=ROOT/'data/government-ingestion-drafts'; DATA=ROOT/'onestop-updates-data.js'; LOG=ROOT/'data/government-auto-publication-log.json'
NA='VERIFY FROM OFFICIAL NOTICE'
RECRUIT=re.compile(r'(recruit|vacanc|career|job|advertisement|notification|appointment|engagement|apprentice|faculty|scientist|consultant|officer|engineer|professor|assistant|technician|clerk)',re.I)

def load(path,default): return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
def norm(s): return re.sub(r'[^a-z0-9]+',' ',str(s).lower()).strip()
def safe_url(v):
    try:return urlparse(str(v)).scheme in ('http','https')
    except:return False
def host_ok(a,b):
    x=urlparse(str(a)).hostname or ''; y=urlparse(str(b)).hostname or ''
    return bool(x and y and (x==y or y.endswith('.'+x) or x.endswith('.'+y)))
def js(v):return json.dumps(str(v),ensure_ascii=False)
def parse_last_date(value):
    """Return a date for common Indian/ISO formats, or None when not parseable."""
    text=str(value or '').strip()
    for pattern in (r'^(\d{1,2})/(\d{1,2})/(\d{4})$',r'^(\d{1,2})-(\d{1,2})-(\d{4})$',r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$',r'^(\d{4})-(\d{1,2})-(\d{1,2})$'):
        m=re.match(pattern,text)
        if not m: continue
        a,b,c=map(int,m.groups())
        try:
            return date(c,a,b) if c>=1000 else date(a,b,c)
        except ValueError:
            return None
    return None

def main():
    policy=load(POLICY,{}); registry=load(REGISTRY,{})
    sources={x.get('id'):x for x in registry.get('sources',[])}; trusted=set(policy.get('trustedSourceIds',[])); allowed=set(policy.get('autoPublishCategories',['jobs']))
    log=load(LOG,{'version':1,'updatedAt':None,'published':[],'held':[],'events':[]}); public=DATA.read_text(encoding='utf-8'); now=datetime.now(timezone.utc).isoformat(); today=date.today(); changed=False; published=held=0
    known={norm(x.get('title')) for x in log.get('published',[])}
    for p in sorted(DRAFT.glob('*.json')):
        try:d=json.loads(p.read_text(encoding='utf-8'))
        except Exception:continue
        if d.get('autoPublicationStatus') in ('published','held'):continue
        title=str(d.get('title','')).strip(); sid=str(d.get('sourceId','')).strip(); notice=str(d.get('noticeUrl','')).strip(); src=sources.get(sid,{})
        reason=None
        if sid not in trusted:reason='untrusted_source'
        elif d.get('category') not in allowed:reason='unsupported_category'
        elif not title or title.lower() in ('unknown',NA.lower()):reason='missing_title'
        elif not RECRUIT.search(title):reason='weak_recruitment_signal'
        elif not safe_url(notice) or not host_ok(src.get('url',''),notice):reason='invalid_or_nonofficial_notice_url'
        elif int(d.get('extractedChars') or 0)<120:reason='notice_fetch_failed_or_empty'
        elif d.get('lastDate')==NA and d.get('dates')==NA:reason='missing_dates'
        else:
            expiry=parse_last_date(d.get('lastDate'))
            if expiry and expiry<today: reason='expired_last_date'
        if not reason and norm(title) in known:reason='duplicate'
        if not reason and any(k not in d for k in ('vacancy','dates','eligibility','fee','age','selection')):reason='ambiguous_extraction'
        if reason:
            d['autoPublicationStatus']='held'; d['autoHoldReason']=reason; d['autoCheckedAt']=now
            p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            log.setdefault('held',[]).append({'title':title,'sourceId':sid,'noticeUrl':notice,'reason':reason,'draftPath':str(p.relative_to(ROOT)),'checkedAt':now}); held+=1; continue
        extra={k:d.get(k,NA) for k in ('vacancy','dates','eligibility','fee','age','selection')}; extra.update({'noticeUrl':notice,'applyUrl':d.get('applyUrl') or notice,'verificationMode':'AUTO — TRUSTED OFFICIAL SOURCE + DATA VALIDATION','autoVerifiedAt':now,'sourceId':sid,'recordStatus':'NEW'})
        meta=d.get('meta') or (('Last date: '+str(d.get('lastDate'))) if d.get('lastDate') and d.get('lastDate')!=NA else str(d.get('dates') or 'Official recruitment notice'))
        matches=list(re.finditer(r'(\n\s*jobs:\[\n)([\s\S]*?)(\n \],)',public))
        if len(matches)!=1: raise RuntimeError('Expected exactly one jobs block')
        m=matches[0]; line='  d(%s,%s,%s,%s),'%(js(title),js(meta),js(notice),json.dumps(extra,ensure_ascii=False,separators=(',',':')))
        public=public[:m.end(2)]+(('\n' if m.group(2) and not m.group(2).endswith('\n') else ''))+line+public[m.end(2):]
        d.update({'autoPublicationStatus':'published','autoVerifiedAt':now,'publishedAt':now}); p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        digest=hashlib.sha256((sid+'|'+notice+'|'+norm(title)).encode()).hexdigest()[:20]
        log.setdefault('published',[]).append({'id':'auto-'+digest,'title':title,'sourceId':sid,'noticeUrl':notice,'publishedAt':now,'verificationMode':'AUTO — TRUSTED OFFICIAL SOURCE + DATA VALIDATION','recordStatus':'NEW','draftPath':str(p.relative_to(ROOT))}); log.setdefault('events',[]).append({'type':'NEW','title':title,'sourceId':sid,'at':now}); known.add(norm(title)); published+=1; changed=True
    if changed:DATA.write_text(public,encoding='utf-8')
    log['published']=log.get('published',[])[-500:]; log['held']=log.get('held',[])[-500:]; log['events']=log.get('events',[])[-1000:]; log['updatedAt']=now; LOG.write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps({'autoPublished':published,'heldForReview':held,'changed':changed}))
if __name__=='__main__':main()
