# Gaurav's World automation (isolated scaffold)

This directory is deliberately separate from the live `gauravs-world/` website. It does not alter the Explore/Learn/Discover links, live blog files, or publish content.

## Planned workflow
- Scheduled news discovery: six times daily (UTC; GitHub may delay scheduled runs).
- Research and source verification across multiple sources.
- Original Hindi-first + English article generation.
- Generate a distinct illustrative cover image.
- Quality checks and duplicate detection.
- Save as a review-only draft; publishing remains disabled until the blog API is verified and owner approves.

## Current implementation status
This is a safe scaffold only. Provider-specific news search, LLM article generation, image generation, and blog draft API adapters are not configured. No secrets are included. The workflow will emit a setup-needed artifact rather than pretending it searched or published.

## Setup required before live automation
Add provider credentials via GitHub Actions Secrets (never commit keys), then implement and test the provider adapters. Verify the existing blog's backend contract before enabling draft transfer. Do not add a publishing token until that contract and access controls have been reviewed.
