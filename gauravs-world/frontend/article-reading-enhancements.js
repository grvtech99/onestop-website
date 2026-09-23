/* Progressive reading-page enhancements. Keeps the existing renderer/share controls intact. */
(() => {
  'use strict';
  const root = document.getElementById('article');
  if (!root) return;
  const id = new URLSearchParams(location.search).get('id') || '';
  const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const style = document.createElement('style');
  style.textContent = '.reading-meta{display:flex;flex-wrap:wrap;gap:7px 14px;color:#64748b;font-size:.86rem;margin:8px 0 16px}.reading-toc{border:1px solid #dce8f5;background:#f6faff;border-radius:12px;padding:14px 18px;margin:20px 0}.reading-toc strong{display:block;margin-bottom:8px}.reading-toc ul{margin:0;padding-left:20px}.reading-toc li{margin:5px 0}.reading-related{border-top:1px solid #e5eaf1;margin-top:30px;padding-top:18px}.reading-related a{display:block;padding:9px 0;border-bottom:1px solid #eef2f7}.reading-top{display:inline-block;margin:22px 0 0;padding:8px 13px;border:1px solid #cfe2f5;border-radius:999px;background:#edf6ff;color:#075da8;font-weight:650;font-size:.88rem}';
  document.head.appendChild(style);
  let article = null, done = false;
  function enhance() {
    const title = root.querySelector('h1'), body = root.querySelector('.article-body');
    if (!title || !body || body.getAttribute('aria-busy') === 'true' || done) return;
    done = true;
    const words = (body.innerText || '').trim().split(/\s+/).filter(Boolean).length;
    const bits = [`लगभग ${Math.max(1, Math.ceil(words / 200))} मिनट पढ़ने का समय`];
    if (article && article.author) bits.unshift(`लेखक: ${article.author}`);
    if (article && article.publishedAt) bits.push(`प्रकाशित: ${article.publishedAt}`);
    if (article && article.updatedAt) bits.push(`अपडेट: ${article.updatedAt}`);
    const meta = document.createElement('div'); meta.className = 'reading-meta';
    meta.innerHTML = bits.map(esc).join(' <span aria-hidden="true">·</span> ');
    const date = root.querySelector('.date');
    if (date && article && article.updatedAt) date.textContent = `अपडेट: ${article.updatedAt}`;
    if (date && !(article && (article.publishedAt || article.date || article.updatedAt))) date.remove();
    (date || title).insertAdjacentElement('afterend', meta);
    const headings = [...body.querySelectorAll('h2,h3')];
    if (headings.length >= 3) {
      const toc = document.createElement('nav'); toc.className = 'reading-toc'; toc.setAttribute('aria-label','लेख की विषय-सूची');
      const rows = headings.map((h,i) => { const anchor = `gw-section-${i+1}`; h.id = anchor; return `<li${h.tagName === 'H3' ? ' style="margin-left:14px"' : ''}><a href="#${anchor}">${esc(h.textContent)}</a></li>`; }).join('');
      toc.innerHTML = `<strong>इस लेख में</strong><ul>${rows}</ul>`; meta.insertAdjacentElement('afterend', toc);
    }
    const top = document.createElement('a'); top.className = 'reading-top'; top.href = '#top'; top.textContent = '↑ ऊपर जाएँ'; body.insertAdjacentElement('afterend', top);
    fetch('./data/articles.json').then(r => r.ok ? r.json() : []).then(data => {
      const list = Array.isArray(data) ? data : (data.articles || []);
      const candidates = list.filter(a => a && a.id && a.id !== id);
      const same = candidates.filter(a => article && article.category && a.category === article.category);
      const related = (same.length ? same : candidates).slice(0,3);
      if (!related.length) return;
      const section = document.createElement('section'); section.className = 'reading-related';
      section.innerHTML = '<h2>संबंधित लेख</h2>' + related.map(a => `<a href="./article-dynamic.html?id=${encodeURIComponent(a.id)}">${esc(a.title || a.id)} →</a>`).join('');
      top.insertAdjacentElement('afterend', section);
    }).catch(() => {});
  }
  const observer = new MutationObserver(enhance); observer.observe(root,{childList:true,subtree:true});
  fetch(`./data/articles/${encodeURIComponent(id)}.json`).then(r => r.ok ? r.json() : null).then(a => { article = a; enhance(); }).catch(() => {});
  enhance();
})();