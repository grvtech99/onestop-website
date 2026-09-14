import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
STATE = DATA / "sarkariresult-monitor-state.json"
LOG = DATA / "sarkariresult-monitor-log.json"

# SarkariResult was removed after repeated direct-access failures. Discovery now
# uses the 20 remaining sources plus FreeJobAlert. Official government sources
# remain the final verification authority.
SOURCES = [
 {"id":"employmentnews","name":"Employment News","url":"https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All"},
 {"id":"ncs","name":"National Career Service","url":"https://ncs.gov.in/latest-update"},
 {"id":"fresherslive","name":"FreshersLive","url":"https://www.fresherslive.com/state-government-jobs"},
 {"id":"jagranjosh","name":"Jagran Josh","url":"https://www.jagranjosh.com/government-jobs"},
 {"id":"testbook","name":"Testbook","url":"https://testbook.com/news/"},
 {"id":"sarkarinaukriblog","name":"Sarkari Naukri Blog","url":"https://www.sarkarinaukriblog.com/","rss":"https://www.sarkarinaukriblog.com/feeds/posts/default"},
 {"id":"careerpower","name":"Career Power","url":"https://www.careerpower.in/blog","rss":"https://www.careerpower.in/blog/feed/"},
 {"id":"indgovtjobs","name":"IndGovtJobs","url":"https://indgovtjobs.net/","rss":"https://indgovtjobs.net/feed/"},
 {"id":"sarkariupdates","name":"SarkariUpdates","url":"https://www.sarkariupdates.live/jobs","rss":"https://www.sarkariupdates.live/feed/"},
 {"id":"exampix","name":"Exampix","url":"https://exampix.com/","rss":"https://exampix.com/feed/"},
 {"id":"inrgovtjobs","name":"INR Govt Jobs","url":"https://www.inrgovtjobs.com/","rss":"https://www.inrgovtjobs.com/feed/"},
 {"id":"sarkarinaukari","name":"Sarkari Naukari","url":"https://sarkarinaukari.it.com/jobs/"},
 {"id":"sarkari247","name":"Sarkari247","url":"https://www.sarkari247.com/"},
 {"id":"sarkarinaukarisetu","name":"Sarkari Naukri Setu","url":"https://www.sarkarinaukarisetu.com/jobs"},
 {"id":"sarkarinaukri","name":"Sarkari-Naukri.in","url":"https://www.sarkari-naukri.in/"},
 {"id":"naukriagent","name":"NaukriAgent","url":"https://naukriagent.com/"},
 {"id":"naukripatrika","name":"Naukri Patrika","url":"https://naukripatrika.in/"},
 {"id":"nayawork","name":"NayaWork","url":"https://nayawork.in/"},
 {"id":"naukrichakri","name":"Naukri Chakri","url":"https://www.naukrichakri.in/"},
 {"id":"sarkariscan","name":"Sarkari Scan","url":"https://sarkariscan.com/"},
 {"id":"freejobalert","name":"FreeJobAlert","url":"https://www.freejobalert.com/latest-notifications/","rss":"https://www.freejobalert.com/feed/"},
]
JOB = re.compile(r"\b(recruit|vacan|job|online form|apprent|notification|constable|teacher|engineer|assistant|officer|clerk|group [abc]|technician|trainee|professor|nurse|steno|driver|advt|employment)\b", re.I)

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def get(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"ONESTOP-Government-Job-Update/3.0","Accept":"application/rss+xml,application/atom+xml,application/xml,text/html;q=0.9,*/*;q=0.1"})
        r = urllib.request.urlopen(req, timeout=15)
        return r.status, r.read(1200000), r.geturl(), None
    except urllib.error.HTTPError as e: return e.code, b"", url, f"HTTP {e.code}"
    except Exception as e: return None, b"", url, str(e)[:200]

def rss_items(body):
    out=[]
    try:
        root=ET.fromstring(body)
        for item in root.iter():
            if item.tag.rsplit("}",1)[-1] not in ("item","entry"): continue
            row={}
            for c in item:
                tag=c.tag.rsplit("}",1)[-1]; val=(c.text or "").strip()
                if tag in ("link","title","description","summary","pubDate","published","updated","guid") and val: row[tag]=val
                if tag=="link" and not val and c.attrib.get("href"): row["link"]=c.attrib["href"]
            if row.get("link") and JOB.search(row.get("title","")): out.append(row)
    except Exception: pass
    return out

def html_items(body, base, limit=120):
    text=body.decode("utf-8","replace"); out=[]
    for m in re.finditer(r'<a\b[^>]*href=[\'\"]([^\'\"]+)[\'\"][^>]*>(.*?)</a>', text, re.I|re.S):
        u=urllib.parse.urljoin(base,m.group(1)).split("#",1)[0]
        title=re.sub(r"<[^>]+>"," ",m.group(2)); title=re.sub(r"\s+"," ",title).strip()
        if u.startswith(("http://","https://")) and JOB.search(title) and len(title)>=12: out.append({"link":u,"title":title})
    return list({x["link"]:x for x in out}.values())[:limit]

def main():
    t=datetime.now(timezone.utc).isoformat(); old={}
    try: old=json.loads(STATE.read_text()).get("items",{})
    except Exception: pass
    discovered=[]; channels=[]; source_results={}
    for src in SOURCES:
        found=[]; mode=None
        if src.get("rss"):
            c,b,final,e=get(src["rss"])
            if c==200: found=rss_items(b); mode="rss" if found else None
        if not found:
            c,b,final,e=get(src["url"])
            if c==200: found=html_items(b,final); mode="html" if found else None
        source_results[src["id"]]={"name":src["name"],"status":"ok" if found else "unavailable","mode":mode,"count":len(found)}
        if found:
            channels.append(src["id"])
            for r in found:
                discovered.append({"url":r.get("link",""),"title":r.get("title",""),"description":r.get("description",r.get("summary","")),"publishedAt":r.get("pubDate",r.get("published",r.get("updated",""))),"discoverySource":src["name"],"discoverySourceId":src["id"]})
    out={}; new=changed=0
    for row in discovered[:2000]:
        u=row["url"].split("#",1)[0]
        if not u.startswith(("http://","https://")): continue
        meta="|".join([u,row.get("title",""),row.get("description",""),row.get("publishedAt",""),row.get("discoverySourceId","")])
        k=hashlib.sha256((row.get("discoverySourceId","")+"|"+u).encode()).hexdigest()[:24]
        fp=hashlib.sha256(meta.encode()).hexdigest(); prev=old.get(k,{})
        out[k]={"id":k,"url":u,"title":row.get("title",""),"description":row.get("description",""),"publishedAt":row.get("publishedAt",""),"fingerprint":fp,"discoveredAt":prev.get("discoveredAt",t),"lastSeenAt":t,"discoverySource":row.get("discoverySource",""),"discoverySourceId":row.get("discoverySourceId",""),"verificationStatus":"pending_official_source","publicationStatus":"hold"}
        if k not in old:new+=1
        elif prev.get("fingerprint")!=fp:changed+=1
    status="ok" if out else "source_unavailable"
    err=None if out else "No usable job signals from monitored sources"
    save(STATE,{"schemaVersion":5,"source":"multi-source-government-jobs","primarySource":"multi-source","lastCheckedAt":t,"lastSuccessfulDiscoveryAt":t if out else None,"status":status,"lastError":err,"items":out,"sources":source_results})
    save(LOG,{"checkedAt":t,"status":status,"new":new,"changed":changed,"items":len(out),"discoveryChannels":channels,"sources":source_results,"policy":"SarkariResult removed; 20 alternate sources plus FreeJobAlert are discovery-only; official government source remains final authority"})
    return 0
if __name__=="__main__": sys.exit(main())
