# ONESTOP Government Job Update — Daily Operations

## Purpose

This document is the operating procedure for maintaining the ONESTOP Government Job Update system safely. The public page must contain only information that has been checked against an official source.

## Daily workflow

### 1. Open Source Review Center

Open `onestop-updates-review.html` and check the latest source health.

Review these official sources when relevant:
- SSC
- UPSC
- Employment News
- National Scholarship Portal

A **CHANGED** source is only a signal. It is not proof that a new recruitment notice exists.

### 2. Check the Review Queue

Open `onestop-update-review-queue.html`.

For every pending item:
- open the official source;
- identify the exact new or changed notice;
- confirm that it is relevant to ONESTOP Job Update;
- do not publish based only on a changed webpage or search result.

### 3. Verify the notice

Before approving an update, confirm all of these from the official notice:

- exact title;
- organisation and post name;
- vacancy / number of posts;
- important dates;
- eligibility / qualification;
- application fee;
- age limit and relaxations where applicable;
- selection process;
- official notification PDF;
- official application URL.

If the notice cannot be verified, reject it rather than guessing missing details.

### 4. Verified Draft

A verified item is placed in the Verified Drafts area. A verified draft is **not public**.

Open `onestop-updates-verified-drafts.html` and review the complete payload again.

### 5. Final Publication Review

Open `onestop-updates-publish.html`.

Use the authenticated **Create Publication Workflow** only after the verified draft has been checked again.

The generated publication PR must be reviewed for:
- official notice;
- vacancy;
- dates;
- eligibility;
- fee;
- age;
- selection;
- notice URL;
- application URL;
- public wording.

### 6. Approval and merge

The repository owner must explicitly approve the publication PR.

Only merge after all final checks are complete.

The publication workflow then performs the controlled update to the public Job Update data.

## Safety rules

1. Never treat a changed source as a confirmed vacancy.
2. Never copy recruitment details from an unofficial source when the official notice is available.
3. Never publish an unverified draft.
4. Never bypass the publication PR and approval gate.
5. Never manually edit public recruitment data with guessed information.
6. Keep official notice and application URLs separate and verify both.
7. If information is unclear, leave it as `Official notice में देखें` or reject the candidate rather than inventing details.
8. A failed source check should trigger manual verification; it should not trigger publication.

## When something goes wrong

### Source check failed
Use the official source links manually. If the source remains unavailable, wait for a later check or verify through another official government channel. Do not create a new update from a failure signal.

### Duplicate title detected
Do not bypass the duplicate check. Search the existing public data and determine whether the notice is actually a new recruitment cycle or an update to an existing item.

### Publication PR fails validation
Do not merge. Correct the draft or reject it, then create a fresh controlled publication PR after verification.

### Wrong information was published
Immediately stop further publication, verify the official notice, and prepare a corrective change through the same controlled review process. Do not silently overwrite details without verification.

## Recommended cadence

- Source monitoring: automatic daily check.
- Review Queue: check whenever a new changed-source item appears.
- Final publication: only when a verified notice is ready.
- Public content audit: periodically compare important active notices with their official sources.

## Status model

`Pending → In Review → Verified → Publication PR → Owner Approved → Published`

Alternative outcome:

`Pending → In Review → Rejected`

## Important distinction

The public ONESTOP Job Update page is the **published information layer**. Review Center, Review Queue, Verified Drafts and Publication Center are **operational control layers**. A source change must never directly cross into the public information layer without verification and final approval.
