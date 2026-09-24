/* Progressive reading-page enhancements. Keeps the existing renderer/share controls intact. */
(() => {
  'use strict';

  const root = document.getElementById('article');
  if (!root) return;

  const id = new URLSearchParams(location.search).get('id') || '';
  const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));

  const style = document.createElement('style');
  style.id = 'reading-enhancements-style';
  style.textContent = `
    .reading-progress{position:fixed;top:0;left:0;width:100%;height:3px;z-index:2100;pointer-events:none;background:transparent}
    .reading-progress-bar{height:100%;width:0;transform-origin:left center;background:#0876d1;transition:width .08s linear}
    .reading-meta{display:flex;flex-wrap:wrap;gap:6px 12px;color:#64748b;font-size:.84rem;margin:7px 0 14px}
    .reading-meta .meta-sep{color:#a3afbf}.reading-meta a{color:#075da8;font-weight:700}.reading-meta a:hover{text-decoration:underline}
    .reading-toc{border:1px solid #dce8f5;background:#f6faff;border-radius:12px;margin:18px 0}
    .reading-toc summary{cursor:pointer;padding:12px 15px;font-weight:750;color:#18324d;list-style:none}
    .reading-toc summary::-webkit-details-marker{display:none}
    .reading-toc summary::after{content:'＋';float:right;color:#0876d1;font-weight:800}
    .reading-toc[open] summary::after{content:'−'}
    .reading-toc ul{margin:0;padding:0 15px 13px 34px}
    .reading-toc li{margin:5px 0}
    .reading-toc li.reading-h3{margin-left:14px;font-size:.94em}
    .article-details{border-top:1px solid #e5eaf1;margin-top:28px;padding-top:18px}.article-details h2{font-size:1.15rem!important;margin:0 0 12px!important}.article-details-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.article-detail{border:1px solid #e2e9f1;border-radius:10px;background:#f9fbfd;padding:9px 11px}.article-detail-label{display:block;color:#64748b;font-size:.72rem;margin-bottom:2px}.article-detail-value{display:block;color:#172033;font-size:.9rem;font-weight:700;line-height:1.4}.article-detail-value a{color:#075da8}.article-tags{margin-top:10px;color:#64748b;font-size:.82rem;line-height:1.6}.article-tags strong{color:#172033}.article-tag{display:inline-block;margin:3px 4px 0 0;padding:2px 7px;border-radius:999px;background:#eaf4ff;color:#075da8;font-size:.74rem}@media(max-width:560px){.article-details{margin-top:24px;padding-top:16px}.article-details-grid{grid-template-columns:1fr 1fr;gap:8px}.article-detail{padding:8px 9px}.article-detail-value{font-size:.82rem}.article-tags{font-size:.78rem}}
    .reading-related{border-top:1px solid #e5eaf1;margin-top:30px;padding-top:18px}
    .reading-related h2,.reading-pagination h2{font-size:1.15rem!important;margin:0 0 10px!important}
    .reading-related-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
    .reading-related-card{display:block;border:1px solid #e2e9f1;border-radius:11px;overflow:hidden;background:#fff;color:#172033}
    .reading-related-card:focus-visible{outline:2px solid #0876d1;outline-offset:2px}
    .reading-related-thumb{display:block;width:100%;aspect-ratio:16/9;object-fit:cover;background:#eaf0f6}
    .reading-related-title{display:block;padding:9px 10px;font-size:.9rem;font-weight:700;line-height:1.4}
    .reading-pagination{display:grid;grid-template-columns:1fr 1fr;gap:10px;border-top:1px solid #e5eaf1;margin-top:24px;padding-top:18px}
    .reading-page-link{display:block;border:1px solid #dfe7ef;border-radius:11px;padding:10px 11px;background:#f9fbfd;color:#17324d}
    .reading-page-link small{display:block;color:#64748b;font-size:.72rem;margin-bottom:3px}
    .reading-page-link strong{display:block;font-size:.88rem;line-height:1.4}
    .reading-top{position:fixed;right:16px;bottom:84px;z-index:950;display:inline-flex;align-items:center;justify-content:center;min-width:42px;height:42px;padding:0 12px;border:1px solid #cfe2f5;border-radius:999px;background:#fff;color:#075da8;font-weight:750;font-size:.82rem;box-shadow:0 8px 22px #102a4418;opacity:0;visibility:hidden;transform:translateY(8px);transition:opacity .18s,transform .18s,visibility .18s}
    .reading-top.is-visible{opacity:1;visibility:visible;transform:translateY(0)}
    .reading-top:focus-visible{outline:2px solid #0876d1;outline-offset:2px}
    @media(max-width:700px){
      .reading-related-grid{grid-template-columns:1fr}
      .reading-pagination{grid-template-columns:1fr}
      .reading-top{right:12px;bottom:82px}
    }
    @media(prefers-reduced-motion:reduce){
      .reading-top{transition:none}
      .reading-progress-bar{transition:none}
    }
  `;
  document.head.appendChild(style);

  let article = null;
  let done = false;
  let progressReady = false;

  const progress = document.createElement('div');
  progress.className = 'reading-progress';
  progress.setAttribute('aria-hidden', 'true');
  progress.innerHTML = '<div class="reading-progress-bar"></div>';
  document.body.appendChild(progress);
  const progressBar = progress.firstElementChild;

  function updateProgress() {
    const doc = document.documentElement;
    const max = Math.max(1, doc.scrollHeight - window.innerHeight);
    const value = Math.min(100, Math.max(0, (window.scrollY / max) * 100));
    progressBar.style.width = value.toFixed(2) + '%';
  }

  let progressTick = false;
  function requestProgressUpdate() {
    if (progressTick) return;
    progressTick = true;
    requestAnimationFrame(() => {
      progressTick = false;
      updateProgress();
    });
  }

  window.addEventListener('scroll', requestProgressUpdate, {passive:true});
  window.addEventListener('resize', requestProgressUpdate, {passive:true});
  window.addEventListener('load', requestProgressUpdate);
  progressReady = true;

  function addTopButton(body) {
    if (root.querySelector('.reading-top')) return;
    const top = document.createElement('a');
    top.className = 'reading-top';
    top.href = '#top';
    top.textContent = '↑ ऊपर';
    top.setAttribute('aria-label', 'लेख के ऊपर जाएँ');
    document.body.appendChild(top);

    const toggle = () => top.classList.toggle('is-visible', window.scrollY > 420);
    window.addEventListener('scroll', toggle, {passive:true});
    toggle();

    top.addEventListener('click', event => {
      event.preventDefault();
      window.scrollTo({top:0, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
    });
  }

  function addToc(body, meta) {
    const headings = [...body.querySelectorAll('h2,h3')];
    if (headings.length < 3 || root.querySelector('.reading-toc')) return;

    const toc = document.createElement('details');
    toc.className = 'reading-toc';
    const rows = headings.map((h,i) => {
      const anchor = `gw-section-${i+1}`;
      h.id = anchor;
      return `<li class="${h.tagName === 'H3' ? 'reading-h3' : ''}"><a href="#${anchor}">${esc(h.textContent)}</a></li>`;
    }).join('');

    toc.innerHTML = `<summary>इस लेख में</summary><ul>${rows}</ul>`;
    meta.insertAdjacentElement('afterend', toc);

    toc.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
      if (window.matchMedia('(max-width:560px)').matches) toc.removeAttribute('open');
    }));
  }

  function articleCard(a) {
    const image = String(a.image || a.coverImage || '').trim();
    const safeImage = /^images\/[A-Za-z0-9][A-Za-z0-9._/-]*\.(png|jpe?g|webp)$/i.test(image) && !image.includes('..') ? `./${image}` : '';
    return `<a class="reading-related-card" href="./article-dynamic.html?id=${encodeURIComponent(a.id)}">${safeImage ? `<img class="reading-related-thumb" src="${esc(safeImage)}" alt="" loading="lazy" decoding="async">` : ''}<span class="reading-related-title">${esc(a.title || a.id)}</span></a>`;
  }

  function addArticleDetails(body) {
    if (root.querySelector('.article-details')) return;
    const section = document.createElement('section');
    section.className = 'article-details';
    const formatDate = value => {
      if (!value) return '';
      const d = new Date(value);
      if (Number.isNaN(d.getTime())) return String(value);
      return new Intl.DateTimeFormat('hi-IN', {day:'numeric', month:'long', year:'numeric'}).format(d);
    };
    const author = article && article.author ? esc(article.author) : '';
    const authorUrl = article ? String(article.authorUrl || article.authorURL || '').trim() : '';
    const authorHtml = authorUrl && /^https:\/\//i.test(authorUrl)
      ? '<a href="' + esc(authorUrl) + '">' + author + '</a>'
      : author;
    const fields = [];
    if (author) fields.push('<div class="article-detail"><span class="article-detail-label">लेखक</span><strong class="article-detail-value">' + authorHtml + '</strong></div>');
    if (article && article.publishedAt) fields.push('<div class="article-detail"><span class="article-detail-label">प्रकाशित</span><strong class="article-detail-value">' + esc(formatDate(article.publishedAt)) + '</strong></div>');
    if (article && article.updatedAt && article.updatedAt !== article.publishedAt) fields.push('<div class="article-detail"><span class="article-detail-label">अपडेट</span><strong class="article-detail-value">' + esc(formatDate(article.updatedAt)) + '</strong></div>');
    if (article && article.category) fields.push('<div class="article-detail"><span class="article-detail-label">श्रेणी</span><strong class="article-detail-value">' + esc(article.category) + '</strong></div>');
    const tags = article && Array.isArray(article.tags) ? article.tags.map(t => String(t).trim()).filter(Boolean) : [];
    section.innerHTML = '<h2>लेख की जानकारी</h2><div class="article-details-grid">' + fields.join('') + '</div>' +
      (tags.length ? '<div class="article-tags"><strong>Tags:</strong> ' + tags.map(t => '<span class="article-tag">' + esc(t) + '</span>').join('') + '</div>' : '');
    body.insertAdjacentElement('afterend', section);
  }

  function addNavigation(list) {
    if (root.querySelector('.reading-pagination')) return;
    const index = list.findIndex(a => a && a.id === id);
    if (index < 0) return;
    const previous = list[index + 1];
    const next = list[index - 1];
    if (!previous && !next) return;

    const section = document.createElement('nav');
    section.className = 'reading-pagination';
    section.setAttribute('aria-label','लेख नेविगेशन');
    section.innerHTML =
      `<h2 style="grid-column:1/-1">आगे पढ़ें</h2>` +
      (previous ? `<a class="reading-page-link" href="./article-dynamic.html?id=${encodeURIComponent(previous.id)}"><small>← पिछला लेख</small><strong>${esc(previous.title || previous.id)}</strong></a>` : '<span></span>') +
      (next ? `<a class="reading-page-link" href="./article-dynamic.html?id=${encodeURIComponent(next.id)}"><small>अगला लेख →</small><strong>${esc(next.title || next.id)}</strong></a>` : '<span></span>');

    const related = root.querySelector('.reading-related');
    const top = root.querySelector('.reading-top');
    if (related) related.insertAdjacentElement('afterend', section);
    else if (top) top.insertAdjacentElement('afterend', section);
    else root.appendChild(section);
  }

  function addRelated(list) {
    if (root.querySelector('.reading-related')) return;
    const candidates = list.filter(a => a && a.id && a.id !== id);
    const same = candidates.filter(a => article && article.category && a.category === article.category);
    const related = (same.length ? same : candidates).slice(0,3);
    if (!related.length) return;

    const section = document.createElement('section');
    section.className = 'reading-related';
    section.innerHTML = '<h2>संबंधित लेख</h2><div class="reading-related-grid">' + related.map(articleCard).join('') + '</div>';
    const top = root.querySelector('.reading-top');
    if (top) top.insertAdjacentElement('afterend', section);
    else root.appendChild(section);
  }

  function enhance() {
    const title = root.querySelector('h1');
    const body = root.querySelector('.article-body');
    if (!title || !body || body.getAttribute('aria-busy') === 'true' || done) {
      if (progressReady) requestProgressUpdate();
      return;
    }

    // Wait for the same article JSON used by the reader before locking the enhancement state.
    // This prevents a refresh race where the reader renders first and metadata arrives second.
    if (!article) {
      if (progressReady) requestProgressUpdate();
      return;
    }

    done = true;
    const words = (body.innerText || '').trim().split(/\s+/).filter(Boolean).length;
    const readingMinutes = Math.max(1, Math.ceil(words / 200));
    const formatDate = value => {
      if (!value) return '';
      const d = new Date(value);
      if (Number.isNaN(d.getTime())) return String(value);
      return new Intl.DateTimeFormat('hi-IN', {day:'numeric', month:'long', year:'numeric'}).format(d);
    };
    const parts = [];
    if (article && article.author) {
      const authorText = esc(article.author);
      const authorUrl = String(article.authorUrl || article.authorURL || '').trim();
      parts.push(authorUrl && /^https:\/\//i.test(authorUrl)
        ? `लेखक: <a href="${esc(authorUrl)}">${authorText}</a>`
        : `लेखक: ${authorText}`);
    }
    if (article && article.publishedAt) parts.push(`प्रकाशित: ${formatDate(article.publishedAt)}`);
    if (article && article.updatedAt && article.updatedAt !== article.publishedAt) parts.push(`अपडेट: ${formatDate(article.updatedAt)}`);
    parts.push(`लगभग ${readingMinutes} मिनट पढ़ने का समय`);

    const meta = document.createElement('div');
    meta.className = 'reading-meta';
    meta.innerHTML = parts.map((bit,i) => (i ? '<span class="meta-sep" aria-hidden="true">·</span>' : '') + bit).join('');
    const date = root.querySelector('.date');
    if (date) date.remove();
    const share = root.querySelector('.article-share');
    (share || title).insertAdjacentElement('afterend', meta);

    addToc(body, meta);
    addTopButton(body);
    addArticleDetails(body);

    fetch('./data/articles.json').then(r => r.ok ? r.json() : null).then(data => {
      const list = Array.isArray(data) ? data : (data && Array.isArray(data.articles) ? data.articles : []);
      if (!list.length) return;
      addRelated(list);
      addNavigation(list);
      requestProgressUpdate();
    }).catch(() => {});

    requestProgressUpdate();
  }

  const observer = new MutationObserver(enhance);
  observer.observe(root, {childList:true, subtree:true});

  fetch(`./data/articles/${encodeURIComponent(id)}.json?v=20260924-3`)
    .then(r => r.ok ? r.json() : null)
    .then(a => { article = a; enhance(); })
    .catch(() => {});

  enhance();
})();
