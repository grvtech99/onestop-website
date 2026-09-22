/* Compact image-and-title article feed; newest first. */
(function () {
  'use strict';
  const MANIFEST_URL = './data/articles.json';
  const root = document.getElementById('posts');
  const search = document.getElementById('search');
  const category = document.getElementById('category');
  if (!root || !search || !category || !Array.isArray(window.articles)) return;

  const fallbackArticles = window.articles.slice();
  const legacyIds = new Set(fallbackArticles.map(a => String(a.id)));
  const esc = value => String(value == null ? '' : value).replace(/[&<>\"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;', "'": '&#39;' })[ch]);
  function timestamp(a) {
    const raw = a.updatedAt || a.publishedAt || a.date || a.createdAt || '';
    const value = Date.parse(raw);
    return Number.isFinite(value) ? value : 0;
  }
  function liked(id) {
    try { return localStorage.getItem('gw-liked-' + id) === '1'; } catch (_) { return false; }
  }
  function render(list) {
    const q = search.value.trim().toLowerCase();
    const c = category.value;
    const filtered = list.filter(a => (c === 'all' || a.category === c) &&
      (String(a.title || '') + ' ' + String(a.description || a.summary || '') + ' ' + String(a.category || '')).toLowerCase().includes(q))
      .slice().sort((a, b) => timestamp(b) - timestamp(a));
    root.innerHTML = filtered.length ? filtered.map(a => {
      const id = String(a.slug || a.id || '');
      const reader = legacyIds.has(String(a.id)) ? 'article.html' : 'article-dynamic.html';
      const href = `${reader}?id=${encodeURIComponent(id)}`;
      const image = String(a.image || a.coverImage || a.thumbnail || '');
      const imageMarkup = image ? `<div class="post-cover-link"><a class="post-image-open" href="${esc(href)}" aria-label="${esc(a.title)} पढ़ें"><img class="post-cover" src="${esc(image)}" alt="${esc(a.title)}" loading="lazy" decoding="async"></a><span class="post-actions"><button class="post-action like-action${liked(id) ? ' is-liked' : ''}" type="button" data-like="${esc(id)}" aria-label="Like" aria-pressed="${liked(id)}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z"/></svg></button><button class="post-action share-action" type="button" data-share="${esc(id)}" data-title="${esc(a.title)}" data-url="${esc(new URL(href, location.href).href)}" aria-label="Share"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.7 10.7 6.6-4.4M8.7 13.3l6.6 4.4"/></svg></button></span></div>` : `<div class="post-cover-link post-cover-placeholder">Gaurav’s World</div>`;
      return `<article class="post">${imageMarkup}<div class="post-content"><h2><a class="post-title" href="${esc(href)}">${esc(a.title)}</a></h2></div></article>`;
    }).join('') : '<div class="empty">कोई लेख नहीं मिला। दूसरा शब्द खोजें।</div>';
  }
  function normalize(item) {
    if (!item || typeof item !== 'object' || !item.title || !(item.slug || item.id)) return null;
    const id = String(item.slug || item.id);
    return { ...item, id, slug: id, title: String(item.title), category: String(item.category || 'General'),
      summary: String(item.summary || item.description || ''), description: String(item.summary || item.description || ''),
      image: String(item.image || item.coverImage || item.thumbnail || ''), updatedAt: item.updatedAt || '', publishedAt: item.publishedAt || item.date || '' };
  }
  root.addEventListener('click', async event => {
    const likeButton = event.target.closest('[data-like]');
    if (likeButton) {
      event.preventDefault(); event.stopPropagation();
      const id = likeButton.dataset.like;
      try {
        const next = !liked(id);
        if (next) localStorage.setItem('gw-liked-' + id, '1'); else localStorage.removeItem('gw-liked-' + id);
        likeButton.classList.toggle('is-liked', next);
        likeButton.setAttribute('aria-pressed', String(next));
      } catch (_) { likeButton.classList.toggle('is-liked'); }
      return;
    }
    const shareButton = event.target.closest('[data-share]');
    if (shareButton) {
      event.preventDefault(); event.stopPropagation();
      const data = { title: shareButton.dataset.title || 'Gaurav’s World', url: shareButton.dataset.url || location.href };
      try {
        if (navigator.share) await navigator.share(data);
        else if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(data.url);
          shareButton.setAttribute('aria-label', 'Link copied');
        } else window.prompt('Copy article link:', data.url);
      } catch (_) { /* Share dismissed or unavailable. */ }
    }
  });
  fetch(MANIFEST_URL, { cache: 'no-store' })
    .then(response => { if (!response.ok) throw new Error('manifest unavailable'); return response.json(); })
    .then(data => {
      const published = Array.isArray(data.articles) ? data.articles.map(normalize).filter(Boolean) : [];
      const byId = new Map(fallbackArticles.map(a => [String(a.slug || a.id), a]));
      published.forEach(a => byId.set(a.id, a));
      window.articles = Array.from(byId.values());
      render(window.articles);
    })
    .catch(() => render(fallbackArticles));
  search.addEventListener('input', () => render(window.articles));
  category.addEventListener('change', () => render(window.articles));
})();
