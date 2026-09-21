/**
 * Gaurav's World — Apps Script backend
 * Script Properties: ADMIN_EMAIL, OPENAI_API_KEY, OPENAI_MODEL,
 * GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO, GITHUB_BRANCH.
 * Deploy only to a verified admin identity. Never expose secrets in browser code.
 */
const MAX_REQUEST_CHARS = 50000;

function doGet() {
  try { assertAdmin_(); return json_({ok:true,service:'gauravs-world-api',version:3,actions:['health','generateDraft','publishArticle']}); }
  catch (err) { return json_({ok:false,error:safeMessage_(err)}); }
}
function doPost(e) {
  try {
    assertAdmin_();
    const raw=e&&e.postData&&e.postData.contents;
    if(typeof raw!=='string'||!raw)throw new Error('Request body is required');
    if(raw.length>MAX_REQUEST_CHARS)throw new Error('Request body is too large');
    let body;try{body=JSON.parse(raw);}catch(_){throw new Error('Invalid JSON request');}
    if(!body||typeof body!=='object'||Array.isArray(body))throw new Error('Invalid request');
    if(body.action==='health')return json_({ok:true,service:'gauravs-world-api',version:3});
    if(body.action==='generateDraft')return json_({ok:true,draft:generateDraft_(body)});
    if(body.action==='publishArticle')return json_({ok:true,published:publishArticle_(body)});
    throw new Error('Unsupported action');
  }catch(err){return json_({ok:false,error:safeMessage_(err)});}
}
function assertAdmin_(){const p=PropertiesService.getScriptProperties();const expected=String(p.getProperty('ADMIN_EMAIL')||'').trim().toLowerCase();const actual=String(Session.getActiveUser().getEmail()||'').trim().toLowerCase();if(!expected||!actual||actual!==expected)throw new Error('Unauthorized: admin identity could not be verified');}
function generateDraft_(input){
 const title=requiredText_(input.title,160,'title'),category=optionalText_(input.category,'General',80,'category'),language=optionalText_(input.language,'Hindi',30,'language'),notes=optionalText_(input.notes,'',4000,'notes');
 const p=PropertiesService.getScriptProperties(),key=p.getProperty('OPENAI_API_KEY'),model=p.getProperty('OPENAI_MODEL')||'gpt-4.1-mini';if(!key)throw new Error('Server configuration missing: OPENAI_API_KEY');
 const payload={model:model,instructions:'Write an original, useful blog article. Do not invent citations or factual claims. Return valid JSON only with keys summary, bodyMarkdown, tags. bodyMarkdown should use Markdown headings and practical steps.',input:'Language: '+language+'\nCategory: '+category+'\nTitle: '+title+'\nNotes: '+notes,text:{format:{type:'json_object'}}};
 const r=UrlFetchApp.fetch('https://api.openai.com/v1/responses',{method:'post',contentType:'application/json',headers:{Authorization:'Bearer '+key},payload:JSON.stringify(payload),muteHttpExceptions:true});const code=r.getResponseCode();if(code<200||code>=300)throw new Error('OpenAI request failed (HTTP '+code+')');let out;try{out=JSON.parse(r.getContentText());}catch(_){throw new Error('Invalid response from OpenAI');}let d;try{d=JSON.parse(extractOutputText_(out));}catch(_){throw new Error('OpenAI returned invalid JSON');}if(!d||typeof d.summary!=='string'||typeof d.bodyMarkdown!=='string')throw new Error('OpenAI returned an invalid draft structure');return{title:title,category:category,language:language,summary:d.summary.slice(0,1200),bodyMarkdown:d.bodyMarkdown.slice(0,30000),tags:Array.isArray(d.tags)?d.tags.slice(0,12).map(t=>String(t).slice(0,60)):[]};
}
function publishArticle_(input){
 const slug=requiredText_(input.slug,100,'slug').toLowerCase();if(!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug))throw new Error('Slug must contain lowercase letters, numbers, and hyphens only');
 const title=requiredText_(input.title,160,'title'),category=optionalText_(input.category,'General',80,'category'),summary=requiredText_(input.summary,1200,'summary'),bodyMarkdown=requiredText_(input.bodyMarkdown,30000,'bodyMarkdown'),image=optionalText_(input.image,'',300,'image');
 if(image&&!/^images\/[a-z0-9][a-z0-9._/-]*\.(png|jpe?g|webp)$/i.test(image))throw new Error('Image must be a repository-relative path inside images/');if(image&&image.split('/').indexOf('..')!==-1)throw new Error('Invalid image path');
 const article={id:slug,title:title,slug:slug,category:category,summary:summary,image:image,bodyMarkdown:bodyMarkdown,updatedAt:new Date().toISOString()};
 const path='gauravs-world/data/articles/'+slug+'.json';const saved=githubPutJson_(path,article,'Publish Gaurav\'s World article: '+slug);
 const manifestPath='gauravs-world/data/articles.json';let entries=[];
 try{const existing=githubGetJson_(manifestPath);if(Array.isArray(existing))entries=existing;else if(existing&&Array.isArray(existing.articles))entries=existing.articles;}catch(err){if(String(err.message).indexOf('HTTP 404')===-1)throw err;}
 const item={id:slug,slug:slug,title:title,category:category,summary:summary,image:image,updatedAt:article.updatedAt};entries=entries.filter(x=>x&&x.slug!==slug&&x.id!==slug);entries.unshift(item);entries=entries.slice(0,500);
 const manifest=githubPutJson_(manifestPath,{articles:entries,updatedAt:article.updatedAt},'Update Gaurav\'s World article manifest');
 return{slug:slug,path:path,commit:manifest.commit||saved.commit,articleCommit:saved.commit,manifestPath:manifestPath,htmlUrl:'https://onestopfzd.in/gauravs-world/article.html?id='+encodeURIComponent(slug)};
}
function githubGetJson_(path){const p=PropertiesService.getScriptProperties(),token=p.getProperty('GITHUB_TOKEN'),owner=p.getProperty('GITHUB_OWNER'),repo=p.getProperty('GITHUB_REPO'),branch=p.getProperty('GITHUB_BRANCH')||'main';if(!token||!owner||!repo)throw new Error('Server configuration missing: GitHub settings');const api='https://api.github.com/repos/'+encodeURIComponent(owner)+'/'+encodeURIComponent(repo)+'/contents/'+path.split('/').map(encodeURIComponent).join('/');const r=UrlFetchApp.fetch(api+'?ref='+encodeURIComponent(branch),{method:'get',headers:{Authorization:'Bearer '+token,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'},muteHttpExceptions:true});if(r.getResponseCode()!==200)throw new Error('GitHub lookup failed (HTTP '+r.getResponseCode()+')');const file=JSON.parse(r.getContentText());return JSON.parse(Utilities.newBlob(Utilities.base64Decode(file.content.replace(/\n/g,''))).getDataAsString('UTF-8'));}
function githubPutJson_(path,data,message){
 const p=PropertiesService.getScriptProperties(),token=p.getProperty('GITHUB_TOKEN'),owner=p.getProperty('GITHUB_OWNER'),repo=p.getProperty('GITHUB_REPO'),branch=p.getProperty('GITHUB_BRANCH')||'main';if(!token||!owner||!repo)throw new Error('Server configuration missing: GitHub settings');
 const api='https://api.github.com/repos/'+encodeURIComponent(owner)+'/'+encodeURIComponent(repo)+'/contents/'+path.split('/').map(encodeURIComponent).join('/'),headers={Authorization:'Bearer '+token,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'};let sha=null;
 const existing=UrlFetchApp.fetch(api+'?ref='+encodeURIComponent(branch),{method:'get',headers:headers,muteHttpExceptions:true});if(existing.getResponseCode()===200){try{sha=JSON.parse(existing.getContentText()).sha;}catch(_){throw new Error('Could not read existing GitHub file metadata');}}else if(existing.getResponseCode()!==404)throw new Error('GitHub lookup failed (HTTP '+existing.getResponseCode()+')');
 const payload={message:message,content:Utilities.base64Encode(JSON.stringify(data,null,2),Utilities.Charset.UTF_8),branch:branch};if(sha)payload.sha=sha;const r=UrlFetchApp.fetch(api,{method:'put',contentType:'application/json',headers:headers,payload:JSON.stringify(payload),muteHttpExceptions:true});const code=r.getResponseCode();if(code<200||code>=300)throw new Error('GitHub publish failed (HTTP '+code+')');const out=JSON.parse(r.getContentText());return{commit:out.commit&&out.commit.sha||'',contentUrl:out.content&&out.content.html_url||''};
}
function extractOutputText_(r){if(r&&typeof r.output_text==='string')return r.output_text;const a=r&&Array.isArray(r.output)?r.output:[];for(let i=0;i<a.length;i++){const c=Array.isArray(a[i].content)?a[i].content:[];for(let j=0;j<c.length;j++)if(c[j].type==='output_text'&&typeof c[j].text==='string')return c[j].text;}throw new Error('No text output received from OpenAI');}
function requiredText_(v,max,field){if(typeof v!=='string')throw new Error('Invalid '+field);const s=v.trim();if(!s||s.length>max)throw new Error('Invalid '+field+' length');return s;}
function optionalText_(v,fallback,max,field){if(v===undefined||v===null||v==='')return fallback;if(typeof v!=='string')throw new Error('Invalid '+field);const s=v.trim();if(s.length>max)throw new Error('Invalid '+field+' length');return s||fallback;}
function safeMessage_(err){const m=String(err&&err.message||'Request failed');if(/token|secret|api.?key|bearer/i.test(m))return'Request failed; check server configuration.';return m.slice(0,240);}
function json_(v){return ContentService.createTextOutput(JSON.stringify(v)).setMimeType(ContentService.MimeType.JSON);}
