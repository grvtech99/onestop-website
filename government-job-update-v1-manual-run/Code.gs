/**
 * ONESTOP Job Update V1 — STANDALONE TEST BACKEND
 *
 * IMPORTANT:
 * - This project is intentionally separate from the legacy Government Job Update system.
 * - V1 is MANUAL RUN / TEST MODE only.
 * - There is NO live website publishing in this version.
 * - Public production integration will be added only after the manual workflow is validated.
 */

const CONFIG = {
  SHEET_ID: '', // <-- add your Google Sheet ID after creating the V1 database sheet
  JOBS_SHEET: 'Jobs',
  FIELDS_SHEET: 'Fields',
  LINKS_SHEET: 'Links',
  TABLES_SHEET: 'Tables',
  ADMIN_KEY: 'CHANGE_THIS_TEST_KEY'
};

const DEFAULT_FIELDS = [
  ['Organization / Authority','Short Text','Job Information',true,true,1],
  ['Recruitment Name','Short Text','Job Information',true,true,2],
  ['Advertisement No.','Short Text','Job Information',false,true,3],
  ['Total Vacancy','Number','Job Information',true,true,4],
  ['Application Start Date','Date','Important Dates',false,true,10],
  ['Last Date to Apply','Date','Important Dates',true,true,11],
  ['Fee Payment Last Date','Date','Important Dates',false,true,12],
  ['Correction Last Date','Date','Important Dates',false,true,13],
  ['Exam Date','Short Text','Important Dates',false,true,14],
  ['Admit Card Date','Short Text','Important Dates',false,true,15],
  ['Result Date','Short Text','Important Dates',false,true,16],
  ['Application Fee','Long Text','Application Fee',false,true,20],
  ['Minimum Age','Short Text','Age Limit',false,true,30],
  ['Maximum Age','Short Text','Age Limit',false,true,31],
  ['Age Calculate As On','Date','Age Limit',false,true,32],
  ['Age Relaxation','Long Text','Age Limit',false,true,33],
  ['Qualification / Eligibility','Long Text','Eligibility',false,true,40],
  ['Salary / Pay Scale','Long Text','Job Information',false,true,41],
  ['Selection Process','Long Text','Selection',false,true,42],
  ['Job Location','Short Text','Job Information',false,true,43],
  ['Application Mode','Short Text','Job Information',false,true,44],
  ['How to Apply','Long Text','How to Apply',false,true,50],
  ['Documents Required','Long Text','How to Apply',false,true,51]
];

function doGet(e) {
  const action = (e && e.parameter && e.parameter.action) || 'health';
  if (action === 'health') return json_({ok:true, mode:'TEST', service:'ONESTOP Job Update V1'});
  if (action === 'latest') return json_(latest_());
  if (action === 'fields') return json_(getFields_());
  if (action === 'bootstrap') return json_(bootstrap_());
  return json_({ok:false,error:'Unknown action'});
}

function doPost(e) {
  try {
    const body = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    if (body.action === 'crawlUrl') return json_(crawlUrl_(body));
    if (body.action === 'saveDraft') return json_(saveDraft_(body));
    if (body.action === 'publishTest') return json_(publishTest_(body));
    if (body.action === 'saveFields') return json_(saveFields_(body));
    return json_({ok:false,error:'Unknown action'});
  } catch (err) {
    return json_({ok:false,error:String(err && err.message || err)});
  }
}

function auth_(body) {
  if (CONFIG.ADMIN_KEY && body.key !== CONFIG.ADMIN_KEY) {
    return {ok:false,error:'Invalid test admin key.'};
  }
  return {ok:true};
}

function crawlUrl_(body) {
  if (!body.url || !/^https?:\\/\\//i.test(body.url)) return {ok:false,error:'Valid http/https URL required.'};
  const r = UrlFetchApp.fetch(body.url, {muteHttpExceptions:true,followRedirects:true,headers:{'User-Agent':'ONESTOP Job Update V1'}});
  const code = r.getResponseCode();
  if (code < 200 || code >= 400) return {ok:false,error:'Source returned HTTP '+code};
  const html = r.getContentText();
  const text = html
    .replace(/<script[\\s\\S]*?<\\/script>/gi,' ')
    .replace(/<style[\\s\\S]*?<\\/style>/gi,' ')
    .replace(/<[^>]+>/g,'\\n')
    .replace(/&nbsp;/gi,' ')
    .replace(/&amp;/gi,'&')
    .replace(/&lt;/gi,'<')
    .replace(/&gt;/gi,'>')
    .replace(/\\r/g,'')
    .replace(/[ \\t]+/g,' ')
    .replace(/\\n\\s*\\n+/g,'\\n')
    .trim();
  return {ok:true,url:body.url,status:code,text:text.slice(0,150000)};
}

function saveDraft_(body) {
  const auth = auth_(body);
  if (!auth.ok) return auth;
  if (!body.record || !body.record.fields) return {ok:false,error:'Vacancy record missing.'};
  const record = normalizeRecord_(body.record,'DRAFT');
  writeJob_(record);
  return {ok:true,id:record.id,status:record.status,updatedAt:record.updatedAt};
}

function publishTest_(body) {
  const auth = auth_(body);
  if (!auth.ok) return auth;
  if (!body.record || !body.record.fields) return {ok:false,error:'Vacancy record missing.'};
  const record = normalizeRecord_(body.record,'PUBLISHED_TEST');
  PropertiesService.getScriptProperties().setProperty('LATEST_TEST_RECORD',JSON.stringify(record));
  writeJob_(record);
  return {ok:true,id:record.id,status:record.status,publishedAt:record.publishedAt};
}

function normalizeRecord_(input,status) {
  const record = JSON.parse(JSON.stringify(input));
  record.id = record.id || Utilities.getUuid();
  record.status = status;
  record.createdAt = record.createdAt || new Date().toISOString();
  record.updatedAt = new Date().toISOString();
  if (status === 'PUBLISHED_TEST') record.publishedAt = new Date().toISOString();
  return record;
}

function latest_() {
  const raw = PropertiesService.getScriptProperties().getProperty('LATEST_TEST_RECORD');
  return raw ? JSON.parse(raw) : {ok:true,record:null};
}

function bootstrap_() {
  const fields = getFields_();
  return {ok:true,mode:'TEST',fields:fields.fields,defaultsLoaded:fields.defaultsLoaded};
}

function getFields_() {
  if (!CONFIG.SHEET_ID) return {ok:true,fields:DEFAULT_FIELDS,defaultsLoaded:true};
  const ss = SpreadsheetApp.openById(CONFIG.SHEET_ID);
  const sh = ss.getSheetByName(CONFIG.FIELDS_SHEET);
  if (!sh || sh.getLastRow() < 2) return {ok:true,fields:DEFAULT_FIELDS,defaultsLoaded:true};
  const values = sh.getDataRange().getValues();
  const fields = values.slice(1).filter(r=>r[0]).map(r=>[String(r[0]),String(r[1]||'Short Text'),String(r[2]||'Job Information'),Boolean(r[3]),r[4] !== false,Number(r[5]||999)]);
  return {ok:true,fields:fields.length?fields:DEFAULT_FIELDS,defaultsLoaded:false};
}

function saveFields_(body) {
  const auth = auth_(body);
  if (!auth.ok) return auth;
  if (!Array.isArray(body.fields)) return {ok:false,error:'fields must be an array'};
  if (!CONFIG.SHEET_ID) {
    PropertiesService.getScriptProperties().setProperty('CUSTOM_FIELDS',JSON.stringify(body.fields));
    return {ok:true,count:body.fields.length,storage:'script-properties'};
  }
  const ss = SpreadsheetApp.openById(CONFIG.SHEET_ID);
  const sh = ss.getSheetByName(CONFIG.FIELDS_SHEET) || ss.insertSheet(CONFIG.FIELDS_SHEET);
  sh.clearContents();
  sh.getRange(1,1,1,6).setValues([['field_name','field_type','section','required','public_visible','display_order']]);
  const rows = body.fields.map(f=>[f[0]||'',f[1]||'Short Text',f[2]||'Job Information',!!f[3],f[4] !== false,Number(f[5]||999)]);
  if (rows.length) sh.getRange(2,1,rows.length,6).setValues(rows);
  return {ok:true,count:rows.length,storage:'sheet'};
}

function writeJob_(record) {
  if (!CONFIG.SHEET_ID) return;
  const ss = SpreadsheetApp.openById(CONFIG.SHEET_ID);
  const sh = ss.getSheetByName(CONFIG.JOBS_SHEET) || ss.insertSheet(CONFIG.JOBS_SHEET);
  if (sh.getLastRow() === 0) {
    sh.appendRow(['id','status','createdAt','updatedAt','publishedAt','title','organization','lastDate','recordJson']);
  }
  const f = record.fields || [];
  const value = function(name){ const hit=f.find(x=>x[0]===name); return hit ? hit[1] : ''; };
  sh.appendRow([
    record.id,record.status,record.createdAt,record.updatedAt,record.publishedAt||'',
    value('Recruitment Name'),value('Organization / Authority'),value('Last Date to Apply'),JSON.stringify(record)
  ]);
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
