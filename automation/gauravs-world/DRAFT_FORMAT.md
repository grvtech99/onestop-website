# Gaurav’s World — Draft Format

This is the handoff format for the draft-only news workflow. It is intentionally separate from the live blog and does not publish or call the blog API.

## Required article fields

- `id`: stable deduplication key, derived from normalized source URL(s) and title.
- `title_hi`: Hindi headline.
- `title_en`: English headline.
- `slug`: URL-safe, unique slug (must be checked against existing posts before import).
- `category`: one of the site's existing categories; do not invent a category without editorial approval.
- `excerpt_hi` / `excerpt_en`: short bilingual summaries.
- `content_hi` / `content_en`: original article text in Hindi and English. Do not copy source paragraphs.
- `sources`: array of `{title, url, publisher, published_at}` for each source used.
- `image_prompt`: prompt for a newly generated illustrative image; do not reuse a publisher's image without permission.
- `image_alt_hi` / `image_alt_en`: descriptive alt text.
- `status`: always `draft` until a human explicitly approves publication.
- `review`: `{fact_check_required: true, reviewed_by: null, approved_at: null}`.

## Editorial and safety gates

1. Use at least two independent sources for consequential factual claims where available; clearly mark claims that rely on one source.
2. Keep source links adjacent to the claims they support. Distinguish reported facts, attributed claims, and analysis.
3. Verify dates, names, figures, and whether a report is new or an update to an older story.
4. Reject duplicates using both normalized URLs and semantic/title similarity review.
5. Avoid fabricated quotations, statistics, citations, or image provenance.
6. Require human review of the Hindi and English versions, source links, image, category, and slug.
7. Never set `published` automatically. Publication remains disabled until the backend contract and authorization are verified and the user explicitly approves the workflow.

## Current implementation boundary

The RSS stage collects candidate links only. Article generation, image generation, secure draft transfer, and publishing are not yet connected. The current workflow must not be described as a completed automatic article publisher.