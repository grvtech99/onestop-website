import json, os, re, sys, urllib.request, urllib.parse, io
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"government-job-update"/"data"
STATE=DATA/"sarkariresult-monitor-state.json"; REGISTRY=DATA/"data"/"government-source-registry.json"
OUT=DATA/"official-verification-state.json"; LOG=DATA/"official-verification-log.json"; CAN=DATA/"canonical-job-records.json"
UA="ONESTOP-Government-Job-Update/4.1"; TIMEOUT=10; WORKERS=10
MAX_RECORDS=int(os.environ.get("ONESTOP_VERIFY_MAX_RECORDS","80")); MAX_CANDIDATES=8
AGG={"freejobalert.com","sarkariresult.com","fresherslive.com","jagranjosh.com","testbook.com","careerpower.in","sarkarinaukriblog.com","indgovtjobs.net","sarkariupdates.live","exampix.com","inrgovtjobs.com","sarkarinaukari.it.com","sarkari247.com","sarkarinaukarisetu.com","sarkari-naukri.in","naukriagent.com","naukripatrika.in","nayawork.in","naukrichakri.in","sarkariscan.com"}
LINK_SIGNAL=re.compile(r"\b(official|notification|advertisement|advt|apply online|online application|career|recruitment|vacancy|download)\b",re.I)
JOB_SIGNAL=re.compile(r"\b(recruit|vacan|job|appointment|apprent|notification|constable|teacher|engineer|assistant|officer|clerk|group\s*[abc]|technician|trainee|professor|nurse|steno|driver|advt|employment|admit card|result|answer key|selection|scholarship|fellowship|admission|notice|corrigendum|addendum)\b",re.I)
SPECIFIC=re.compile(r"(recruit|career|vacan|notice|notification|advert|apply|job|result|admit|answer|syllabus|admission)",re.I)
DATE_RE=re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]20\d{2}|20\d{2}[/-]\d{1,2}[/-]\d{1,2})\b")
ADVT_RE=re.compile(r"\b(?:advt?\.?|advertisement|notification|cen|ref(?:erence)?|file)\s*(?:no\.?|number)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9./_-]{2,})\b",re.I)

def mod(name,path):
 s=spec_from_file_location(name,path); m=module_from_spec(s); s.loader.exec_module(m); return m
engine=mod("canonical_engine",ROOT/"scripts"/"canonical-record-engine.py"); fields=mod("job_fields",ROOT/"scripts"/"job-field-extractor.py")
def save(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def host(u): return urllib.parse.urlparse(u).netloc.lower().split(":")[0].removeprefix("www.")
def same_domain(h,d): return h==d or h.endswith("."+d)
def agg(u): return any(same_domain(host(u),d) for d in AGG)
def fetch(u,limit=8000000):
 try:
  req=urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"application/pdf,text/html,application/xhtml+xml,*/*;q=0.1"})
  with urllib.request.urlopen(req,timeout=TIMEOUT) as r: return r.status,r.read(limit),r.geturl(),r.headers.get("Content-Type","")
 except Exception as e: return getattr(e,"code",None),b"",u,""
def html_text(b):
 s=unescape(b.decode("utf-8","replace")); s=re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>|<noscript[^>]*>.*?</noscript>"," ",s,flags=re.I|re.S); return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",s)).strip()
def title(b):
 m=re.search(r"<title[^>]*>(.*?)</title>",b.decode("utf-8","replace"),re.I|re.S); return html_text(m.group(1).encode())[:400] if m else ""
def pdf_text(b):
 try:
  from pypdf import PdfReader
  r=PdfReader(io.BytesIO(b)); out=[]
  for p in r.pages[:50]:
   try: out.append(p.extract_text() or "")
   except Exception: pass
  return re.sub(r"\s+"," "," ".join(out)).strip()
 except Exception: return ""
def text_of(u,b,ct):
 if "pdf" in (ct or "").lower() or u.lower().split("?",1)[0].endswith(".pdf"): return pdf_text(b),"pdf"
 return html_text(b),"html"
def registry():
 trusted=set(); aliases={}
 try:
  o=json.loads(REGISTRY.read_text(encoding="utf-8"))
  for x in o.get("sources",[]):
   h=host(x.get("url",""))
   if h: trusted.add(h)
   for k in (x.get("name",""),x.get("id","")):
    if k and h: aliases[k.lower()]=h
 except Exception: pass
 trusted.update({"sbi.co.in","rites.com","hurl.net.in","concorindia.co.in","bhel.com","bel-india.in","hal-india.co.in","ongcindia.com","ntpc.co.in","iocl.com","gailonline.com","licindia.in","powergrid.in","pfcindia.com","coalindia.in","hpcl.co.in","bpcl.in","rcfltd.com","balmerlawrie.com","mecl.co.in","ibps.in","nabard.org"})
 return trusted,aliases
TRUSTED,ALIASES=registry()
def trusted(u): return any(same_domain(host(u),d) for d in TRUSTED)
def links(b,base):
 out=[]; seen=set(); raw=b.decode("utf-8","replace")
 for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>",raw,re.I|re.S):
  hm=re.search(r'href\s*=\s*["\']([^"\']+)["\']',m.group(1),re.I)
  if not hm: continue
  u=urllib.parse.urljoin(base,unescape(hm.group(1))).split("#",1)[0]
  if not u.startswith(("http://","https://")) or u in seen or agg(u): continue
  seen.add(u); label=html_text(m.group(2).encode("utf-8","replace"))[:300]; explicit=bool(LINK_SIGNAL.search(label)); tr=trusted(u)
  if explicit or tr: out.append({"url":u,"label":label,"explicit":explicit,"trusted":tr})
 return out
def tok(s): return {x for x in re.findall(r"[a-z0-9]{3,}",(s or "").lower()) if x not in {"the","and","for","online","apply","2024","2025","2026","recruitment","notification","government","govt","posts","post","jobs","job"}}
def evidence(item,ut,body,url,mode,explicit=False,tr=False):
 a=tok(item["title"]); b=tok(ut+" "+body[:60000]); overlap=len(a&b)/max(1,len(a)); signal=bool(JOB_SIGNAL.search(ut+" "+body[:60000])); dates=bool(DATE_RE.search(body[:60000])); ia=ADVT_RE.findall(item["title"]+" "+item.get("description","")); oa=ADVT_RE.findall(body[:60000]); adv=bool(ia and oa and any(x.lower()==y.lower() for x in ia for y in oa)); path=bool(SPECIFIC.search(urllib.parse.urlparse(url).path)); score=(40 if (tr or explicit or trusted(url)) else 0)+(20 if explicit else 0)+min(25,round(overlap*25))+(10 if signal else 0)+(5 if dates else 0)+(15 if adv else 0)+(5 if path else 0)
 return {"score":min(score,120),"titleOverlap":round(overlap,3),"jobSignal":signal,"dateSignal":dates,"advertisementMatch":adv,"specificOfficialPath":path,"trustedDomain":bool(tr or trusted(url)),"explicitOfficialLink":explicit,"mode":mode}
def candidates(item,discovery_body,discovery_final):
 out=[]
 if trusted(item.get("url","")): out.append({"url":item["url"],"label":"official discovery","explicit":True,"trusted":True})
 out+=links(discovery_body,discovery_final)
 hay=(item.get("title","")+" "+item.get("description","")).lower()
 for name,dom in ALIASES.items():
  if re.search(r"(?<![a-z])"+re.escape(name)+r"(?![a-z])",hay,re.I): out.append({"url":"https://"+dom+"/","label":"registry domain","explicit":False,"trusted":True})
 seen=set(); clean=[]
 for c in out:
  if c["url"] not in seen and not agg(c["url"]): seen.add(c["url"]); clean.append(c)
 return clean[:MAX_CANDIDATES]
def verify_one(item):
 now=datetime.now(timezone.utc).isoformat(); title0=(item.get("title") or "").strip(); desc=(item.get("description") or "").strip(); result={"id":item["id"],"discoveryUrl":item.get("url",""),"status":"hold","publicationStatus":"hold","checkedAt":now,"officialSource":None,"checks":{},"evidence":{}}
 ds,db,df,dct=fetch(item.get("url","")) if item.get("url","").startswith(("http://","https://")) else (None,b"",item.get("url",""),""); dtext,_=text_of(df,db,dct); cs=candidates(item,db,df); first=[]
 with ThreadPoolExecutor(max_workers=min(8,max(1,len(cs)))) as pool:
  fs={pool.submit(fetch,c["url"]):c for c in cs}
  for f in as_completed(fs):
   c=fs[f]
   try: st,b,u,ct=f.result()
   except Exception: continue
   if st!=200 or not b: continue
   tx,mode=text_of(u,b,ct)
   if len(tx)>=100: first.append((c,u,b,tx,mode,title(b)))
 second=[]
 for c,u,b,tx,mode,pt in first:
  if mode=="html" and (c["trusted"] or c["explicit"] or trusted(u)):
   for x in links(b,u):
    if SPECIFIC.search(x["url"]) or SPECIFIC.search(x["label"]): second.append(x)
 second=second[:12]
 if second:
  with ThreadPoolExecutor(max_workers=min(8,len(second))) as pool:
   fs={pool.submit(fetch,c["url"]):c for c in second}
   for f in as_completed(fs):
    c=fs[f]
    try: st,b,u,ct=f.result()
    except Exception: continue
    if st!=200 or not b: continue
    tx,mode=text_of(u,b,ct)
    if len(tx)>=100: first.append((c,u,b,tx,mode,title(b)))
 best=None
 for c,u,b,tx,mode,pt in first:
  ev=evidence(item,pt,tx,u,mode,c.get("explicit",False),c.get("trusted",False))
  if best is None or ev["score"]>best[0]["score"]: best=(ev,u,tx,pt)
 if best:
  ev,u,tx,pt=best; result["evidence"]=ev; result["officialSource"]={"sourceId":"official-source-v4.1","url":u,"title":pt,"sourceType":"official_pdf" if ev["mode"]=="pdf" else "official_html","matchScore":ev["score"]}; result["fields"]=fields.normalize_record({"title":title0 or pt,"text":tx[:80000],"notificationUrl":u,"source":item.get("discoverySource") or "MultiSource","category":fields.classify_update_type(title0,tx[:30000])}); result["fields"]["title"]=result["fields"].get("title") or title0 or pt; result["fields"]["source"]=item.get("discoverySource") or "MultiSource"; result["fields"]["updateType"]=result["fields"].get("category") or "jobs"; result["fields"]["officialSource"]=u
  result["checks"]={"nonempty_title":bool(title0),"discovery_fetched":bool(dtext or desc),"official_source_resolved":True,"trusted_official_domain":bool(ev["trustedDomain"]),"content_match":bool(ev["titleOverlap"]>=0.12),"job_signal":bool(ev["jobSignal"]),"publication_evidence":bool(ev["advertisementMatch"] or ev["specificOfficialPath"] or ev["explicitOfficialLink"])}
  if ev["score"]>=65 and all(result["checks"].values()): result["status"],result["publicationStatus"]="verified","ready"; result["reason"]="v4.1_official_source_and_content_verified"
  else: result["reason"]="v4.1_hold_insufficient_official_evidence"
 else:
  result["fields"]=fields.normalize_record({"title":title0,"text":dtext or desc,"notificationUrl":item.get("url",""),"source":item.get("discoverySource") or "MultiSource","category":fields.classify_update_type(title0,dtext or desc)}); result["checks"]={"nonempty_title":bool(title0),"discovery_fetched":bool(dtext or desc),"official_source_resolved":False,"trusted_official_domain":False,"content_match":False,"job_signal":False,"publication_evidence":False}; result["reason"]="v4.1_no_official_source_resolved"
 return result
def main():
 now=datetime.now(timezone.utc).isoformat(); state=json.loads(STATE.read_text(encoding="utf-8"))
 try: can=json.loads(CAN.read_text(encoding="utf-8"))
 except Exception: can={"schemaVersion":1,"items":{}}
 try: prev=json.loads(OUT.read_text(encoding="utf-8"))
 except Exception: prev={}
 items=list(state.get("items",{}).items()); items.sort(key=lambda p:p[1].get("lastSeenAt") or p[1].get("lastDiscoveredAt") or p[1].get("discoveredAt") or "",reverse=True); old=prev.get("items",{}) if isinstance(prev.get("items",{}),dict) else {}; items.sort(key=lambda p:0 if old.get(p[0],{}).get("status")!="verified" else 1); selected,skipped=items[:MAX_RECORDS],items[MAX_RECORDS:]; results={}; counts={"verified":0,"hold":0,"checked":0,"new":0,"changed":0,"unchanged":0,"skipped":len(skipped),"selectionLimit":MAX_RECORDS}
 with ThreadPoolExecutor(max_workers=WORKERS) as pool:
  fs={pool.submit(verify_one,it):(iid,it) for iid,it in selected}
  for f in as_completed(fs):
   iid,it=fs[f]
   try:r=f.result()
   except Exception as e:r={"id":iid,"discoveryUrl":it.get("url",""),"status":"hold","publicationStatus":"hold","checkedAt":now,"officialSource":None,"checks":{"verifier_error":False},"reason":"v4.1_exception:"+type(e).__name__,"fields":{}}
   results[iid]=r; counts["checked"]+=1; counts["verified"]+=r.get("status")=="verified"; counts["hold"]+=r.get("status")!="verified"; incoming=dict(r.get("fields",{})); incoming.update({"jobId":iid,"notificationUrl":incoming.get("notificationUrl") or it.get("url",""),"source":it.get("discoverySource") or "MultiSource","verificationStatus":r.get("status","hold"),"publicationStatus":r.get("publicationStatus","hold"),"officialSource":r.get("officialSource"),"lastSeenAt":now}); can,event=engine.upsert(incoming,can); ev=str(event.get("event","unchanged")).lower(); counts["new" if ev in ("created","new") else "changed" if ev in ("updated","changed") else "unchanged"]+=1; r["canonicalRecordId"]=event.get("jobId",iid); r["changeEvent"]=event.get("event","unchanged")
 for iid,it in skipped: results[iid]={"id":iid,"discoveryUrl":it.get("url",""),"status":"hold","publicationStatus":"hold","checkedAt":now,"officialSource":None,"checks":{"deferred_due_to_run_bound":False},"reason":"deferred_due_to_v4.1_verification_run_bound","fields":{}}
 save(CAN,can); save(OUT,{"schemaVersion":9,"engine":"official-verification-v4.1","checkedAt":now,"sourceStatus":state.get("status"),"counts":counts,"items":results}); save(LOG,{"checkedAt":now,"status":"ok","engine":"official-verification-v4.1","counts":counts,"strategy":"Discovery-only aggregators; resolve official sources through registry, explicit official links, organization domains, then second-hop official recruitment/career pages with HTML/PDF extraction."}); print(json.dumps({"status":"PASS","engine":"official-verification-v4.1",**counts},indent=2)); return 0
if __name__=="__main__": sys.exit(main())
