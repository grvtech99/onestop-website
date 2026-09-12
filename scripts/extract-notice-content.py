#!/usr/bin/env python3
"""Extract readable text from a discovered HTML/PDF notice URL.

Writes local intermediate text only. It does not verify or publish notices.
PDF extraction uses pdftotext when available; otherwise the URL is recorded as
unprocessed so a human can inspect it.
"""
from __future__ import annotations
import argparse, hashlib, html, re, shutil, subprocess, tempfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

TIMEOUT=30
MAX_BYTES=8*1024*1024

def fetch(url):
    req=Request(url,headers={"User-Agent":"ONESTOP-Government-Notice-Bot/1.0"})
    with urlopen(req,timeout=TIMEOUT) as r:
        return r.read(MAX_BYTES+1), r.headers.get_content_type()

def clean_html(data):
    text=data.decode('utf-8','ignore')
    text=re.sub(r'(?is)<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>',' ',text)
    text=re.sub(r'(?s)<[^>]+>',' ',text)
    return re.sub(r'\s+',' ',html.unescape(text)).strip()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('url')
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    data,ctype=fetch(args.url)
    if len(data)>MAX_BYTES: raise RuntimeError('notice exceeds safety size limit')
    digest=hashlib.sha256(data).hexdigest()
    parsed=urlparse(args.url)
    is_pdf=ctype=='application/pdf' or parsed.path.lower().endswith('.pdf')
    text=''
    if is_pdf:
        if not shutil.which('pdftotext'):
            text='[PDF NOT LOCALLY EXTRACTED — VERIFY FROM OFFICIAL NOTICE]\n'+args.url
        else:
            with tempfile.TemporaryDirectory() as td:
                src=Path(td)/'notice.pdf'; dst=Path(td)/'notice.txt'
                src.write_bytes(data)
                p=subprocess.run(['pdftotext','-layout',str(src),str(dst)],capture_output=True,text=True,timeout=30)
                if p.returncode!=0:
                    text='[PDF EXTRACTION FAILED — VERIFY FROM OFFICIAL NOTICE]\n'+args.url
                else: text=dst.read_text(errors='ignore')
    else:
        text=clean_html(data)
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(text+'\n',encoding='utf-8')
    print(f'content_sha256={digest} content_type={ctype} chars={len(text)} out={out}')

if __name__=='__main__': main()
