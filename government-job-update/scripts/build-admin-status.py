#!/usr/bin/env python3
"""Build one public, read-only status document for the Government Job Update dashboard."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'data'
TEST = BASE / 'test-results'
OUT = DATA / 'admin-dashboard-state.json'

def read(name, default):
    p = DATA / name
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return default

def read_test(name):
    p = TEST / name
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return {}

def parse_dt(value):
    if not value: return None
    try: return datetime.fromisoformat(value.replace('Z','+00:00'))
    except Exception: return None

def iso(dt): return dt.astimezone(timezone.utc).isoformat() if dt else None

monitor = read('sarkariresult-monitor-state.json', {})
verify = read('official-verification-state.json', {})
canonical = read('canonical-job-records.json', {'items': {}})
queue = read('publication-queue.json', {'items': []})
monitor_log = read('sarkariresult-monitor-log.json', {})
verify_log = read('official-verification-log.json', {})
e2e = read_test('e2e-live-report.json')
gate = read_test('publication-gate-test-report.json')

now = datetime.now(timezone.utc)
checked = parse_dt(monitor.get('lastCheckedAt'))
next_run = None
if checked:
    # Scheduled at minute 47 of every UTC hour; calculate the next occurrence after last check.
    candidate = checked.replace(minute=47, second=0, microsecond=0)
    if candidate <= now:
        from datetime import timedelta
        candidate += timedelta(hours=1)
    next_run = candidate

items = canonical.get('items') or {}
verified_items = [x for x in items.values() if x.get('verificationStatus') == 'verified' and x.get('publicationStatus') == 'ready']
held_items = [x for x in items.values() if x.get('publicationStatus') == 'hold' or x.get('verificationStatus') in ('hold','pending_official_source')]

source_status = monitor.get('status', 'unknown')
http_error = monitor.get('lastError') or ''
recovery = {
    'state': 'RECOVERY_WATCH' if source_status == 'source_unavailable' else 'HEALTHY',
    'safeRetryEnabled': True,
    'bypassAttempted': False,
    'lastHttpError': http_error,
    'recoveryRule': 'Resume normal discovery automatically when the public SarkariResult endpoint returns a successful response; never bypass 403/429, CAPTCHA, access controls, or rate limits.'
}

def test_status(report):
    if not report: return 'NOT_AVAILABLE'
    if report.get('passed') is True: return 'PASS'
    if report.get('status') in ('pass','passed','ok'): return 'PASS'
    if report.get('passed') is False: return 'FAIL'
    return 'CHECK'

out = {
    'schemaVersion': 1,
    'generatedAt': now.isoformat(),
    'schedule': {'cronUtc': '47 * * * *', 'description': 'Every hour at minute 47 UTC (~:17 IST). GitHub Actions schedules may be delayed.'},
    'production': {
        'source': 'SarkariResult',
        'sourceUrl': monitor.get('sourceUrl', 'https://www.sarkariresult.com/'),
        'status': source_status,
        'lastCheckedAt': monitor.get('lastCheckedAt'),
        'lastSuccessfulDiscoveryAt': monitor.get('lastSuccessfulDiscoveryAt'),
        'lastError': http_error,
        'discoveredCount': len(monitor.get('items') or {}),
        'newCount': monitor_log.get('new', verify.get('counts', {}).get('new', 0)),
        'changedCount': monitor_log.get('changed', verify.get('counts', {}).get('changed', 0)),
    },
    'recovery': recovery,
    'pipeline': {
        'extraction': 'READY',
        'officialVerification': 'READY' if source_status != 'source_unavailable' else 'WAITING_FOR_DISCOVERY',
        'canonical': 'READY',
        'publicationGate': 'READY',
        'websiteFeed': 'READY',
        'verifiedCount': len(verified_items),
        'holdCount': len(held_items),
        'publishedCount': len(queue.get('items') or []),
        'canonicalCount': len(items),
        'publicationReadyCount': queue.get('readyCount', len(queue.get('items') or [])),
        'publicationBlockedCount': queue.get('blockedCount', 0),
    },
    'tests': {'controlledE2E': test_status(e2e), 'publicationGateRegression': test_status(gate), 'controlledE2EIsProductionDiscovery': False},
    'timing': {'lastRunAt': verify.get('checkedAt') or monitor.get('lastCheckedAt'), 'nextExpectedRunAt': iso(next_run)},
    'recent': {'discovery': monitor_log, 'verification': verify_log},
    'policy': {'discoverySource': 'SarkariResult only', 'finalAuthority': 'Official government/recruitment authority', 'publication': 'verified-only', 'heldRecordsArePublished': False, 'freeJobAlertUsed': False},
}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'Wrote {OUT}')
