/* ONESTOP Job Update V1 — pasted table normalizer
   Converts one-cell-per-row pasted text into editable Information | Details rows.
   Leaves already structured multi-column tables unchanged. */
(function(){
  const $ = id => document.getElementById(id);
  const clean = s => String(s ?? '').replace(/\u00a0/g,' ').replace(/[\t ]+/g,' ').trim();
  const esc = s => String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function splitLabelValue(text){
    const s=clean(text).replace(/^\|+|\|+$/g,'').trim();
    if(!s) return null;
    let m=s.match(/^(.{2,100}?)\s*[:：]\s*(.+)$/s);
    if(m) return [clean(m[1]),clean(m[2])];
    m=s.match(/^(.{2,100}?)\s+[—–-]\s+(.+)$/s);
    if(m && !/^https?:$/i.test(m[1])) return [clean(m[1]),clean(m[2])];
    return null;
  }
  function normalizeTable(t){
    if(!t || !Array.isArray(t.rows) || !Array.isArray(t.columns)) return false;
    if(t.columns.length>2) return false;
    const rows=t.rows.map(r=>Array.isArray(r)?r.map(clean):[clean(r)]).filter(r=>r.some(Boolean));
    if(!rows.length) return false;
    // Only normalize when imported content is essentially a single text column,
    // or when the second column is empty throughout.
    const oneCol=rows.every(r=>r.length===1 || !clean(r[1]));
    if(!oneCol) return false;
    const parsed=rows.map(r=>splitLabelValue(r[0]||''));
    const usable=parsed.filter(Boolean).length;
    if(usable < Math.max(2,Math.ceil(rows.length*0.25))) return false;
    t.name='MAIN INFORMATION TABLE';
    t.columns=['Information','Details'];
    t.rows=rows.map((r,i)=>{
      const p=parsed[i];
      if(p) return p;
      const txt=clean(r[0]||'');
      // Keep headings and unlabelled source lines instead of dropping content.
      return [txt,''];
    });
    // Pull title into Recruitment Name only when that core field is blank.
    try {
      const titleRow=t.rows.find(r=>/recruitment|examination|exam|vacancy|engineering services/i.test(r[0]+' '+r[1]) && (r[0].length+r[1].length)>12);
      if(titleRow && window.state && Array.isArray(state.fields)){
        const f=state.fields.find(x=>x[0]==='Recruitment Name');
        if(f && !clean(f[1])) f[1]=clean(titleRow[1] || titleRow[0]);
      }
    } catch(e) {}
    return true;
  }
  function refresh(){
    try {
      if(!window.state || !Array.isArray(state.tables)) return;
      let changed=false;
      state.tables.forEach(t=>{ if(normalizeTable(t)) changed=true; });
      if(changed){
        if(typeof window.renderTables==='function') window.renderTables();
        if(typeof window.renderFields==='function') window.renderFields();
        if(typeof window.checkData==='function') window.checkData();
        if(typeof window.preview==='function') window.preview();
      }
    } catch(e) { console.warn('ONESTOP table normalization:',e); }
  }
  // Run after the existing import handler has populated state.tables.
  document.addEventListener('click',e=>{
    const b=e.target.closest('button');
    if(b && /import pasted table/i.test(b.textContent||'')) setTimeout(refresh,80);
  });
  document.addEventListener('paste',()=>setTimeout(refresh,250));
  window.addEventListener('load',()=>setTimeout(refresh,300));
})();
