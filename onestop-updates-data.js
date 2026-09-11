/* ONESTOP Government Updates — official-source data layer
   Sources used here are official government portals. The UI remains ONESTOP-native.
*/
(function(){
'use strict';
var DATA={
 jobs:[
  ['Ramagundam Fertilizers & Chemicals Ltd — Engineer & Others','Last date: 24/09/2026','https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All'],
  ['NIPER Kolkata — Professor Recruitment','Last date: 17/09/2026','https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All'],
  ['National Disaster Management Authority — Young Consultant','Last date: 18/10/2026','https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All'],
  ['National Board of Examinations in Medical Sciences — Executive Director','Last date: 30/10/2026','https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All'],
  ['LBSNAA — Administrative Officer & Others','Last date: 11/09/2026','https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All'],
  ['Sainik School Ambikapur — Laboratory Assistant & Others','Last date: 12/09/2026','https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All'],
  ['BRIC-NIAB — Scientist-B & Others','Last date: 11/09/2026','https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All']
 ],
 admit:[
  ['UPSC NDA & NA II / CDS II 2026 — e-Admit Card available','Exam: 13/09/2026','https://www.upsc.gov.in/examinations/Combined%20Defence%20Services%20Examination%20%28II%29%2C%202026'],
  ['UPSC Engineering Services Main 2026 — Interview Schedule','Uploaded: 07/09/2026','https://www.upsc.gov.in/exams-related-info/interview-schedule'],
  ['UPSC Combined Geo-Scientist Main 2026 — Interview Schedule','Uploaded: 02/09/2026','https://www.upsc.gov.in/exams-related-info/interview-schedule']
 ],
 results:[
  ['UPSC Assistant Director Grade-II (IEDS), Leather & Footwear — Final Result','Uploaded: 09/09/2026','https://www.upsc.gov.in/recruitment/recruitment-test/results/final-result'],
  ['UPSC Assistant Director Grade-II (IEDS), Chemical — Final Result','Uploaded: 08/09/2026','https://www.upsc.gov.in/recruitment/recruitment-test/results/final-result'],
  ['SSC Annual Departmental Typing Test 2024 — Result','Uploaded: 09/09/2026','https://ssc.gov.in/'],
  ['SSC Annual Departmental Stenography Test 2024 — Result','Uploaded: 09/09/2026','https://ssc.gov.in/']
 ],
 answer:[
  ['SSC Assistant Section Officer / Assistant Grade LDCE 2025 — Tentative Answer Key','Uploaded: 09/09/2026','https://ssc.gov.in/'],
  ['SSC Senior Secretariat Assistant / UDC LDCE 2025 — Tentative Answer Key','Uploaded: 09/09/2026','https://ssc.gov.in/'],
  ['SSC Junior Secretariat Assistant / LDC LDCE 2025 — Tentative Answer Key','Uploaded: 09/09/2026','https://ssc.gov.in/'],
  ['SSC Senior Secretariat Assistant / UDC LDCE 2025 (CSCS) — Tentative Answer Key','Uploaded: 09/09/2026','https://ssc.gov.in/']
 ],
 admission:[
  ['UPSC Annual Calendar 2027 — Examination planning update','Current official update','https://www.upsc.gov.in/highlight'],
  ['SSC Examination Calendar — 2026 schedule','Current official calendar','https://ssc.gov.in/']
 ],
 scholarship:[
  ['National Scholarship Portal 2026-27 — Portal Open','Student applications are open from 01/06/2026','https://scholarships.gov.in/Students'],
  ['PM-USP Central Sector Scholarship — Renewal','Student application closes 31/10/2026','https://scholarships.gov.in/All-Scholarships'],
  ['AICTE Pragati / Saksham / Swanath Scholarships','Student application closes 31/10/2026','https://scholarships.gov.in/All-Scholarships'],
  ['National Means-cum-Merit Scholarship','Student application closes 30/09/2026','https://scholarships.gov.in/All-Scholarships'],
  ['Pre-Matric Scholarship for Students with Disabilities','Student application closes 30/09/2026','https://scholarships.gov.in/All-Scholarships']
 ],
 syllabus:[
  ['SSC Junior Engineer Examination 2026 — Syllabus & exam resources','Official examination resources','https://ssc.gov.in/'],
  ['SSC CGL 2026 — Examination resources','Official examination resources','https://ssc.gov.in/'],
  ['UPSC Active Examinations 2026 — Official information','Official examination information','https://www.upsc.gov.in/hi/examinations/active-exams']
 ],
 important:[
  ['SSC Sub-Inspector in Delhi Police & CAPFs Examination 2026 — Notice','New: 10/09/2026','https://ssc.gov.in/'],
  ['SSC Junior Engineer Examination 2026 — Addendum Notice','New: 10/09/2026','https://ssc.gov.in/'],
  ['SSC Combined Hindi Translators Examination 2025 — Final Vacancies','Updated: 08/09/2026','https://ssc.gov.in/'],
  ['UPSC candidates — Face Authentication advisory','Current official advisory','https://www.upsc.gov.in/highlight'],
  ['UPSC Annual Calendar 2027','Current official highlight','https://www.upsc.gov.in/highlight']
 ]
};
function esc(s){return String(s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function render(id,items){var panel=document.getElementById(id);if(!panel)return;var ul=panel.querySelector('.list');if(!ul)return;ul.innerHTML=items.map(function(x,i){return '<li>'+(i===0?'<span class="tag">OFFICIAL</span>':'')+'<a class="item" href="'+esc(x[2])+'" target="_blank" rel="noopener noreferrer">'+esc(x[0])+'</a><small style="display:block;color:#60708d;font-size:11px;margin-top:3px">'+esc(x[1])+'</small></li>';}).join('');}
function run(){render('jobs',DATA.jobs);render('admit',DATA.admit);render('results',DATA.results);render('answer',DATA.answer);render('admission',DATA.admission);render('scholarship',DATA.scholarship);render('syllabus',DATA.syllabus);render('important',DATA.important);}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
})();
