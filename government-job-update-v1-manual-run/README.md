# ONESTOP Government Job Update — V1 Manual Run

Standalone V1 for the new ONESTOP Job Update System.

> **Do not connect this folder to the legacy `government-job-update/` implementation.** V1 is intentionally isolated.

## Current locked workflow

`PDF / URL → Extract → Predefined + Custom Fields → Dynamic Tables → Edit → Data Check → Preview → Manual Execute / Test Publish`

There is **no live production publishing** in V1. The public production Latest Government Jobs page will be integrated only after this manual workflow is validated.

## Files

- `admin.html` — manual-run admin interface
- `app.js` — PDF text extraction, URL extraction, field editor, custom fields, dynamic tables, links, validation and test execution
- `public-preview.html` — local/public test record preview
- `styles.css` — responsive UI
- `Code.gs` — standalone Apps Script test backend

## Backend capabilities in this build

- `GET ?action=health` — backend health check
- `GET ?action=latest` — latest test record
- `GET ?action=fields` — configured/default field definitions
- `GET ?action=bootstrap` — V1 bootstrap payload
- `POST action=crawlUrl` — fetch readable text from a supplied official URL
- `POST action=saveDraft` — save a verified draft record
- `POST action=publishTest` — save a verified test publication; never touches production
- `POST action=saveFields` — save configurable field definitions

## Google Sheet setup

Create a new Google Sheet dedicated to V1, for example:

`ONESTOP JOB UPDATE V1 — DATABASE`

Copy its spreadsheet ID and put it into `CONFIG.SHEET_ID` in `Code.gs`.

The backend can create these sheets automatically:

- `Jobs`
- `Fields`
- `Links`
- `Tables`

Do not use the legacy Government Job Update spreadsheet for V1.

## Apps Script deployment

1. Create a **new standalone Google Apps Script project** for this V1.
2. Add the contents of `Code.gs`.
3. Set `CONFIG.SHEET_ID`.
4. Replace `CONFIG.ADMIN_KEY` with a long private test key. Do not publish the key in the GitHub frontend.
5. Deploy as a Web App for the V1 test backend.
6. Keep the deployment URL private until the admin frontend is configured.

The frontend can then use the deployed `/exec` endpoint for URL extraction and test-backend actions.

## PDF extraction

Text-based PDFs are extracted in the browser using PDF.js. The extractor applies conservative field matching and always requires admin review before test publication.

Scanned/image-only PDFs are not silently treated as successfully extracted. They are flagged for OCR/manual entry in this V1.

## Security / scope

V1 does not include:

- automatic live publishing
- automatic web-wide crawling
- CAPTCHA bypass
- proxy rotation
- hidden endpoints
- unofficial-source auto-publishing
- candidate accounts or applications

The production website integration is deliberately postponed until the manual test flow is approved.
