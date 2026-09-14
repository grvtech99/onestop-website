import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFICATION = ROOT / 'data' / 'official-verification-state.json'
CANONICAL = ROOT / 'data' / 'canonical-job-records.json'
OUT = ROOT / 'data' / 'publication-queue.json'

REQUIRED_FIELDS = ('title', 'notificationUrl', 'source', 'verificationStatus', 'publicationStatus')

def main():
    verification = json.loads(VERIFICATION.read_text(encoding='utf-8'))
    try:
        canonical = json.loads(CANONICAL.read_text(encoding='utf-8'))
    except Exception:
        canonical = {'items': {}}
    queue = []
    blocked = 0
    for item_id, item in verification.get('items', {}).items():
        if item.get('status') != 'verified' or item.get('publicationStatus') != 'ready':
            blocked += 1
            continue
        cid = item.get('canonicalRecordId') or item_id
        record = canonical.get('items', {}).get(cid, {})
        merged = dict(record)
        merged.update({k: v for k, v in item.get('fields', {}).items() if v not in (None, '', [], {})})
        merged.update({
            'jobId': cid,
            'source': record.get('source') or 'SarkariResult',
            'verificationStatus': 'verified',
            'publicationStatus': 'ready',
            'officialSource': item.get('officialSource') or record.get('officialSource'),
        })
        if any(merged.get(k) in (None, '') for k in REQUIRED_FIELDS):
            blocked += 1
            continue
        queue.append(merged)
    result = {
        'schemaVersion': 2,
        'generatedAt': verification.get('checkedAt'),
        'policy': 'verified-only',
        'readyCount': len(queue),
        'blockedCount': blocked,
        'items': queue,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'readyCount': len(queue), 'blockedCount': blocked}, indent=2))
    return 0

if __name__ == '__main__':
    sys.exit(main())
