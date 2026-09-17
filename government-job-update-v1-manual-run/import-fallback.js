/* ONESTOP Job Update V1 — paste fallback for sources that return HTTP 403/CORS. */
(function(){
  function boot(){
    const status=document.getElementById('urlStatus');
    if(!status||document.getElementById('pasteImportBox'))return;
    const box=document.createElement('div');box.id='pasteImportBox';box.style.cssText='margin-top:14px;padding:14px;border:1px solid #f0c36d;border-radius:10px;background:#fffaf0';
    box.innerHTML='<b>URL blocked? Import the source table here</b><p class="muted">If the source blocks automated access (HTTP 403), open its page in another tab, select and copy the full information table, then paste it below. HTML or copied spreadsheet-style rows are supported. Nothing is published automatically.</p><textarea id="sourceTablePaste" rows="7" placeholder="Paste copied table or HTML here…" style="width:100%;min-height:130px"></textarea><div class="row-actions"><button type="button" id="pasteImportBtn" class="btn secondary">Import pasted table</button><button type="button" id="pasteClearBtn" class="btn secondary">Clear</button></div><div id="pasteImportStatus" class="muted" style="margin-top:8px"></div>';
    status.insertAdjacentElement('afterend',box);
    document.getElementById('pasteClearBtn').onclick=()=>{document.getElementById('sourceTablePaste').value='';document.getElementById('pasteImportStatus').textContent=''};
    document.getElementById('pasteImportBtn').onclick=importPasted;
  }
  function importPasted(){
    const raw=document.getElementById('sourceTablePaste').value.trim(),out=document.getElementById('pasteImportStatus');
    if(!raw){out.textContent='Paste a table first.';return}
    let parsed=[];
    if(/<\s*(table|tr|td|th)\b/i.test(raw)){
      const doc=new DOMParser().parseFromString(raw,'text/html');
      doc.querySelectorAll('table').forEach((table,idx)=>{
        const rows=[...table.querySelectorAll('tr')].map(tr=>[...tr.querySelectorAll(':scope > th, :scope > td')].map(c=>(c.innerText||c.textContent||'').replace(/\u00a0/g,' ').trim())).filter(r=>r.some(Boolean));
        if(rows.length>1){const n=Math.max(...rows.map(r=>r.length));const norm=rows.map(r=>{while(r.length<n)r.push('');return r});parsed.push({name:idx===0?'MAIN INFORMATION TABLE':'Imported Table '+(idx+1),columns:norm[0].map((v,i)=>v||'Column '+(i+1)),rows:norm.slice(1)})}
      });
    }
    if(!parsed.length){
      const lines=raw.split(/\r?\n/).map(s=>s.trim()).filter(Boolean);
      const rows=lines.map(line=>line.split(/\t|\s*\|\s*/).map(c=>c.trim()));
      const n=Math.max(0,...rows.map(r=>r.length));
      if(rows.length>1&&n>1){const norm=rows.map(r=>{while(r.length<n)r.push('');return r});parsed=[{name:'MAIN INFORMATION TABLE',columns:norm[0].map((v,i)=>v||'Column '+(i+1)),rows:norm.slice(1)}]}
    }
    if(!parsed.length){out.textContent='No table structure found. Copy the table itself (not just the page title), or paste rows separated by tabs/pipes.';return}
    if(typeof state==='undefined'||typeof renderTables!=='function'){out.textContent='Admin editor is still loading. Refresh once and retry.';return}
    state.tables=parsed;
    if(typeof renderTables==='function')renderTables();
    if(typeof preview==='function')preview();
    out.textContent='Imported '+parsed.length+' table(s) into the editable Dynamic Tables section. Please review before saving or test publishing.';
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();