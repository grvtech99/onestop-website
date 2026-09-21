# Admin Studio ↔ Apps Script integration

## Current state

- `admin/index.html` is a browser-only draft editor/exporter.
- `Code.gs` exposes `health`, `generateDraft`, and `publishArticle` handlers.
- The Admin Studio has **not** been connected to the deployed endpoint.
- The endpoint URL must not be guessed or committed as a secret.

## Important deployment constraint

Apps Script web apps use Google identity/session behavior that varies by account and deployment. `Session.getActiveUser().getEmail()` may be blank for some consumer-account deployments. `ContentService` also does not provide configurable CORS headers, so a direct browser `fetch()` from the static site may fail even if the script is deployed. Do not work around this by making the endpoint public or placing a shared password/token in the HTML.

## Required setup before wiring the browser UI

1. Deploy the Apps Script as a Web App with the narrowest supported access setting.
2. Set Script Properties: `ADMIN_EMAIL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `GITHUB_TOKEN`, `GITHUB_OWNER=grvtech99`, `GITHUB_REPO=onestop-website`, `GITHUB_BRANCH=main`.
3. Confirm the deployed URL works only for the intended admin identity, and test `Session.getActiveUser().getEmail()` in that exact deployment.
4. Test `doPost` from an authorized environment. Verify both success and denied access.
5. Choose a browser-compatible authenticated transport. If direct browser calls are blocked by CORS, use a same-origin server/proxy with real authentication; do not expose a bearer token or use a public unauthenticated proxy.

## API request shapes

### Generate draft

```json
{
  "action": "generateDraft",
  "title": "Mobile se PDF kaise banaye",
  "category": "Digital Services",
  "language": "Hindi",
  "notes": "Explain practical Android steps"
}
```

Expected success shape:

```json
{
  "ok": true,
  "draft": {
    "title": "...",
    "category": "...",
    "language": "...",
    "summary": "...",
    "bodyMarkdown": "...",
    "tags": []
  }
}
```

### Publish article

```json
{
  "action": "publishArticle",
  "slug": "mobile-pdf-guide",
  "title": "Mobile se PDF kaise banaye",
  "category": "Digital Services",
  "summary": "...",
  "bodyMarkdown": "...",
  "image": "images/mobile-pdf-guide.webp"
}
```

The current backend writes the JSON file to `gauravs-world/data/articles/<slug>.json`. It does **not** upload images or update the homepage article listing automatically. The current article reader/homepage must be updated to load this data format before published entries appear automatically.

## Acceptance tests

- Missing/incorrect admin identity is denied.
- Missing OpenAI/GitHub properties returns a safe error without revealing secrets.
- Invalid slug, path traversal, oversized request, invalid JSON, and unsupported action are rejected.
- A successful draft returns the required JSON fields.
- Publish creates or updates only the expected `gauravs-world/data/articles/<slug>.json` path.
- Public homepage can read the published article only after the data-loading integration is implemented.
- No API keys, GitHub tokens, or reusable admin credentials exist in repository HTML/JS.
