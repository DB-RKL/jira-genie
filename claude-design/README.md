# Jira Analytics — Claude Design Package

Upload this folder (or the zip) to [claude.ai/design](https://claude.ai/design) to generate a customer-facing presentation.

## Quick start (2 minutes)

1. Go to **claude.ai/design**
2. Choose **Presentation** / slide deck
3. **Upload** `slides-content.md` (or the whole zip)
4. **Paste** the contents of `PROMPT.txt` as your design brief
5. Optional: attach Databricks design system if your org has one configured
6. Generate, iterate, then **Export → PPTX** or **PDF**

## What's in this package

| File | Purpose |
|------|---------|
| `PROMPT.txt` | Copy-paste master prompt for Claude Design |
| `slides-content.md` | Full slide copy — upload as reference document |
| `slides.json` | Structured 12-slide spec (titles, layouts, bullets, notes) |
| `design-direction.md` | Visual style, layout, and brand guidance |

## Recommended Claude Design prompt flow

**First message** — paste `PROMPT.txt` and attach `slides-content.md`.

**Follow-ups** (if needed):
- "Make slide 9 an architecture flow diagram left-to-right"
- "Use a 2x2 card grid on slides 3 and 4"
- "Add a stat highlight on slides 5–8"
- "Export as PPTX when done"

## Audience & positioning

- **Audience:** Engineering leaders, PMO, platform owners
- **Tone:** Outcome-first, customer-facing, not internal/dev
- **Positioning:** Pilot-ready accelerator on Databricks — not oversold as turnkey enterprise prod
- **Duration:** ~20 minutes (12 slides)

## Do not include in slides

- Personal catalog names, emails, or internal workspace hosts
- Deep technical implementation details (save for appendix if asked)
