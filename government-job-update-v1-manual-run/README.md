# ONESTOP Government Job Update — V1 Manual Run

This is a new standalone prototype. The legacy `government-job-update/` workflow is not used by V1.

## V1 purpose

Manual test flow only:

`PDF / URL → Extract → Edit → Data Check → Preview → Execute`

Nothing is published to the live website from this prototype. `Execute` stores the verified test record in browser localStorage and downloads a JSON snapshot so the data contract can be inspected before a real backend is connected.

## Files

- `admin.html` — manual-run admin prototype
- `public-preview.html` — renders the current local test record
- `app.js` — extraction, fields, tables, validation and local execution
- `styles.css` — responsive UI

## PDF extraction

V1 extracts text from text-based PDFs in the browser using PDF.js and applies conservative field matching. Scanned/image-only PDFs are reported as requiring OCR/manual entry; they are never silently treated as successfully extracted.

## Safety

No crawler, CAPTCHA bypass, proxy rotation, hidden endpoint, automatic publication or unofficial-source auto-publish is included in V1.
