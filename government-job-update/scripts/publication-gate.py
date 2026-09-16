import json, re, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
VERIFICATION=DATA/'official-verification-state.json'
CANONICAL=DATA/'canonical-job-records.json'
MONITOR=DATA/'sarkariresult-monitor-state.json'
OUT=DATA/'publication-queue.json'
HISTORY=DATA/'publication-history.json'
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

def item_key(item):
    return str(item.get('jobId') or item.get('id') or item.get('notificationUrl') or '').strip()

def main():
    verification=json.loads(VERIFICATION.read_text(encoding='utf-8'))
    try:canonical=json.loads(CANONICAL.read_text(encoding='utf-8'))
    except Exception:canonical={'items':{}}
    try:monitor=json.loads(MONITOR.read_text(encoding='utf-8')).get('items',{})
    except Exception:monitor={}
    try:previous=json.loads(OUT.read_text(encoding='utf-8'))
    except Exception:previous={'items':[]}
    try:history=json.loads(HISTORY.read_text(encoding='utf-8'))
    except Exception:history={'items':[]}

    # The history is the durable publication memory. It prevents a source rotating
    # an older vacancy off its listing from deleting that vacancy from our public feed.
    history_items=history.get('items',[]) if isinstance(history.get('items',[]),list) else []
    previous_items=previous.get('items',[]) if isinstance(previous.get('items',[]),list) else []
    memory=[]; memory_ids=set()
    for old in history_items + previous_items:
        oid=item_key(old)
        if oid and oid not in memory_ids:
            memory.append(dict(old)); memory_ids.add(oid)

    by_url={str(v.get('url','')):v for v in monitor.values() if v.get('url')}
    queue=[]; queue_ids=set(); blocked=0; reused=0; category_counts={}
    current_ids=set()
    verification_items=verification.get('items',{})
    for item_id,item in verification_items.items():
        if item.get('status')!='verified' or item.get('publicationStatus')!='ready':
            blocked+=1; continue
        cid=item.get('canonicalRecordId') or item_id
        current_ids.add(str(cid))
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

    # Retain every previously published, still-active vacancy unless the current
    # verification explicitly knows the record and has moved it out of ready state.
    # This handles source-list rotation and temporary discovery gaps across runs.
    for old in memory:
        oid=item_key(old)
        if not oid or oid in queue_ids or not deadline_active(old): continue
        if old.get('verificationStatus')!='verified' or old.get('publicationStatus')!='ready': continue
        if oid in current_ids: continue
        old=dict(old)
        old['retainedWhileDeadlineActive']=True
        old['retentionReason']='previously_published_source_listing_rotated_or_temporarily_missing_but_official_application_deadline_not_passed'
        queue.append(old); queue_ids.add(oid); reused+=1
        c=old.get('category','jobs'); category_counts[c]=category_counts.get(c,0)+1

    # Update durable history with everything currently public. Expired records remain
    # in history for audit, but are never re-published by the active-retention rule.
    history_by_id={}
    for old in memory: history_by_id[item_key(old)]=old
    for current in queue: history_by_id[item_key(current)]=current
    HISTORY.write_text(json.dumps({'schemaVersion':1,'updatedAt':datetime.now(timezone.utc).isoformat(),'items':list(history_by_id.values())},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    result={'schemaVersion':6,'generatedAt':verification.get('checkedAt'),'policy':'verified-only-plus-durable-active-retention','readyCount':len(queue),'blockedCount':blocked,'reusedActiveCount':reused,'categoryCounts':category_counts,'items':queue}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','readyCount':len(queue),'blockedCount':blocked,'reusedActiveCount':reused,'historyCount':len(history_by_id),'categoryCounts':category_counts},indent=2))
    return 0
if __name__=='__main__':sys.exit(main())
