/* ONESTOP Internet Speed Widget — mobile-safe responsive layout v3 */
(function(){
  'use strict';
  if(window.__ONESTOP_SPEED_WIDGET__) return;
  window.__ONESTOP_SPEED_WIDGET__ = true;
  var root=document.createElement('div');
  root.id='onestop-speed-widget';
  root.innerHTML='<div class="os-speed-head"><span>📶 Internet Speed</span><button type="button" id="osSpeedTest">Test Speed</button></div><div class="os-speed-grid"><div><small>DOWNLOAD</small><strong id="osDown">—</strong><em>Mbps</em></div><div><small>UPLOAD</small><strong id="osUp">—</strong><em>Mbps</em></div><div><small>PING</small><strong id="osPing">—</strong><em>ms</em></div></div><div class="os-speed-meta"><span>🌐 <b id="osNet">Detecting…</b></span><span>🏢 <b id="osIsp">Detecting…</b></span></div><div id="osStatus" class="os-speed-status">Ready to test your connection</div></div>';
  var style=document.createElement('style');
  style.textContent='#onestop-speed-widget{position:absolute!important;right:20px!important;top:18px!important;width:265px!important;box-sizing:border-box;padding:11px 12px!important;border:1px solid rgba(255,255,255,.28);border-radius:15px;background:rgba(3,29,80,.78);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);box-shadow:0 8px 22px rgba(0,0,0,.16);color:#fff;z-index:20;font-family:Arial,Helvetica,sans-serif}.os-speed-head{display:flex;align-items:center;justify-content:space-between;gap:7px;font-size:15px;font-weight:800}.os-speed-head button{border:1px solid rgba(255,255,255,.4);background:#fff;color:#0757c9;border-radius:7px;padding:5px 8px;font-size:10px;font-weight:800;cursor:pointer;white-space:nowrap}.os-speed-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin:8px 0}.os-speed-grid>div{background:rgba(255,255,255,.1);border-radius:8px;padding:6px 3px;text-align:center}.os-speed-grid small{display:block;font-size:8px;opacity:.78;letter-spacing:.35px}.os-speed-grid strong{display:inline-block;font-size:16px;margin-top:1px}.os-speed-grid em{font-style:normal;font-size:8px;opacity:.75;margin-left:1px}.os-speed-meta{display:flex;justify-content:space-between;gap:6px;font-size:8.5px;opacity:.9}.os-speed-meta span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.os-speed-status{margin-top:6px;font-size:8.5px;opacity:.75}.os-speed-testing{opacity:.75;pointer-events:none}.hero{overflow:visible!important}@media(max-width:850px){#onestop-speed-widget{position:relative!important;inset:auto!important;right:auto!important;top:auto!important;left:auto!important;bottom:auto!important;width:calc(100% - 30px)!important;max-width:520px!important;margin:14px auto 0!important;display:block!important;clear:both!important}.hero{overflow:visible!important}}@media(max-width:520px){#onestop-speed-widget{width:calc(100% - 24px)!important;max-width:none!important;margin:12px auto 0!important;padding:10px!important}.os-speed-head{font-size:14px}.os-speed-grid strong{font-size:15px}.os-speed-meta{font-size:8px}}';
  document.head.appendChild(style);
  function api(url,opts){return fetch(url,Object.assign({cache:'no-store'},opts||{}));}
  function set(id,v){var e=document.getElementById(id);if(e)e.textContent=v;}
  async function ping(){var t=performance.now();var r=await api('https://speed.cloudflare.com/__down?bytes=1000');if(!r.ok)throw new Error('Ping endpoint failed');return Math.max(1,Math.round(performance.now()-t));}
  async function download(){var bytes=5000000,t=performance.now();var r=await api('https://speed.cloudflare.com/__down?bytes='+bytes);if(!r.ok)throw new Error('Download endpoint failed');var b=await r.arrayBuffer();return ((b.byteLength*8)/((performance.now()-t)/1000)/1000000);}
  async function upload(){var bytes=1000000,data=new Uint8Array(bytes),t=performance.now();var r=await api('https://speed.cloudflare.com/__up',{method:'POST',body:data,headers:{'Content-Type':'application/octet-stream'}});if(!r.ok)throw new Error('Upload endpoint failed');return ((bytes*8)/((performance.now()-t)/1000)/1000000);}
  async function isp(){try{var r=await api('https://ipapi.co/json/');var j=await r.json();return j.org||j.isp||'Unknown ISP';}catch(e){return 'Unavailable';}}
  function network(){var c=navigator.connection||navigator.mozConnection||navigator.webkitConnection;return c?(c.type||c.effectiveType||'Unknown'):'Unknown';}
  async function run(){var btn=document.getElementById('osSpeedTest'),status=document.getElementById('osStatus');if(!btn)return;btn.classList.add('os-speed-testing');status.textContent='Testing connection…';set('osNet',network());try{var p=await ping();set('osPing',p);status.textContent='Measuring download…';var d=await download();set('osDown',d.toFixed(1));status.textContent='Measuring upload…';var u=await upload();set('osUp',u.toFixed(1));status.textContent='Speed test complete';}catch(e){console.error('ONESTOP speed test',e);status.textContent='Test could not complete. Try again.';}finally{btn.classList.remove('os-speed-testing');}}
  function mount(){var hero=document.querySelector('.hero');var quick=document.querySelector('.hero-quick');if(!hero||document.getElementById(root.id))return;hero.style.position='relative';hero.style.overflow='visible';if(window.matchMedia('(max-width:850px)').matches&&quick){quick.insertAdjacentElement('afterend',root);}else{hero.appendChild(root);}set('osNet',network());isp().then(function(v){set('osIsp',v);});document.getElementById('osSpeedTest').addEventListener('click',run);}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();

  /* ONESTOP Sarkari Result live updates */
  var jobsRoot=document.createElement('div');
  jobsRoot.id='onestop-job-updates';
  jobsRoot.innerHTML='<div class="os-job-top"><div><span class="os-job-kicker">🇮🇳 Sarkari Updates</span><h3>Latest Government Updates</h3></div><span class="os-job-source">Source: SarkariResult.com</span></div><div class="os-job-tabs" role="tablist"><button class="active" data-tab="jobs" role="tab">💼 Latest Job</button><button data-tab="admit" role="tab">🎫 Admit Card</button><button data-tab="result" role="tab">🏆 Result</button></div><div class="os-job-panel"><div id="osJobLoading">Loading latest updates…</div><div id="osJobList"></div></div><div class="os-job-footer"><span id="osJobUpdated">Live source loading…</span><a href="https://www.sarkariresult.com/" target="_blank" rel="noopener noreferrer">View SarkariResult →</a></div>';
  var jobStyle=document.createElement('style');
  jobStyle.textContent='#onestop-job-updates{grid-column:1/-1;width:100%;box-sizing:border-box;margin:4px 0 8px;padding:14px 15px 12px;border:1px solid rgba(255,255,255,.25);border-radius:18px;background:linear-gradient(135deg,rgba(3,29,80,.86),rgba(7,87,201,.58));backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);box-shadow:0 10px 28px rgba(0,0,0,.15);color:#fff;font-family:Arial,"Segoe UI",sans-serif;position:relative;z-index:8}.os-job-top{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:10px}.os-job-kicker{display:inline-block;font-size:10px;letter-spacing:.5px;text-transform:uppercase;opacity:.82;font-weight:800}.os-job-top h3{font-size:18px;line-height:1.2;margin-top:2px}.os-job-source{font-size:9px;opacity:.72;white-space:nowrap}.os-job-tabs{display:flex;gap:7px;margin-bottom:9px}.os-job-tabs button{flex:0 0 auto;border:1px solid rgba(255,255,255,.3);border-radius:9px;background:rgba(255,255,255,.09);color:#fff;padding:7px 13px;font-size:11px;font-weight:800;cursor:pointer;transition:.18s}.os-job-tabs button:hover{background:rgba(255,255,255,.16)}.os-job-tabs button.active{background:#fff;color:#0757c9;border-color:#fff;box-shadow:0 4px 12px rgba(0,0,0,.12)}.os-job-panel{min-height:86px}.os-job-list{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.os-job-item{display:flex;align-items:flex-start;gap:7px;min-width:0;padding:8px 9px;border:1px solid rgba(255,255,255,.18);border-radius:9px;background:rgba(255,255,255,.08);color:#fff;font-size:11px;line-height:1.35;transition:.18s}.os-job-item:hover{background:rgba(255,255,255,.14);transform:translateY(-1px)}.os-job-dot{width:5px;height:5px;min-width:5px;margin-top:5px;border-radius:50%;background:#c6e2ff}.os-job-item a{color:#fff;text-decoration:none;font-weight:700;display:block;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}.os-job-empty,.os-job-error{padding:10px;border-radius:9px;background:rgba(255,255,255,.08);font-size:11px;color:#e3efff}.os-job-footer{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:9px;font-size:9px;color:#dceaff}.os-job-footer a{color:#fff;font-weight:800;text-decoration:none}.os-job-footer a:hover{text-decoration:underline}@media(max-width:850px){#onestop-job-updates{grid-column:auto;margin:0 0 8px;padding:12px;width:100%;}.os-job-top h3{font-size:16px}.os-job-source{display:none}.os-job-list{grid-template-columns:1fr 1fr}.os-job-tabs{overflow-x:auto;padding-bottom:1px;scrollbar-width:none}.os-job-tabs::-webkit-scrollbar{display:none}}@media(max-width:520px){#onestop-job-updates{border-radius:14px;padding:10px}.os-job-tabs button{font-size:10px;padding:7px 10px}.os-job-list{grid-template-columns:1fr}.os-job-item{font-size:10.5px}.os-job-footer{font-size:8px}.os-job-panel{min-height:72px}}';
  document.head.appendChild(jobStyle);

  var jobData={jobs:[],admit:[],result:[]};
  var jobCache={};
  var activeJobTab='jobs';
  function jobEscape(v){var d=document.createElement('div');d.textContent=String(v||'');return d.innerHTML;}
  function jobSourceUrl(tab){return 'https://r.jina.ai/https://www.sarkariresult.com/';}
  function parseSarkariResult(markdown){
    var lines=String(markdown||'').split(/\r?\n/),sections={jobs:[],admit:[],result:[]},current=null;
    for(var i=0;i<lines.length;i++){
      var raw=lines[i].replace(/\*\*/g,'').trim();
      var low=raw.toLowerCase();
      if(/^#+\s*latest job/.test(low)||low==='latest job'){current='jobs';continue;}
      if(/^#+\s*admit card/.test(low)||low==='admit card'){current='admit';continue;}
      if(/^#+\s*(latest result|result|results)/.test(low)||low==='result'||low==='results'){current='result';continue;}
      if(current){
        var m=raw.match(/^[-*]\s*\[([^\]]+)\]\((https?:\/\/[^)]+)\)/);
        if(!m)m=raw.match(/^[-*]\s*(.+?)\s+(https?:\/\/\S+)$/);
        if(m){var title=(m[1]||'').trim();var url=(m[2]||'').trim();if(title&&url&&!sections[current].some(function(x){return x.title===title;}))sections[current].push({title:title,url:url});}
      }
    }
    return sections;
  }
  function renderJobList(){
    var list=document.getElementById('osJobList'),loading=document.getElementById('osJobLoading');
    if(!list)return;
    if(loading)loading.style.display='none';
    var items=jobData[activeJobTab]||[];
    if(!items.length){list.className='';list.innerHTML='<div class="os-job-empty">Live updates are temporarily unavailable. Open SarkariResult to view the latest '+jobEscape(activeJobTab==='jobs'?'jobs':activeJobTab==='admit'?'admit cards':'results')+'.</div>';return;}
    list.className='os-job-list';list.innerHTML=items.slice(0,9).map(function(item){return '<div class="os-job-item"><span class="os-job-dot"></span><a href="'+jobEscape(item.url)+'" target="_blank" rel="noopener noreferrer">'+jobEscape(item.title)+'</a></div>';}).join('');
  }
  async function loadJobs(){
    var loading=document.getElementById('osJobLoading');
    try{
      if(loading)loading.textContent='Loading latest updates from SarkariResult.com…';
      var response=await fetch(jobSourceUrl('all'),{cache:'no-store',headers:{'Accept':'text/plain'}});
      if(!response.ok)throw new Error('Source request failed');
      var text=await response.text();
      var parsed=parseSarkariResult(text);
      if(!parsed.jobs.length&&!parsed.admit.length&&!parsed.result.length)throw new Error('No category data found');
      jobData=parsed;
      jobCache.loadedAt=Date.now();
      var updated=document.getElementById('osJobUpdated');if(updated)updated.textContent='Updated just now • live source';
      renderJobList();
    }catch(error){
      console.error('ONESTOP Sarkari Result updates',error);
      var updated=document.getElementById('osJobUpdated');if(updated)updated.textContent='Live source unavailable right now';
      renderJobList();
    }
  }
  function mountJobs(){
    var hero=document.querySelector('.hero'),quick=document.querySelector('.hero-quick');
    if(!hero||document.getElementById(jobsRoot.id))return;
    if(quick){quick.insertAdjacentElement('afterend',jobsRoot);}else{hero.insertBefore(jobsRoot,hero.firstChild);}
    jobsRoot.querySelectorAll('.os-job-tabs button').forEach(function(btn){btn.addEventListener('click',function(){activeJobTab=btn.getAttribute('data-tab')||'jobs';jobsRoot.querySelectorAll('.os-job-tabs button').forEach(function(b){b.classList.toggle('active',b===btn);});renderJobList();});});
    renderJobList();
    loadJobs();
    window.setInterval(loadJobs,30*60*1000);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mountJobs);else mountJobs();
})();
