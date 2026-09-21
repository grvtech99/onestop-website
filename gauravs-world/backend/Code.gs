/**
 * Gaurav's World — Apps Script backend starter
 * Keep deployment restricted to a verified admin identity.
 * Script Properties: ADMIN_EMAIL, OPENAI_API_KEY, OPENAI_MODEL.
 * Never place secrets in HTML or client-side JavaScript.
 * Draft generation only; GitHub publishing is not implemented here.
 */

const MAX_REQUEST_CHARS = 12000;

function doGet() {
  try {
    assertAdmin_();
    return json_({ ok: true, service: 'gauravs-world-api', version: 1,
      actions: ['health', 'generateDraft'] });
  } catch (err) {
    return json_({ ok: false, error: safeMessage_(err) });
  }
}

function doPost(e) {
  try {
    assertAdmin_();
    const raw = e && e.postData && e.postData.contents;
    if (typeof raw !== 'string' || !raw) throw new Error('Request body is required');
    if (raw.length > MAX_REQUEST_CHARS) throw new Error('Request body is too large');
    let body;
    try { body = JSON.parse(raw); } catch (_) { throw new Error('Invalid JSON request'); }
    if (!body || typeof body !== 'object' || Array.isArray(body)) throw new Error('Invalid request');

    if (body.action === 'health') return json_({ ok: true, service: 'gauravs-world-api', version: 1 });
    if (body.action === 'generateDraft') return json_({ ok: true, draft: generateDraft_(body) });
    throw new Error('Unsupported action');
  } catch (err) {
    return json_({ ok: false, error: safeMessage_(err) });
  }
}

function assertAdmin_() {
  const props = PropertiesService.getScriptProperties();
  const expected = String(props.getProperty('ADMIN_EMAIL') || '').trim().toLowerCase();
  const actual = String(Session.getActiveUser().getEmail() || '').trim().toLowerCase();
  if (!expected || !actual || actual !== expected) {
    throw new Error('Unauthorized: admin identity could not be verified');
  }
}

function generateDraft_(input) {
  const title = requiredText_(input.title, 160, 'title');
  const category = optionalText_(input.category, 'General', 80, 'category');
  const language = optionalText_(input.language, 'Hindi', 30, 'language');
  const notes = optionalText_(input.notes, '', 4000, 'notes');
  const apiKey = PropertiesService.getScriptProperties().getProperty('OPENAI_API_KEY');
  const model = PropertiesService.getScriptProperties().getProperty('OPENAI_MODEL') || 'gpt-4.1-mini';
  if (!apiKey) throw new Error('Server configuration missing: OPENAI_API_KEY');

  const payload = {
    model: model,
    instructions: 'Write an original, useful blog article. Do not invent citations or factual claims. Return valid JSON only with keys: summary, bodyMarkdown, tags. bodyMarkdown should use Markdown headings and practical steps.',
    input: 'Language: ' + language + '\nCategory: ' + category + '\nTitle: ' + title + '\nNotes: ' + notes,
    text: { format: { type: 'json_object' } }
  };
  const response = UrlFetchApp.fetch('https://api.openai.com/v1/responses', {
    method: 'post', contentType: 'application/json',
    headers: { Authorization: 'Bearer ' + apiKey },
    payload: JSON.stringify(payload), muteHttpExceptions: true
  });
  const code = response.getResponseCode();
  if (code < 200 || code >= 300) throw new Error('OpenAI request failed (HTTP ' + code + ')');
  let result;
  try { result = JSON.parse(response.getContentText()); } catch (_) { throw new Error('Invalid response from OpenAI'); }
  const outputText = extractOutputText_(result);
  let draft;
  try { draft = JSON.parse(outputText); } catch (_) { throw new Error('OpenAI returned invalid JSON'); }
  if (!draft || typeof draft.summary !== 'string' || typeof draft.bodyMarkdown !== 'string') {
    throw new Error('OpenAI returned an invalid draft structure');
  }
  return {
    title: title,
    category: category,
    language: language,
    summary: draft.summary.slice(0, 1200),
    bodyMarkdown: draft.bodyMarkdown.slice(0, 30000),
    tags: Array.isArray(draft.tags) ? draft.tags.slice(0, 12).map(function(tag) { return String(tag).slice(0, 60); }) : []
  };
}

function extractOutputText_(result) {
  if (result && typeof result.output_text === 'string') return result.output_text;
  const output = (result && Array.isArray(result.output)) ? result.output : [];
  for (let i = 0; i < output.length; i++) {
    const content = Array.isArray(output[i].content) ? output[i].content : [];
    for (let j = 0; j < content.length; j++) {
      if (content[j].type === 'output_text' && typeof content[j].text === 'string') return content[j].text;
    }
  }
  throw new Error('No text output received from OpenAI');
}

function requiredText_(value, max, field) {
  if (typeof value !== 'string') throw new Error('Invalid ' + field);
  const text = value.trim();
  if (!text || text.length > max) throw new Error('Invalid ' + field + ' length');
  return text;
}

function optionalText_(value, fallback, max, field) {
  if (value === undefined || value === null || value === '') return fallback;
  if (typeof value !== 'string') throw new Error('Invalid ' + field);
  const text = value.trim();
  if (text.length > max) throw new Error('Invalid ' + field + ' length');
  return text || fallback;
}

function safeMessage_(err) {
  const message = String(err && err.message || 'Request failed');
  if (/token|secret|api.?key|bearer/i.test(message)) return 'Request failed; check server configuration.';
  return message.slice(0, 240);
}

function json_(value) {
  return ContentService.createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}
