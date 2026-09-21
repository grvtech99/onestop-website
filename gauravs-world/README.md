# Gaurav's World — fresh rebuild

This folder is a new lightweight static blog entry point, built independently of the deleted project.

## Current files
- `index.html` — responsive, dependency-free landing page with client-side search and topic filtering.

## Performance approach
- No framework, external font, image library, or runtime spreadsheet/API request on initial load.
- Inline CSS and small vanilla JavaScript; responsive cards and search.
- Add optimized WebP/AVIF images only when needed, with explicit dimensions and lazy loading.

## Important status
The landing page is created, but this is not yet a complete publishing CMS. A secure admin publishing flow needs a server-side credential holder (for example, a small authenticated backend). Never put a GitHub personal access token, OpenAI API key, or other secret in browser HTML/JavaScript. GitHub Pages is static hosting and cannot securely perform privileged publishing by itself.

## Next implementation items
1. Add article detail routing and a content data format.
2. Set up authenticated server-side publishing and image upload.
3. Connect the domain/path and verify GitHub Pages deployment, mobile behavior, and performance.
