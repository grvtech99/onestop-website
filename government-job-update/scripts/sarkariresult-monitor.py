import hashlib,json,sys,urllib.error,urllib.request,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urljoin
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'data'; BASE='https://www.sarkariresult.com/'; UA='ONESTOP-Government-Job-Update/1.0'; STATE=D/'sarkariresult-monitor-state.json'; LOG=D/'sarkariresult-monitor-log.json'
def save(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def get(u):
 try:
  r=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':UA}),timeout=20); return r.status,r.read(2000000),None
 except urllib.error.HTTPError as e: return e.code,b'',f'HTTP {e.code}'
 except Exception as e: return None,b'',str(e)[:300]
def locs(b):
 try: return [e.text.strip() for e in ET.fromstring(b).iter() if e.tag.rsplit('}',1)[-1]=='loc' and e.text]
 except Exception: return []
def main():
 t=datetime.now(timezone.utc).isoformat(); old={}
 try: old=json.loads(STATE.read_text(encoding='utf-8')).get('items',{})
 except Exception: pass
 log={'checkedAt':t,'source':BASE,'status':'unknown','new':0,'changed':0,'error':None}; c,b,e=get(urljoin(BASE,'robots.txt'))
 if c!=200: log.update(status='source_unavailable',error=e or f'HTTP {c}'); save(LOG,log); return 0
 rules=b.decode('utf-8','replace').lower()
 if 'user-agent: *' in rules and 'disallow: /' in rules: log.update(status='robots_blocked',error='robots.txt disallows generic crawling'); save(LOG,log); return 0
 urls=[]
 for ep in ('feed_rss.xml','sitemap.xml'):
  c,x,e=get(urljoin(BASE,ep))
  if c==200: urls += [u for u in locs(x) if u.startswith(BASE)]
 urls=list(dict.fromkeys(urls))[:500]
 if not urls: log.update(status='source_unavailable',error='No accessible public discovery index'); save(LOG,log); return 0
 out={}
 for u in urls:
  k=hashlib.sha256(u.encode()).hexdigest()[:24]; fp=hashlib.sha256(u.encode()).hexdigest(); out[k]={'id':k,'url':u,'fingerprint':fp,'discoveredAt':t}; log['new']+=k not in old; log['changed']+=k in old and old[k].get('fingerprint')!=fp
 save(STATE,{'schemaVersion':1,'source':'sarkariresult','sourceUrl':BASE,'status':'ok','lastCheckedAt':t,'lastSuccessfulDiscoveryAt':t,'lastError':None,'items':out}); save(LOG,log); return 0
if __name__=='__main__': sys.exit(main())
