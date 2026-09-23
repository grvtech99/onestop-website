/* Category-aware compact homepage feed. */
(function () {
  'use strict';
  const MANIFEST_URL = './data/articles.json';
  const root = document.getElementById('posts');
  const search = document.getElementById('search');
  const category = document.getElementById('category');
  if (!root || !search || !category) return;

  const style = document.createElement('style');
  style.textContent = `
    /* The original #posts grid was forcing each category section into a separate column. */
    #posts { display:block; width:100%; }
    #posts .home-section{margin:14px 0 20px}
    #posts .section-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:0 0 7px}
    #posts .section-head h2{font-size:1.05rem;margin:0;font-weight:800;color:#172033}
    #posts .section-view{font-size:.75rem;font-weight:700;color:#0876d1;background:#e8f3ff;border-radius:999px;padding:5px 10px;border:0;cursor:pointer}
    #posts .section-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
    #posts .post{display:flex;align-items:center;gap:12px;min-width:0;background:#fff;border:1px solid #e5eaf1;border-radius:10px;overflow:hidden;padding:8px}
    #posts .post-cover-link{display:block;position:relative;flex:0 0 104px;width:104px;height:78px;aspect-ratio:4/3;overflow:hidden;background:#eaf0f6;border-radius:7px}
    #posts .post-cover-link>a{display:block;width:100%;height:100%}
    #posts .post-cover{display:block;width:100%;height:100%;object-fit:cover}
    #posts .post-content{flex:1 1 0;min-width:0;display:flex;align-items:center;padding:6px 8px 6px 0}
    #posts .post h2{margin:0;font-size:.95rem;line-height:1.25}
    #posts .post-actions{right:4px;bottom:4px;gap:4px}
    #posts .post-action{width:26px;height:26px}
    #posts .post-action svg{width:14px;height:14px}
    @media(max-width:800px){#posts .section-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}}
    @media(max-width:560px){
      #posts .home-section{margin:12px 0 18px}
      #posts .section-head h2{font-size:.94rem}
      #posts .section-grid{display:flex;flex-direction:column;gap:0}
      #posts .post{gap:10px;width:100%;border:0;border-bottom:1px solid #e5eaf1;border-radius:0;background:transparent;padding:5px 2px;min-height:0}
      #posts .post-cover-link{flex-basis:104px;width:104px;height:78px}
      #posts .post-content{padding:6px 4px 6px 0}
      #posts .post h2{font-size:.8rem;line-height:1.2;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
      #posts .post-action{width:23px;height:23px}
    }
  `;
  document.head.appendChild(style);
  const fallbackArticles = Array.isArray(window.articles) ? window.articles.slice() : [];
  const esc = value => String(value == null ? '' : value).replace(/[&<>\"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[ch]));
  function timestamp(a){const v=Date.parse(a.updatedAt||a.publishedAt||a.date||a.createdAt||'');return Number.isFinite(v)?v:0;}
  function liked(id){try{return localStorage.getItem('gw-liked-'+id)==='1';}catch(_){return false;}}
  function card(a){
    const id=String(a.slug||a.id||'');const href=`article-dynamic.html?id=${encodeURIComponent(id)}`;
    const image=String(a.image||a.coverImage||a.thumbnail||'');
    const media=image?`<div class=\"post-cover-link\"><a href=\"${esc(href)}\" aria-label=\"${esc(a.title)} पढ़ें\"><img class=\"post-cover\" src=\"${esc(image)}\" alt=\"${esc(a.title)}\" loading=\"lazy\" decoding=\"async\"></a><span class=\"post-actions\"><button class=\"post-action like-action${liked(id)?' is-liked':''}\" type=\"button\" data-like=\"${esc(id)}\" aria-label=\"Like\" aria-pressed=\"${liked(id)}\"><svg viewBox=\"0 0 24 24\"><path d=\"M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z\"/></svg></button><button class=\"post-action share-action\" type=\"button\" data-share=\"${esc(id)}\" data-title=\"${esc(a.title)}\" data-url=\"${esc(new URL(href,location.href).href)}\" aria-label=\"Share\"><svg viewBox=\"0 0 24 24\"><circle cx=\"18\" cy=\"5\" r=\"3\"/><circle cx=\"6\" cy=\"12\" r=\"3\"/><circle cx=\"18\" cy=\"19\" r=\"3\"/><path d=\"m8.7 10.7 6.6-4.4M8.7 13.3l6.6 4.4\"/></svg></button></span></div>`:`<a class=\"post-cover-link\" href=\"${esc(href)}\"></a>`;
    return `<article class=\"post\">${media}<div class=\"post-content\"><h2><a class=\"post-title\" href=\"${esc(href)}\">${esc(a.title)}</a></h2></div></article>`;
  }
  const groups=[['Technology','Technology'],['Science','Science'],['History','History'],['Universe','Universe']];
  function render(list){
    const q=search.value.trim().toLowerCase();const selected=category.value;
    const filtered=list.filter(a=>(selected==='all'||a.category===selected)&&(String(a.title||'')+' '+String(a.description||a.summary||'')+' '+String(a.category||'')).toLowerCase().includes(q)).slice().sort((a,b)=>timestamp(b)-timestamp(a));
    if(selected!=='all') {root.innerHTML=filtered.length?filtered.map(card).join(''):'<div class=\"empty\">अभी कोई प्रकाशित लेख नहीं मिला।</div>';return;}
    const section=(name,items)=>items.length?`<section class=\"home-section\"><div class=\"section-head\"><h2>${name}</h2><button class=\"section-view\" type=\"button\" data-view=\"${esc(name)}\">View all →</button></div><div class=\"section-grid\">${items.map(card).join('')}</div></section>`:'';
    let html=section('Latest Articles',filtered.slice(0,6));
    groups.forEach(([name,key])=>{const items=filtered.filter(a=>String(a.category||'').toLowerCase()===key.toLowerCase()).slice(0,4);html+=section(name,items);});
    root.innerHTML=html||'<div class=\"empty\">अभी कोई प्रकाशित लेख नहीं मिला।</div>';
  }
  function normalize(item){if(!item||typeof item!=='object'||!item.title||!(item.slug||item.id))return null;const id=String(item.slug||item.id);return {...item,id,slug:id,title:String(item.title),category:String(item.category||'General'),summary:String(item.summary||item.description||''),description:String(item.summary||item.description||''),image:String(item.image||item.coverImage||item.thumbnail||''),updatedAt:item.updatedAt||'',publishedAt:item.publishedAt||item.date||''};}
  root.addEventListener('click',async event=>{
    const view=event.target.closest('[data-view]');if(view){category.value=view.dataset.view;category.dispatchEvent(new Event('change',{bubbles:true}));root.scrollIntoView({behavior:'smooth',block:'start'});return;}
    const like=event.target.closest('[data-like]');if(like){event.preventDefault();event.stopPropagation();const id=like.dataset.like;try{const next=!liked(id);if(next)localStorage.setItem('gw-liked-'+id,'1');else localStorage.removeItem('gw-liked-'+id);like.classList.toggle('is-liked',next);like.setAttribute('aria-pressed',String(next));}catch(_){like.classList.toggle('is-liked');}return;}
    const share=event.target.closest('[data-share]');if(share){event.preventDefault();event.stopPropagation();const data={title:share.dataset.title||'Gaurav’s World',url:share.dataset.url||location.href};try{if(navigator.share)await navigator.share(data);else if(navigator.clipboard&&navigator.clipboard.writeText){await navigator.clipboard.writeText(data.url);share.setAttribute('aria-label','Link copied');}else window.prompt('Copy article link:',data.url);}catch(_){}}
  });
  search.addEventListener('input',()=>render(window.articles||fallbackArticles));category.addEventListener('change',()=>render(window.articles||fallbackArticles));
  render(fallbackArticles);
  fetch(MANIFEST_URL,{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('manifest unavailable: '+r.status);return r.json();}).then(data=>{const published=Array.isArray(data.articles)?data.articles.map(normalize).filter(Boolean):[];const byId=new Map(fallbackArticles.map(a=>[String(a.slug||a.id),a]));published.forEach(a=>byId.set(a.id,a));window.articles=Array.from(byId.values());render(window.articles);}).catch(()=>{window.articles=fallbackArticles;render(fallbackArticles);if(!fallbackArticles.length)root.innerHTML='<div class=\"empty\">लेख लोड नहीं हो पाए। कृपया refresh करें।</div>';});
})();
