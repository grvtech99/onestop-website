/* Published article reader enhancement. Render Markdown images and formatting safely. */
(() => {
  'use strict';
  const params = new URLSearchParams(location.search);
  const id = params.get('id');
  const legacy = new Set(['computer-basics','online-safety','ai-tools','digital-skills','pdf-mobile','typing-practice']);
  if (!id || legacy.has(id) || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id)) return;
  const root = document.getElementById('article');
  if (!root) return;
  const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const readable = id.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  root.innerHTML = `<span class="tag">Gaurav's World</span><h1>${esc(readable)}</h1><p class="date">लेख खोला जा रहा है…</p><div class="article-body" aria-busy="true"><p>कृपया प्रतीक्षा करें—लेख का विवरण लोड हो रहा है।</p></div>`;
  document.title = `${readable} | Gaurav's World`;

  function safeImageUrl(raw) {
    const value = String(raw || '').trim();
    if (/^https:\/\/[a-z0-9.-]+\//i.test(value)) return value;
    if (/^images\/[A-Za-z0-9][A-Za-z0-9._/-]*\.(png|jpe?g|webp)$/i.test(value) && !value.includes('..')) return `./${value}`;
    return '';
  }
  function inline(text) {
    let value = esc(text);
    value = value.replace(/!\[([^\]]*)\]\((https?:\/\/[^\s)]+|images\/[A-Za-z0-9][A-Za-z0-9._/-]*\.(?:png|jpe?g|webp))\)/gi, (whole, alt, rawUrl) => {
      const url = safeImageUrl(rawUrl);
      return url ? `<figure class="article-inline-image"><img class="article-image-bg" src="${esc(url)}" alt="" aria-hidden="true" loading="lazy" decoding="async"><img src="${esc(url)}" alt="${esc(alt)}" loading="lazy" decoding="async"><figcaption>${esc(alt)}</figcaption></figure>` : esc(whole);
    });
    value = value.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    value = value.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\*(.+?)\*/g, '<em>$1</em>');
    return value;
  }
  function markdown(source) {
    const lines = String(source || '').replace(/\r/g, '').split('\n');
    const out = []; let list = false;
    const closeList = () => { if (list) { out.push('</ul>'); list = false; } };
    for (const line of lines) {
      const t = line.trim();
      if (!t) { closeList(); continue; }
      const h = /^(#{1,3})\s+(.+)$/.exec(t);
      const li = /^[-*]\s+(.+)$/.exec(t);
      if (h) { closeList(); const level = h[1].length; out.push(`<h${level}>${inline(h[2])}</h${level}>`); }
      else if (li) { if (!list) { out.push('<ul>'); list = true; } out.push(`<li>${inline(li[1])}</li>`); }
      else { closeList(); out.push(`<p>${inline(t)}</p>`); }
    }
    closeList(); return out.join('');
  }
  function addBreadcrumb(category, title) {
    if (root.querySelector('.article-breadcrumb')) return;
    const nav = document.createElement('nav');
    nav.className = 'article-breadcrumb';
    nav.setAttribute('aria-label','ब्रेडक्रंब');
    const categoryUrl = category ? `./?category=${encodeURIComponent(category)}#posts` : './#posts';
    nav.innerHTML = `<a href="./">मुख्य पृष्ठ</a><span aria-hidden="true">›</span><a href="${esc(categoryUrl)}">${esc(category || 'लेख')}</a><span aria-hidden="true">›</span><span aria-current="page">${esc(title)}</span>`;
    const style = document.createElement('style');
    style.id = 'article-breadcrumb-style';
    style.textContent = '.article-breadcrumb{display:flex;flex-wrap:wrap;align-items:center;gap:5px 7px;color:#64748b;font-size:.78rem;line-height:1.4;margin:0 0 10px}.article-breadcrumb a{color:#64748b}.article-breadcrumb a:hover,.article-breadcrumb a:focus-visible{color:#0876d1}.article-breadcrumb span[aria-hidden="true"]{color:#9aa8b8}.article-breadcrumb span[aria-current="page"]{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}@media(max-width:560px){.article-breadcrumb{font-size:.74rem;margin-bottom:8px}}';
    if (!document.getElementById('article-breadcrumb-style')) document.head.appendChild(style);
    root.prepend(nav);
  }

  function addShareControls(title) {
    if (root.querySelector('.article-share')) return;
    const bar = document.createElement('div');
    bar.className = 'article-share';
    bar.style.cssText = 'display:flex;align-items:center;gap:8px;margin:10px 0 14px;';
    bar.innerHTML = '<button type="button" class="article-share-btn" data-share-native aria-label="लेख शेयर करें" title="Share"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="18" cy="5" r="2.2"></circle><circle cx="6" cy="12" r="2.2"></circle><circle cx="18" cy="19" r="2.2"></circle><path d="m8 11 7.8-4.7M8 13l7.8 4.7"></path></svg><span>Share</span></button><button type="button" class="article-share-btn" data-share-copy aria-label="लेख का लिंक कॉपी करें" title="Copy link"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="10" height="10" rx="2"></rect><path d="M6 15H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1"></path></svg><span>Copy link</span></button>';
    const style = document.createElement('style');
    style.textContent = '.article-share-btn{display:inline-flex;align-items:center;gap:6px;min-height:36px;padding:6px 11px;border:1px solid #d5e2ee;border-radius:8px;background:#f7fbff;color:#075da8;font:650 .8rem/1 system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;cursor:pointer;white-space:nowrap}.article-share-btn svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round;flex:0 0 16px}.article-share-btn:hover{background:#edf6ff;border-color:#c3d9ec}.article-share-btn:active{transform:translateY(1px)}.article-share-btn:focus-visible{outline:2px solid #0876d1;outline-offset:2px}@media(max-width:560px){.article-share-btn{min-height:34px;padding:5px 10px;font-size:.77rem}.article-share{margin-top:8px!important;margin-bottom:12px!important}}';
    if (!document.getElementById('article-share-style')) { style.id = 'article-share-style'; document.head.appendChild(style); }
    const heading = root.querySelector('h1');
    if (heading) heading.insertAdjacentElement('afterend', bar); else root.prepend(bar);
    const url = location.href;
    bar.querySelector('[data-share-native]').addEventListener('click', async () => {
      try {
        if (navigator.share) await navigator.share({title, url});
        else if (navigator.clipboard && navigator.clipboard.writeText) { await navigator.clipboard.writeText(url); bar.querySelector('[data-share-native]').textContent = '✓ लिंक कॉपी हुआ'; }
        else window.prompt('Copy article link:', url);
      } catch (_) {}
    });
    bar.querySelector('[data-share-copy]').addEventListener('click', async () => {
      const button = bar.querySelector('[data-share-copy]');
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) { await navigator.clipboard.writeText(url); button.textContent = '✓ कॉपी हो गया'; }
        else { window.prompt('Copy article link:', url); }
      } catch (_) { window.prompt('Copy article link:', url); }
    });
  }
  fetch(`./data/articles/${encodeURIComponent(id)}.json`)
    .then(r => { if (!r.ok) throw new Error('not found'); return r.json(); })
    .then(a => {
      if (!a || !a.title) throw new Error('invalid article');
      const body = a.bodyMarkdown || a.body || a.content || '';
      const imagePath = String(a.image || a.coverImage || '').trim();
      const coverUrl = /^images\/[A-Za-z0-9][A-Za-z0-9._/-]*\.(png|jpe?g|webp)$/i.test(imagePath) && !imagePath.includes('..') ? `./${imagePath}` : '';
      const cover = coverUrl ? `<figure class="article-cover"><img class="article-image-bg" src="${esc(coverUrl)}" alt="" aria-hidden="true" loading="eager" decoding="async"><img src="${esc(coverUrl)}" alt="${esc(a.title)}" loading="eager" fetchpriority="high" decoding="async"></figure>` : '';
      root.innerHTML = `<span class="tag">${esc(a.category || 'General')}</span><h1>${esc(a.title)}</h1>${cover}<p class="date">${esc(a.updatedAt || a.date || 'Published')}</p>${a.summary ? `<p class="notice">${esc(a.summary)}</p>` : ''}<div class="article-body">${markdown(body)}</div>`;
      addBreadcrumb(a.category || 'General', a.title);
      addShareControls(a.title);
      root.querySelectorAll('.article-body img').forEach(img => {
        img.style.display = 'block'; img.style.width = '100%'; img.style.maxWidth = '100%'; img.style.height = '100%'; img.style.maxHeight = 'none'; img.style.margin = '0 auto'; img.style.objectFit = 'contain'; img.style.borderRadius = '10px';
        img.addEventListener('error', () => { const figure = img.closest('figure'); if (figure) figure.remove(); else img.remove(); });
      });
      document.title = `${a.title} | Gaurav's World`;
    })
    .catch(() => { root.innerHTML = `<h1>${esc(readable)}</h1><p>यह लेख अभी लोड नहीं हो पाया। कृपया इंटरनेट कनेक्शन जाँचकर पेज दोबारा खोलें।</p><p><a href="./">सभी लेखों पर वापस जाएँ</a></p>`; });
})();
