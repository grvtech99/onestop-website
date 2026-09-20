// Set this to your deployed Apps Script Web App /exec URL.
const API_URL = "https://script.google.com/macros/s/AKfycbywnTL4O_EpmdOe3EgYesh-wEAsXMsuus6H1L2n8-rBD2oYWR4v6-3DrUTs8mSTE7f9/exec";
const $ = s => document.querySelector(s);
const state = {posts:[], category:"All", query:"", page:1, pageSize:30, sort:"new"};
const fallbackPosts = [
 {id:"demo-ai",title:"क्या AI इंसानों की नौकरियाँ बदल देगा?",hook:"आने वाले समय में काम करने का तरीका कैसे बदल सकता है?",category:"Technology",publishedAt:"2026-09-20",thumbnail:"",excerpt:"",status:"published"},
 {id:"demo-time",title:"अंतरिक्ष में समय धीमा क्यों हो जाता है?",hook:"समय हर जगह एक जैसा नहीं चलता—आखिर क्यों?",category:"Science",publishedAt:"2026-09-19",thumbnail:"",status:"published"},
 {id:"demo-pyramid",title:"क्या प्राचीन सभ्यताओं के पास उन्नत तकनीक थी?",category:"History",publishedAt:"2026-09-18",status:"published"},
 {id:"demo-end",title:"ब्रह्मांड का अंत कैसे हो सकता है?",category:"Universe",publishedAt:"2026-09-17",status:"published"},
 {id:"demo-ocean",title:"समुद्र की गहराई में क्या छिपा है?",category:"Mystery",publishedAt:"2026-09-16",status:"published"},
 {id:"demo-battery",title:"मोबाइल की बैटरी जल्दी खत्म क्यों होती है?",category:"Technology",publishedAt:"2026-09-15",status:"published"}
];
function dateText(v){if(!v)return "";const d=new Date(v);return isNaN(d)?String(v):d.toLocaleDateString("hi-IN",{day:"numeric",month:"long",year:"numeric"});}
function esc(s=""){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function imageOrEmpty(src){return src && /^https?:\/\//i.test(src) ? `<img loading="lazy" src="${esc(src)}" alt="">` : "";}
async function api(action, params={}) {
 if(!API_URL.startsWith("https://")) throw new Error("Apps Script API URL सेट नहीं है");
 const url=new URL(API_URL);url.searchParams.set("action",action);
 Object.entries(params).forEach(([k,v])=>url.searchParams.set(k,typeof v==="string"?v:JSON.stringify(v)));
 const r=await fetch(url.toString(),{method:"GET"});const j=await r.json();if(!j.ok)throw new Error(j.error||"API error");return j.data;
}
function categories(){
 const cats=["All","Technology","Science","History","Universe","Mystery","Nature","World","AI","Trending"];
 $("#categories").innerHTML=cats.map(c=>`<button class="cat ${state.category===c?"active":""}" data-cat="${esc(c)}">${c==="All"?"सभी":esc(c)}</button>`).join("");
 $("#categories").querySelectorAll("button").forEach(b=>b.onclick=()=>{state.category=b.dataset.cat;state.page=1;categories();renderFeed();});
}
function filtered(){
 let a=state.posts.filter(p=>p.status==="published");
 if(state.category!=="All")a=a.filter(p=>(p.category||"").toLowerCase()===state.category.toLowerCase() || (state.category==="Trending" && (p.tags||"").toString().toLowerCase().includes("trending")));
 if(state.query)a=a.filter(p=>(p.title+" "+(p.hook||"")+" "+(p.category||"")).toLowerCase().includes(state.query.toLowerCase()));
 if(state.sort==="old")a.reverse();return a;
}
function renderFeed(){
 const a=filtered(), shown=a.slice(0,state.page*state.pageSize);
 $("#feed").innerHTML=shown.length?shown.map((p,i)=>`<a class="story" href="article.html?id=${encodeURIComponent(p.id)}"><span class="story-num">${String(i+1).padStart(2,"0")}</span><span class="story-copy"><span class="story-cat">${esc(p.category||"ARTICLE")}</span><span class="story-title">${esc(p.title||"Untitled")}</span><span class="story-date">${dateText(p.publishedAt||p.updatedAt)}</span></span>${imageOrEmpty(p.thumbnail)}<span class="story-arrow">›</span></a>`).join(""):`<p class="state">इस खोज में कोई लेख नहीं मिला।</p>`;
 $("#moreBtn").hidden=shown.length>=a.length;
}
async function loadPosts(){
 try{state.posts=await api("list");if(!Array.isArray(state.posts))state.posts=[];}
 catch(e){state.posts=fallbackPosts;console.warn(e.message);}
 if(state.posts.length){const featured=state.posts.find(p=>p.status==="published"&&p.heroImage);if(featured){$("#feature").querySelector("h1").textContent=featured.title;$("#feature").querySelector("p").textContent=featured.hook||featured.excerpt||"";const img=$("#featureImg");img.src=featured.heroImage;img.hidden=false;$("#feature").onclick=()=>location.href="article.html?id="+encodeURIComponent(featured.id);}}
 categories();renderFeed();
}
async function loadArticle(){
 const root=$("#articleRoot");const id=new URLSearchParams(location.search).get("id");if(!id){root.innerHTML='<p class="state">लेख ID नहीं मिला। <a href="index.html">होम पर लौटें</a></p>';return;}
 let p=state.posts.find(x=>x.id===id);
 if(!p){try{p=await api("get",{id});}catch(e){}}
 if(!p){root.innerHTML='<p class="state">यह लेख नहीं मिला या प्रकाशित नहीं है। <a href="index.html">वापस जाएँ</a></p>';return;}
 document.title=(p.title||"लेख")+" — Gaurav’s World";
 root.innerHTML=`<div class="article-cat">${esc(p.category||"ARTICLE")}</div><h1>${esc(p.title||"")}</h1><div class="article-meta">${dateText(p.publishedAt||p.updatedAt)} · ${esc(p.author||"Gaurav")}</div>${p.heroImage?`<img class="article-hero" src="${esc(p.heroImage)}" alt="${esc(p.title)}">`:""}${p.hook?`<div class="article-hook">${esc(p.hook)}</div>`:""}<div class="article-actions"><button id="saveArticle">☆ सेव करें</button><button id="shareArticle">↗ शेयर</button></div><article class="article-content">${(p.content||p.excerpt||"").split(/\n+/).map(t=>t.trim()?`<p>${esc(t)}</p>`:"").join("")}</article>`;
 $("#saveArticle").onclick=()=>{let s=JSON.parse(localStorage.getItem("gw_saved")||"[]");if(!s.includes(p.id))s.push(p.id);localStorage.setItem("gw_saved",JSON.stringify(s));$("#saveArticle").textContent="✓ सेव हो गया";};
 $("#shareArticle").onclick=()=>navigator.share?navigator.share({title:p.title,url:location.href}):navigator.clipboard.writeText(location.href);
}
document.addEventListener("DOMContentLoaded",()=>{
 if($("#searchBtn"))$("#searchBtn").onclick=()=>{$("#searchWrap").classList.toggle("open");$("#searchInput").focus();};
 if($("#searchInput"))$("#searchInput").oninput=e=>{state.query=e.target.value;state.page=1;renderFeed();};
 if($("#sortSelect"))$("#sortSelect").onchange=e=>{state.sort=e.target.value;state.page=1;renderFeed();};
 if($("#moreBtn"))$("#moreBtn").onclick=()=>{state.page++;renderFeed();};
 if($("#savedBtn"))$("#savedBtn").onclick=()=>{const ids=JSON.parse(localStorage.getItem("gw_saved")||"[]");state.posts=state.posts.filter(p=>ids.includes(p.id));state.category="All";renderFeed();};
 if($("#shareBtn"))$("#shareBtn").onclick=()=>navigator.share?navigator.share({title:document.title,url:location.href}):navigator.clipboard.writeText(location.href);
 if($("#feed"))loadPosts();
 if($("#articleRoot"))loadArticle();
});
