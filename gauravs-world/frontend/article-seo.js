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

  fetch(`./data/articles/${encodeURIComponent(id)}.json?v=20260924-2`)
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

      const oldBreadcrumb = document.getElementById('breadcrumb-jsonld');
      if (oldBreadcrumb) oldBreadcrumb.remove();
      const breadcrumbScript = document.createElement('script');
      breadcrumbScript.id = 'breadcrumb-jsonld';
      breadcrumbScript.type = 'application/ld+json';
      const categoryName = plain(article.category || 'लेख');
      breadcrumbScript.textContent = JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'मुख्य पृष्ठ', item: new URL('./', location.href).href },
          { '@type': 'ListItem', position: 2, name: categoryName, item: new URL(`./?category=${encodeURIComponent(categoryName)}#posts`, location.href).href },
          { '@type': 'ListItem', position: 3, name: plain(article.title), item: canonicalUrl }
        ]
      });
      document.head.appendChild(breadcrumbScript);

      const old = document.getElementById('blogposting-jsonld');
      if (old) old.remove();
      const schema = {
        '@context': 'https://schema.org',
        '@type': 'BlogPosting',
        headline: plain(article.title),
        description,
        inLanguage: 'hi',
        mainEntityOfPage: { '@type': 'WebPage', '@id': canonicalUrl },
        publisher: { '@type': 'Organization', name: "Gaurav's World", url: new URL('./', location.href).href }
      };
      if (article.category) schema.articleSection = plain(article.category);
      if (article.tags) schema.keywords = Array.isArray(article.tags) ? article.tags.map(plain).filter(Boolean) : plain(article.tags);

      if (image) schema.image = [image];
      const published = article.publishedAt || article.date;
      const modified = article.updatedAt || published;
      if (published) schema.datePublished = published;
      if (modified) schema.dateModified = modified;
      if (article.author) {
        schema.author = { '@type': 'Person', name: plain(article.author) };
        const authorUrl = article.authorUrl || article.authorURL;
        if (authorUrl && /^https?:\\/\\//i.test(String(authorUrl))) schema.author.url = String(authorUrl);
      }
      if (image) ensureMeta('og:image:alt', plain(article.title), true);
      const script = document.createElement('script');
      script.id = 'blogposting-jsonld';
      script.type = 'application/ld+json';
      script.textContent = JSON.stringify(schema);
      document.head.appendChild(script);
    })
    .catch(() => { /* Keep the existing reader usable if metadata lookup fails. */ });
})();
