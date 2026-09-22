/* Published article loader: responsive image cards, newest first. */
(function () {
  'use strict';
  const MANIFEST_URL = './data/articles.json';
  const root = document.getElementById('posts');
  const search = document.getElementById('search');
  const category = document.getElementById('category');
  if (!root || !search || !category || !Array.isArray(window.articles)) return;

  const style = document.createElement('style');
  style.textContent = `
    #posts .post{padding:0;overflow:hidden;display:flex;flex-direction:column;min-width:0}
    #posts .post-cover-link{display:block;width:100%;aspect-ratio:4/3;overflow:hidden;background:#edf2f7}
    #posts .post-cover{display:block;width:100%;height:100%;object-fit:cover}
    #posts .post-content{padding:18px;min-width:0}
    #posts .post h2{margin:11px 0 8px}
    #posts .post-title{color:inherit;display:block}
    #posts .post-title:hover{color:var(--brand);text-decoration:underline}
    #posts .post p{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
    #posts .meta{overflow-wrap:anywhere}
    @media(max-width:560px){#posts .post-content{padding:15px}#posts .post h2{font-size:1.15rem}}
    @media(min-width:801px){#posts .post-cover-link{aspect-ratio:4/3}}
  `;
  document.head.appendChild(style);

  const fallbackArticles = window.articles.slice();
  const legacyIds = new Set(fallbackArticles.map(a => String(a.id)));
  const esc = value => String(value == null ? '' : value).replace(/[&<>\"']/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;', "'": '&#39;'
  })[ch]);

  function timestamp(a) {
    const raw = a.updatedAt || a.publishedAt || a.date || a.createdAt || '';
    const value = Date.parse(raw);
    return Number.isFinite(value) ? value : 0;
  }

  function render(list) {
    const q = search.value.trim().toLowerCase();
    const c = category.value;
    const filtered = list
      .filter(a => (c === 'all' || a.category === c) &&
        (String(a.title || '') + ' ' + String(a.description || a.summary || '') + ' ' + String(a.category || '')).toLowerCase().includes(q))
      .slice()
      .sort((a, b) => timestamp(b) - timestamp(a));

    root.innerHTML = filtered.length ? filtered.map(a => {
      const id = String(a.slug || a.id || '');
      const reader = legacyIds.has(String(a.id)) ? 'article.html' : 'article-dynamic.html';
      const href = `${reader}?id=${encodeURIComponent(id)}`;
      const rawDate = a.publishedAt || a.updatedAt || a.date || '';
      const parsed = Date.parse(rawDate);
      const date = Number.isFinite(parsed) ? new Date(parsed).toLocaleDateString() : (rawDate || 'Published');
      const image = String(a.image || a.coverImage || a.thumbnail || '');
      const imageMarkup = image ? `<a class=\"post-cover-link\" href=\"${esc(href)}\" aria-label=\"${esc(a.title)} पढ़ें\"><img class=\"post-cover\" src=\"${esc(image)}\" alt=\"${esc(a.title)}\" loading=\"lazy\" decoding=\"async\"></a>` : '';
      return `<article class=\"post\">${imageMarkup}<div class=\"post-content\"><span class=\"tag\">${esc(a.category || 'General')}</span><h2><a class=\"post-title\" href=\"${esc(href)}\">${esc(a.title)}</a></h2><p>${esc(a.description || a.summary || '')}</p><div class=\"meta\">${esc(a.author || 'Gaurav Yadav')} · ${esc(date)}</div><a class=\"read\" href=\"${esc(href)}\">पूरा लेख पढ़ें →</a></div></article>`;
    }).join('') : '<div class=\"empty\">कोई लेख नहीं मिला। दूसरा शब्द खोजें।</div>';
  }

  function normalize(item) {
    if (!item || typeof item !== 'object' || !item.title || !(item.slug || item.id)) return null;
    const id = String(item.slug || item.id);
    return { ...item, id, slug: id, title: String(item.title), category: String(item.category || 'General'),
      summary: String(item.summary || item.description || ''), description: String(item.summary || item.description || ''),
      image: String(item.image || item.coverImage || item.thumbnail || ''), updatedAt: item.updatedAt || '', publishedAt: item.publishedAt || item.date || '' };
  }

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
