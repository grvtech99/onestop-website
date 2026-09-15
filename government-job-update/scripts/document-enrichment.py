import json
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
VERIFY=DATA/'official-verification-state.json'
CAN=DATA/'canonical-job-records.json'
UA='ONESTOP-Government-Job-Update/4.0'
TIMEOUT=12
MAX_PDF=6
MAX_PDF_BYTES=8_000_000
MAX_TEXT=120_000

fields_path=ROOT/'scripts'/'job-field-extractor.py'
from importlib.util import spec_from_file_location, module_from_spec
spec=spec_from_file_location('job_fields',fields_path); fields=module_from_spec(spec); spec.loader.exec_module(fields)

def get(url, accept='text/html,application/pdf,*/*;q=0.1'):
    try:
        req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':accept})
        with urllib.request.urlopen(req,timeout=TIMEOUT) as r:
            return r.status,r.read(MAX_PDF_BYTES+1),r.geturl(),r.headers.get('content-type','')
    except Exception:
        return None,b'',url,''

def html_text(body):
    s=unescape(body.decode('utf-8','replace'))
    s=re.sub(r'<script[^>]*>.*?</script>|<style[^>]*>.*?</style>|<noscript[^>]*>.*?</noscript>',' ',s,flags=re.I|re.S)
    return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',s)).strip()

def page_title(body):
    m=re.search(r'<title[^>]*>(.*?)</title>',body.decode('utf-8','replace'),re.I|re.S)
    return html_text(m.group(1).encode())[:300] if m else ''

def links(body,base):
    out=[]
    for m in re.finditer(r'<a\b[^>]*href=[\'\"]([^\'\"]+)[\'\"][^>]*>(.*?)</a>',body.decode('utf-8','replace'),re.I|re.S):
        u=urllib.parse.urljoin(base,unescape(m.group(1))).split('#',1)[0]
        if not u.startswith(('http://','https://')): continue
        label=re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',m.group(2))).strip()
        if u not in [x[0] for x in out]: out.append((u,label))
    return out

def tokens(s):
    return {x for x in re.findall(r'[a-z0-9]{3,}',(s or '').lower()) if x not in {'the','and','for','online','apply','2026','2025','2024','recruitment','notification','government','govt','posts','post','jobs','job','various'}}

def link_score(title,url,label):
    a=tokens(title); b=tokens(url+' '+label); overlap=len(a&b)
    low=(url+' '+label).lower()
    specific=sum(k in low for k in ('recruit','career','vacan','notice','notification','advert','apply','admit','result','exam','schedule','circular','pdf'))
    generic=sum(k in low for k in ('home','index','contact','about','login','careers.html'))
    return overlap*4+specific-generic*3

def is_pdf(url,ctype=''):
    return 'pdf' in (ctype or '').lower() or url.lower().split('?',1)[0].endswith('.pdf')

def extract_pdf_text(body):
    if len(body)>MAX_PDF_BYTES:return ''
    with tempfile.NamedTemporaryFile(suffix='.pdf',delete=True) as f:
        f.write(body); f.flush()
        try:
            p=subprocess.run(['pdftotext','-layout',f.name,'-'],capture_output=True,text=True,timeout=20)
            if p.returncode==0:return re.sub(r'\s+',' ',p.stdout).strip()[:MAX_TEXT]
        except Exception: pass
    return ''

def good_value(v):
    if v in (None,'',[]): return False
    s=str(v).strip()
    if len(s)<2:return False
    bad=('free tools for government job application','sarkari result','join our telegram','share on whatsapp','advertisement download mobile app','official website click here')
    return not any(x in s.lower() for x in bad)

def extract(title,text):
    r=fields.normalize_record({'title':title,'text':text,'source':'Official Document','category':fields.classify_update_type(title,text)})
    return {k:v for k,v in r.items() if good_value(v)}

def main():
    if not VERIFY.exists():return 0
    verification=json.loads(VERIFY.read_text(encoding='utf-8'))
    canonical=json.loads(CAN.read_text(encoding='utf-8')) if CAN.exists() else {'items':{}}
    updated=0; docs_total=0
    for item_id,item in verification.get('items',{}).items():
        if item.get('status')!='verified' or item.get('publicationStatus')!='ready':continue
        official=item.get('officialSource') or {}; official_url=official.get('url',''); title=(item.get('fields') or {}).get('title') or ''
        if not official_url:continue
        status,body,resolved,ctype=get(official_url)
        if status!=200 or not body:continue
        doc_candidates=[]
        if is_pdf(resolved,ctype): doc_candidates=[(resolved,'Official Notification PDF')]
        else:
            for u,label in links(body,resolved):
                low=(u+' '+label).lower()
                if '.pdf' in low or any(k in low for k in ('notification','advertisement','recruit','vacancy','admit','result','answer','exam','schedule','circular')):
                    doc_candidates.append((u,label))
        doc_candidates=sorted(dict(doc_candidates).items(),key=lambda x:link_score(title,x[0],x[1]),reverse=True)[:MAX_PDF]
        # Prefer a specific official document over a generic careers/home page.
        if not is_pdf(resolved,ctype) and doc_candidates:
            best_url,best_label=doc_candidates[0]
            if link_score(title,best_url,best_label)>link_score(title,resolved,page_title(body)):
                ps,pb,pr,pc=get(best_url)
                if ps==200 and pb:
                    official_url=pr; official={'sourceId':'official-government-domain','url':pr,'title':best_label or page_title(pb),'matchScore':max(official.get('matchScore',0),0.35),'titleOverlap':official.get('titleOverlap',0),'sourceType':'official_notification_or_recruitment_document'}
                    item['officialSource']=official
                    body=pb; resolved=pr; ctype=pc
        texts=[]; documents=[]
        if is_pdf(resolved,ctype):
            txt=extract_pdf_text(body)
            if txt:texts.append(txt); documents.append({'url':resolved,'title':official.get('title') or 'Official Notification PDF','type':'pdf','extracted':True})
        else:
            page_txt=html_text(body)
            if page_txt:texts.append(page_txt)
            documents.append({'url':resolved,'title':official.get('title') or page_title(body),'type':'html','extracted':True})
            for u,label in doc_candidates[:MAX_PDF]:
                ps,pb,pr,pc=get(u,accept='application/pdf,text/html,*/*;q=0.1')
                if ps!=200 or not pb:continue
                txt=extract_pdf_text(pb) if is_pdf(pr,pc) else html_text(pb)
                if txt:
                    texts.append(txt); documents.append({'url':pr,'title':label or 'Official document','type':'pdf' if is_pdf(pr,pc) else 'html','extracted':True})
        if not texts:continue
        combined='\n'.join(texts)[:MAX_TEXT]
        rich=extract(title,combined)
        f=item.setdefault('fields',{})
        # Official-document extraction is higher priority than aggregator/source-page text.
        for key,value in rich.items():
            if key in {'title','source','category','updateType'}:continue
            if good_value(value):f[key]=value
        f['documentText']=combined
        f['documentSources']=documents
        f['documentCount']=len(documents)
        f['documentExtractedAt']=datetime.now(timezone.utc).isoformat()
        item['officialSource']=official
        cid=item.get('canonicalRecordId') or item_id
        if cid in canonical.get('items',{}):
            c=canonical['items'][cid]
            for key,value in f.items():
                if value not in (None,'',[]):c[key]=value
            c['officialSource']=official
            c['documentSources']=documents
            c['documentCount']=len(documents)
            c['documentExtractedAt']=f['documentExtractedAt']
            c['updatedAt']=f['documentExtractedAt']
        updated+=1; docs_total+=len(documents)
    VERIFY.write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if CAN.exists():CAN.write_text(json.dumps(canonical,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','recordsEnriched':updated,'documentsExtracted':docs_total},indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
