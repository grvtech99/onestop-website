/**
 * Gaurav's World — Apps Script backend
 * Script Properties: ADMIN_EMAIL, OPENAI_API_KEY, OPENAI_MODEL,
 * GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO, GITHUB_BRANCH.
 * Deploy only to a verified admin identity. Never expose secrets in browser code.
 * Supports draft generation and guarded GitHub JSON article publishing.
 * Image upload is intentionally a separate next step (binary/base64 limits need testing).
 */
const MAX_REQUEST_CHARS = 12000;

function doGet() {
  try {
    assertAdmin_();
    return json_({ok:true, service:'gauravs-world-api', version:2,
      actions:['health','generateDraft','publishArticle']});
  } catch (err) { return json_({ok:false,error:safeMessage_(err)}); }
}

function doPost(e) {
  try {
    assertAdmin_();
    const raw = e && e.postData && e.postData.contents;
    if (typeof raw !== 'string' || !raw) throw new Error('Request body is required');
    if (raw.length > MAX_REQUEST_CHARS) throw new Error('Request body is too large');
    let body;
    try { body=JSON.parse(raw); } catch (_) { throw new Error('Invalid JSON request'); }
    if (!body || typeof body !== 'object' || Array.isArray(body)) throw new Error('Invalid request');
    if (body.action==='health') return json_({ok:true,service:'gauravs-world-api',version:2});
    if (body.action==='generateDraft') return json_({ok:true,draft:generateDraft_(body)});
    if (body.action==='publishArticle') return json_({ok:true,published:publishArticle_(body)});
    throw new Error('Unsupported action');
  } catch (err) { return json_({ok:false,error:safeMessage_(err)}); }
}

function assertAdmin_() {
  const props=PropertiesService.getScriptProperties();
  const expected=String(props.getProperty('ADMIN_EMAIL')||'').trim().toLowerCase();
  const actual=String(Session.getActiveUser().getEmail()||'').trim().toLowerCase();
  if (!expected || !actual || actual!==expected) throw new Error('Unauthorized: admin identity could not be verified');
}

function generateDraft_(input) {
  const title=requiredText_(input.title,160,'title');
  const category=optionalText_(input.category,'General',80,'category');
  const language=optionalText_(input.language,'Hindi',30,'language');
  const notes=optionalText_(input.notes,'',4000,'notes');
  const props=PropertiesService.getScriptProperties();
  const apiKey=props.getProperty('OPENAI_API_KEY');
  const model=props.getProperty('OPENAI_MODEL')||'gpt-4.1-mini';
  if (!apiKey) throw new Error('Server configuration missing: OPENAI_API_KEY');
  const payload={model:model,instructions:'Write an original, useful blog article. Do not invent citations or factual claims. Return valid JSON only with keys summary, bodyMarkdown, tags. bodyMarkdown should use Markdown headings and practical steps.',input:'Language: '+language+'\nCategory: '+category+'\nTitle: '+title+'\nNotes: '+notes,text:{format:{type:'json_object'}}};
  const response=UrlFetchApp.fetch('https://api.openai.com/v1/responses',{method:'post',contentType:'application/json',headers:{Authorization:'Bearer '+apiKey},payload:JSON.stringify(payload),muteHttpExceptions:true});
  const code=response.getResponseCode();
  if(code<200||code>=300) throw new Error('OpenAI request failed (HTTP '+code+')');
  let result; try{result=JSON.parse(response.getContentText());}catch(_){throw new Error('Invalid response from OpenAI');}
  let draft; try{draft=JSON.parse(extractOutputText_(result));}catch(_){throw new Error('OpenAI returned invalid JSON');}
  if(!draft||typeof draft.summary!=='string'||typeof draft.bodyMarkdown!=='string') throw new Error('OpenAI returned an invalid draft structure');
  return {title:title,category:category,language:language,summary:draft.summary.slice(0,1200),bodyMarkdown:draft.bodyMarkdown.slice(0,30000),tags:Array.isArray(draft.tags)?draft.tags.slice(0,12).map(function(t){return String(t).slice(0,60);}):[]};
}

function publishArticle_(input) {
  const slug=requiredText_(input.slug,100,'slug').toLowerCase();
  if(!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) throw new Error('Slug must contain lowercase letters, numbers, and hyphens only');
  const title=requiredText_(input.title,160,'title');
  const category=optionalText_(input.category,'General',80,'category');
  const summary=requiredText_(input.summary,1200,'summary');
  const bodyMarkdown=requiredText_(input.bodyMarkdown,30000,'bodyMarkdown');
  const image=optionalText_(input.image,'',300,'image');
  if(image && !/^images\/[a-z0-9][a-z0-9._/-]*\.(png|jpe?g|webp)$/i.test(image)) throw new Error('Image must be a repository-relative path inside images/');
  if(image && image.split('/').indexOf('..')!==-1) throw new Error('Invalid image path');
  const article={id:slug,title:title,slug:slug,category:category,summary:summary,image:image,bodyMarkdown:bodyMarkdown,updatedAt:new Date().toISOString()};
  const path='gauravs-world/data/articles/'+slug+'.json';
  const result=githubPutJson_(path,article,'Publish Gaurav\'s World article: '+slug);
  return {slug:slug,path:path,commit:result.commit,htmlUrl:'https://onestopfzd.in/gauravs-world/article.html?id='+encodeURIComponent(slug)};
}

function githubPutJson_(path, data, message) {
  const props=PropertiesService.getScriptProperties();
  const token=props.getProperty('GITHUB_TOKEN');
  const owner=props.getProperty('GITHUB_OWNER');
  const repo=props.getProperty('GITHUB_REPO');
  const branch=props.getProperty('GITHUB_BRANCH')||'main';
  if(!token||!owner||!repo) throw new Error('Server configuration missing: GitHub settings');
  const api='https://api.github.com/repos/'+encodeURIComponent(owner)+'/'+encodeURIComponent(repo)+'/contents/'+path.split('/').map(encodeURIComponent).join('/');
  const headers={Authorization:'Bearer '+token,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'};
  let sha=null;
  const existing=UrlFetchApp.fetch(api+'?ref='+encodeURIComponent(branch),{method:'get',headers:headers,muteHttpExceptions:true});
  if(existing.getResponseCode()===200){try{sha=JSON.parse(existing.getContentText()).sha;}catch(_){throw new Error('Could not read existing GitHub file metadata');}}
  else if(existing.getResponseCode()!==404) throw new Error('GitHub lookup failed (HTTP '+existing.getResponseCode()+')');
  const payload={message:message,content:Utilities.base64Encode(JSON.stringify(data,null,2),Utilities.Charset.UTF_8),branch:branch};
  if(sha) payload.sha=sha;
  const response=UrlFetchApp.fetch(api,{method:'put',contentType:'application/json',headers:headers,payload:JSON.stringify(payload),muteHttpExceptions:true});
  const code=response.getResponseCode();
  if(code<200||code>=300) throw new Error('GitHub publish failed (HTTP '+code+')');
  const out=JSON.parse(response.getContentText());
  return {commit:out.commit&&out.commit.sha||'',contentUrl:out.content&&out.content.html_url||''};
}

function extractOutputText_(result){
  if(result&&typeof result.output_text==='string')return result.output_text;
  const output=result&&Array.isArray(result.output)?result.output:[];
  for(let i=0;i<output.length;i++){const content=Array.isArray(output[i].content)?output[i].content:[];for(let j=0;j<content.length;j++){if(content[j].type==='output_text'&&typeof content[j].text==='string')return content[j].text;}}
  throw new Error('No text output received from OpenAI');
}
function requiredText_(value,max,field){if(typeof value!=='string')throw new Error('Invalid '+field);const text=value.trim();if(!text||text.length>max)throw new Error('Invalid '+field+' length');return text;}
function optionalText_(value,fallback,max,field){if(value===undefined||value===null||value==='')return fallback;if(typeof value!=='string')throw new Error('Invalid '+field);const text=value.trim();if(text.length>max)throw new Error('Invalid '+field+' length');return text||fallback;}
function safeMessage_(err){const message=String(err&&err.message||'Request failed');if(/token|secret|api.?key|bearer/i.test(message))return 'Request failed; check server configuration.';return message.slice(0,240);}
function json_(value){return ContentService.createTextOutput(JSON.stringify(value)).setMimeType(ContentService.MimeType.JSON);}
