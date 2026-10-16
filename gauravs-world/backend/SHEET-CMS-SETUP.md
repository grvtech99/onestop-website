# Gaurav's World — Google Sheets CMS Setup

## 1. Create the master Sheet
Use the supplied Gaurav's World Content CMS Template and open it with Google Sheets.

Keep these sheet names unchanged:
- CONTENT
- JOBS
- RESULTS
- ADMISSIONS
- ANSWER_KEY
- ADMIT_CARD
- EXAM_DATES
- SCHEMES
- SCHOLARSHIPS
- SETTINGS

The first row of each content sheet is the header row.

## 2. Connect the Sheet to the secure Admin
Open the secure Gaurav's World Admin web app using the configured admin Google account.
In Content Sync, paste only the Google Spreadsheet ID and click Connect Sheet.
The Spreadsheet ID is the part between /d/ and /edit in the Google Sheets URL.
The backend stores this ID in Apps Script Script Properties. The Sheet is read server-side with Apps Script's Spreadsheet service; it is not exposed to the public website.

## 3. Add content
Add a row to the appropriate sheet and set status = NEW.
For an existing row that you intentionally changed and want to re-import, set its status back to NEW.
Do not manually set adminId for a new row.

## 4. Sync
In Admin:
1. Preview Sync — checks rows before import.
2. Sync to Drafts — imports NEW/REVIEW rows into gauravs-world/data/drafts/.
3. The source row is then marked SYNCED.
4. The Admin editor loads the resulting draft for editorial review.
5. Save Draft or Publish remains a separate action.
This keeps spreadsheet ingestion separate from publication.

## 5. Structured sheets
JOBS, RESULTS, ADMISSIONS, ANSWER_KEY, ADMIT_CARD, EXAM_DATES, SCHEMES and SCHOLARSHIPS are converted into a standard Gaurav's World Markdown draft.
The conversion is deterministic: spreadsheet fields become labelled sections in the draft. The editor can then improve wording, add images, and publish.

## 6. Security
- Google Sheet access is server-side.
- Existing Admin authentication remains required.
- GitHub and OpenAI credentials remain in Apps Script Script Properties.
- No GitHub token, OpenAI key, or Sheet credentials are placed in browser JavaScript.
- Sync never publishes directly; it creates drafts.
- A row is marked SYNCED only after the GitHub draft write succeeds.

## 7. Required one-time Apps Script property
GAURAVS_WORLD_SHEET_ID = <your Google Spreadsheet ID>
The Admin's Connect Sheet button sets this property for you.

## 8. Deployment
The repository's GitHub Actions workflow now includes SheetSync.gs. Once the existing Apps Script CI/CD credentials are configured, backend changes can be synchronized through the existing deployment workflow.
## 9. First test run (recommended)
Use one test row first; do not start with bulk content.

### TEST 1 — CONTENT
In the CONTENT sheet, add one row with:
- type = ARTICLE
- category = Technology
- title = Gaurav's World CMS Test Article
- slug = gauravs-world-cms-test
- summary = Test article for Sheet CMS import.
- content = ## Test Article\n\nThis is a temporary CMS import test.\n\n### Verification\n\nConfirm that the text reaches the secure Admin draft editor.
- author = Gaurav
- status = NEW

Leave heroImage and tags empty for this first test.

### Verify
1. In Admin, click **Preview Sync**. The test row should appear.
2. Click **Sync to Drafts**.
3. Confirm the row changes from NEW to SYNCED.
4. Confirm the imported draft opens automatically in the Article Editor.
5. Check title, category, summary, body, slug and author.
6. Click **Save Draft** and verify the draft remains editable.
7. Only after all checks pass, use **Publish** if you want to test the live publication path.

### Cleanup
After testing, delete the temporary published article if it was published. If it was only a draft, use **Delete Draft** from the Admin editor.

## 10. Bulk rollout rule
After the first test succeeds, add real rows in small batches. Keep new rows at status = NEW. Review imported drafts before publishing; the Sheet sync is intentionally not an auto-publish mechanism.
