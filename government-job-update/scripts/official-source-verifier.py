import hashlib,json,re,sys,urllib.error,urllib.request
from datetime import datetime,timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin,urlparse
from importlib.util import spec_from_file_location,module_from_spec
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'data'
STATE=D/'sarkariresult-monitor-state.json'; REGISTRY=D/'data'/'government-source-registry.json'; OUT=D/'official-verification-state.json'; LOG=D/'official-verification-log.json'; CANONICAL=D/'canonical-job-records.json'
spec=spec_from_file_location('canonical_engine',ROOT/'scripts'/'canonical-record-engine.py'); engine=module_from_spec(spec); spec.loader.exec_module(engine)
spec2=spec_from_file_location('field_extractor',ROOT/'scripts'/'job-field-extractor.py'); fields=module_from_spec(spec2); spec2.loader.exec_module(fields)
UA='ONESTOP-Government-Job-Update/1.0'; KEYWORDS=('recruitment','vacancy','vacancies','notification','apply online','admit card','result','answer key','application')
DATE_RE=re.compile(r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',re.I)
def save(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def get(url):
    try:
        r=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/xhtml+xml,application/pdf;q=0.8,*/*;q=0.1'}),timeout=20); return r.status,r.read(1500000),r.geturl(),None
    except urllib.error.HTTPError as e: return e.code,b'',url,f'HTTP {e.code}'
    except Exception as e: return None,b'',url,str(e)[:300]
def clean_text(body):
    s=unescape(body.decode('utf-8','replace')); s=re.sub(r'<script[^>]*>.*?</script>|<style[^>]*>.*?</style>','\n',s,flags=re.I|re.S); s=re.sub(r'<(?:br|p|div|li|tr|td|th|h[1-6])[^>]*>', '\n', s, flags=re.I); s=re.sub(r'<[^>]+>',' ',s); return '\n'.join(re.sub(r'[ \t]+',' ',x).strip() for x in s.splitlines() if x.strip())
def flat(text): return re.sub(r'\s+',' ',text).strip()
def title(body):
    m=re.search(r'<title[^>]*>(.*?)</title>',body.decode('utf-8','replace'),re.I|re.S); return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',m.group(1))).strip()[:300] if m else ''
def links(body,base):
    s=body.decode('utf-8','replace'); out=[]
    for href in re.findall(r'href=["\']([^"\']+)["\']',s,re.I):
        u=urljoin(base,href).split('#',1)[0]
        if u.startswith(('http://','https://')): out.append(u)
    return list(dict.fromkeys(out))
def stable_source_match(src_title,official_title,official_text):
    words=set(re.findall(r'[a-z0-9]{4,}',src_title.lower())); target=set(re.findall(r'[a-z0-9]{4,}',(official_title+' '+official_text[:12000]).lower())); return (len(words&target)/len(words)) if words else 0
def main():
    now=datetime.now(timezone.utc).isoformat()
    try: state=json.loads(STATE.read_text(encoding='utf-8'))
    except Exception: state={'status':'source_unavailable','items':{}}
    try: registry=json.loads(REGISTRY.read_text(encoding='utf-8'))
    except Exception: registry={'sources':[]}
    try: canonical=json.loads(CANONICAL.read_text(encoding='utf-8'))
    except Exception: canonical={'schemaVersion':1,'items':{}}
    sources={s['id']:s for s in registry.get('sources',[]) if s.get('enabled')}; results={}; counts={'verified':0,'hold':0,'checked':0,'new':0,'changed':0,'unchanged':0}
    for item_id,item in state.get('items',{}).items():
        counts['checked']+=1; src_url=item.get('url',''); result={'id':item_id,'discoveryUrl':src_url,'status':'hold','publicationStatus':'hold','reason':'missing_official_source','checkedAt':now,'officialSource':None,'checks':{}}
        c,b,final,e=get(src_url)
        if c!=200:
            result['reason']='discovery_source_fetch_failed'; result['error']=e or f'HTTP {c}'; counts['hold']+=1; results[item_id]=result
            continue
        body=clean_text(b); flat_body=flat(body); src_title=item.get('title') or title(b)
        raw={'title':src_title,'text':body,'notificationUrl':src_url,'source':'SarkariResult'}
        extracted=fields.normalize_record(raw)
        result['fields']=extracted
        result['checks']['nonempty_title']=bool(src_title); result['checks']['extractable_notice_content']=len(body)>=200; result['checks']['recruitment_signal']=any(k in flat_body.lower() for k in KEYWORDS); result['checks']['last_date_or_valid_dates']=bool(DATE_RE.search(flat_body))
        candidates=[]
        for u in links(b,final):
            host=urlparse(u).hostname or ''
            for sid,s in sources.items():
                base_host=urlparse(s['url']).hostname or ''
                if host==base_host or host.endswith('.'+base_host): candidates.append((sid,u))
        for sid,u in candidates:
            cc,bb,ff,ee=get(u)
            if cc!=200 or not bb: continue
            ot=title(bb); ob=clean_text(bb); score=stable_source_match(src_title,ot,ob)
            if len(ob)>=200 and (score>=0.25 or sid in src_url.lower()): result['officialSource']={'sourceId':sid,'url':u,'title':ot,'matchScore':round(score,3)}; break
        result['checks']['official_notice_url']=bool(result['officialSource']); result['checks']['trusted_source']=bool(result['officialSource']); result['checks']['safe_http_urls']=bool(result['officialSource'] and result['officialSource']['url'].startswith(('http://','https://')))
        passed=all(result['checks'].values())
        if passed: result['status']='verified'; result['publicationStatus']='ready'; result['reason']='all_required_checks_passed'; counts['verified']+=1
        else: result['reason']='failed_checks:'+','.join(k for k,v in result['checks'].items() if not v); counts['hold']+=1
        incoming=dict(extracted); incoming.update({'jobId':item_id,'notificationUrl':extracted.get('notificationUrl') or src_url,'source':'SarkariResult','verificationStatus':result['status'],'publicationStatus':result['publicationStatus'],'officialSource':result['officialSource'],'lastSeenAt':now})
        old=canonical.get('items',{}).get(item_id); canonical,event_info=engine.upsert(incoming,canonical); counts[event_info['event'].lower()]+=1
        result['canonicalRecordId']=event_info['jobId']; result['changeEvent']=event_info['event']; result['recordVersion']=event_info['recordVersion']; results[item_id]=result
    save(CANONICAL,canonical); save(OUT,{'schemaVersion':1,'checkedAt':now,'sourceStatus':state.get('status'),'counts':counts,'items':results}); save(LOG,{'checkedAt':now,'status':'ok','counts':counts}); return 0
if __name__=='__main__': sys.exit(main())
