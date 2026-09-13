#!/usr/bin/env python3
"""Extract readable text from an official HTML/PDF notice URL.

Intermediate extraction only: this script never verifies or publishes a notice.
"""
from __future__ import annotations
import argparse, hashlib, html, re, shutil, subprocess, tempfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

TIMEOUT=30
MAX_BYTES=8*1024*1024
UA="ONESTOP-Government-Notice-Bot/1.0"


def fetch(url):
    req=Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/pdf;q=0.9,*/*;q=0.8"})
    with urlopen(req,timeout=TIMEOUT) as r:
        data=r.read(MAX_BYTES+1)
        return data,r.headers.get_content_type(),r.geturl()


def clean_html(data):
    text=data.decode('utf-8','ignore')
    text=re.sub(r'(?is)<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>|<template.*?</template>',' ',text)
    text=re.sub(r'(?is)<!--.*?-->',' ',text)
    text=re.sub(r'(?s)<[^>]+>',' ',text)
    text=html.unescape(text).replace('\xa0',' ')
    return re.sub(r'\s+',' ',text).strip()


def pdf_text(data,url):
    if not shutil.which('pdftotext'):
        return '[PDF NOT LOCALLY EXTRACTED — VERIFY FROM OFFICIAL NOTICE]\n'+url,'unprocessed'
    with tempfile.TemporaryDirectory() as td:
        src=Path(td)/'notice.pdf'; dst=Path(td)/'notice.txt'
        src.write_bytes(data)
        p=subprocess.run(['pdftotext','-layout','-enc','UTF-8',str(src),str(dst)],capture_output=True,text=True,timeout=30)
        if p.returncode!=0:
            return '[PDF EXTRACTION FAILED — VERIFY FROM OFFICIAL NOTICE]\n'+url,'failed'
        text=dst.read_text(errors='ignore').strip()
        if not text:
            return '[PDF CONTAINS NO EXTRACTABLE TEXT — POSSIBLY SCANNED; VERIFY FROM OFFICIAL NOTICE]\n'+url,'scanned-or-empty'
        return text,'extracted'


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('url'); ap.add_argument('--out',required=True); args=ap.parse_args()
    data,ctype,final_url=fetch(args.url)
    if len(data)>MAX_BYTES: raise RuntimeError('notice exceeds safety size limit')
    digest=hashlib.sha256(data).hexdigest(); parsed=urlparse(final_url)
    is_pdf=ctype=='application/pdf' or parsed.path.lower().endswith('.pdf')
    status='extracted'
    if is_pdf: text,status=pdf_text(data,final_url)
    else:
        text=clean_html(data)
        if not text: status='empty-html'
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(text+'\n',encoding='utf-8')
    print(f'content_sha256={digest} content_type={ctype} chars={len(text)} extraction_status={status} final_url={final_url} out={out}')

if __name__=='__main__': main()
