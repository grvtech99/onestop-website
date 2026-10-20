/* Loads the five newest published Gaurav's World articles into the ONESTOP header ticker. */
(function(){
  'use strict';
  const track=document.getElementById('latest-ticker-track');
  if(!track)return;
  const manifest='/gauravs-world/data/articles.json';
  const blogBase='/gauravs-world/article-dynamic.html?id=';
  function addItem(parent,article,duplicate){
    const link=document.createElement('a');
    link.className='latest-ticker-item';
    link.href=blogBase+encodeURIComponent(String(article.slug||article.id));
    link.textContent=String(article.title||'').trim();
    link.setAttribute('aria-label','आर्टिकल पढ़ें: '+link.textContent);
    if(duplicate){link.tabIndex=-1;link.setAttribute('aria-hidden','true');}
    const dot=document.createElement('span');
    dot.className='latest-ticker-separator';
    dot.setAttribute('aria-hidden','true');
    parent.append(link,dot);
  }
  fetch(manifest+'?ticker='+Date.now(),{cache:'no-store'})
    .then(function(response){if(!response.ok)throw new Error('Article list unavailable');return response.json();})
    .then(function(data){
      const articles=Array.isArray(data.articles)?data.articles:[];
      const latest=articles.filter(function(a){return a&&a.title&&(a.slug||a.id)&&a.publishedAt&&Number.isFinite(Date.parse(a.publishedAt));})
        .sort(function(a,b){return Date.parse(b.publishedAt)-Date.parse(a.publishedAt);}).slice(0,5);
      track.replaceChildren();
      if(!latest.length){
        const empty=document.createElement('span');empty.className='latest-ticker-empty';empty.textContent='Latest articles will appear here.';track.appendChild(empty);return;
      }
      latest.forEach(function(article){addItem(track,article,false);});
      latest.forEach(function(article){addItem(track,article,true);});
    })
    .catch(function(){
      track.replaceChildren();
      const fallback=document.createElement('span');fallback.className='latest-ticker-empty';fallback.textContent='Latest articles are temporarily unavailable.';track.appendChild(fallback);
    });
})();