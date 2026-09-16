#!/usr/bin/env python3
"""Build the read-only admin dashboard snapshot for the Government Job Update pipeline."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'data'
TEST = BASE / 'test-results'
OUT = DATA / 'admin-dashboard-state.json'
def read(name, default):
    try: return json.loads((DATA / name).read_text(encoding='utf-8'))
    except Exception: return default
def read_test(name):
    try: return json.loads((TEST / name).read_text(encoding='utf-8'))
    except Exception: return {}
monitor=read('sarkariresult-monitor-state.json',{})
monitor_log=read('sarkariresult-monitor-log.json',{})
canonical=read('canonical-job-records.json',{'items':{}})
queue=read('publication-queue.json',{'items':[]})
history=read('publication-history.json',{'items':[]})
buffer=read('discovery-buffer.json',{'items':{}})
execution=read('admin-execution-status.json',{'steps':{}})
e2e=read_test('e2e-live-report.json')
gate=read_test('publication-gate-test-report.json')
step_labels={'discovery':'Multi-source discovery','buffer':'Discovery buffer','officialVerification':'Official-source verification','verificationRecovery':'Official-link recovery','enrichment':'Notification enrichment','controlledE2E':'Controlled E2E','publicationRegression':'Publication regression','publicationQueue':'Publication queue/history','executionStatus':'Execution telemetry','adminSnapshot':'Admin snapshot','stateSave':'State commit'}
steps=[{'id':k,'label':v,'status':execution.get('steps',{}).get(k,'NOT_REPORTED')} for k,v in step_labels.items()]
failed=[s for s in steps if s['status'] in ('FAILURE','CANCELLED','TIMED_OUT')]
current=next((s for s in steps if s['status'] in ('IN_PROGRESS','QUEUED')),None)
problem=failed[0] if failed else None
pipeline_status='PROBLEM' if problem else ('RUNNING' if current else 'READY')
items=canonical.get('items') or {}
verified_count=sum(1 for x in items.values() if x.get('verificationStatus')=='verified' and x.get('publicationStatus')=='ready')
hold_count=sum(1 for x in items.values() if x.get('publicationStatus')=='hold' or x.get('verificationStatus') in ('hold','pending_official_source'))
queue_items=queue.get('items') or []
history_items=history.get('items') or []
buffer_items=buffer.get('items') or {}
out={'schemaVersion':5,'generatedAt':datetime.now(timezone.utc).isoformat(),'pipelineStatus':pipeline_status,'problemStep':problem,'currentStep':current,'workflow':{'name':execution.get('workflow') or 'Government Job Update — Multi-Source Discovery','runId':execution.get('runId'),'runNumber':execution.get('runNumber'),'runAttempt':execution.get('runAttempt'),'commitSha':execution.get('commitSha'),'runUrl':execution.get('runUrl'),'overall':execution.get('overall'),'failedSteps':execution.get('failedSteps',[]),'blockedSteps':execution.get('blockedSteps',[])},'steps':steps,'production':{'source':'Multi-Source Government Jobs','status':monitor.get('status','unknown'),'lastCheckedAt':monitor.get('lastCheckedAt'),'lastSuccessfulDiscoveryAt':monitor.get('lastSuccessfulDiscoveryAt'),'lastError':monitor.get('lastError'),'discoveredCount':len(monitor.get('items') or {}),'newCount':monitor_log.get('new',0),'changedCount':monitor_log.get('changed',0)},'bufferFlow':{'status':'ACTIVE' if buffer_items else 'EMPTY','bufferedCount':len(buffer_items),'bufferedAt':buffer.get('bufferedAt'),'sourceCheckedAt':buffer.get('sourceCheckedAt'),'sourceStatus':buffer.get('sourceStatus'),'intermediatePush':False},'publication':{'readyCount':queue.get('readyCount',len(queue_items)),'blockedCount':queue.get('blockedCount',0),'reusedActiveCount':queue.get('reusedActiveCount',0),'historyCount':len(history_items),'policy':queue.get('policy','verified-only-plus-durable-active-retention')},'pipelineCounts':{'canonicalCount':len(items),'verifiedReadyCount':verified_count,'holdCount':hold_count,'publishedQueueCount':len(queue_items)},'tests':{'controlledE2E':'PASS' if e2e.get('passed') is True or e2e.get('status') in ('pass','passed','ok') else ('FAIL' if e2e.get('passed') is False else 'NOT_AVAILABLE'),'publicationGateRegression':'PASS' if gate.get('passed') is True or gate.get('status') in ('pass','passed','ok') else ('FAIL' if gate.get('passed') is False else 'NOT_AVAILABLE')},'diagnostics':{'rootCauseControls':['Verification workset is bounded and prioritizes non-verified/recent discoveries.','Recovery workset is bounded and prioritizes deferred/recent records.','No intermediate git push is performed by the buffer step.','Workflow runs are serialized with queue:max so pending scheduled runs are not silently replaced.','Admin reads the persisted snapshot and live GitHub Actions telemetry.'],'finalAuthority':'Official government/recruitment source','heldRecordsArePublished':False}}
OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'PASS','pipelineStatus':pipeline_status,'problemStep':problem,'readyCount':queue.get('readyCount',len(queue_items)),'bufferedCount':len(buffer_items),'historyCount':len(history_items)},indent=2))
