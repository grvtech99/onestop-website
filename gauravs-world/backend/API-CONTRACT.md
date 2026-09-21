# Gaurav’s World — Backend API Contract (Draft)

Status: specification only. No endpoint is deployed or configured by this file.

## Architecture boundary

- The GitHub Pages site is public and must be treated as untrusted.
- All OpenAI and GitHub credentials stay in server-side environment secrets.
- The browser calls only the private backend URL configured by the operator.
- The backend authenticates every admin operation and validates every field independently.
- Never treat a hidden URL, client-side password, or CORS policy as authentication.

## Proposed routes

Base path: `/api/v1`

### `GET /health`
Public, read-only. Returns `{ "ok": true, "service": "gauravs-world-api", "version": "v1" }` without exposing configuration, secrets, user data, or provider status.

### `POST /admin/articles/generate`
Admin-authenticated. Request JSON:

```json
{
  "topic": "string, 3–180 chars",
  "audience": "string, max 160 chars",
  "language": "hi | en | hi-en",
  "category": "string, max 60 chars",
  "tone": "string, max 80 chars",
  "includeFaq": true
}
```

Returns a validated draft object; it does not publish automatically. Enforce request size limits, per-user rate limits, timeout, and provider error redaction.

### `POST /admin/articles/validate`
Admin-authenticated. Accepts the article object matching `../data/article-schema.json`. Returns `{ "valid": boolean, "errors": [] }`. Validation must run server-side.

### `POST /admin/articles/publish`
Admin-authenticated and protected by CSRF/origin checks where applicable. Accepts a validated article draft plus explicit `confirmPublish: true`. Backend creates or updates the article and its metadata in the configured GitHub repository using a narrowly scoped token. Return commit SHA and public article URL only after GitHub confirms success. Never accept arbitrary repository names, paths, or branch names from the browser.

### `POST /admin/images/publish`
Admin-authenticated. Accept only approved image MIME types, verify file signatures (not just extension), enforce configured byte/pixel limits, sanitize names, and store under the fixed `gauravs-world/images/` directory. Return the committed relative path after success.

## Authentication and security requirements

1. Use a server-verified identity/session (for example, a managed identity provider or signed, HttpOnly, Secure, SameSite cookie session). Do not implement a client-only password gate.
2. Require authorization on every `/admin/*` route; deny by default.
3. Use CSRF protection for cookie-authenticated mutations and validate allowed origins as defense in depth.
4. Keep `OPENAI_API_KEY`, `GITHUB_TOKEN`, session-signing keys, and provider secrets in backend secret storage only.
5. Give the GitHub token the minimum repository permissions required; never expose it to browser code or logs.
6. Add rate limits, request/body limits, timeouts, safe error messages, structured audit logs without secrets, and abuse monitoring.
7. Escape or safely render generated content; treat model output and uploaded files as untrusted.
8. Use idempotency keys or conflict checks for publish operations to prevent duplicate commits.
9. Keep preview/draft generation separate from publication; publication requires an explicit admin action.

## Standard response envelope

Success: `{ "ok": true, "data": {} }`

Failure: `{ "ok": false, "error": { "code": "SAFE_MACHINE_CODE", "message": "User-safe explanation" } }`

Do not return stack traces, tokens, environment values, raw provider responses, or private repository metadata.

## Suggested implementation sequence

1. Choose backend host and identity provider.
2. Configure secrets in that host’s secret manager.
3. Implement `/health` and authentication middleware.
4. Implement generation and schema validation without publishing.
5. Test abuse limits, authorization, malformed payloads, and secret redaction.
6. Add GitHub publishing with least privilege and explicit confirmation.
7. Connect Admin Draft Studio only after the deployed endpoint and auth flow are verified.

## Not implemented by this document

This contract does not create a server, provision hosting, configure OAuth, set secrets, call OpenAI, upload images, or publish articles. Those require a selected hosting/auth setup and operator-controlled credentials.