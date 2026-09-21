# Gaurav's World — Private publishing backend plan

The public GitHub Pages site is static. Never place an OpenAI API key, GitHub token, admin password, or other secret in `index.html`, `article.html`, or browser-delivered JavaScript.

## Recommended separation
1. **Public site (GitHub Pages):** renders published articles and public images only.
2. **Private admin UI:** login-protected interface; a hidden URL or client-side password is not security.
3. **Server-side publishing endpoint:** authenticates the admin, calls OpenAI using a server-side secret, validates generated content, then commits approved content/images using a narrowly scoped GitHub credential.
4. **Approval gate:** drafts remain unpublished until the admin explicitly previews and approves them.

## Required protections before production
- Authenticate and authorize every write endpoint server-side.
- Keep OpenAI and GitHub credentials in server-side environment secrets, never in the repository or frontend.
- Restrict GitHub credential permissions to required repository operations.
- Validate request size, file types, image dimensions, article IDs, and content fields.
- Add rate limits, CSRF protection where cookie sessions are used, audit logs, and safe error messages.
- Use HTTPS and rotate/revoke credentials if exposed.
- Test unauthorized requests, expired sessions, malformed inputs, duplicate IDs, and failed upstream calls.

## Deployment status
This file documents the safe architecture only. No private backend, OAuth client, secrets, or deployment has been configured by this repository change. Those require the owner's hosting/account setup and explicit secret configuration.
