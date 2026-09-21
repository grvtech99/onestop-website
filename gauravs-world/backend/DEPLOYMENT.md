# Gaurav's World — Apps Script Backend Deployment

## Current implementation

`Code.gs` exposes these actions:

- `GET`: admin identity check and service/version information.
- `POST {"action":"health"}`: authenticated health response.
- `POST {"action":"generateDraft", ...}`: asks the OpenAI Responses API for a structured draft.
- `POST {"action":"publishArticle", ...}`: writes an article JSON file and updates `gauravs-world/data/articles.json` through the GitHub Contents API.

The Admin Draft Studio at `admin/index.html` is still a browser-only editor/exporter. It is **not yet wired to call this API**, and image uploading is not implemented; publish requests can reference only an existing repository-relative image path under `images/`.

## Required Script Properties

In Apps Script, open **Project Settings → Script Properties** and configure these values. Keep secrets out of source code and the website.

| Property | Purpose |
|---|---|
| `ADMIN_EMAIL` | Exact allowed Google account email, normalized to lowercase by the script |
| `OPENAI_API_KEY` | Server-side OpenAI API key used for draft generation |
| `OPENAI_MODEL` | Model available to your API account; defaults to `gpt-4.1-mini` |
| `GITHUB_TOKEN` | GitHub token with the minimum required contents-write permission for the target repository |
| `GITHUB_OWNER` | `grvtech99` |
| `GITHUB_REPO` | `onestop-website` |
| `GITHUB_BRANCH` | `main` |

Do not paste any actual token or key into GitHub, HTML, screenshots, or chat messages.

## Deploy safely

1. Create or open the standalone Apps Script project intended for this backend.
2. Copy the current `gauravs-world/backend/Code.gs` from the repository into the script editor and save.
3. Set all required Script Properties above.
4. Select **Deploy → New deployment → Web app**.
5. For **Execute as**, use **Me** only if that is the intended GitHub-writing identity.
6. Set **Who has access** to the narrowest available option that genuinely restricts the endpoint to the admin account. Do not expose this privileged endpoint to anonymous/public users.
7. Deploy, copy the Web app URL privately, and test while signed in as the intended admin.
8. If code changes later, create a new version and update the deployment; saving the editor alone may not update the deployed version.

### Identity verification caveat

`Session.getActiveUser().getEmail()` can be blank or unavailable depending on deployment and account context, particularly for consumer Google accounts. The code denies requests when the email cannot be verified or does not match `ADMIN_EMAIL`. Do not bypass this by making the endpoint public or by putting a password in client-side JavaScript. If Apps Script cannot reliably provide the required identity guarantee, use a backend with a verified identity provider instead.

## API request examples

### Health

```json
{"action":"health"}
```

### Generate draft

```json
{
  "action":"generateDraft",
  "title":"Computer Basics for Beginners",
  "category":"Computer Skills",
  "language":"Hindi",
  "notes":"Explain with practical examples"
}
```

A successful response includes `draft.title`, `draft.category`, `draft.language`, `draft.summary`, `draft.bodyMarkdown`, and `draft.tags`.

### Publish article

```json
{
  "action":"publishArticle",
  "slug":"computer-basics-guide",
  "title":"Computer Basics Guide",
  "category":"Computer Skills",
  "summary":"A practical beginner-friendly guide.",
  "bodyMarkdown":"## Introduction\nArticle text...",
  "image":"images/computer-basics.webp"
}
```

`image` is optional and must refer to an already-existing image inside the repository's `gauravs-world/images/` directory. The backend validates the slug and basic text/path constraints, writes `gauravs-world/data/articles/<slug>.json`, and updates the manifest. Review generated content before publishing.

## Frontend routing

- The homepage loader merges published manifest entries with its built-in sample articles.
- Legacy sample IDs should continue opening `article.html`.
- Newly published IDs open `article-dynamic.html?id=<slug>` and load their JSON from `data/articles/<slug>.json`.
- The static admin page currently exports JSON locally; it does not yet authenticate or submit to the Apps Script API.

## Verification checklist (must be performed after deployment)

- [ ] Confirm the deployed `GET` response succeeds for the intended admin.
- [ ] Confirm an unauthorized account is denied; if identity is blank, treat deployment as not ready.
- [ ] Call authenticated `health` and verify `ok: true`.
- [ ] Generate a small draft and inspect the returned structure.
- [ ] Publish a test slug with an existing image or no image.
- [ ] Verify the new article JSON and manifest entry appear in the GitHub `main` branch.
- [ ] Open the returned dynamic article URL and verify the article renders.
- [ ] Verify existing legacy article links still open the legacy reader.
- [ ] Only after those tests, connect the Admin Draft Studio to the API using a secure design.

## Security and known limitations

- GitHub and OpenAI credentials belong only in Script Properties.
- The static Admin Draft Studio is not an authentication boundary. Do not treat a hidden URL or client-side password as protection.
- The backend has a request-size limit and generic error-message filtering, but production hardening still needs thoughtful rate limiting, audit logging, and abuse controls.
- Apps Script `ContentService` does not provide a configurable CORS policy. Browser integration may require a carefully designed proxy or a different backend. Do not weaken authentication to solve browser CORS errors.
- The backend has not been live-deployed or end-to-end tested as part of this repository change. A successful GitHub commit is not proof of a working deployment.
