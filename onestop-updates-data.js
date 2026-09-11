/* ONESTOP Government Updates — official-source data layer */
(function(){
'use strict';
var NA='Official notice में देखें';
function d(title,meta,url,extra){extra=extra||{};return Object.assign({title:title,meta:meta,url:url,vacancy:NA,dates:meta,eligibility:NA,fee:NA,age:NA,selection:NA,noticeUrl:url,applyUrl:url},extra);}
var DATA={
 jobs:[
  d('Ramagundam Fertilizers & Chemicals Ltd — Engineer & Others','Last date: 24/09/2026','https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All'),
  d('NIPER Kolkata — Professor Recruitment','Last date: 17/09/2026','https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All'),
  d('National Disaster Management Authority — Young Consultant','Last date: 18/10/2026','https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All'),
  d('National Board of Examinations in Medical Sciences — Executive Director','Last date: 30/10/2026','https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All'),
  d('LBSNAA — Administrative Officer & Others','Last date: 11/09/2026','https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All'),
  d('Sainik School Ambikapur — Laboratory Assistant & Others','Last date: 12/09/2026','https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All'),
  d('BRIC-NIAB — Scientist-B & Others','Last date: 11/09/2026','https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All')
 ],
 admit:[
  d('UPSC NDA & NA II / CDS II 2026 — e-Admit Card available','Exam: 13/09/2026','https://www.upsc.gov.in/examinations/Combined%20Defence%20Services%20Examination%20%28II%29%2C%202026',{vacancy:'Not a recruitment vacancy — examination admit card',dates:'Examination: 13/09/2026; e-Admit Card uploaded: 03/09/2026',eligibility:'For candidates whose applications were accepted for the examination',selection:'Examination process as prescribed by UPSC'}),
  d('UPSC Engineering Services Main 2026 — Interview Schedule','Uploaded: 07/09/2026','https://www.upsc.gov.in/exams-related-info/interview-schedule',{vacancy:'Not applicable — interview schedule',dates:'Schedule uploaded: 07/09/2026',selection:'Interview / Personality Test as per UPSC schedule'}),
  d('UPSC Combined Geo-Scientist Main 2026 — Interview Schedule','Uploaded: 02/09/2026','https://www.upsc.gov.in/exams-related-info/interview-schedule',{vacancy:'Not applicable — interview schedule',dates:'Schedule uploaded: 02/09/2026',selection:'Interview / Personality Test as per UPSC schedule'}),
  d('SSC Selection Post Phase-XIV/2026 — Exam City Information','Exam window: 16/09/2026 to 26/09/2026','https://ssc.gov.in/',{vacancy:'Selection Posts examination',dates:'Computer Based Examination: 16/09/2026–26/09/2026',eligibility:'Candidates with accepted applications; verify regional instructions',selection:'Computer Based Examination and applicable subsequent stages'})
 ],
 results:[
  d('UPSC Assistant Director Grade-II (IEDS), Leather & Footwear — Final Result','Uploaded: 09/09/2026','https://www.upsc.gov.in/recruitment/recruitment-test/results/final-result',{vacancy:'02 Posts',dates:'Final result uploaded: 09/09/2026',selection:'Final result published by UPSC'}),
  d('UPSC Assistant Director Grade-II (IEDS), Chemical — Final Result','Uploaded: 08/09/2026','https://www.upsc.gov.in/recruitment/recruitment-test/results/final-result',{vacancy:'03 Posts',dates:'Final result uploaded: 08/09/2026',selection:'Final result published by UPSC'}),
  d('SSC Annual Departmental Typing Test 2024 — Result','Uploaded: 09/09/2026','https://ssc.gov.in/',{vacancy:'Departmental examination result',dates:'Result notice: 09/09/2026',selection:'As prescribed by SSC'}),
  d('SSC Annual Departmental Stenography Test 2024 — Result','Uploaded: 09/09/2026','https://ssc.gov.in/',{vacancy:'Departmental examination result',dates:'Result notice: 09/09/2026',selection:'As prescribed by SSC'})
 ],
 answer:[
  d('SSC Assistant Section Officer / Assistant Grade LDCE 2025 — Tentative Answer Key','Uploaded: 09/09/2026','https://ssc.gov.in/',{vacancy:'Departmental competitive examination',dates:'Tentative answer key notice: 09/09/2026'}),
  d('SSC Senior Secretariat Assistant / UDC LDCE 2025 — Tentative Answer Key','Uploaded: 09/09/2026','https://ssc.gov.in/',{vacancy:'Departmental competitive examination',dates:'Tentative answer key notice: 09/09/2026'}),
  d('SSC Junior Secretariat Assistant / LDC LDCE 2025 — Tentative Answer Key','Uploaded: 09/09/2026','https://ssc.gov.in/',{vacancy:'Departmental competitive examination',dates:'Tentative answer key notice: 09/09/2026'}),
  d('SSC Senior Secretariat Assistant / UDC LDCE 2025 (CSCS) — Tentative Answer Key','Uploaded: 09/09/2026','https://ssc.gov.in/',{vacancy:'Departmental competitive examination',dates:'Tentative answer key notice: 09/09/2026'})
 ],
 admission:[
  d('UPSC Annual Calendar 2027 — Examination planning update','Current official update','https://www.upsc.gov.in/highlight',{vacancy:'Not applicable — examination calendar',dates:'Annual Calendar 2027: current UPSC highlight',selection:'Refer to each examination notification'}),
  d('SSC Examination Calendar — 2026 schedule','Current official calendar','https://ssc.gov.in/',{vacancy:'Not applicable — examination calendar',dates:'SSC 2026–27 tentative calendar',selection:'Refer to individual SSC notices'}),
  d('SSC Combined Higher Secondary (10+2) Level Examination 2026 — Notification','Applications close: 07/10/2026','https://ssc.gov.in/',{vacancy:'Group C posts',dates:'Online application last date: 07/10/2026; fee payment: 08/10/2026',eligibility:'See official SSC recruitment notice',fee:'See official SSC recruitment notice',age:'See official SSC recruitment notice',selection:'See official SSC examination scheme'})
 ],
 scholarship:[
  d('National Scholarship Portal 2026-27 — Portal Open','Student applications are open from 01/06/2026','https://scholarships.gov.in/Students',{vacancy:'Scholarship applications',dates:'Academic year 2026-27; portal open from 01/06/2026',eligibility:'Scheme-specific — verify on NSP',selection:'Scheme-specific verification and approval'}),
  d('PM-USP Central Sector Scholarship — Renewal','Student application closes 31/10/2026','https://scholarships.gov.in/All-Scholarships',{dates:'Student application closes: 31/10/2026',eligibility:'Scheme-specific — verify on NSP'}),
  d('AICTE Pragati / Saksham / Swanath Scholarships','Student application closes 31/10/2026','https://scholarships.gov.in/All-Scholarships',{dates:'Student application closes: 31/10/2026',eligibility:'Scheme-specific — verify on NSP'}),
  d('National Means-cum-Merit Scholarship','Student application closes 30/09/2026','https://scholarships.gov.in/All-Scholarships',{dates:'Student application closes: 30/09/2026',eligibility:'Scheme-specific — verify on NSP'}),
  d('Pre-Matric Scholarship for Students with Disabilities','Student application closes 30/09/2026','https://scholarships.gov.in/All-Scholarships',{dates:'Student application closes: 30/09/2026',eligibility:'Scheme-specific — verify on NSP'})
 ],
 syllabus:[
  d('SSC Junior Engineer Examination 2026 — Syllabus & exam resources','Official examination resources','https://ssc.gov.in/',{vacancy:'Examination information',selection:'Refer to the current SSC scheme and syllabus'}),
  d('SSC CGL 2026 — Examination resources','Official examination resources','https://ssc.gov.in/',{vacancy:'Examination information',selection:'Refer to the current SSC scheme and syllabus'}),
  d('UPSC Active Examinations 2026 — Official information','Official examination information','https://www.upsc.gov.in/hi/examinations/active-exams',{vacancy:'Examination information',selection:'Refer to the individual UPSC examination notification'})
 ],
 important:[
  d('SSC Sub-Inspector in Delhi Police & CAPFs Examination 2026 — Notice','New: 10/09/2026','https://ssc.gov.in/',{vacancy:'Sub-Inspector recruitment examination',dates:'Notice: 10/09/2026',eligibility:'See official SSC notice',fee:'See official SSC notice',age:'See official SSC notice',selection:'See official SSC examination scheme'}),
  d('SSC Junior Engineer Examination 2026 — Addendum Notice','New: 10/09/2026','https://ssc.gov.in/',{vacancy:'Junior Engineer examination',dates:'Addendum: 10/09/2026',selection:'See official SSC examination scheme'}),
  d('SSC Combined Higher Secondary (10+2) Level Examination 2026 — Notification','New: 07/09/2026','https://ssc.gov.in/',{vacancy:'Group C posts',dates:'Applications close: 07/10/2026; fee payment: 08/10/2026',eligibility:'See official SSC recruitment notice',fee:'See official SSC recruitment notice',age:'See official SSC recruitment notice',selection:'See official SSC examination scheme'}),
  d('SSC Combined Hindi Translators Examination 2025 — Final Vacancies','Updated: 08/09/2026','https://ssc.gov.in/',{vacancy:'Final vacancies updated',dates:'Updated: 08/09/2026',selection:'See official SSC notice'}),
  d('UPSC candidates — Face Authentication advisory','Current official advisory','https://www.upsc.gov.in/highlight',{vacancy:'Not applicable — candidate advisory',dates:'Current UPSC advisory',eligibility:'Applies to candidates appearing in UPSC examinations',selection:'Follow venue instructions in the official advisory'}),
  d('UPSC Annual Calendar 2027','Current official highlight','https://www.upsc.gov.in/highlight',{vacancy:'Not applicable — annual calendar',dates:'Annual Calendar 2027',selection:'Refer to individual examination notifications'})
 ]
};
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function injectSearch(){
 var section=document.querySelector('.grid');if(!section||document.getElementById('osUpdateSearch'))return;
 var box=document.createElement('div');box.id='osUpdateSearch';box.style.cssText='grid-column:1/-1;display:flex;gap:10px;flex-wrap:wrap;margin-bottom:4px';
 box.innerHTML='<input id="osSearchInput" type="search" placeholder="🔎 Search jobs, results, admit cards, scholarships…" style="flex:1;min-width:240px;padding:13px 15px;border:1px solid #d8e3f5;border-radius:12px;font-size:14px;outline:none"><select id="osCategoryFilter" style="padding:13px 15px;border:1px solid #d8e3f5;border-radius:12px;background:#fff;color:#18325d;font-weight:700"><option value="all">All Categories</option><option value="jobs">Latest Jobs</option><option value="admit">Admit Card</option><option value="results">Results</option><option value="answer">Answer Key</option><option value="admission">Admission</option><option value="scholarship">Scholarship</option><option value="syllabus">Syllabus</option><option value="important">Important</option></select>';
 section.parentNode.insertBefore(box,section);
 var input=document.getElementById('osSearchInput'),filter=document.getElementById('osCategoryFilter');
 function apply(){var q=input.value.toLowerCase().trim(),cat=filter.value;Object.keys(DATA).forEach(function(id){var panel=document.getElementById(id);if(!panel)return;panel.style.display=(cat==='all'||cat===id)?'block':'none';if(cat!=='all'&&cat!==id)return;panel.querySelectorAll('li').forEach(function(li){var text=li.textContent.toLowerCase();li.style.display=(!q||text.indexOf(q)!==-1)?'block':'none';});});}
 input.addEventListener('input',apply);filter.addEventListener('change',apply);
}
function openDetail(x){var modal=document.getElementById('updateModal');if(!modal)return;document.getElementById('detailTitle').textContent=x.title;document.getElementById('detailMeta').textContent=x.meta||'';var fields=[['Post / Vacancy',x.vacancy],['Important Dates',x.dates],['Eligibility',x.eligibility],['Application Fee',x.fee],['Age Limit',x.age],['Selection Process',x.selection]];document.getElementById('detailGrid').innerHTML=fields.map(function(f){return '<div class="detail-box"><strong>'+esc(f[0])+'</strong><span>'+esc(f[1]||NA)+'</span></div>';}).join('');document.getElementById('officialNotice').href=x.noticeUrl||x.url;document.getElementById('applyLink').href=x.applyUrl||x.url;modal.classList.add('show');document.body.style.overflow='hidden';}
function closeDetail(){var modal=document.getElementById('updateModal');if(modal)modal.classList.remove('show');document.body.style.overflow='';}
function render(id,items){var panel=document.getElementById(id);if(!panel)return;var ul=panel.querySelector('.list');if(!ul)return;ul.innerHTML=items.map(function(x,i){return '<li>'+(i===0?'<span class="tag">OFFICIAL</span>':'')+'<a href="#" class="item os-update-item" data-update-id="'+esc(id+'-'+i)+'">'+esc(x.title)+'</a><small style="display:block;color:#60708d;font-size:11px;margin-top:3px">'+esc(x.meta)+'</small></li>';}).join('');}
function run(){render('jobs',DATA.jobs);render('admit',DATA.admit);render('results',DATA.results);render('answer',DATA.answer);render('admission',DATA.admission);render('scholarship',DATA.scholarship);render('syllabus',DATA.syllabus);render('important',DATA.important);injectSearch();Object.keys(DATA).forEach(function(id){DATA[id].forEach(function(x,i){var el=document.querySelector('[data-update-id="'+id+'-'+i+'"]');if(el)el.addEventListener('click',function(e){e.preventDefault();openDetail(x);});});});var close=document.getElementById('closeModal');if(close)close.addEventListener('click',closeDetail);var modal=document.getElementById('updateModal');if(modal)modal.addEventListener('click',function(e){if(e.target===modal)closeDetail();});document.addEventListener('keydown',function(e){if(e.key==='Escape')closeDetail();});}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
})();