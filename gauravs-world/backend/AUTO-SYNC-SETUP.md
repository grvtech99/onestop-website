# Gaurav's World — Apps Script Auto-Sync

This repository is the source of truth for the secure admin backend.

## What the workflow does

When files under `gauravs-world/backend/` change on `main`:

1. GitHub Actions authenticates to the existing Apps Script project.
2. It clones the current Apps Script project first, so existing remote files/manifest are preserved.
3. It replaces the GitHub-controlled `Code.gs` and `Admin.html`.
4. It pushes those files to Apps Script.
5. It creates a new immutable Apps Script version.
6. It redeploys the existing production deployment to that new version.

The production deployment ID is kept in a GitHub Secret, so the public web-app URL does not need to change.

## One-time setup

Google's clasp CI/CD documentation requires these GitHub Actions secrets:

- `CLASPRC_JSON`: the contents of the authenticated `~/.clasprc.json`.
- `CLASP_DEPLOYMENT_ID`: the existing production web-app deployment ID.

Also enable the Google Apps Script API for the Google account/project used by clasp.

Do **not** commit `.clasprc.json`, OAuth credentials, or access tokens to GitHub.

After these two secrets exist, no future Code.gs/Admin.html copy-paste into Apps Script is required. A commit to `main` will perform the sync automatically.

## Safety

The workflow only runs for backend changes. It uses the existing deployment ID rather than creating a new public deployment, and it clones the current Apps Script project before pushing so files not controlled by this repository are retained.
