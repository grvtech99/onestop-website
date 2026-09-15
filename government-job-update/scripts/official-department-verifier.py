import json
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
UA='ONESTOP-Government-Job-Update/3.0'
TIMEOUT=5
WORKERS=20
MAX_RECORDS=300
MAX_LINKS=8
GOV_HINTS=('gov.in','nic.in','ac.in','edu.in','govt.in')

AUTHORITY_ALIASES={
 'ssc':'https://ssc.gov.in/','staff selection commission':'https://ssc.gov.in/',
 'upsc':'https://www.upsc.gov.in/','union public service commission':'https://www.upsc.gov.in/',
 'rrb':'https://www.rrbapply.gov.in/','railway recruitment':'https://www.rrbapply.gov.in/',
 'nta':'https://exams.nta.ac.in/','national testing agency':'https://exams.nta.ac.in/',
 'drdo':'https://www.drdo.gov.in/','isro':'https://www.isro.gov.in/','csir':'https://www.csir.res.in/',
 'icmr':'https://www.icmr.gov.in/','aiims':'https://www.aiims.edu/','ugc':'https://www.ugc.gov.in/',
 'ibps':'https://www.ibps.in/','rbi':'https://www.rbi.org.in/','sbi':'https://sbi.co.in/',
 'nabard':'https://www.nabard.org/','sebi':'https://www.sebi.gov.in/','epfo':'https://www.epfindia.gov.in/',
 'esic':'https://www.esic.gov.in/','employees state insurance':'https://www.esic.gov.in/',
 'bhel':'https://www.bhel.com/','bel':'https://bel-india.in/','hal':'https://hal-india.co.in/',
 'ongc':'https://ongcindia.com/','ntpc':'https://www.ntpc.co.in/','iocl':'https://iocl.com/',
 'gail':'https://www.gailonline.com/','lic':'https://licindia.in/',
 'uppsc':'https://uppsc.up.nic.in/','upsssc':'https://upsssc.gov.in/','bpsc':'https://www.bpsc.bih.nic.in/',
 'rpsc':'https://rpsc.rajasthan.gov.in/','mppsc':'https://mppsc.mp.gov.in/','hpsc':'https://hpsc.gov.in/',
 'wbpsc':'https://psc.wb.gov.in/','mpsc':'https://mpsc.gov.in/','tnpsc':'https://www.tnpsc.gov.in/',
 'kpsc':'https://kpsc.kar.nic.in/','employment news':'https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All',
 'national scholarship portal':'https://scholarships.gov.in/','nsp':'https://scholarships.gov.in/',
 'mecl':'https://mecl.co.in/','mineral exploration':'https://mecl.co.in/',
 'nfsu':'https://nfsu.ac.in/','national forensic sciences university':'https://nfsu.ac.in/',
 'balmer lawrie':'https://www.balmerlawrie.com/','rcf':'https://www.rcfltd.com/','rashtriya chemicals':'https://www.rcfltd.com/',
 'hpcl':'https://www.hindustanpetroleum.com/','bpcl':'https://www.bharatpetroleum.in/','coal india':'https://www.coalindia.in/',
 'powergrid':'https://www.powergrid.in/','pfc':'https://www.pfcindia.com/','rec limited':'https://recindia.nic.in/',
 'nfdb':'https://nfdb.gov.in/','fci':'https://fci.gov.in/','nabcons':'https://www.nabcons.com/'
}

JOB_WORDS=('recruitment','vacancy','notification','apply','posts','post','job','career','selection','apprentice','employment')
TYPE_WORDS={
 'admit_card':('admit card','e-admit','hall ticket','exam city','city intimation','call letter'),
 'result':('result','final result','score card','scorecard','marks'),
 'answer_key':('answer key','response sheet','provisional key','final key'),
 'cut_off':('cut-off','cut off'),
 'merit_list':('merit list','selection list','shortlist','shortlisted'),
 'exam_schedule':('exam date','exam schedule','examination schedule','time table','timetable'),
 'document_verification':('document verification','certificate verification','dv schedule'),
 'counselling':('counselling','counseling','seat allotment'),
 'scholarship':('scholarship','fellowship','stipend'),
 'admission':('admission','entrance','application form','college admission','university admission'),
 'syllabus':('syllabus','exam pattern','exam resources'),
 'notice':('corrigendum','addendum','important notice','advisory','notification','notice'),
}

def load_module(name,path):
 spec=spec_from_file_location(name,path); module=module_from_spec(spec); spec.loader.exec_module(module); return module
engine=load_module('canonical_engine',ROOT/'scripts'/'canonical-record-engine.py')
fields=load_module('job_fields',ROOT/'scripts'/'job-field-extractor.py')

def save(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def get(url):
 try:
  req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/xhtml+xml,*/*;q=0.1'})
  with urllib.request.urlopen(req,timeout=TIMEOUT) as r:return r.status,r.read(700_000),r.geturl()
 except Exception as exc:return getattr(exc,'code',None),b'',url
def html_text(body):
 s=unescape(body.decode('utf-8','replace')); s=re.sub(r'<script[^>]*>.*?</script>|<style[^>]*>.*?</style>',' ',s,flags=re.I|re.S); return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',s)).strip()
def title_of(body):
 m=re.search(r'<title[^>]*>(.*?)</title>',body.decode('utf-8','replace'),re.I|re.S); return html_text(m.group(1).encode())[:300] if m else ''
def official(url):
 host=urlparse(url).netloc.lower().split(':')[0]; return any(host==h or host.endswith('.'+h) for h in GOV_HINTS)
def extract_urls(text,base=''):
 text=unescape(text or ''); found=[]
 for raw in re.findall(r'https?://[^\s"\'<>]+',text,re.I):
  u=raw.rstrip(').,;');
  if official(u):found.append(u)
 for raw in re.findall(r'href=["\']([^"\']+)["\']',text,re.I):
  u=urljoin(base,unescape(raw)).split('#',1)[0]
  if official(u):found.append(u)
 return list(dict.fromkeys(found))[:MAX_LINKS]
def links(body,base):
 html=body.decode('utf-8','replace'); out=[]
 for href in re.findall(r'href=["\']([^"\']+)["\']',html,re.I):
  u=urljoin(base,unescape(href)).split('#',1)[0]
  if not u.startswith(('http://','https://')) or u in out:continue
  low=u.lower()
  if official(u) or any(k in low for k in ('recruit','career','vacan','notice','notification','advert','apply','job','result','admit','answer','syllabus','admission','scholar')):out.append(u)
  if len(out)>=MAX_LINKS:break
 return out

def authority_candidates(title,desc):
 hay=(title+' '+desc).lower(); out=[]
 try:
  registry=json.loads(REGISTRY.read_text(encoding='utf-8')).get('sources',[])
  for src in registry:
   name=(src.get('name','')+' '+src.get('id','')).lower()
   if any(tok in hay for tok in [src.get('id','').lower(),src.get('name','').lower()] if tok):out.append(src.get('url'))
 except Exception:pass
 for alias,url in AUTHORITY_ALIASES.items():
  if re.search(r'(?<![a-z])'+re.escape(alias)+r'(?![a-z])',hay,re.I):out.append(url)
 return list(dict.fromkeys(x for x in out if x))[:10]

def update_type(title,desc):
 return fields.classify_update_type(title,desc)
def score(title,official_title,body_text,category):
 a=set(re.findall(r'[a-z0-9]{3,}',title.lower())); b=set(re.findall(r'[a-z0-9]{3,}',(official_title+' '+body_text[:12000]).lower()))
 overlap=len(a&b)/len(a) if a else 0.0
 signals=TYPE_WORDS.get(category,JOB_WORDS); signal=any(x in (official_title+' '+body_text[:15000]).lower() for x in signals)
 authority=any(x in (official_title+' '+body_text[:15000]).lower() for x in re.findall(r'[a-z]{3,}',title.lower())[:3])
 return round(min(1.0,overlap+(.12 if signal else 0)+(.08 if authority else 0)),3)

def verify_one(item,old):
 item_id=item['id']; previous=old.get(item_id,{})
 if previous.get('status')=='verified' and previous.get('officialSource'):
  r=dict(previous); r['checkedAt']=datetime.now(timezone.utc).isoformat(); r['verificationReused']=True; return r
 now=datetime.now(timezone.utc).isoformat(); title=item.get('title','').strip(); desc=item.get('description','').strip(); category=update_type(title,desc)
 result={'id':item_id,'discoveryUrl':item.get('url',''),'status':'hold','publicationStatus':'hold','checkedAt':now,'officialSource':None,'checks':{},'discoveryAccess':'metadata_embedded_link','discoveryMode':item.get('discoveryMode','unknown')}
 result['fields']=fields.normalize_record({'title':title,'text':desc,'notificationUrl':item.get('url',''),'source':item.get('discoverySource','MultiSource'),'category':category})
 result['fields']['category']=category; result['fields']['updateType']=category
 result['checks']['nonempty_title']=bool(title); result['checks']['discovery_signal']=bool(title or desc)
 candidates=[]; candidates.extend(extract_urls(desc,item.get('url','')))
 if official(item.get('url','')):candidates.insert(0,item['url'])
 candidates.extend(authority_candidates(title,desc))
 if not candidates and item.get('url','').startswith(('http://','https://')):
  status,body,final=get(item['url'])
  if status==200 and body:candidates.extend([u for u in links(body,final) if official(u)])
 candidates=list(dict.fromkeys(candidates))[:MAX_LINKS+4]
 pages=[]
 with ThreadPoolExecutor(max_workers=min(8,max(1,len(candidates)))) as pool:
  futures={pool.submit(get,u):u for u in candidates}
  for future in as_completed(futures):
   u=futures[future]
   try:ps,page,resolved=future.result()
   except Exception:continue
   if ps==200 and page:pages.append((resolved,page,title_of(page),html_text(page)))
 # One bounded second hop from authority landing pages finds the specific official notice.
 second=[]
 for resolved,page,ot,txt in pages:
  second.extend([u for u in links(page,resolved) if official(u)])
 for u in list(dict.fromkeys(second))[:MAX_LINKS]:
  if any(u==p[0] for p in pages):continue
  ps,page,resolved=get(u)
  if ps==200 and page:pages.append((resolved,page,title_of(page),html_text(page)))
 found=[]
 for resolved,page,ot,txt in pages:
  if not official(resolved) or len(txt)<80:continue
  low=(title+' '+ot+' '+txt[:18000]).lower(); year=bool(re.search(r'\b20\d{2}\b',txt[:25000]))
  sc=score(title,ot,txt,category)
  signal=any(x in low for x in TYPE_WORDS.get(category,JOB_WORDS))
  if year and signal and sc>=0.10:found.append((sc,resolved,ot))
 if found:
  sc,url,ot=max(found,key=lambda x:x[0]); result['officialSource']={'sourceId':'official-government-domain','url':url,'title':ot,'matchScore':sc}
 result['checks']['official_notice_url']=bool(result['officialSource']); result['checks']['trusted_source']=bool(result['officialSource']); result['checks']['safe_http_urls']=bool(result['officialSource'] and result['officialSource']['url'].startswith(('http://','https://'))); result['checks']['official_content_match']=bool(result['officialSource'] and result['officialSource']['matchScore']>=0.10)
 if all(result['checks'].values()):result['status'],result['publicationStatus']='verified','ready'; result['reason']='official_government_source_verified_for_'+category
 else:result['reason']='failed_checks:'+','.join(k for k,v in result['checks'].items() if not v)
 return result

def main():
 now=datetime.now(timezone.utc).isoformat(); state=json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {'status':'source_unavailable','items':{}}; canonical=json.loads(CAN.read_text(encoding='utf-8')) if CAN.exists() else {'schemaVersion':1,'items':{}}; previous=json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {'items':{}}
 all_items=list(state.get('items',{}).items()); all_items.sort(key=lambda p:-len((p[1].get('title','')+' '+p[1].get('description','')))); selected=all_items[:MAX_RECORDS]; skipped=all_items[MAX_RECORDS:]
 results={}; counts={'verified':0,'hold':0,'checked':0,'new':0,'changed':0,'unchanged':0,'reused':0,'skipped':len(skipped)}
 with ThreadPoolExecutor(max_workers=WORKERS) as pool:
  futures={pool.submit(verify_one,item,previous.get('items',{})):(item_id,item) for item_id,item in selected}
  for future in as_completed(futures):
   item_id,item=futures[future]
   try:result=future.result()
   except Exception as exc:result={'id':item_id,'discoveryUrl':item.get('url',''),'status':'hold','publicationStatus':'hold','checkedAt':now,'officialSource':None,'checks':{'verifier_error':False},'reason':'verifier_exception:'+type(exc).__name__}
   results[item_id]=result; counts['checked']+=1; counts['reused']+=int(bool(result.get('verificationReused'))); counts['verified']+=int(result.get('status')=='verified'); counts['hold']+=int(result.get('status')!='verified')
   incoming=dict(result.get('fields',{})); incoming.update({'jobId':item_id,'notificationUrl':incoming.get('notificationUrl') or item.get('url',''),'source':item.get('discoverySource','MultiSource'),'verificationStatus':result.get('status','hold'),'publicationStatus':result.get('publicationStatus','hold'),'officialSource':result.get('officialSource'),'lastSeenAt':now}); canonical,event=engine.upsert(incoming,canonical); ev=str(event.get('event','unchanged')).lower(); counts['new' if ev in ('created','new') else 'changed' if ev in ('updated','changed') else 'unchanged']+=1; result.update({'canonicalRecordId':event.get('jobId',item_id),'changeEvent':event.get('event','unchanged'),'recordVersion':event.get('recordVersion')})
 for item_id,item in skipped:
  results[item_id]={'id':item_id,'discoveryUrl':item.get('url',''),'status':'hold','publicationStatus':'hold','checkedAt':now,'officialSource':None,'checks':{'deferred_due_to_run_bound':False},'reason':'deferred_due_to_verification_run_bound','fields':fields.normalize_record({'title':item.get('title',''),'text':item.get('description',''),'notificationUrl':item.get('url',''),'source':item.get('discoverySource','MultiSource')})}
 save(CAN,canonical); save(OUT,{'schemaVersion':6,'checkedAt':now,'sourceStatus':state.get('status'),'counts':counts,'items':results}); save(LOG,{'checkedAt':now,'status':'ok','counts':counts,'strategy':'Parallel authority-aware verification across jobs, admit cards, results, answer keys, admissions, scholarships, syllabus and notices'}); print(json.dumps(counts,indent=2)); return 0
if __name__=='__main__':sys.exit(main())
