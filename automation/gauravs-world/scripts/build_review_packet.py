#!/usr/bin/env python3
"""Build a readable, review-only Markdown packet from validated RSS candidates."""
import json
from pathlib import Path

ROOT = Path("automation/gauravs-world/output")
SOURCE = ROOT / "candidate-validation.json"
TARGET = ROOT / "EDITOR_REVIEW.md"


def main():
    if not SOURCE.exists():
        raise SystemExit("Missing candidate-validation.json; run validation first.")
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    lines = [
        "# Gaurav's World — Editorial Review Packet",
        "",
        f"**Status:** {data.get('status', 'unknown')}  ",
        f"**Generated (UTC):** {data.get('generated_at_utc') or 'not supplied'}  ",
        f"**Candidates:** {data.get('accepted_count', 0)} accepted / {data.get('rejected_count', 0)} rejected",
        "",
        "> REVIEW ONLY — no article or image was generated, no blog API was called, and nothing was published.",
        "",
        "## Candidate sources",
        "",
    ]
    candidates = data.get("accepted", [])
    if not candidates:
        lines.append("No valid candidates in this run.")
    for i, item in enumerate(candidates, 1):
        title = str(item.get("title", "Untitled")).replace("\n", " ").strip()
        url = str(item.get("url", "")).strip()
        source = str(item.get("source", item.get("publisher", "Source not specified"))).replace("\n", " ").strip()
        published = str(item.get("published", item.get("published_at", "Date not supplied"))).replace("\n", " ").strip()
        lines.extend([
            f"### {i}. {title}",
            f"- Source: {source}",
            f"- Published: {published}",
            f"- Link: {url}",
            "- Editor decision: [ ] Keep  [ ] Reject  [ ] Needs fact-check",
            "- Proposed angle (editor fills in):",
            "- Key claims to verify:",
            "",
        ])
    lines.extend([
        "## Before any article generation",
        "",
        "- [ ] Open and read the original source; verify date and context.",
        "- [ ] Confirm the story is relevant and not a duplicate of recent posts.",
        "- [ ] Record at least two independent sources for consequential claims.",
        "- [ ] Mark uncertain or disputed details explicitly; do not invent facts.",
        "- [ ] Approve a specific topic and angle before drafting.",
        "",
        "## Publication gate",
        "",
        "Human review and explicit approval are required. This packet does not publish or change the live blog.",
        "",
    ])
    ROOT.mkdir(parents=True, exist_ok=True)
    TARGET.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote review packet: {TARGET} ({len(candidates)} candidates); review only.")


if __name__ == "__main__":
    main()
