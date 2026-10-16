/**
 * Gaurav's World — Google Sheets CMS Sync
 * Runs inside the same secure Apps Script project as Code.gs.
 *
 * Required Script Property:
 *   GAURAVS_WORLD_SHEET_ID = Google Spreadsheet ID
 *
 * Flow:
 *   Google Sheet (NEW row) -> secure Admin -> GitHub draft -> Admin review -> Publish
 *
 * The Sheet is never exposed to the public GitHub Pages site.
 */

const GW_SYNC_SHEETS_ = [
  'CONTENT',
  'JOBS',
  'RESULTS',
  'ADMISSIONS',
  'ANSWER_KEY',
  'ADMIT_CARD',
  'EXAM_DATES',
  'SCHEMES',
  'SCHOLARSHIPS'
];

const GW_SYNC_STATUSES_ = ['NEW', 'REVIEW'];

function sheetSyncHealth() {
  assertAdmin_();
  const id = String(PropertiesService.getScriptProperties().getProperty('GAURAVS_WORLD_SHEET_ID') || '').trim();
  if (!id) return { ok: true, configured: false, spreadsheetName: '', pending: 0 };

  const ss = SpreadsheetApp.openById(id);
  const pending = sheetPendingCount_(ss);
  return {
    ok: true,
    configured: true,
    spreadsheetIdMasked: id.slice(0, 6) + '…' + id.slice(-4),
    spreadsheetName: ss.getName(),
    pending: pending
  };
}

function configureSheetSync(spreadsheetId) {
  assertAdmin_();
  const id = String(spreadsheetId || '').trim();
  if (!/^[A-Za-z0-9_-]{20,}$/.test(id)) throw new Error('Invalid Google Spreadsheet ID');
  const ss = SpreadsheetApp.openById(id);
  PropertiesService.getScriptProperties().setProperty('GAURAVS_WORLD_SHEET_ID', id);
  return { ok: true, spreadsheetName: ss.getName(), pending: sheetPendingCount_(ss) };
}

function previewSheetSync() {
  assertAdmin_();
  const ss = getContentSpreadsheet_();
  const rows = collectSheetRows_(ss);
  return { ok: true, spreadsheetName: ss.getName(), rows: rows };
}

function syncSheetToDrafts() {
  assertAdmin_();
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const ss = getContentSpreadsheet_();
    const rows = collectSheetRows_(ss);
    const imported = [];
    const skipped = [];
    const errors = [];

    rows.forEach(item => {
      if (!GW_SYNC_STATUSES_.includes(item.status)) {
        skipped.push({ sheet: item.sheet, row: item.rowNumber, reason: 'Status is not NEW/REVIEW' });
        return;
      }

      try {
        const article = sheetRowToArticle_(item);
        const draft = normalize_(article);
        draft.status = 'draft';
        draft.source = 'google-sheet';
        draft.sourceSheet = item.sheet;
        draft.sourceRow = item.rowNumber;
        draft.sourceId = item.sourceId;
        draft.updatedAt = new Date().toISOString();

        const r = githubPutJson_(
          'gauravs-world/data/drafts/' + draft.slug + '.json',
          draft,
          'Import Google Sheet draft: ' + draft.slug
        );

        markSheetRowSynced_(item, draft.id);
        imported.push({
          sheet: item.sheet,
          row: item.rowNumber,
          sourceId: item.sourceId,
          slug: draft.slug,
          title: draft.title,
          commit: r.commit
        });
      } catch (e) {
        errors.push({
          sheet: item.sheet,
          row: item.rowNumber,
          sourceId: item.sourceId,
          message: safeMessage_(e)
        });
      }
    });

    return {
      ok: errors.length === 0,
      imported: imported,
      skipped: skipped,
      errors: errors,
      total: rows.length
    };
  } finally {
    lock.releaseLock();
  }
}

function getContentSpreadsheet_() {
  const id = String(PropertiesService.getScriptProperties().getProperty('GAURAVS_WORLD_SHEET_ID') || '').trim();
  if (!id) throw new Error('Google Sheet is not configured. Add the Spreadsheet ID first.');
  try {
    return SpreadsheetApp.openById(id);
  } catch (e) {
    throw new Error('Google Sheet could not be opened. Check the Spreadsheet ID and access.');
  }
}

function collectSheetRows_(ss) {
  const out = [];
  GW_SYNC_SHEETS_.forEach(name => {
    const sheet = ss.getSheetByName(name);
    if (!sheet) return;

    const range = sheet.getDataRange();
    const values = range.getDisplayValues();
    if (!values.length) return;

    const headers = values[0].map(v => String(v || '').trim());
    if (!headers.length) return;

    const index = {};
    headers.forEach((h, i) => { if (h) index[h] = i; });

    for (let r = 1; r < values.length; r++) {
      const row = values[r];
      if (row.every(v => String(v || '').trim() === '')) continue;

      const obj = {};
      headers.forEach((h, i) => { obj[h] = String(row[i] || '').trim(); });

      const status = String(obj.status || '').toUpperCase();
      if (!status) continue;

      const sourceId = firstNonEmpty_(
        obj.contentId, obj.jobId, obj.resultId, obj.admissionId,
        obj.answerKeyId, obj.admitCardId, obj.examId,
        obj.schemeId, obj.scholarshipId
      ) || (name.toLowerCase() + '-row-' + (r + 1));

      out.push({
        sheet: name,
        rowNumber: r + 1,
        headers: headers,
        index: index,
        data: obj,
        status: status,
        sourceId: sourceId
      });
    }
  });
  return out;
}

function sheetPendingCount_(ss) {
  return collectSheetRows_(ss).filter(x => GW_SYNC_STATUSES_.includes(x.status)).length;
}

function sheetRowToArticle_(item) {
  const d = item.data;
  const type = item.sheet;

  if (type === 'CONTENT') {
    const title = d.title;
    const rawSlug = String(d.slug || '').trim().toLowerCase();
    const slug = /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(rawSlug)
      ? rawSlug
      : sheetSlug_(title, d.contentId || item.rowNumber);
    if (!title) throw new Error('CONTENT row needs title');
    if (!d.content) throw new Error('CONTENT row needs content');

    return {
      slug: slug,
      title: title,
      category: d.category || 'Technology',
      summary: d.summary || d.hook || '',
      bodyMarkdown: d.content,
      image: d.heroImage || '',
      tags: csv_(d.tags),
      author: d.author || 'Gaurav'
    };
  }

  const meta = {
    JOBS: { category: 'Jobs', id: 'jobId', title: d.postName || d.title || d.organization || 'Job Update' },
    RESULTS: { category: 'Results', id: 'resultId', title: (d.examName || 'Exam') + ' Result' },
    ADMISSIONS: { category: 'Admissions', id: 'admissionId', title: d.title || 'Admission Update' },
    ANSWER_KEY: { category: 'Answer Key', id: 'answerKeyId', title: (d.examName || 'Exam') + ' Answer Key' },
    ADMIT_CARD: { category: 'Admit Card', id: 'admitCardId', title: (d.examName || 'Exam') + ' Admit Card' },
    EXAM_DATES: { category: 'Exam Dates', id: 'examId', title: d.examName || 'Exam Date Update' },
    SCHEMES: { category: 'Schemes', id: 'schemeId', title: d.title || 'Government Scheme' },
    SCHOLARSHIPS: { category: 'Scholarships', id: 'scholarshipId', title: d.title || 'Scholarship Update' }
  }[type];

  if (!meta) throw new Error('Unsupported sheet: ' + type);

  const title = meta.title;
  const slug = sheetSlug_(title, d[meta.id] || item.sourceId);
  const summary = buildSummary_(type, d);
  const bodyMarkdown = buildStructuredMarkdown_(type, d);

  return {
    slug: slug,
    title: title,
    category: meta.category,
    summary: summary,
    bodyMarkdown: bodyMarkdown,
    image: '',
    tags: [meta.category, 'Gaurav\'s World'],
    author: 'Gaurav'
  };
}

function buildSummary_(type, d) {
  switch (type) {
    case 'JOBS':
      return [d.organization, d.postName, d.applicationLastDate ? 'Last date: ' + d.applicationLastDate : ''].filter(Boolean).join(' · ');
    case 'RESULTS':
      return [d.organization, d.examName, d.resultDate ? 'Result: ' + d.resultDate : ''].filter(Boolean).join(' · ');
    case 'ADMISSIONS':
      return [d.organization, d.course, d.lastDate ? 'Last date: ' + d.lastDate : ''].filter(Boolean).join(' · ');
    case 'ANSWER_KEY':
      return [d.organization, d.examName, d.answerKeyDate ? 'Answer key: ' + d.answerKeyDate : ''].filter(Boolean).join(' · ');
    case 'ADMIT_CARD':
      return [d.examName, d.examDate ? 'Exam: ' + d.examDate : '', d.admitCardDate ? 'Admit card: ' + d.admitCardDate : ''].filter(Boolean).join(' · ');
    case 'EXAM_DATES':
      return [d.organization, d.examName, d.examDate ? 'Exam: ' + d.examDate : ''].filter(Boolean).join(' · ');
    case 'SCHEMES':
      return [d.department, d.eligibility, d.lastDate ? 'Last date: ' + d.lastDate : ''].filter(Boolean).join(' · ');
    case 'SCHOLARSHIPS':
      return [d.provider, d.eligibility, d.amount ? 'Amount: ' + d.amount : ''].filter(Boolean).join(' · ');
    default:
      return '';
  }
}

function buildStructuredMarkdown_(type, d) {
  const hidden = {
    status: true, adminId: true, updatedAt: true,
    contentId: true, jobId: true, resultId: true, admissionId: true,
    answerKeyId: true, admitCardId: true, examId: true, schemeId: true,
    scholarshipId: true
  };

  const labels = {
    applicationStart: 'Application Start',
    applicationLastDate: 'Last Date',
    applicationFee: 'Application Fee',
    applyLink: 'Apply Link',
    notificationLink: 'Official Notification',
    resultDate: 'Result Date',
    resultLink: 'Result Link',
    startDate: 'Start Date',
    lastDate: 'Last Date',
    fee: 'Fee',
    answerKeyDate: 'Answer Key Date',
    answerKeyLink: 'Answer Key Link',
    objectionStart: 'Objection Start',
    objectionLastDate: 'Objection Last Date',
    objectionLink: 'Objection Link',
    examDate: 'Exam Date',
    admitCardDate: 'Admit Card Date',
    downloadLink: 'Download Link',
    officialLink: 'Official Link',
    amount: 'Amount',
    postName: 'Post Name',
    totalPosts: 'Total Posts',
    qualification: 'Qualification',
    ageLimit: 'Age Limit',
    organization: 'Organization',
    department: 'Department',
    provider: 'Provider',
    course: 'Course',
    eligibility: 'Eligibility',
    benefits: 'Benefits',
    instructions: 'Instructions',
    shift: 'Shift',
    details: 'Details'
  };

  const lines = ['## Important Details', ''];

  Object.keys(d).forEach(key => {
    if (hidden[key]) return;
    const value = String(d[key] || '').trim();
    if (!value) return;

    const label = labels[key] || humanize_(key);
    if (/link$/i.test(key) || key === 'applyLink' || key === 'officialLink' || key === 'downloadLink') {
      lines.push('- **' + label + ':** ' + value);
    } else {
      lines.push('- **' + label + ':** ' + value.replace(/\n+/g, '\n  '));
    }
  });

  return lines.join('\n');
}

function markSheetRowSynced_(item, contentId) {
  const sheet = getContentSpreadsheet_().getSheetByName(item.sheet);
  if (!sheet) throw new Error('Sheet disappeared: ' + item.sheet);

  const statusCol = item.index.status !== undefined ? item.index.status + 1 : null;
  const adminCol = item.index.adminId !== undefined ? item.index.adminId + 1 : null;
  const updatedCol = item.index.updatedAt !== undefined ? item.index.updatedAt + 1 : null;

  if (statusCol) sheet.getRange(item.rowNumber, statusCol).setValue('SYNCED');
  if (adminCol) sheet.getRange(item.rowNumber, adminCol).setValue(contentId);
  if (updatedCol) sheet.getRange(item.rowNumber, updatedCol).setValue(new Date());
  SpreadsheetApp.flush();
}

function sheetSlug_(title, id) {
  let base = String(title || 'content').toLowerCase()
    .replace(/&/g, ' and ')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-+/g, '-');

  if (!base) base = 'content';
  const suffix = String(id || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  if (suffix) base += '-' + suffix;
  return safeSlug_(base.slice(0, 100).replace(/-+$/g, ''));
}

function firstNonEmpty_() {
  for (let i = 0; i < arguments.length; i++) {
    const v = String(arguments[i] || '').trim();
    if (v) return v;
  }
  return '';
}

function csv_(v) {
  return String(v || '').split(',').map(x => x.trim()).filter(Boolean).slice(0, 15);
}

function humanize_(s) {
  return String(s || '')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}
