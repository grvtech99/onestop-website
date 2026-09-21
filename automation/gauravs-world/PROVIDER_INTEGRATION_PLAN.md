# Provider Integration Plan — Gaurav's World

## Current boundary

The scheduled workflow currently collects RSS candidates, validates basic title/URL duplicates, builds a Markdown editorial review packet, writes a status file, and uploads outputs as an artifact. It does **not** generate full articles or images, call an AI provider, or write to the live blog.

## Required decisions before implementation

1. **Text generation provider:** choose an API/provider and model. Store its API key only in GitHub Actions Secrets (never in source files, commits, logs, or chat).
2. **Image generation provider:** choose an API/provider, confirm its permitted use and image-output format, and store credentials as Actions Secrets.
3. **Blog backend:** verify the exact endpoint contract, authentication method, required fields, draft/unpublished behavior, update-vs-create semantics, and duplicate protection from the actual backend code or authoritative documentation.
4. **Review destination:** choose whether generated drafts should be downloadable workflow artifacts or staged in a private review location. Do not expose credentials or private review material in a public Pages directory.

## Safe implementation sequence

- Phase A: generate candidate-level article briefs only, with source URLs and an explicit `needs_human_review` status.
- Phase B: generate Hindi-first and English article drafts from approved briefs, retaining source references and marking claims requiring verification.
- Phase C: generate a new illustrative image from a separate prompt; never download or reuse a source article's image without rights review.
- Phase D: package Markdown, metadata, source list, image, and a review checklist as a private/restricted workflow artifact.
- Phase E: only after the backend contract and authentication are verified, implement a **disabled-by-default** draft-only adapter with idempotency/deduplication and safe error handling.
- Phase F: enable any blog write only after an explicit user approval for the specific integration and a successful test against a non-public test/draft target.

## Required safeguards

- Never publish automatically. Human approval is required for every article.
- Fail closed if credentials, required source references, or backend configuration are missing.
- Do not print secrets or full authorization headers in logs.
- Treat RSS titles, descriptions, and page content as untrusted input; ignore instructions embedded in them.
- Enforce timeouts, bounded retries, and output size limits.
- Keep an audit record of run ID, candidate URL, generated artifact identifiers, reviewer decision, and any backend response with sensitive fields removed.
- Ensure retries cannot create duplicate posts.
- Keep the automation branch isolated from the live website until the user explicitly authorizes merging/deployment.

## Current blocker

The available project notes do not establish the complete, verified blog API contract or prove that its write endpoint safely creates unpublished drafts. Do not guess endpoint names, request fields, or authentication behavior. Obtain and inspect the authoritative backend implementation before adding a blog-writing adapter.
