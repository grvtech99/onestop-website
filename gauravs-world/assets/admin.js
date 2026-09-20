const API_URL='https://script.google.com/macros/s/AKfycbywnTL4O_EpmdOe3EgYesh-wEAsXMsuus6H1L2n8-rBD2oYWR4v6-3DrUTs8mSTE7f9/exec';
const $=s=>document.querySelector(s);
let key="";
function esc(s=""){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
async function call(action,data={}){
 if(!API_URL.startsWith("https://"))throw Error("API_URL सेट नहीं है");
 const url=new URL(API_URL);url.searchParams.set("action",action);url.searchParams.set("adminKey",key);
 Object.entries(data).forEach(([k,v])=>url.searchParams.set(k,typeof v==="string"?v:JSON.stringify(v)));
 const r=await fetch(url.toString(),{method:"GET"});const j=await r.json();if(!j.ok)throw Error(j.error||"Request failed");return j.data;
}
function getForm(){return {id:$("#postId").value,title:$("#title").value.trim(),hook:$("#hook").value.trim(),category:$("#category").value,status:$("#status").value,thumbnail:$("#thumbnail").value.trim(),heroImage:$("#heroImage").value.trim(),excerpt:$("#excerpt").value.trim(),content:$("#content").value,tags:$("#tags").value,author:$("#author").value.trim()};}
function reset(){ $("#postForm").reset();$("#postId").value="";$("#author").value="Gaurav";$("#saveMsg").textContent=""; }
async function refresh(){
 const posts=await call("adminList");
 $("#adminPosts").innerHTML=posts.map(p=>`<div class="adminpost"><div><strong>${esc(p.title)}</strong><small>${esc(p.category)} · ${esc(p.status)}</small></div><div><button data-edit="${esc(p.id)}">Edit</button><button data-delete="${esc(p.id)}">Delete</button></div></div>`).join("")||"<p>अभी कोई पोस्ट नहीं।</p>";
 $("#adminPosts").querySelectorAll("[data-edit]").forEach(b=>b.onclick=()=>edit(posts.find(p=>p.id===b.dataset.edit)));
 $("#adminPosts").querySelectorAll("[data-delete]").forEach(b=>b.onclick=async()=>{if(confirm("यह पोस्ट delete करें?")){try{await call("delete",{id:b.dataset.delete});await refresh();}catch(e){alert(e.message)}}});
}
function edit(p){if(!p)return;for(const k of ["id","title","hook","category","status","thumbnail","heroImage","excerpt","content","tags","author"])if($("#"+k))$("#"+k).value=p[k]||"";window.scrollTo({top:0,behavior:"smooth"});}
document.addEventListener("DOMContentLoaded",()=>{
 $("#loginForm").onsubmit=async e=>{e.preventDefault();key=$("#adminKey").value;try{await call("adminList");sessionStorage.setItem("gw_admin_key",key);$("#loginPanel").hidden=true;$("#editorPanel").hidden=false;await refresh();}catch(err){$("#loginMsg").textContent=err.message;key="";}};
 const saved=sessionStorage.getItem("gw_admin_key");if(saved){key=saved;call("adminList").then(()=>{ $("#loginPanel").hidden=true;$("#editorPanel").hidden=false;return refresh();}).catch(()=>{sessionStorage.removeItem("gw_admin_key");key="";});}
 $("#postForm").onsubmit=async e=>{e.preventDefault();try{await call("save",getForm());$("#saveMsg").textContent="Saved successfully";reset();await refresh();}catch(err){$("#saveMsg").textContent=err.message;}};
 $("#resetBtn").onclick=reset;$("#logoutBtn").onclick=()=>{sessionStorage.removeItem("gw_admin_key");key="";location.reload();};
});
