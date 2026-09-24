/* Gaurav's World — Article SEO v2
   Reads per-article SEO fields from data/articles/*.json and applies
   metadata, canonical URL, robots, Open Graph, Twitter and JSON-LD.
   Note: GitHub Pages query-string pages still rely on JS execution for
   per-article metadata; static prerendering is required for guaranteed
   social-crawler previews.
*/
(() => {
  'use strict';
  const params = new URLSearchParams(location.search);
  const id = params.get('id');
  if (!id || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id)) return;

  const ensureMeta = (key, value, property = false) => {
    if (value === undefined || value === null || value === '') return;
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

  const plain = value => String(value || '')
    .replace(/<[^>]*>/g, ' ')
    .replace(/[*_`#>]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  const defaultCanonical = new URL(`./article-dynamic.html?id=${encodeURIComponent(id)}`, location.href).href;

  const applyArticle = article => {
    if (!article || !article.title) return;

    const baseTitle = plain(article.title);
    const seoTitle = plain(article.seoTitle || baseTitle);
    const title = seoTitle ? `${seoTitle} | Gaurav's World` : "Gaurav's World";
    const description = plain(article.metaDescription || article.summary || article.description || article.excerpt || baseTitle);
    const socialTitle = plain(article.socialTitle || seoTitle || baseTitle);
    const socialDescription = plain(article.socialDescription || description);
    const imagePath = String(article.image || article.coverImage || '').trim();
    const image = /^https:\/\//i.test(imagePath)
      ? imagePath
      : /^images\/[A-Za-z0-9][A-Za-z0-9._/-]*\.(png|jpe?g|webp)$/i.test(imagePath) && !imagePath.includes('..')
        ? new URL(`./${imagePath}`, location.href).href
        : '';
    const canonical = /^https:\/\/[^\s]+$/i.test(String(article.canonicalUrl || '').trim())
      ? String(article.canonicalUrl).trim()
      : defaultCanonical;
    const indexable = article.indexable !== false;

    document.title = title;
    ensureMeta('description', description);
    ensureMeta('robots', indexable ? 'index,follow,max-image-preview:large' : 'noindex,nofollow');
    ensureMeta('keywords', plain(article.focusKeyword || (Array.isArray(article.tags) ? article.tags.join(', ') : article.tags || '')));

    ensureMeta('og:type', 'article', true);
    ensureMeta('og:site_name', "Gaurav's World", true);
    ensureMeta('og:title', socialTitle, true);
    ensureMeta('og:description', socialDescription, true);
    ensureMeta('og:url', canonical, true);
    ensureMeta('og:locale', 'hi_IN', true);
    ensureMeta('og:image', image, true);
    ensureMeta('og:image:alt', baseTitle, true);

    const published = article.publishedAt || article.date || '';
    const modified = article.updatedAt || published || '';
    if (published) ensureMeta('article:published_time', published, true);
    if (modified) ensureMeta('article:modified_time', modified, true);
    if (article.category) ensureMeta('article:section', plain(article.category), true);
    if (Array.isArray(article.tags)) article.tags.slice(0, 15).forEach(tag => ensureMeta('article:tag', plain(tag), true));

    ensureMeta('twitter:card', image ? 'summary_large_image' : 'summary');
    ensureMeta('twitter:title', socialTitle);
    ensureMeta('twitter:description', socialDescription);
    if (image) ensureMeta('twitter:image', image);

    ensureCanonical(canonical);

    const removeSchema = id => { const old = document.getElementById(id); if (old) old.remove(); };
    removeSchema('breadcrumb-jsonld');
    removeSchema('blogposting-jsonld');

    const categoryName = plain(article.category || 'लेख');
    const breadcrumbScript = document.createElement('script');
    breadcrumbScript.id = 'breadcrumb-jsonld';
    breadcrumbScript.type = 'application/ld+json';
    breadcrumbScript.textContent = JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'मुख्य पृष्ठ', item: new URL('./', location.href).href },
        { '@type': 'ListItem', position: 2, name: categoryName, item: new URL(`./?category=${encodeURIComponent(categoryName)}#posts`, location.href).href },
        { '@type': 'ListItem', position: 3, name: baseTitle, item: canonical }
      ]
    });
    document.head.appendChild(breadcrumbScript);

    const schema = {
      '@context': 'https://schema.org',
      '@type': 'BlogPosting',
      headline: baseTitle,
      name: baseTitle,
      description,
      inLanguage: 'hi',
      url: canonical,
      mainEntityOfPage: { '@type': 'WebPage', '@id': canonical },
      publisher: { '@type': 'Organization', name: "Gaurav's World", url: new URL('./', location.href).href }
    };
    if (article.category) schema.articleSection = plain(article.category);
    if (Array.isArray(article.tags)) schema.keywords = article.tags.map(plain).filter(Boolean);
    if (image) schema.image = [image];
    if (published) schema.datePublished = published;
    if (modified) schema.dateModified = modified;
    if (article.author) {
      schema.author = { '@type': 'Person', name: plain(article.author) };
      const authorUrl = article.authorUrl || article.authorURL;
      if (authorUrl && /^https:\/\//i.test(String(authorUrl))) schema.author.url = String(authorUrl);
    }

    const script = document.createElement('script');
    script.id = 'blogposting-jsonld';
    script.type = 'application/ld+json';
    script.textContent = JSON.stringify(schema);
    document.head.appendChild(script);
  };

  if (window.gwArticle) applyArticle(window.gwArticle);
  else window.addEventListener('gw:article-loaded', event => applyArticle(event.detail), {once:true});
})();