# Gaurav's World automation — isolated review pipeline

This directory is deliberately separate from the live `gauravs-world/` website. The workflow checks out `gauravs-world-automation`; it does not call the live blog API or publish content.

## Implemented in this branch
- RSS discovery across BBC, Guardian, TechCrunch, and Google News Hindi/India queries.
- URL/title duplicate validation artifact.
- OpenAI Responses API draft generation in Hindi-first + English, based on RSS metadata.
- OpenAI `gpt-image-1` cover illustration generation (no text/logos/watermarks).
- Up to 3 candidates per run, configurable through `MAX_DRAFTS_PER_RUN` in the workflow.
- Review JSONs under `automation/gauravs-world/output/drafts/` and cover PNGs under `automation/gauravs-world/images/`.
- Workflow attempts to commit generated review material only to `gauravs-world-automation` and uploads a downloadable artifact.
- Publication to the live blog is deliberately disabled. Human fact-check and approval are required.

## Required GitHub configuration
In repository Settings → Secrets and variables → Actions:
- Add repository secret `OPENAI_API_KEY` (never commit or paste it into chat).
- Optional repository variable `OPENAI_MODEL`, e.g. `gpt-4.1-mini`. If absent, the script defaults to that model.
- Ensure the repository Actions setting permits the workflow's `GITHUB_TOKEN` to write contents. The workflow requests `contents: write` and only pushes to the automation branch.

## Run it safely
1. Open the repository's Actions tab.
2. Select **Gaurav's World — News Review Drafts**.
3. Choose **Run workflow** and select branch `gauravs-world-automation`.
4. Open the run; inspect logs and download the `gauravs-world-review-drafts-*` artifact.
5. Review JSON drafts and image files before any manual use.

## Important limitations
- This workflow has not been executed end-to-end in the user's GitHub account; API billing, secret presence, permissions, and provider response must be confirmed by a real run.
- GitHub scheduled workflows execute from the repository's default branch. Since this workflow is isolated on `gauravs-world-automation`, the six-times-daily schedule will not run until the workflow is deliberately made available on the default branch. Do not merge it into the live branch without explicit approval. Use manual `workflow_dispatch` on the automation branch for testing.
- RSS descriptions are not full independent research. Generated text may lack context or contain errors; it must be checked against the linked sources. The script explicitly records that independent fact-checking has not occurred.
- Image generation may fail independently; the text draft is still saved with an image failure status.
- The workflow stores generated files in the automation branch; it does not upload them into the live site's image directory.
- The existing Apps Script `/exec` endpoint is not called. Its admin-only access and Postman 401 issue remain separate and are not bypassed.
- No automatic public publishing, social posting, or scheduled blog API transfer is enabled.
