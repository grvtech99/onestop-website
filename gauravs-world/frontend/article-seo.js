/* Dynamic metadata for the article reader. Note: social crawlers may not execute JS; prerendering/static article HTML is needed for guaranteed previews. */
(() => {
  'use strict';
  const params = new URLSearchParams(location.search);
  const id = params.get('id');
  if (!id || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id)) return;

  const ensureMeta = (key, value, property = false) => {
    if (!value) return;
    const attr = property ? 'property' : 'name';
    let el = document.head.querySelector(`meta[${attr}="${key}"]`);
    if (!el) {
      el = document.createElement('meta');
      el.setAttribute(attr, key);
      document.head.appendChild(el);
    }
    el.setAttribute('content', String(value).slice(0, 1000));
  };
  const ensureCanonical = url => {
    let el = document.head.querySelector('link[rel="canonical"]');
    if (!el) {
      el = document.createElement('link');
      el.rel = 'canonical';
      document.head.appendChild(el);
    }
    el.href = url;
  };
  const plain = value => String(value || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
  const canonicalUrl = new URL(`./article-dynamic.html?id=${encodeURIComponent(id)}`, location.href).href;

  fetch(`./data/articles/${encodeURIComponent(id)}.json`)
    .then(response => {
      if (!response.ok) throw new Error('Article unavailable');
      return response.json();
    })
    .then(article => {
      if (!article || !article.title) return;
      const title = `${plain(article.title)} | Gaurav's World`;
      const description = plain(article.summary || article.description || article.excerpt || article.title);
      const imagePath = String(article.image || article.coverImage || '').trim();
      const image = /^https:\/\//i.test(imagePath)
        ? imagePath
        : /^images\/[A-Za-z0-9][A-Za-z0-9._/-]*\.(png|jpe?g|webp)$/i.test(imagePath) && !imagePath.includes('..')
          ? new URL(`./${imagePath}`, location.href).href
          : '';

      document.title = title;
      ensureMeta('description', description);
      ensureMeta('og:type', 'article', true);
      ensureMeta('og:site_name', "Gaurav's World", true);
      ensureMeta('og:title', title, true);
      ensureMeta('og:description', description, true);
      ensureMeta('og:url', canonicalUrl, true);
      ensureMeta('og:image', image, true);
      ensureMeta('twitter:card', image ? 'summary_large_image' : 'summary');
      ensureMeta('twitter:title', title);
      ensureMeta('twitter:description', description);
      if (image) ensureMeta('twitter:image', image);
      ensureCanonical(canonicalUrl);

      const old = document.getElementById('blogposting-jsonld');
      if (old) old.remove();
      const schema = {
        '@context': 'https://schema.org',
        '@type': 'BlogPosting',
        headline: plain(article.title),
        description,
        mainEntityOfPage: { '@type': 'WebPage', '@id': canonicalUrl },
        publisher: { '@type': 'Organization', name: "Gaurav's World" }
      };
      if (image) schema.image = [image];
      const published = article.publishedAt || article.date;
      const modified = article.updatedAt || published;
      if (published) schema.datePublished = published;
      if (modified) schema.dateModified = modified;
      if (article.author) schema.author = { '@type': 'Person', name: plain(article.author) };
      const script = document.createElement('script');
      script.id = 'blogposting-jsonld';
      script.type = 'application/ld+json';
      script.textContent = JSON.stringify(schema);
      document.head.appendChild(script);
    })
    .catch(() => { /* Keep the existing reader usable if metadata lookup fails. */ });
})();
