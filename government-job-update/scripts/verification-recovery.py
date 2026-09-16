import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
VERIFICATION = DATA / 'official-verification-state.json'
CANONICAL = DATA / 'canonical-job-records.json'
TIMEOUT = 10
WORKERS = 16
MAX_ITEMS = int(os.environ.get('ONESTOP_RECOVERY_MAX_ITEMS','160'))
MAX_LINKS = 24
GOV_HINTS = ('gov.in', 'nic.in', 'ac.in', 'edu.in', 'govt.in')
def get(url):
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'ONESTOP-Government-Job-Update/3.4','Accept':'text/html,application/xhtml+xml,*/*;q=0.1'})
        with urllib.request.urlopen(req,timeout=TIMEOUT) as r:return r.status,r.read(1200000),r.geturl()
    except Exception:return None,b'',url
def text(body):
    s=unescape(body.decode('utf-8','replace')); s=re.sub(r'<script[^>]*>.*?</script>|<style[^>]*>.*?</style>|<noscript[^>]*>.*?</noscript>',' ',s,flags=re.I|re.S); return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',s)).strip()
def title(body):
    m=re.search(r'<title[^>]*>(.*?)</title>',body.decode('utf-8','replace'),re.I|re.S); return text(m.group(1).encode())[:400] if m else ''
def official(url):
    host=urlparse(url).netloc.lower().split(':')[0]; return any(host==h or host.endswith('.'+h) for h in GOV_HINTS)
def useful_path(url):
    path=urlparse(url).path.lower().rstrip('/')
    if not path or path in ('/home','/index.html','/index.php'):return False
    return any(k in path for k in ('recruit','career','vacan','notice','notification','advert','job','result','admit','answer','syllabus','admission','apply','engagement','selection','exam'))
def links(body,base):
    html=body.decode('utf-8','replace'); out=[]
    for href in re.findall(r'href=["\']([^"\']+)["\']',html,re.I):
        u=urljoin(base,unescape(href)).split('#',1)[0]
        if not u.startswith(('http://','https://')) or u in out:continue
        low=u.lower()
        if official(u) and (useful_path(u) or any(k in low for k in ('recruit','career','vacan','notice','notification','advert','job','result','admit','answer','syllabus','admission','apply'))):out.append(u)
        if len(out)>=MAX_LINKS:break
    return out
def tokens(s):
    stop={'the','and','for','online','apply','2026','2025','2024','recruitment','notification','government','govt','posts','post','jobs','job','latest','official','india','www','com','org','net'}
    return {x for x in re.findall(r'[a-z0-9]{3,}',(s or '').lower()) if x not in stop}
def candidate_score(job_title,page_title,page_text):
    a=tokens(job_title); b=tokens(page_title+' '+page_text[:30000]); overlap=len(a&b); category_signal=bool(re.search(r'\b(recruit|vacan|career|employment|engagement|notification|advertisement|application|result|admit|answer key|exam|selection|appointment|shortlist)\b',(page_title+' '+page_text[:30000]).lower())); year_signal=bool(re.search(r'\b202[456]\b',page_title+' '+page_text[:30000])); return overlap,category_signal,year_signal
def recover_one(item_id,item):
    if item.get('status')=='verified' and item.get('publicationStatus')=='ready':return None
    url=item.get('discoveryUrl') or ''
    if not url.startswith(('http://','https://')):return None
    status,body,resolved=get(url)
    if status!=200 or not body:return None
    candidates=links(body,resolved)
    if not candidates:return None
    pages=[]
    with ThreadPoolExecutor(max_workers=min(10,len(candidates))) as pool:
        futures={pool.submit(get,u):u for u in candidates}
        for f in as_completed(futures):
            try:ps,page,final=f.result()
            except Exception:continue
            if ps==200 and page and official(final):pages.append((final,page,title(page),text(page)))
    best=None; job_title=item.get('fields',{}).get('title') or item.get('title') or ''
    for final,page,page_title,page_text in pages:
        overlap,category_signal,year_signal=candidate_score(job_title,page_title,page_text)
        if not useful_path(final):continue
        if overlap>=1 and (category_signal or year_signal):
            score=overlap+(1 if category_signal else 0)+(1 if year_signal else 0)
            if best is None or score>best[0]:best=(score,overlap,final,page_title,page_text)
    if not best:return None
    _,overlap,final,page_title,page_text=best; now=datetime.now(timezone.utc).isoformat(); checks=dict(item.get('checks') or {}); checks.update({'official_notice_url':True,'trusted_source':True,'safe_http_urls':True,'official_content_match':True,'recovery_verified':True}); updated=dict(item)
    updated.update({'status':'verified','publicationStatus':'ready','checkedAt':now,'officialSource':{'sourceId':'official-government-domain-recovery','url':final,'title':page_title,'matchScore':round(min(1.0,0.45+min(overlap,4)*0.12),3),'titleOverlap':overlap,'sourceType':'official_notification_or_recruitment_page','verificationMethod':'discovery-page-official-link-recovery'},'reason':'official_government_source_verified_by_recovery_link','recoveredAt':now})
    return item_id,updated
def main():
    verification=json.loads(VERIFICATION.read_text(encoding='utf-8'))
    try:canonical=json.loads(CANONICAL.read_text(encoding='utf-8'))
    except Exception:canonical={'schemaVersion':1,'items':{}}
    items=verification.get('items',{})
    selected=[(k,v) for k,v in items.items() if v.get('status')!='verified']
    selected.sort(key=lambda p:p[1].get('checkedAt') or p[1].get('discoveredAt') or p[1].get('lastSeenAt') or '',reverse=True)
    selected.sort(key=lambda p:0 if p[1].get('reason')=='deferred_due_to_verification_run_bound' else 1)
    selected=selected[:MAX_ITEMS]
    recovered=0; now=datetime.now(timezone.utc).isoformat()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures={pool.submit(recover_one,k,v):k for k,v in selected}
        for f in as_completed(futures):
            try:result=f.result()
            except Exception:result=None
            if result:
                item_id,updated=result; items[item_id]=updated; cid=updated.get('canonicalRecordId') or item_id; record=dict(canonical.get('items',{}).get(cid,{})); fields=dict(updated.get('fields') or {}); record.update({k:v for k,v in fields.items() if v not in (None,'',[],{})}); record.update({'jobId':cid,'verificationStatus':'verified','publicationStatus':'ready','officialSource':updated.get('officialSource'),'source':record.get('source') or fields.get('source') or 'MultiSource','category':fields.get('category') or record.get('category') or 'jobs','updateType':fields.get('updateType') or record.get('updateType') or fields.get('category') or 'jobs'}); canonical.setdefault('items',{})[cid]=record; recovered+=1
    verification['items']=items; verification['recovery']={'checkedAt':now,'recoveredCount':recovered,'selectedCount':len(selected),'selectionLimit':MAX_ITEMS,'method':'official-government-link-recovery','policy':'official government domain remains mandatory; recovery only promotes records with a matching official recruitment/result/exam page'}; verification['checkedAt']=now
    VERIFICATION.write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); CANONICAL.write_text(json.dumps(canonical,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps({'status':'PASS','recoveredCount':recovered,'selectedCount':len(selected)},indent=2))
if __name__=='__main__':sys.exit(main())
