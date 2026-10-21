/* ONESTOP Internet Speed Widget — mobile-safe responsive layout v3 + passport photo fix */
(function(){
  'use strict';
  if(window.__ONESTOP_SPEED_WIDGET__) return;
  window.__ONESTOP_SPEED_WIDGET__ = true;
  var root=document.createElement('div');
  root.id='onestop-speed-widget';
  root.innerHTML='<div class="os-speed-head"><span class="os-speed-title"><span class="os-speed-icon" aria-hidden="true"><svg viewBox="0 0 24 24" focusable="false"><path d="M2.5 8.8a15 15 0 0 1 19 0M5.7 12a10 10 0 0 1 12.6 0M8.9 15.2a5 5 0 0 1 6.2 0M12 19h.01"/></svg></span><span>Internet Speed</span><span class="os-speed-network-chip"><span class="os-speed-network-icon" aria-hidden="true">●</span><b id="osNet">Detecting…</b></span></span><button type="button" id="osSpeedTest">Test Speed</button></div><div class="os-speed-grid"><div><small>DOWNLOAD</small><strong id="osDown">—</strong><em>Mbps</em></div><div><small>UPLOAD</small><strong id="osUp">—</strong><em>Mbps</em></div><div><small>PING</small><strong id="osPing">—</strong><em>ms</em></div></div><div class="os-speed-meta"><span>🏢 <b id="osIsp">Detecting…</b></span></div><div id="osStatus" class="os-speed-status">Ready to test your connection</div></div>';
  var style=document.createElement('style');
  style.textContent=`
#onestop-speed-widget{position:relative!important;inset:auto!important;width:100%!important;max-width:none!important;min-width:0!important;min-height:0;display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;box-sizing:border-box;margin:0!important;padding:10px 12px!important;border:1px solid rgba(255,255,255,.3);border-radius:24px;background:rgba(255,255,255,.13);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);box-shadow:0 8px 22px rgba(0,0,0,.16);color:#fff;z-index:2;font-family:Arial,Helvetica,sans-serif}
.hero-inner>.hero-quick{grid-column:1/-1;grid-row:1;align-self:start}.hero-right-stack{grid-column:2;grid-row:2;align-self:start;display:flex;flex-direction:column;gap:16px;min-width:0;width:100%;margin:0!important}.hero-inner>div:not(.hero-quick):not(.hero-right-stack){grid-column:1;grid-row:2;align-self:start}
.hero-right-stack .hero-card{width:100%;min-width:0;margin:0;box-sizing:border-box}
.hero-right-stack .hero-card img{max-width:100%}
.os-speed-head{grid-column:1/-1;grid-row:1;display:flex;align-items:center;justify-content:space-between;gap:7px;font-size:15px;font-weight:800}
.os-speed-title{display:inline-flex;align-items:center;gap:7px;color:#ffd166;font-weight:900;text-shadow:0 1px 2px rgba(4,35,83,.7);min-width:0;flex-wrap:wrap}
.os-speed-icon{display:inline-flex;align-items:center;justify-content:center;color:#22e6a8;flex:0 0 21px;width:21px;height:21px;line-height:1}.os-speed-icon svg{display:block;width:100%;height:100%;fill:none;stroke:currentColor;stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round}
.os-speed-network-chip{display:inline-flex;align-items:center;gap:4px;margin-left:2px;padding:2px 7px;border:1px solid rgba(34,230,168,.65);border-radius:20px;background:rgba(6,44,86,.4);color:#fff;font-size:11px;font-weight:900;text-shadow:none;white-space:nowrap}
.os-speed-network-icon{color:#22e6a8;font-size:12px;line-height:1;text-shadow:0 0 7px rgba(34,230,168,.6)}
.os-speed-head button{border:1px solid rgba(255,255,255,.45);background:linear-gradient(135deg,#0757c9,#1688e8);color:#fff;border-radius:8px;padding:7px 11px;font-size:12px;font-weight:900;cursor:pointer;white-space:nowrap;box-shadow:0 3px 8px rgba(0,24,70,.22);flex-shrink:0}
.os-speed-grid{grid-column:1/-1;grid-row:2;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin:7px 0 6px}
.os-speed-grid>div{min-width:0;background:rgba(255,255,255,.25);border:1px solid rgba(255,255,255,.25);border-radius:9px;padding:7px 3px;text-align:center}
.os-speed-grid small{display:block;color:#073c87;font-size:10px;opacity:1;letter-spacing:.35px;font-weight:900}
.os-speed-grid strong{display:inline-block;font-size:18px;font-weight:900;margin-top:1px;color:#fff;text-shadow:0 1px 2px rgba(0,35,83,.35)}
.os-speed-grid em{font-style:normal;font-size:11px;font-weight:800;color:#fff;opacity:1;margin-left:2px}
.os-speed-meta{grid-column:2;grid-row:3;display:flex;justify-content:flex-end;align-items:center;gap:8px;font-size:12px;font-weight:800;opacity:1;min-height:16px;max-width:100%}
.os-speed-meta b{font-size:12px;font-weight:900}
.os-speed-meta span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.os-speed-status{grid-column:1;grid-row:3;align-self:center;margin-top:0;font-size:11px;font-weight:800;opacity:1;line-height:1.25;min-width:0}
.os-speed-testing{opacity:.75;pointer-events:none}
.hero{overflow:visible!important}
@media(max-width:1100px){.hero-inner{column-gap:24px}.hero-right-stack{gap:14px}.hero-right-stack .hero-card{padding:22px}.hero-right-stack .hero-card h2{font-size:26px}}
@media(max-width:850px){.hero-inner{grid-template-columns:minmax(0,1fr);row-gap:16px}.hero-inner>.hero-quick{grid-column:1;grid-row:1}.hero-inner>div:not(.hero-quick):not(.hero-right-stack){grid-column:1;grid-row:2;min-width:0}.hero-right-stack{grid-column:1;grid-row:3;gap:14px;min-width:0}.hero-right-stack .hero-card{margin-top:0!important}}
@media(max-width:520px){#onestop-speed-widget{padding:10px!important;border-radius:22px;grid-template-columns:minmax(0,1fr) auto}.os-speed-head{font-size:14px}.os-speed-title{gap:5px}.os-speed-icon{flex-basis:20px;width:20px;height:20px}.os-speed-network-chip{font-size:10px;padding:2px 6px}.os-speed-grid strong{font-size:17px}.os-speed-grid small{font-size:10px}.os-speed-grid em{font-size:10px}.os-speed-meta,.os-speed-meta b{font-size:11px}.os-speed-status{font-size:11px}}
`;

  document.head.appendChild(style);
  function api(url,opts){return fetch(url,Object.assign({cache:'no-store'},opts||{}));}
  function set(id,v){var e=document.getElementById(id);if(e)e.textContent=v;}
  async function ping(){var t=performance.now();var r=await api('https://speed.cloudflare.com/__down?bytes=1000');if(!r.ok)throw new Error('Ping endpoint failed');return Math.max(1,Math.round(performance.now()-t));}
  async function download(){var bytes=5000000,t=performance.now();var r=await api('https://speed.cloudflare.com/__down?bytes='+bytes);if(!r.ok)throw new Error('Download endpoint failed');var b=await r.arrayBuffer();return ((b.byteLength*8)/((performance.now()-t)/1000)/1000000);}
  async function upload(){var bytes=1000000,data=new Uint8Array(bytes),t=performance.now();var r=await api('https://speed.cloudflare.com/__up',{method:'POST',body:data,headers:{'Content-Type':'application/octet-stream'}});if(!r.ok)throw new Error('Upload endpoint failed');return ((bytes*8)/((performance.now()-t)/1000)/1000000);}
  async function isp(){try{var r=await api('https://ipapi.co/json/');var j=await r.json();return j.org||j.isp||'Unknown ISP';}catch(e){return 'Unavailable';}}
  function network(){var c=navigator.connection||navigator.mozConnection||navigator.webkitConnection;return c?(c.type||c.effectiveType||'Unknown'):'Unknown';}
  async function run(){var btn=document.getElementById('osSpeedTest'),status=document.getElementById('osStatus');if(!btn)return;btn.classList.add('os-speed-testing');status.textContent='Testing connection…';set('osNet',network());try{var p=await ping();set('osPing',p);status.textContent='Measuring download…';var d=await download();set('osDown',d.toFixed(1));status.textContent='Measuring upload…';var u=await upload();set('osUp',u.toFixed(1));status.textContent='Speed test complete';}catch(e){console.error('ONESTOP speed test',e);status.textContent='Test could not complete. Try again.';}finally{btn.classList.remove('os-speed-testing');}}
  function mount(){var hero=document.querySelector('.hero');var inner=hero&&hero.querySelector('.hero-inner');var card=inner&&inner.querySelector('.hero-card');if(!hero||!inner||!card||document.getElementById(root.id))return;hero.style.position='relative';hero.style.overflow='visible';var stack=document.createElement('div');stack.className='hero-right-stack';inner.insertBefore(stack,card);stack.appendChild(root);stack.appendChild(card);set('osNet',network());isp().then(function(v){set('osIsp',v);});document.getElementById('osSpeedTest').addEventListener('click',run);}
  function replacePassportPhoto(){
    var url='https://raw.githubusercontent.com/grvtech99/onestop-website/main/PASSPORT_PHOTO.webp?photo=20260916';
    document.querySelectorAll('img[src*="PASSPORT_PHOTO.webp"],img[src*="PASSPORT%20PHOTO.png"],img[src*="PASSPORT PHOTO.png"]').forEach(function(img){img.src=url;img.removeAttribute('srcset');});
  }
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',mount);
    document.addEventListener('DOMContentLoaded',replacePassportPhoto);
  }else{mount();replacePassportPhoto();}
})();