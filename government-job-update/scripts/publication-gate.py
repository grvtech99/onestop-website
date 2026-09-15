import json, re, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
VERIFICATION=DATA/'official-verification-state.json'
CANONICAL=DATA/'canonical-job-records.json'
MONITOR=DATA/'sarkariresult-monitor-state.json'
OUT=DATA/'publication-queue.json'
REQUIRED_FIELDS=('title','notificationUrl','source','verificationStatus','publicationStatus')

def parse_date(value):
    s=str(value or '').strip()
    for p in (r'\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b',r'\b(20\d{2})[/-](\d{1,2})[/-](\d{1,2})\b'):
        m=re.search(p,s)
        if not m: continue
        try:
            if len(m.group(1))==4:return datetime(int(m.group(1)),int(m.group(2)),int(m.group(3))).date()
            return datetime(int(m.group(3)),int(m.group(2)),int(m.group(1))).date()
        except ValueError:pass
    months={m:i for i,m in enumerate(('jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'),1)}
    m=re.search(r'\b(\d{1,2})\s+([A-Za-z]{3,9})\s+(20\d{2})\b',s)
    if m:
        try:return datetime(int(m.group(3)),months[m.group(2)[:3].lower()],int(m.group(1))).date()
        except (ValueError,KeyError):pass
    return None

def deadline_active(item):
    last=item.get('applicationLastDate') or item.get('lastDate') or item.get('application_last_date')
    d=parse_date(last)
    return bool(d and d>=datetime.now(timezone.utc).date())

def main():
    verification=json.loads(VERIFICATION.read_text(encoding='utf-8'))
    try:canonical=json.loads(CANONICAL.read_text(encoding='utf-8'))
    except Exception:canonical={'items':{}}
    try:monitor=json.loads(MONITOR.read_text(encoding='utf-8')).get('items',{})
    except Exception:monitor={}
    try:previous=json.loads(OUT.read_text(encoding='utf-8'))
    except Exception:previous={'items':[]}
    by_url={str(v.get('url','')):v for v in monitor.values() if v.get('url')}
    queue=[]; queue_ids=set(); blocked=0; reused=0; category_counts={}
    for item_id,item in verification.get('items',{}).items():
        if item.get('status')!='verified' or item.get('publicationStatus')!='ready':
            blocked+=1; continue
        cid=item.get('canonicalRecordId') or item_id
        record=canonical.get('items',{}).get(cid,{})
        merged=dict(record)
        merged.update({k:v for k,v in item.get('fields',{}).items() if v not in (None,'',[],{})})
        m=by_url.get(item.get('discoveryUrl',''),{})
        for key in ('discoveredAt','lastSeenAt','lastDiscoveredAt','publishedAt'):
            if m.get(key) and not merged.get(key):merged[key]=m[key]
        merged.update({'jobId':cid,'source':record.get('source') or item.get('fields',{}).get('source') or 'MultiSource','verificationStatus':'verified','publicationStatus':'ready','officialSource':item.get('officialSource') or record.get('officialSource'),'category':item.get('fields',{}).get('category') or record.get('category') or 'jobs','updateType':item.get('fields',{}).get('updateType') or record.get('updateType') or item.get('fields',{}).get('category') or 'jobs'})
        if any(merged.get(k) in (None,'') for k in REQUIRED_FIELDS):
            blocked+=1; continue
        queue.append(merged); queue_ids.add(cid)
        c=merged.get('category','jobs'); category_counts[c]=category_counts.get(c,0)+1

    # Keep an already-published vacancy visible when its source site rotates it out,
    # provided its official application deadline has not passed yet.
    for old in previous.get('items',[]) if isinstance(previous.get('items',[]),list) else []:
        oid=old.get('jobId') or old.get('id') or old.get('notificationUrl')
        if not oid or oid in queue_ids or not deadline_active(old): continue
        if old.get('verificationStatus')!='verified' or old.get('publicationStatus')!='ready': continue
        old=dict(old)
        old['retainedWhileDeadlineActive']=True
        old['retentionReason']='discovery_source_listing_rotated_but_official_application_deadline_not_passed'
        queue.append(old); queue_ids.add(oid); reused+=1
        c=old.get('category','jobs'); category_counts[c]=category_counts.get(c,0)+1

    result={'schemaVersion':5,'generatedAt':verification.get('checkedAt'),'policy':'verified-only-plus-active-retention','readyCount':len(queue),'blockedCount':blocked,'reusedActiveCount':reused,'categoryCounts':category_counts,'items':queue}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','readyCount':len(queue),'blockedCount':blocked,'reusedActiveCount':reused,'categoryCounts':category_counts},indent=2))
    return 0
if __name__=='__main__':sys.exit(main())
