/* ONESTOP Job Update V1 — paste import for Word/Excel copied tables.
   Preserves every non-empty source row/cell, expands uneven rows, and normalizes
   label:value lines into Information | Details without dropping section headings. */
(function(){
  const byId=id=>document.getElementById(id);
  const tidy=s=>String(s??'').replace(/\u00a0/g,' ').replace(/[\u200b\ufeff]/g,'').replace(/[ \t]+/g,' ').trim();
  function boot(){
    const status=byId('urlStatus');
    if(!status||byId('pasteImportBox'))return;
    const box=document.createElement('div');box.id='pasteImportBox';
    box.style.cssText='margin-top:14px;padding:14px;border:1px solid #f0c36d;border-radius:10px;background:#fffaf0';
    box.innerHTML='<b>URL blocked? Paste copied Word / Excel table</b><p class="muted">Copy the whole information table from the source page, Word, or Excel and paste here. All rows/cells are retained. HTML, tab-separated and pipe-separated content are supported. Review before saving.</p><textarea id="sourceTablePaste" rows="8" placeholder="Paste the complete copied table here…" style="width:100%;min-height:150px"></textarea><div class="row-actions"><button type="button" id="pasteImportBtn" class="btn secondary">Import pasted table</button><button type="button" id="pasteClearBtn" class="btn secondary">Clear</button></div><div id="pasteImportStatus" class="muted" style="margin-top:8px"></div>';
    status.insertAdjacentElement('afterend',box);
    byId('pasteClearBtn').onclick=()=>{byId('sourceTablePaste').value='';byId('pasteImportStatus').textContent=''};
    byId('pasteImportBtn').onclick=importPasted;
  }
  function readHtml(raw){
    const doc=new DOMParser().parseFromString(raw,'text/html');
    const tables=[...doc.querySelectorAll('table')];
    return tables.map((table,idx)=>{
      const rows=[...table.querySelectorAll('tr')].map(tr=>[...tr.children].filter(c=>/^(TD|TH)$/i.test(c.tagName)).map(c=>tidy(c.innerText||c.textContent||''))).filter(r=>r.some(Boolean));
      return makeTable(rows,idx);
    }).filter(Boolean);
  }
  function readPlain(raw){
    // Clipboard from Word/Excel normally preserves cell boundaries as tabs and rows as newlines.
    const lines=raw.replace(/\r/g,'').split('\n');
    const rows=lines.map(line=>line.split('\t').map(tidy));
    return makeTable(rows,0);
  }
  function makeTable(inputRows,idx){
    let rows=(inputRows||[]).map(r=>Array.isArray(r)?r.map(tidy):[tidy(r)]).filter(r=>r.some(Boolean));
    if(!rows.length)return null;
    const width=Math.max(...rows.map(r=>r.length));
    rows=rows.map(r=>{const out=r.slice();while(out.length<width)out.push('');return out});
    // A two-column paste where the first cell contains "Label: value" is better
    // represented as explicit Information | Details. Preserve headings and all rows.
    const oneTextCol=rows.every(r=>r.slice(1).every(v=>!v));
    if(oneTextCol){
      const pairs=rows.map(r=>splitPair(r[0]));
      const count=pairs.filter(Boolean).length;
      if(count>=Math.max(2,Math.ceil(rows.length*.2))){
        rows=rows.map((r,i)=>pairs[i]||[r[0],'']);
        return {name:idx===0?'MAIN INFORMATION TABLE':'Imported Table '+(idx+1),columns:['Information','Details'],rows};
      }
    }
    // Retain native multi-column Word/Excel layout. Do not promote first data row
    // to headers, because source tables often start with a merged title/section row.
    const columns=Array.from({length:width},(_,i)=>'Source Column '+(i+1));
    return {name:idx===0?'MAIN INFORMATION TABLE':'Imported Table '+(idx+1),columns,rows};
  }
  function splitPair(value){
    const s=tidy(value);if(!s)return null;
    let m=s.match(/^(.{2,100}?)\s*[:：]\s*(.+)$/s);
    if(m)return [tidy(m[1]),tidy(m[2])];
    m=s.match(/^(.{2,100}?)\s+[—–]\s+(.+)$/s);
    if(m)return [tidy(m[1]),tidy(m[2])];
    return null;
  }
  function importPasted(){
    const raw=byId('sourceTablePaste').value.trim(),out=byId('pasteImportStatus');
    if(!raw){out.textContent='Paste the complete table first.';return}
    let parsed=[];
    if(/<\s*(table|tr|td|th)\b/i.test(raw))parsed=readHtml(raw);
    if(!parsed.length){const t=readPlain(raw);if(t)parsed=[t]}
    if(!parsed.length){out.textContent='No rows detected. Copy the whole table from Word/Excel and paste again.';return}
    if(typeof state==='undefined'||typeof renderTables!=='function'){out.textContent='Admin editor is still loading. Refresh and retry.';return}
    state.tables=parsed;
    if(typeof renderTables==='function')renderTables();
    if(typeof preview==='function')preview();
    const rowCount=parsed.reduce((n,t)=>n+t.rows.length,0);
    out.textContent='Imported '+parsed.length+' table(s), '+rowCount+' source row(s). Cell content has been preserved in editable columns. Check section headings and merged-cell rows in the editor/preview.';
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();