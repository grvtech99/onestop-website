import hashlib,json,sys,urllib.error,urllib.request,xml.etree.ElementTree as ET,re
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urljoin
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'data'; BASE='https://www.sarkariresult.com/'; UA='ONESTOP-Government-Job-Update/1.1'; STATE=D/'sarkariresult-monitor-state.json'; LOG=D/'sarkariresult-monitor-log.json'
def save(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def get(u):
 try:
  r=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':UA,'Accept':'application/xml,text/xml,text/html;q=0.9,*/*;q=0.1'}),timeout=20); return r.status,r.read(2000000),r.geturl(),None
 except urllib.error.HTTPError as e: return e.code,b'',u,f'HTTP {e.code}'
 except Exception as e: return None,b'',u,str(e)[:300]
def state(status,t,error=None,items=None):
 save(STATE,{'schemaVersion':2,'source':'sarkariresult','sourceUrl':BASE,'status':status,'lastCheckedAt':t,'lastSuccessfulDiscoveryAt':t if status=='ok' else None,'lastError':error,'items':items or {}})
def rss_items(b):
 out=[]
 try:
  root=ET.fromstring(b)
  for item in root.iter():
   if item.tag.rsplit('}',1)[-1]!='item': continue
   row={}
   for c in item:
    tag=c.tag.rsplit('}',1)[-1]
    if c.text and tag in ('link','title','description','pubDate','guid'): row[tag]=c.text.strip()
   if row.get('link'): out.append(row)
 except Exception: pass
 return out
def sitemap_entries(b):
 out=[]
 try:
  root=ET.fromstring(b); kind=root.tag.rsplit('}',1)[-1]
  if kind=='sitemapindex':
   for e in root.iter():
    if e.tag.rsplit('}',1)[-1]=='loc' and e.text: out.append({'url':e.text.strip()})
  elif kind=='urlset':
   current=None
   for e in root.iter():
    tag=e.tag.rsplit('}',1)[-1]
    if tag=='url': current={}
    elif current is not None and tag in ('loc','lastmod') and e.text: current[tag]=e.text.strip()
    if tag=='url' and current is not None and current.get('loc'): out.append(current); current=None
 except Exception: pass
 return out
def main():
 t=datetime.now(timezone.utc).isoformat(); old={}
 try: old=json.loads(STATE.read_text(encoding='utf-8')).get('items',{})
 except Exception: pass
 log={'checkedAt':t,'source':BASE,'status':'unknown','new':0,'changed':0,'error':None,'discoveryChannels':[]}
 c,b,final,e=get(urljoin(BASE,'robots.txt'))
 if c!=200:
  log.update(status='source_unavailable',error=e or f'HTTP {c}'); state('source_unavailable',t,log['error'],old); save(LOG,log); return 0
 rules=b.decode('utf-8','replace').lower()
 if 'user-agent: *' in rules and re.search(r'user-agent:\s*\*.*?disallow:\s*/(?:\s|$)',rules,re.S):
  log.update(status='robots_blocked',error='robots.txt disallows generic crawling'); state('robots_blocked',t,log['error'],old); save(LOG,log); return 0
 discovered=[]
 c,x,final,e=get(urljoin(BASE,'feed_rss.xml'))
 if c==200:
  discovered += [{'url':r['link'],'title':r.get('title',''),'description':r.get('description',''),'publishedAt':r.get('pubDate','')} for r in rss_items(x)]
  if discovered: log['discoveryChannels'].append('public-rss')
 c,x,final,e=get(urljoin(BASE,'sitemap.xml'))
 if c==200:
  entries=sitemap_entries(x)
  if entries and entries[0].get('url','').endswith('sitemap.xml'):
   for sm in entries[:5]:
    cc,xx,ff,ee=get(sm['url'])
    if cc==200: entries=sitemap_entries(xx); break
  if entries: discovered += entries; log['discoveryChannels'].append('public-sitemap')
  elif final.rstrip('/')==BASE.rstrip('/'):
   discovered += [{'url':u} for u in re.findall(r'href=[\"\']([^\"\']+)[\"\']',x.decode('utf-8','replace'),re.I) if urljoin(BASE,u).startswith(BASE)]
   if discovered: log['discoveryChannels'].append('public-sitemap-redirect-html')
 if not discovered:
  log.update(status='source_unavailable',error='No accessible public RSS/sitemap discovery items'); state('source_unavailable',t,log['error'],old); save(LOG,log); return 0
 out={}
 for row in discovered[:1000]:
  u=row.get('url','').split('#',1)[0]
  if not u.startswith(BASE): continue
  meta='|'.join([u,row.get('title',''),row.get('description',''),row.get('publishedAt',''),row.get('lastmod','')])
  k=hashlib.sha256(u.encode()).hexdigest()[:24]; fp=hashlib.sha256(meta.encode()).hexdigest()
  prev=old.get(k,{})
  out[k]={'id':k,'url':u,'title':row.get('title',''),'description':row.get('description',''),'publishedAt':row.get('publishedAt',''),'lastmod':row.get('lastmod',''),'fingerprint':fp,'discoveredAt':prev.get('discoveredAt',t),'lastSeenAt':t,'verificationStatus':'pending_official_source','publicationStatus':'hold'}
  if k not in old: log['new']+=1
  elif prev.get('fingerprint')!=fp: log['changed']+=1
 state('ok',t,None,out); log['status']='ok'; save(LOG,log); return 0
if __name__=='__main__': sys.exit(main())
