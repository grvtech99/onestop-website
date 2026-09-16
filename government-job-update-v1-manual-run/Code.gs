/** ONESTOP Job Update V1 — TEST BACKEND ONLY
 * Deploy as a Web App for URL extraction + test publication.
 * No legacy project/code is referenced here.
 */
const CONFIG = {
  SHEET_ID: '',
  SHEET_NAME: 'Vacancies',
  ADMIN_KEY: 'CHANGE_THIS_TEST_KEY'
};

function doGet(e) {
  const action = (e && e.parameter && e.parameter.action) || 'health';
  if (action === 'health') return json_({ ok: true, mode: 'TEST', service: 'ONESTOP Job Update V1' });
  if (action === 'latest') return json_(latest_());
  return json_({ ok: false, error: 'Unknown action' });
}

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents || '{}');
    if (body.action === 'crawlUrl') return json_(crawlUrl_(body));
    if (body.action === 'publishTest') return json_(publishTest_(body));
    return json_({ ok: false, error: 'Unknown action' });
  } catch (err) {
    return json_({ ok: false, error: String(err && err.message || err) });
  }
}

function crawlUrl_(body) {
  if (!body.url || !/^https?:\/\//i.test(body.url)) return { ok: false, error: 'Valid http/https URL required.' };
  const r = UrlFetchApp.fetch(body.url, { muteHttpExceptions: true, followRedirects: true });
  const code = r.getResponseCode();
  if (code < 200 || code >= 400) return { ok: false, error: 'Source returned HTTP ' + code };
  const html = r.getContentText();
  const text = html.replace(/<script[\s\S]*?<\/script>/gi, ' ').replace(/<style[\s\S]*?<\/style>/gi, ' ').replace(/<[^>]+>/g, '\n').replace(/&nbsp;/gi, ' ').replace(/&amp;/gi, '&').replace(/&lt;/gi, '<').replace(/&gt;/gi, '>').replace(/\r/g, '').replace(/[ \t]+/g, ' ');
  return { ok: true, url: body.url, status: code, text: text.slice(0, 100000) };
}

function publishTest_(body) {
  if (CONFIG.ADMIN_KEY && body.key !== CONFIG.ADMIN_KEY) return { ok: false, error: 'Invalid test admin key.' };
  if (!body.record || !body.record.fields) return { ok: false, error: 'Vacancy record missing.' };
  const id = Utilities.getUuid();
  const record = JSON.parse(JSON.stringify(body.record));
  record.id = id;
  record.status = 'PUBLISHED_TEST';
  record.publishedAt = new Date().toISOString();
  PropertiesService.getScriptProperties().setProperty('LATEST_TEST_RECORD', JSON.stringify(record));
  if (CONFIG.SHEET_ID) appendSheet_(record);
  return { ok: true, id: id, status: record.status, publishedAt: record.publishedAt };
}

function latest_() {
  const raw = PropertiesService.getScriptProperties().getProperty('LATEST_TEST_RECORD');
  return raw ? JSON.parse(raw) : { ok: true, record: null };
}

function appendSheet_(record) {
  const ss = SpreadsheetApp.openById(CONFIG.SHEET_ID);
  const sh = ss.getSheetByName(CONFIG.SHEET_NAME) || ss.insertSheet(CONFIG.SHEET_NAME);
  if (sh.getLastRow() === 0) sh.appendRow(['id', 'publishedAt', 'title', 'organization', 'recordJson']);
  const f = record.fields || [];
  const value = n => ((f.find(x => x[0] === n) || [ '', '' ])[1]);
  sh.appendRow([record.id, record.publishedAt, value('Recruitment Name'), value('Organization / Authority'), JSON.stringify(record)]);
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
