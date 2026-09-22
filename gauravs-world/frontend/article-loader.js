/* Published article reader enhancement. Include after the existing legacy reader script. */
(() => {
  'use strict';
  const params = new URLSearchParams(location.search);
  const id = params.get('id');
  const legacy = new Set(['computer-basics','online-safety','ai-tools','digital-skills','pdf-mobile','typing-practice']);
  if (!id || legacy.has(id) || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id)) return;
  const root = document.getElementById('article');
  if (!root) return;
  const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const inline = text => esc(text)
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>');
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
  fetch(`./data/articles/${encodeURIComponent(id)}.json`, {cache:'no-store'})
    .then(r => { if (!r.ok) throw new Error('not found'); return r.json(); })
    .then(a => {
      if (!a || !a.title) throw new Error('invalid article');
      const body = a.bodyMarkdown || a.body || a.content || '';
      const imagePath = String(a.image || a.coverImage || '').trim();
      const imageUrl = /^images\/[A-Za-z0-9][A-Za-z0-9._/-]*\.(png|jpe?g|webp)$/i.test(imagePath) && !imagePath.includes('..') ? `./${imagePath}` : '';
      const cover = imageUrl ? `<figure class="article-cover"><img src="${esc(imageUrl)}" alt="${esc(a.title)}" loading="eager" decoding="async"></figure>` : '';
      root.innerHTML = `<span class="tag">${esc(a.category || 'General')}</span><h1>${esc(a.title)}</h1>${cover}<p class="date">${esc(a.updatedAt || a.date || 'Published')}</p>${a.summary ? `<p class="notice">${esc(a.summary)}</p>` : ''}<div class="article-body">${markdown(body)}</div>`;
      const img = root.querySelector('.article-cover img');
      if (img) img.addEventListener('error', () => { const figure = img.closest('figure'); if (figure) figure.remove(); });
      document.title = `${a.title} | Gaurav's World`;
    })
    .catch(() => { root.innerHTML = '<p>यह लेख अभी उपलब्ध नहीं है। कृपया सभी लेखों पर वापस जाएँ।</p>'; });
})();
