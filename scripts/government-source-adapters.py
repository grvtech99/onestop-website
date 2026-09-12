#!/usr/bin/env python3
"""High-value source adapters for ONESTOP notice discovery.

Adapters only improve discovery metadata. They never verify or publish a notice.
"""
from __future__ import annotations
import re
from urllib.parse import urljoin

KEYWORDS={
 'ssc': re.compile(r'(notice|recruit|vacanc|admit|result|answer|calendar|exam)',re.I),
 'upsc': re.compile(r'(recruit|vacanc|examination|admit|result|answer|calendar|notice)',re.I),
 'employment_news': re.compile(r'(job|recruit|vacanc|employment|advertisement|notification)',re.I),
}

def classify(source_id:str,url:str,label:str='')->str:
    rx=KEYWORDS.get(source_id,re.compile(r'(recruit|vacanc|job|notice|notification|admit|result|answer|scholarship|admission)',re.I))
    return 'high' if rx.search(url) or rx.search(label) else 'low'

def discover(source_id:str,base_url:str,html:str):
    """Return [{url,priority,sourceId}] from an official HTML page."""
    results=[]
    for m in re.finditer(r'href\\s*=\\s*["\\\']([^"\\\']+)',html,re.I):
        raw=m.group(1).strip()
        url=urljoin(base_url,raw)
        priority=classify(source_id,url,raw)
        if priority=='high' and url.startswith(('http://','https://')):
            results.append({'url':url,'priority':priority,'sourceId':source_id})
    seen=set(); out=[]
    for x in results:
        if x['url'] not in seen:
            seen.add(x['url']); out.append(x)
    return out
