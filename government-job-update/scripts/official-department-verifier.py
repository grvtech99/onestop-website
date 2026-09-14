import json,re,sys,urllib.error,urllib.request
from datetime import datetime,timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin
from importlib.util import spec_from_file_location,module_from_spec
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'data'; STATE=D/'sarkariresult-monitor-state.json'; REG=D/'data'/'government-source-registry.json'; OUT=D/'official-verification-state.json'; LOG=D/'official-verification-log.json'; CAN=D/'canonical-job-records.json'
s=spec_from_file_location('engine',ROOT/'scripts'/'canonical-record-engine.py'); engine=module_from_spec(s); s.loader.exec_module(engine)
s=spec_from_file_location('fields',ROOT/'scripts'/'job-field-extractor.py'); fields=module_from_spec(s); s.loader.exec_module(fields)
UA='ONESTOP-Government-Job-Update/1.1'; KEYS=('recruitment','vacancy','notification','apply online','career','jobs','application','admit card','result','answer key'); DATE=re.compile(r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',re.I)
def save(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def get(u):
 try:
  r=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':UA,'Accept':'text/html,application/xhtml+xml,application/pdf;q=0.8,*/*;q=0.1'}),timeout=20); return r.status,r.read(1500000),r.geturl()
 except Exception as e: return getattr(e,'code',None),b'',u
def clean(b):
 x=unescape(b.decode('utf-8','replace')); x=re.sub(r'<script[^>]*>.*?</script>|<style[^>]*>.*?</style>','\n',x,flags=re.I|re.S); x=re.sub(r'<(?:br|p|div|li|tr|td|th|h[1-6])[^>]*>','\n',x,flags=re.I); x=re.sub(r'<[^>]+>',' ',x); return '\n'.join(re.sub(r'[ \t]+',' ',z).strip() for z in x.splitlines() if z.strip())
def ttl(b):
 m=re.search(r'<title[^>]*>(.*?)</title>',b.decode('utf-8','replace'),re.I|re.S); return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',m.group(1))).strip()[:300] if m else ''
def links(b,base):
 return list(dict.fromkeys(urljoin(base,h).split('#',1)[0] for h in re.findall(r'href=["\']([^"\']+)["\']',b.decode('utf-8','replace'),re.I) if urljoin(base,h).startswith(('http://','https://'))))
def score(a,b):
 w=set(re.findall(r'[a-z0-9]{4,}',a.lower())); t=set(re.findall(r'[a-z0-9]{4,}',b.lower())); return len(w&t)/len(w) if w else 0
def main():
 now=datetime.now(timezone.utc).isoformat()
 try: state=json.loads(STATE.read_text())
 except Exception: state={'status':'source_unavailable','items':{}}
 try: reg=json.loads(REG.read_text())
 except Exception: reg={'sources':[]}
 try: can=json.loads(CAN.read_text())
 except Exception: can={'schemaVersion':1,'items':{}}
 sources={x['id']:x for x in reg.get('sources',[]) if x.get('enabled')}; results={}; counts={'verified':0,'hold':0,'checked':0,'new':0,'changed':0,'unchanged':0}
 for iid,item in state.get('items',{}).items():
  counts['checked']+=1; url=item.get('url',''); st=item.get('title','').strip(); desc=item.get('description','').strip(); c,b,final=get(url); text=clean(b) if c==200 and b else desc; st=ttl(b) or st if c==200 and b else st
  ex=fields.normalize_record({'title':st,'text':text,'notificationUrl':url,'source':'SarkariResult'}); r={'id':iid,'discoveryUrl':url,'status':'hold','publicationStatus':'hold','checkedAt':now,'officialSource':None,'checks':{},'discoveryAccess':'ok' if c==200 else 'metadata_only'}
  r['fields']=ex; r['checks']['nonempty_title']=bool(st); r['checks']['discovery_signal']=bool(st or desc); hay=(st+' '+text).lower(); candidates=[]
  for sid,src in sources.items():
   nt=set(re.findall(r'[a-z0-9]{4,}',src.get('name','').lower())); ht=set(re.findall(r'[a-z0-9]{4,}',hay)); ov=len(nt&ht); exact=src.get('name','').lower() in hay
   if exact or ov>=1: candidates.append((100 if exact else ov*10,src))
  found=[]
  for _,src in sorted(candidates,reverse=True,key=lambda x:x[0])[:4]:
   cc,bb,ff=get(src['url'])
   if cc!=200 or not bb: continue
   pages=[(src['url'],bb,ff)]
   for u in links(bb,ff):
    if any(k in u.lower() for k in ('recruit','career','vacan','job','notice','notification','advert','latest')): pages.append((u,None,u))
   for u,p,base in pages[:18]:
    if p is None:
     cc,p,base=get(u)
     if cc!=200 or not p: continue
    ot=ttl(p); ob=clean(p); low=ob.lower(); sc=score(st,ot+' '+ob[:20000]);
    if len(ob)>=200 and sc>=0.25 and any(k in low for k in KEYS) and DATE.search(low): found.append((sc,src,u,ot))
  if found:
   sc,src,u,ot=max(found,key=lambda x:x[0]); r['officialSource']={'sourceId':src['id'],'url':u,'title':ot,'matchScore':round(sc,3)}
  r['checks']['official_notice_url']=bool(r['officialSource']); r['checks']['trusted_source']=bool(r['officialSource']); r['checks']['safe_http_urls']=bool(r['officialSource'] and r['officialSource']['url'].startswith(('http://','https://'))); r['checks']['official_content_match']=bool(r['officialSource'] and r['officialSource']['matchScore']>=0.25)
  if all(r['checks'].values()): r['status']='verified'; r['publicationStatus']='ready'; r['reason']='official_department_match_and_required_checks_passed'; counts['verified']+=1
  else: r['reason']='failed_checks:'+','.join(k for k,v in r['checks'].items() if not v); counts['hold']+=1
  incoming=dict(ex); incoming.update({'jobId':iid,'notificationUrl':ex.get('notificationUrl') or url,'source':'SarkariResult','verificationStatus':r['status'],'publicationStatus':r['publicationStatus'],'officialSource':r['officialSource'],'lastSeenAt':now}); can,ev=engine.upsert(incoming,can); counts[ev['event'].lower()]+=1; r.update({'canonicalRecordId':ev['jobId'],'changeEvent':ev['event'],'recordVersion':ev['recordVersion']}); results[iid]=r
 save(CAN,can); save(OUT,{'schemaVersion':2,'checkedAt':now,'sourceStatus':state.get('status'),'counts':counts,'items':results}); save(LOG,{'checkedAt':now,'status':'ok','counts':counts,'strategy':'SarkariResult metadata -> targeted official department verification'}); return 0
if __name__=='__main__': sys.exit(main())
