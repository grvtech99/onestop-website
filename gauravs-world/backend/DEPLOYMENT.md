# Gaurav's World — Apps Script Backend Setup

## What is included

`Code.gs` is a starter API with two actions: `health` and `generateDraft`. It checks the executing user's email against `ADMIN_EMAIL` and calls the OpenAI Responses API from the server. It does **not** publish to GitHub yet.

## Configure in Apps Script

1. Create a new standalone Google Apps Script project.
2. Paste the contents of `Code.gs` into the script editor.
3. Open **Project Settings → Script Properties** and add:
   - `ADMIN_EMAIL`: the exact Google account email allowed to use this API
   - `OPENAI_API_KEY`: your OpenAI API key
   - `OPENAI_MODEL`: a model available to your API account (starter default: `gpt-4.1-mini`)
   - `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO`, `GITHUB_BRANCH`: reserved for the later publishing step; not used by this starter
4. Save and deploy as **Web app**. Prefer **Execute as: Me** and restrict access to the narrowest option that includes only your account. Do not choose public/anonymous access for an admin endpoint.
5. Test `doGet` while signed in as the allowed account. Confirm an unauthorized account cannot access it.

## Important identity caveat

`Session.getActiveUser().getEmail()` may be blank or unavailable depending on the deployment type and account context, especially for consumer Google accounts. If it cannot reliably return the signed-in admin email, this starter intentionally denies access. Do not work around this by making the endpoint public or by adding a password in client-side JavaScript. Use a backend with a verified identity provider if Apps Script cannot provide the required identity guarantee.

## API request format

Send a JSON POST body:

```json
{
  "action": "generateDraft",
  "title": "Computer Basics for Beginners",
  "category": "Computer Skills",
  "language": "Hindi",
  "notes": "Explain with practical examples"
}
```

The response is JSON with `ok: true` and a `draft` containing `title`, `category`, `language`, `summary`, `bodyMarkdown`, and `tags`.

## Security and current limitations

- Keep all API keys in Apps Script Script Properties, never in the website or repository.
- Do not commit real secrets to GitHub.
- Add stronger rate limiting, request-size limits, structured audit logging, and origin/CSRF protections before production use.
- This API currently returns generated drafts only. It does not write files to GitHub, upload images, authenticate the static Admin Draft Studio, or publish articles.
- Apps Script `ContentService` does not provide a configurable CORS policy. Browser integration may require a carefully designed proxy or a different backend. Do not weaken authentication to make browser calls work.
- Review generated content before publishing; model output can be incorrect.
