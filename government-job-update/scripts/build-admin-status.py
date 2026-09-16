#!/usr/bin/env python3
"""Build one public, read-only status document for the Government Job Update dashboard."""
from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'data'
TEST = BASE / 'test-results'
OUT = DATA / 'admin-dashboard-state.json'

def read(name, default):
    p = DATA / name
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return default

def read_test(name):
    p = TEST / name
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return {}

def parse_dt(value):
    if not value: return None
    try: return datetime.fromisoformat(value.replace('Z','+00:00'))
    except Exception: return None

def iso(dt): return dt.astimezone(timezone.utc).isoformat() if dt else None

monitor = read('sarkariresult-monitor-state.json', {})
verify = read('official-verification-state.json', {})
canonical = read('canonical-job-records.json', {'items': {}})
queue = read('publication-queue.json', {'items': []})
history = read('publication-history.json', {'items': []})
monitor_log = read('sarkariresult-monitor-log.json', {})
verify_log = read('official-verification-log.json', {})
e2e = read_test('e2e-live-report.json')
gate = read_test('publication-gate-test-report.json')

now = datetime.now(timezone.utc)
checked = parse_dt(monitor.get('lastCheckedAt'))
next_run = None
if checked:
    base = checked.replace(second=0, microsecond=0)
    for _ in range(12):
        base += timedelta(minutes=1)
        if base.minute % 10 == 3:
            next_run = base
            break

items = canonical.get('items') or {}
verified_items = [x for x in items.values() if x.get('verificationStatus') == 'verified' and x.get('publicationStatus') == 'ready']
held_items = [x for x in items.values() if x.get('publicationStatus') == 'hold' or x.get('verificationStatus') in ('hold','pending_official_source')]
source_status = monitor.get('status', 'unknown')
http_error = monitor.get('lastError') or ''
source_results = monitor.get('sources') or monitor_log.get('sources') or {}
active_source_names = [v.get('name') for v in source_results.values() if isinstance(v, dict) and v.get('status') == 'ok' and v.get('name')]
queue_items = queue.get('items') or []
history_items = history.get('items') or []
reused_active = int(queue.get('reusedActiveCount') or 0)
base_recovery_state = 'RECOVERY_WATCH' if source_status == 'source_unavailable' else 'HEALTHY'
recovery_state = f'{base_recovery_state} • BUFFER RETAINED {reused_active} • HISTORY {len(history_items)}'
recovery = {
    'state': recovery_state,
    'safeRetryEnabled': True,
    'bypassAttempted': False,
    'lastHttpError': http_error,
    'activeRetentionEnabled': True,
    'activeRetainedCount': reused_active,
    'publicationHistoryCount': len(history_items),
    'recoveryRule': 'Resume multi-source discovery automatically on the next scheduled run when monitored public sources become available; never bypass 403/429, CAPTCHA, access controls, or rate limits.',
    'publicationRetentionRule': 'Previously published verified records remain in the public queue while their application deadline is still active when a source temporarily rotates or omits the listing.'
}

def test_status(report):
    if not report: return 'NOT_AVAILABLE'
    if report.get('passed') is True: return 'PASS'
    if report.get('status') in ('pass','passed','ok'): return 'PASS'
    if report.get('passed') is False: return 'FAIL'
    return 'CHECK'

publication_gate_state = f"READY • BUFFER RETAINED {reused_active}"
out = {
    'schemaVersion': 4,
    'generatedAt': now.isoformat(),
    'schedule': {'cronUtc': '3/10 * * * *', 'description': 'Every 10 minutes at minutes 03, 13, 23, 33, 43 and 53 UTC (~:33, :43, :53, :03, :13 and :23 IST). GitHub Actions schedules may be delayed.'},
    'production': {
        'source': 'Multi-Source Government Jobs', 'sourceUrl': None, 'status': source_status,
        'lastCheckedAt': monitor.get('lastCheckedAt'), 'lastSuccessfulDiscoveryAt': monitor.get('lastSuccessfulDiscoveryAt'),
        'lastError': http_error, 'discoveredCount': len(monitor.get('items') or {}),
        'newCount': monitor_log.get('new', verify.get('counts', {}).get('new', 0)),
        'changedCount': monitor_log.get('changed', verify.get('counts', {}).get('changed', 0)),
    },
    'recovery': recovery,
    'pipeline': {
        'extraction': 'READY', 'officialVerification': 'READY' if source_status != 'source_unavailable' else 'WAITING_FOR_DISCOVERY',
        'canonical': 'READY', 'publicationGate': publication_gate_state, 'websiteFeed': 'READY',
        'verifiedCount': len(verified_items), 'holdCount': len(held_items), 'publishedCount': len(queue_items),
        'canonicalCount': len(items), 'publicationReadyCount': queue.get('readyCount', len(queue_items)),
        'publicationBlockedCount': queue.get('blockedCount', 0), 'reusedActiveCount': reused_active,
        'publicationHistoryCount': len(history_items),
    },
    'bufferFlow': {
        'status': 'ACTIVE' if queue_items else 'EMPTY',
        'readyCount': queue.get('readyCount', len(queue_items)),
        'retainedActiveCount': reused_active,
        'historyCount': len(history_items),
        'blockedCount': queue.get('blockedCount', 0),
        'policy': queue.get('policy', 'verified-only-plus-durable-active-retention'),
    },
    'tests': {'controlledE2E': test_status(e2e), 'publicationGateRegression': test_status(gate), 'controlledE2EIsProductionDiscovery': False},
    'timing': {'lastRunAt': verify.get('checkedAt') or monitor.get('lastCheckedAt'), 'nextExpectedRunAt': iso(next_run)},
    'recent': {'discovery': monitor_log, 'verification': verify_log},
    'policy': {
        'discoverySource': '20 alternate sources + FreeJobAlert', 'discoverySourceCount': len(source_results) or 21,
        'activeDiscoverySources': active_source_names, 'finalAuthority': 'Official government/recruitment authority',
        'publication': 'verified-only', 'heldRecordsArePublished': False, 'freeJobAlertUsed': 'freejobalert' in source_results,
        'durablePublicationHistory': True,
    },
}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'Wrote {OUT}')
