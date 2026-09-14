# ONESTOP Government Update — Secure Admin Access

## Security model

`admin.html` is a read-only monitoring UI. It must **not** implement password authentication in JavaScript, because a password embedded in a static GitHub Pages site is not a security boundary.

The supported production model is:

```text
Browser
  ↓
Cloudflare Access / Zero Trust identity login
  ↓
Authorized admin policy
  ↓
GitHub Pages admin.html
  ↓
Read-only monitoring JSON
```

The GitHub Actions token remains server-side inside GitHub Actions. No GitHub token or secret is sent to the browser.

## One-time infrastructure configuration

Because GitHub Pages itself is static hosting, the final authentication boundary must be configured at the domain/edge layer. This cannot safely be completed by editing repository HTML alone.

### Cloudflare Access (recommended)

1. Put `onestopfzd.in` behind Cloudflare DNS/proxy.
2. Open Cloudflare Zero Trust → Access → Applications.
3. Create a **Self-hosted** application for the ONESTOP domain.
4. Protect the admin page path:
   - `/government-job-update/admin.html`
5. Also protect the admin monitoring JSON paths so they cannot be read anonymously:
   - `/government-job-update/data/admin-dashboard-state.json`
   - `/government-job-update/data/admin-execution-status.json`
6. Create an **Allow** policy containing only the administrator's identity (for example, the administrator's verified email address or an approved identity-provider group).
7. Do not create a public/Everyone Allow policy for these paths.
8. Keep the public updates page outside the protected application:
   - `/government-job-update/onestop-updates.html`
9. Test in an incognito window:
   - public updates → accessible
   - admin page → login required
   - admin JSON → login required
   - non-authorized account → denied

### Important

The authentication provider is intentionally external to the static page. This prevents credentials, client secrets, session-signing keys, and GitHub tokens from being shipped to visitors.

## Existing application safeguards

- `meta robots=noindex,nofollow` is set on the admin page.
- The UI is read-only.
- No GitHub token is exposed.
- No repository write operation is exposed to the browser.
- Government publication remains verified-only.
- SarkariResult remains the only discovery source.
- Official government/recruitment authority remains the final verification authority.
- 403/429/CAPTCHA/access-control bypass is prohibited.
- Controlled E2E is explicitly not treated as production discovery.

## GitHub Actions

The workflow writes only non-sensitive execution metadata to `admin-execution-status.json`. The file contains run identifiers, commit SHA, step outcomes, and a GitHub Actions run URL; it does not contain secrets.

For stronger privacy, keep the two admin JSON paths behind the same Access policy as the admin page.

## If Cloudflare Access is not available

Do **not** replace it with a frontend password, hard-coded PIN, hidden URL, Base64 credential, or localStorage flag. Those are not secure authentication mechanisms for a public static site.

Use a real identity/access gateway before exposing the admin route.
