import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
STATE=DATA/'sarkariresult-monitor-state.json'
REGISTRY=DATA/'data'/'government-source-registry.json'
OUT=DATA/'official-verification-state.json'
LOG=DATA/'official-verification-log.json'
CAN=DATA/'canonical-job-records.json'
UA='ONESTOP-Government-Job-Update/3.3'
TIMEOUT=7
WORKERS=20
MAX_RECORDS=int(os.environ.get('ONESTOP_VERIFY_MAX_RECORDS','160'))
MAX_LINKS=16
GOV_HINTS=('gov.in','nic.in','ac.in','edu.in','govt.in')
AUTHORITY_ALIASES={'ssc':'https://ssc.gov.in/','staff selection commission':'https://ssc.gov.in/','upsc':'https://www.upsc.gov.in/','rrb':'https://www.rrbapply.gov.in/','railway recruitment':'https://www.rrbapply.gov.in/','nta':'https://exams.nta.ac.in/','national testing agency':'https://exams.nta.ac.in/','drdo':'https://www.drdo.gov.in/','isro':'https://www.isro.gov.in/','csir':'https://www.csir.res.in/','icmr':'https://www.icmr.gov.in/','aiims':'https://www.aiims.edu/','ugc':'https://www.ugc.gov.in/','ibps':'https://www.ibps.in/','rbi':'https://www.rbi.org.in/','sbi':'https://sbi.co.in/','nabard':'https://www.nabard.org/','sebi':'https://www.sebi.gov.in/','epfo':'https://www.epfindia.gov.in/','esic':'https://www.esic.gov.in/','bhel':'https://www.bhel.com/','bel':'https://bel-india.in/','hal':'https://hal-india.co.in/','ongc':'https://ongcindia.com/','ntpc':'https://www.ntpc.co.in/','iocl':'https://iocl.com/','gail':'https://www.gailonline.com/','lic':'https://licindia.in/','uppsc':'https://uppsc.up.nic.in/','upsssc':'https://upsssc.gov.in/','bpsc':'https://www.bpsc.bih.nic.in/','rpsc':'https://rpsc.rajasthan.gov.in/','mppsc':'https://mppsc.mp.gov.in/','hpsc':'https://hpsc.gov.in/','wbpsc':'https://psc.wb.gov.in/','mpsc':'https://mpsc.gov.in/','tnpsc':'https://www.tnpsc.gov.in/','kpsc':'https://kpsc.kar.nic.in/','employment news':'https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All','national scholarship portal':'https://scholarships.gov.in/','nsp':'https://scholarships.gov.in/','mecl':'https://mecl.co.in/','nfsu':'https://nfsu.ac.in/','balmer lawrie':'https://www.balmerlawrie.com/','rcf':'https://www.rcfltd.com/','hpcl':'https://www.hindustanpetroleum.com/','bpcl':'https://www.bharatpetroleum.in/','coal india':'https://www.coalindia.in/','powergrid':'https://www.powergrid.in/','pfc':'https://www.pfcindia.com/','rec limited':'https://recindia.nic.in/','nfdb':'https://nfdb.gov.in/','fci':'https://fci.gov.in/','nabcons':'https://www.nabcons.com/','kea':'https://cetonline.karnataka.gov.in/kea/','karnataka examination authority':'https://cetonline.karnataka.gov.in/kea/'}
TYPE_WORDS={'admit_card':('admit card','e-admit','hall ticket','exam city','city intimation','call letter'),'result':('result','final result','score card','scorecard','marks'),'answer_key':('answer key','response sheet','provisional key','final key'),'cut_off':('cut-off','cut off'),'merit_list':('merit list','selection list','shortlist','shortlisted'),'exam_schedule':('exam date','exam schedule','examination schedule','time table','timetable'),'document_verification':('document verification','certificate verification','dv schedule'),'counselling':('counselling','counseling','seat allotment'),'scholarship':('scholarship','fellowship','stipend'),'admission':('admission','entrance','college admission','university admission'),'syllabus':('syllabus','exam pattern','exam resources'),'notice':('corrigendum','addendum','important notice','advisory','notice')}

def load_module(name,path):
 spec=spec_from_file_location(name,path); module=module_from_spec(spec); spec.loader.exec_module(module); return module
engine=load_module('canonical_engine',ROOT/'scripts'/'canonical-record-engine.py')
fields=load_module('job_fields',ROOT/'scripts'/'job-field-extractor.py')

def save(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def get(url):
 try:
  req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/xhtml+xml,*/*;q=0.1'})
  with urllib.request.urlopen(req,timeout=TIMEOUT) as r:return r.status,r.read(1000000),r.geturl()
 except Exception as exc:return getattr(exc,'code',None),b'',url

def html_text(body):
 s=unescape(body.decode('utf-8','replace')); s=re.sub(r'<script[^>]*>.*?</script>|<style[^>]*>.*?</style>|<noscript[^>]*>.*?</noscript>',' ',s,flags=re.I|re.S); return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',s)).strip()
def title_of(body):
 m=re.search(r'<title[^>]*>(.*?)</title>',body.decode('utf-8','replace'),re.I|re.S); return html_text(m.group(1).encode())[:300] if m else ''
def official(url):
 host=urlparse(url).netloc.lower().split(':')[0]
 return any(host==h or host.endswith('.'+h) for h in GOV_HINTS)
def links(body,base):
 html=body.decode('utf-8','replace'); out=[]
 for href in re.findall(r'href=["\']([^"\']+)["\']',html,re.I):
  u=urljoin(base,unescape(href)).split('#',1)[0]
  if not u.startswith(('http://','https://')) or u in out: continue
  low=u.lower()
  if official(u) or any(k in low for k in ('recruit','career','vacan','notice','notification','advert','apply','job','result','admit','answer','syllabus','admission','scholar')): out.append(u)
  if len(out)>=MAX_LINKS: break
 return out

def authority_candidates(title,desc):
 hay=(title+' '+desc).lower(); out=[]
 for alias,url in AUTHORITY_ALIASES.items():
  if re.search(r'(?<![a-z])'+re.escape(alias)+r'(?![a-z])',hay,re.I): out.append(url)
 try:
  registry=json.loads(REGISTRY.read_text(encoding='utf-8')).get('sources',[])
  for src in registry:
   a=(src.get('name','')+' '+src.get('id','')).lower()
   if a and a in hay: out.append(src.get('url'))
 except Exception: pass
 return list(dict.fromkeys(x for x in out if x))[:10]

def tokens(s): return {x for x in re.findall(r'[a-z0-9]{3,}',(s or '').lower()) if x not in {'the','and','for','online','apply','2026','2025','2024','recruitment','notification','government','govt','posts','post','jobs','job'}}
def authority_hit(title,desc,url):
 hay=(title+' '+desc).lower(); host=urlparse(url).netloc.lower()
 for alias in AUTHORITY_ALIASES:
  if re.search(r'(?<![a-z])'+re.escape(alias)+r'(?![a-z])',hay,re.I):
   if any(part in host for part in re.findall(r'[a-z]{4,}',alias.lower())): return True
 return False

def score(title,official_title,body_text,category,url,desc):
 a=tokens(title); b=tokens(official_title+' '+body_text[:18000]); overlap=len(a&b)/len(a) if a else 0
 signal=any(x in (official_title+' '+body_text[:18000]).lower() for x in TYPE_WORDS.get(category,('recruitment','vacancy','notification','career','employment')))
 auth=authority_hit(title,desc,url)
 return round(min(1.0,overlap+(.25 if auth else 0)+(.10 if signal else 0)),3),len(a&b)

def rich_fields(item,source_text,source_title=''):
 base={'title':item.get('title',''),'text':source_text or item.get('description',''),'notificationUrl':item.get('url',''),'source':item.get('discoverySource','MultiSource'),'category':fields.classify_update_type(item.get('title',''),source_text or item.get('description',''))}
 r=fields.normalize_record(base); r['title']=item.get('title','') or source_title or r.get('title'); r['source']=item.get('discoverySource','MultiSource'); r['category']=base['category']; r['updateType']=base['category']; return r

def candidate_pages(title,desc,discovery_body,discovery_url):
 candidates=authority_candidates(title,desc)
 candidates.extend([u for u in links(discovery_body,discovery_url) if official(u)])
 candidates=list(dict.fromkeys(candidates))[:MAX_LINKS]
 first=[]
 with ThreadPoolExecutor(max_workers=min(10,max(1,len(candidates)))) as pool:
  futures={pool.submit(get,u):u for u in candidates}
  for future in as_completed(futures):
   try:ps,page,resolved=future.result()
   except Exception:continue
   if ps==200 and page:first.append((resolved,page,title_of(page),html_text(page)))
 second=[]
 for resolved,page,ot,txt in first:
  if not official(resolved):continue
  for u in links(page,resolved):
   if u.rstrip('/')==resolved.rstrip('/'):continue
   second.append(u)
  if len(second)>=MAX_LINKS:break
 second=list(dict.fromkeys(second))[:MAX_LINKS]
 if second:
  with ThreadPoolExecutor(max_workers=min(10,len(second))) as pool:
   futures={pool.submit(get,u):u for u in second}
   for future in as_completed(futures):
    try:ps,page,resolved=future.result()
    except Exception:continue
    if ps==200 and page:first.append((resolved,page,title_of(page),html_text(page)))
 return first

def verify_one(item):
 item_id=item['id']; now=datetime.now(timezone.utc).isoformat(); title=item.get('title','').strip(); desc=item.get('description','').strip(); category=fields.classify_update_type(title,desc)
 result={'id':item_id,'discoveryUrl':item.get('url',''),'status':'hold','publicationStatus':'hold','checkedAt':now,'officialSource':None,'checks':{},'discoveryAccess':'unfetched','discoveryMode':item.get('discoveryMode','unknown')}
 discovery_text=desc; discovery_title=title; discovery_body=b''
 if item.get('url','').startswith(('http://','https://')):
  ds,db,df=get(item['url'])
  if ds==200 and db:
   discovery_body=db; discovery_text=html_text(db)[:60000]; discovery_title=title_of(db) or title; result['discoveryAccess']='fetched'
 result['fields']=rich_fields(item,discovery_text,discovery_title)
 pages=candidate_pages(title,desc,discovery_body,item.get('url',''))
 found=[]
 for resolved,page,ot,txt in pages:
  if not official(resolved) or len(txt)<100: continue
  sc,overlap=score(title,ot,txt,category,resolved,desc)
  low=(title+' '+ot+' '+txt[:22000]).lower(); year=bool(re.search(r'\b20\d{2}\b',txt[:30000])); signal=any(x in low for x in TYPE_WORDS.get(category,('recruitment','vacancy','notification')))
  path=urlparse(resolved).path.lower(); specific=any(k in path for k in ('recruit','career','vacan','notice','notification','advert','apply','job','result','admit','answer','syllabus','admission'))
  if year and signal and specific and ((overlap>=2 and sc>=0.30) or (authority_hit(title,desc,resolved) and overlap>=1 and sc>=0.30)):
   found.append((sc,overlap,resolved,ot,txt))
 if found:
  sc,overlap,url,ot,txt=max(found,key=lambda x:(x[0],x[1])); result['officialSource']={'sourceId':'official-government-domain','url':url,'title':ot,'matchScore':sc,'titleOverlap':overlap,'sourceType':'official_notification_or_recruitment_page'}
  official_rich=rich_fields(item,txt,ot)
  for key,value in official_rich.items():
   if value not in (None,'',[]) and result['fields'].get(key) in (None,'',[]): result['fields'][key]=value
 result['checks']['nonempty_title']=bool(title); result['checks']['discovery_signal']=bool(title or desc); result['checks']['discovery_fetched']=bool(discovery_text); result['checks']['official_notice_url']=bool(result['officialSource']); result['checks']['trusted_source']=bool(result['officialSource']); result['checks']['safe_http_urls']=bool(result['officialSource'] and result['officialSource']['url'].startswith(('http://','https://'))); result['checks']['official_content_match']=bool(result['officialSource'] and result['officialSource']['matchScore']>=0.30)
 if all(result['checks'].values()): result['status'],result['publicationStatus']='verified','ready'; result['reason']='official_government_source_verified_with_source_details'
 else: result['reason']='failed_checks:'+','.join(k for k,v in result['checks'].items() if not v)
 return result

def main():
 now=datetime.now(timezone.utc).isoformat(); state=json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {'status':'source_unavailable','items':{}}; canonical=json.loads(CAN.read_text(encoding='utf-8')) if CAN.exists() else {'schemaVersion':1,'items':{}}; previous=json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {'items':{}}
 all_items=list(state.get('items',{}).items())
 all_items.sort(key=lambda p:p[1].get('lastSeenAt') or p[1].get('lastDiscoveredAt') or p[1].get('discoveredAt') or '',reverse=True)
 all_items.sort(key=lambda p:0 if previous.get('items',{}).get(p[0],{}).get('status')!='verified' else 1)
 selected=all_items[:MAX_RECORDS]; skipped=all_items[MAX_RECORDS:]
 results={}; counts={'verified':0,'hold':0,'checked':0,'new':0,'changed':0,'unchanged':0,'reused':0,'skipped':len(skipped),'selectionLimit':MAX_RECORDS}
 with ThreadPoolExecutor(max_workers=WORKERS) as pool:
  futures={pool.submit(verify_one,item):(item_id,item) for item_id,item in selected}
  for future in as_completed(futures):
   item_id,item=futures[future]
   try: result=future.result()
   except Exception as exc: result={'id':item_id,'discoveryUrl':item.get('url',''),'status':'hold','publicationStatus':'hold','checkedAt':now,'officialSource':None,'checks':{'verifier_error':False},'reason':'verifier_exception:'+type(exc).__name__,'fields':rich_fields(item,item.get('description',''))}
   results[item_id]=result; counts['checked']+=1; counts['verified']+=int(result.get('status')=='verified'); counts['hold']+=int(result.get('status')!='verified')
   incoming=dict(result.get('fields',{})); incoming.update({'jobId':item_id,'notificationUrl':incoming.get('notificationUrl') or item.get('url',''),'source':item.get('discoverySource','MultiSource'),'verificationStatus':result.get('status','hold'),'publicationStatus':result.get('publicationStatus','hold'),'officialSource':result.get('officialSource'),'lastSeenAt':now}); canonical,event=engine.upsert(incoming,canonical); ev=str(event.get('event','unchanged')).lower(); counts['new' if ev in ('created','new') else 'changed' if ev in ('updated','changed') else 'unchanged']+=1; result.update({'canonicalRecordId':event.get('jobId',item_id),'changeEvent':event.get('event','unchanged'),'recordVersion':event.get('recordVersion')})
 for item_id,item in skipped: results[item_id]={'id':item_id,'discoveryUrl':item.get('url',''),'status':'hold','publicationStatus':'hold','checkedAt':now,'officialSource':None,'checks':{'deferred_due_to_run_bound':False},'reason':'deferred_due_to_verification_run_bound','fields':rich_fields(item,item.get('description',''))}
 save(CAN,canonical); save(OUT,{'schemaVersion':7,'checkedAt':now,'sourceStatus':state.get('status'),'counts':counts,'items':results}); save(LOG,{'checkedAt':now,'status':'ok','counts':counts,'strategy':'Prioritize new/pending and most recently discovered records within a bounded verification workset; previously verified records are refreshed only after pending work. Parallel official verification with bounded second-hop official link discovery remains strict.'}); return 0
if __name__=='__main__':sys.exit(main())
