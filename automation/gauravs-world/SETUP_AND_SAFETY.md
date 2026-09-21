# Gaurav's World Automation — Setup & Safety

## Current state
The scheduled workflow collects RSS candidates, validates them, and uploads a review artifact. The current `run.py` is intentionally a status-only stub. It does **not** generate articles or images, call the blog API, or publish.

## Workflow location
GitHub Actions only discovers workflow files under the repository-root `.github/workflows/` directory. The automation branch has `/.github/workflows/gauravs-world-news-drafts.yml`; the older nested copy under `automation/gauravs-world/.github/` is not an active Actions workflow and should be treated as historical until removed deliberately.

## Before enabling AI generation
1. Choose and document an approved text-generation provider and image-generation provider.
2. Add credentials only in repository **Settings → Secrets and variables → Actions**. Never commit keys or paste them into chat.
3. Implement provider adapters that read credentials from environment variables, enforce timeouts/retries, and redact secrets from logs.
4. Keep generated content in the workflow artifact or a private review location. Do not write to the live blog.
5. Validate each draft against `ARTICLE_GENERATION_SPEC.md` and `DRAFT_FORMAT.md`; require source URLs, bilingual consistency, duplicate checks, and explicit review status.
6. Test with a manual workflow run and inspect the artifact before relying on scheduled runs.

## Image handling
Generate a fresh illustrative image from the approved prompt. Store the generated asset with the draft and include alt text in Hindi and English. Do not reuse source-article images or imply an illustrative image is documentary evidence. Provider/API configuration is not implemented yet.

## Publishing gate
Publishing remains disabled. Do not implement blog writes until the exact backend API contract, authorization model, and draft-vs-publish semantics have been verified from the backend source. Any eventual publish action must require a separate explicit human approval step and must never be triggered by the six-times-daily schedule.

## Schedule
The workflow's cron expression is `15 0,4,8,12,16,20 * * *` (six times daily in UTC). GitHub may delay scheduled runs. This schedule alone does not prove that a run succeeded; inspect the Actions run and artifact.
