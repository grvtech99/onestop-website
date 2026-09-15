import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VERIFICATION=ROOT/'data'/'official-verification-state.json'
CANONICAL=ROOT/'data'/'canonical-job-records.json'
OUT=ROOT/'data'/'publication-queue.json'
REQUIRED_FIELDS=('title','notificationUrl','source','verificationStatus','publicationStatus')

def main():
 verification=json.loads(VERIFICATION.read_text(encoding='utf-8'))
 try:canonical=json.loads(CANONICAL.read_text(encoding='utf-8'))
 except Exception:canonical={'items':{}}
 queue=[]; blocked=0; category_counts={}
 for item_id,item in verification.get('items',{}).items():
  if item.get('status')!='verified' or item.get('publicationStatus')!='ready':blocked+=1; continue
  cid=item.get('canonicalRecordId') or item_id; record=canonical.get('items',{}).get(cid,{})
  merged=dict(record); merged.update({k:v for k,v in item.get('fields',{}).items() if v not in (None,'',[],{})})
  merged.update({'jobId':cid,'source':record.get('source') or item.get('fields',{}).get('source') or 'MultiSource','verificationStatus':'verified','publicationStatus':'ready','officialSource':item.get('officialSource') or record.get('officialSource'),'category':item.get('fields',{}).get('category') or record.get('category') or 'jobs','updateType':item.get('fields',{}).get('updateType') or record.get('updateType') or item.get('fields',{}).get('category') or 'jobs'})
  if any(merged.get(k) in (None,'') for k in REQUIRED_FIELDS):blocked+=1; continue
  queue.append(merged); c=merged.get('category','jobs'); category_counts[c]=category_counts.get(c,0)+1
 result={'schemaVersion':3,'generatedAt':verification.get('checkedAt'),'policy':'verified-only','readyCount':len(queue),'blockedCount':blocked,'categoryCounts':category_counts,'items':queue}
 OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps({'status':'PASS','readyCount':len(queue),'blockedCount':blocked,'categoryCounts':category_counts},indent=2)); return 0
if __name__=='__main__':sys.exit(main())
