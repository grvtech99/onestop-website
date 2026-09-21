/* Gaurav's World published-article loader.
 * Merges published manifest entries with the homepage's existing articles.
 */
(function () {
  'use strict';
  const MANIFEST_URL = './data/articles.json';
  const root = document.getElementById('posts');
  const search = document.getElementById('search');
  const category = document.getElementById('category');
  if (!root || !search || !category || !Array.isArray(window.articles)) return;

  const fallbackArticles = window.articles.slice();
  const legacyIds = new Set(fallbackArticles.map(a => String(a.id)));
  const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[ch]);

  function render(list) {
    const q = search.value.trim().toLowerCase();
    const c = category.value;
    const filtered = list.filter(a => (c === 'all' || a.category === c) &&
      (String(a.title || '') + ' ' + String(a.description || a.summary || '') + ' ' + String(a.category || '')).toLowerCase().includes(q));
    root.innerHTML = filtered.length ? filtered.map(a => {
      const id = String(a.slug || a.id || '');
      const reader = legacyIds.has(String(a.id)) ? 'article.html' : 'article-dynamic.html';
      const date = a.date || (a.updatedAt ? new Date(a.updatedAt).toLocaleDateString() : 'Published');
      return `<article class="post"><span class="tag">${esc(a.category || 'General')}</span><h2>${esc(a.title)}</h2><p>${esc(a.description || a.summary || '')}</p><div class="meta">${esc(date)}</div><a class="read" href="${reader}?id=${encodeURIComponent(id)}">और पढ़ें →</a></article>`;
    }).join('') : '<div class="empty">कोई लेख नहीं मिला। दूसरा शब्द खोजें।</div>';
  }

  function normalize(item) {
    if (!item || typeof item !== 'object' || !item.title || !(item.slug || item.id)) return null;
    const id = String(item.slug || item.id);
    return { id, slug: id, title: String(item.title), category: String(item.category || 'General'),
      summary: String(item.summary || ''), description: String(item.summary || ''),
      image: String(item.image || ''), updatedAt: item.updatedAt || '' };
  }

  fetch(MANIFEST_URL, { cache: 'no-store' })
    .then(response => { if (!response.ok) throw new Error('manifest unavailable'); return response.json(); })
    .then(data => {
      const published = Array.isArray(data.articles) ? data.articles.map(normalize).filter(Boolean) : [];
      const byId = new Map(fallbackArticles.map(a => [String(a.id), a]));
      published.forEach(a => byId.set(a.id, a));
      window.articles = Array.from(byId.values());
      render(window.articles);
    })
    .catch(() => render(fallbackArticles));

  search.addEventListener('input', () => render(window.articles));
  category.addEventListener('change', () => render(window.articles));
})();
