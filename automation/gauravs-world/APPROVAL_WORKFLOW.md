# Gaurav’s World — Draft Review & Approval Workflow

This document describes the human-in-the-loop process for the news-draft pipeline. It does not enable publishing.

## Current pipeline boundary

The scheduled workflow collects and validates RSS candidates, runs the current status script, and uploads the output as a GitHub Actions artifact. Article generation, image generation, and blog API writes are not connected in the current implementation. Treat candidate feeds as leads—not verified reporting.

## Review steps

1. Open the latest successful workflow run in GitHub Actions.
2. Download its output artifact and inspect the candidate JSON and validation report.
3. Open each source URL directly. Confirm the article exists, note its publication date, and verify claims against the source—not just the headline or feed excerpt.
4. Select a topic only after checking relevance, recency, source quality, and duplication against recent Gaurav’s World posts.
5. Prepare a Hindi-first article with a faithful English counterpart. Attribute claims and distinguish verified facts from uncertainty.
6. Create or select an illustrative image that does not imply it is a photograph of a real event unless it genuinely is and is properly licensed.
7. Complete `REVIEW_CHECKLIST.md`. Return for revision if any material check fails.
8. Record the exact reviewed version and reviewer decision. Any substantive edit after approval requires another review.

## Publication gate

Publishing remains disabled until all of the following are verified:

- The blog backend/API contract and authentication model are documented and tested.
- The destination supports a genuine draft/unpublished state.
- Credentials are stored only as GitHub Actions secrets or an appropriate secret manager, never in repository files or article artifacts.
- The integration has safe failure handling, duplicate prevention, and a test path that cannot alter the live blog.
- A human explicitly approves the exact article and image version.

Until then, keep output as review artifacts and manually transfer approved material using the existing trusted blog workflow. Do not interpret a green Actions run as publication success.

## Suggested decision record

- Candidate/source URLs:
- Source publication dates:
- Draft version or commit:
- Image file and license/generation note:
- Reviewer:
- Decision: APPROVE / REVISE / REJECT
- Corrections and notes:
- Approval date:
