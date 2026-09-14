/* ONESTOP Government Updates — verified publication API layer */
(function(){
'use strict';
var API_URL='data/publication-queue.json';
var CATEGORIES=['jobs','admit','results','answer','admission','scholarship','syllabus','important'];
var LABELS={jobs:'💼 Latest Jobs',admit:'🎫 Admit Card',results:'🏆 Results',answer:'🔑 Answer Key',admission:'🎓 Admission',scholarship:'💰 Scholarship & Student',syllabus:'📘 Syllabus',important:'⭐ Important Updates'};
var NA='Official notice में देखें';
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function clearPanels(){CATEGORIES.forEach(function(id){var p=document.getElementById(id);if(!p)return;var ul=p.querySelector('.list');if(ul)ul.innerHTML='<li><span class="item">Verified updates loading…</span></li>';});}
function normalize(x){
 x=x||{}; var o=x.fields||x;
 return {id:x.jobId||o.jobId||x.id||'',title:o.title||x.title||'Untitled update',meta:o.meta||x.meta||((o.applicationLastDate||x.applicationLastDate)?'Last date: '+(o.applicationLastDate||x.applicationLastDate):''),vacancy:o.vacancies||o.vacancy||NA,dates:o.dates||((o.applicationStartDate||o.applicationLastDate)?'Application: '+(o.applicationStartDate||'—')+' to '+(o.applicationLastDate||'—'):NA),eligibility:o.qualification||o.eligibility||NA,fee:o.fee||NA,age:o.ageLimit||o.age||NA,selection:o.selection||NA,noticeUrl:o.notificationUrl||x.notificationUrl||x.officialSource&&x.officialSource.url||'',applyUrl:o.applyUrl||x.applyUrl||x.officialSource&&x.officialSource.url||'',department:o.department||'',organization:o.organization||'',category:o.category||'',jobType:o.jobType||'',state:o.state||'',source:x.source||o.source||'SarkariResult',verificationStatus:x.verificationStatus||o.verificationStatus||'',publicationStatus:x.publicationStatus||o.publicationStatus||''};
}
function category(x){
 var c=String(x.category||'').toLowerCase();
 if(CATEGORIES.indexOf(c)>=0)return c;
 var t=(x.title+' '+x.meta).toLowerCase();
 if(/admit|e-admit|interview schedule|exam city/.test(t))return 'admit';
 if(/answer key/.test(t))return 'answer';
 if(/result|final result/.test(t))return 'results';
 if(/scholarship|national scholarship|pm-usp|pragati|saksham|swanath/.test(t))return 'scholarship';
 if(/syllabus|exam resources/.test(t))return 'syllabus';
 if(/admission|calendar/.test(t))return 'admission';
 if(/important|advisory|addendum|corrigendum/.test(t))return 'important';
 return 'jobs';
}
function detail(x){
 var modal=document.getElementById('updateModal');if(!modal)return;
 document.getElementById('detailTitle').textContent=x.title;
 document.getElementById('detailMeta').textContent=(x.organization?x.organization+' • ':'')+(x.department||'')+(x.source?' • Source: '+x.source:'');
 var fields=[['Post / Vacancy',x.vacancy],['Important Dates',x.dates],['Eligibility / Qualification',x.eligibility],['Application Fee',x.fee],['Age Limit',x.age],['Selection Process',x.selection],['Department',x.department||NA],['Job Type',x.jobType||NA]];
 document.getElementById('detailGrid').innerHTML=fields.map(function(f){return '<div class="detail-box"><strong>'+esc(f[0])+'</strong><span>'+esc(f[1]||NA)+'</span></div>';}).join('');
 document.getElementById('officialNotice').href=x.noticeUrl||'#';
 document.getElementById('applyLink').href=x.applyUrl||x.noticeUrl||'#';
 modal.classList.add('show');document.body.style.overflow='hidden';
}
function render(cat,items){
 var p=document.getElementById(cat);if(!p)return;var ul=p.querySelector('.list');if(!ul)return;
 if(!items.length){ul.innerHTML='<li><span class="item">No verified updates available right now.</span></li>';return;}
 ul.innerHTML=items.slice(0,15).map(function(x){return '<li><span class="fresh-badge fresh-new">VERIFIED</span><a href="#" class="item os-api-item" data-id="'+esc(x.id)+'">'+esc(x.title)+'</a><small style="display:block;color:#60708d;font-size:11px;margin-top:3px">'+esc(x.meta||x.dates)+'</small></li>';}).join('');
 items.slice(0,15).forEach(function(x){var el=ul.querySelector('[data-id="'+CSS.escape(x.id)+'"]');if(el)el.addEventListener('click',function(e){e.preventDefault();detail(x);});});
}
function addStatus(){
 var notice=document.querySelector('.notice');if(!notice)return;
 notice.innerHTML='<strong>✅ Verification:</strong> This page displays only records released through the verified-only publication queue. Unverified or held records are never rendered here. Always review the official notice before applying.';
}
function load(){
 clearPanels();addStatus();
 fetch(API_URL,{cache:'no-store',headers:{'Accept':'application/json'}}).then(function(r){if(!r.ok)throw new Error('API HTTP '+r.status);return r.json();}).then(function(payload){
   var items=Array.isArray(payload.items)?payload.items:[];
   items=items.filter(function(x){return x && x.verificationStatus==='verified' && x.publicationStatus==='ready';}).map(normalize);
   var grouped={};CATEGORIES.forEach(function(c){grouped[c]=[];});items.forEach(function(x){grouped[category(x)].push(x);});
   CATEGORIES.forEach(function(c){render(c,grouped[c]);});
   var count=items.length;var hero=document.querySelector('.hero p');if(hero)hero.textContent=count?'Verified government updates — '+count+' publication-ready record'+(count===1?'':'s')+' currently available.':'No verified publication-ready government updates are available right now.';
 }).catch(function(err){
   CATEGORIES.forEach(function(id){var p=document.getElementById(id);if(!p)return;var ul=p.querySelector('.list');if(ul)ul.innerHTML='<li><span class="item">Verified update feed temporarily unavailable.</span></li>';});
   var hero=document.querySelector('.hero p');if(hero)hero.textContent='Verified government update feed is temporarily unavailable. Please check again shortly.';
   if(window.console)console.warn('ONESTOP verified feed:',err);
 });
}
function close(){var m=document.getElementById('updateModal');if(m)m.classList.remove('show');document.body.style.overflow='';}
function init(){var c=document.getElementById('closeModal');if(c)c.addEventListener('click',close);var m=document.getElementById('updateModal');if(m)m.addEventListener('click',function(e){if(e.target===m)close();});document.addEventListener('keydown',function(e){if(e.key==='Escape')close();});load();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
