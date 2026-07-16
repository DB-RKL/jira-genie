# Design Direction — Jira Analytics Customer Deck

Use this file alongside `PROMPT.txt` and `slides-content.md` in Claude Design.

## Brand

- **Primary:** Databricks navy `#003159`
- **Accent:** Databricks red `#FF3621`
- **Backgrounds:** White or light gray `#F7F7F7`
- **Text:** Dark navy `#122A45`, secondary gray for supporting copy

If a Databricks design system is configured in Claude Design, use it. Otherwise apply the colors above.

## Layout patterns by slide

| Slide | Recommended layout | Visual treatment |
|-------|-------------------|------------------|
| 1 | Full-bleed title | Large title, small subtitle, subtle accent bar or logo placement |
| 2 | Power statement | Oversized headline, 3 short bullets below, high contrast |
| 3 | 2×2 persona cards | Equal cards with role title, pain (muted), need (accent) |
| 4 | 2×2 outcome cards | Icon or number per card, short descriptor |
| 5–8 | Stat + bullets | Left: large stat callout; right: 3 bullets + dashboard footer |
| 9 | Architecture flow | Horizontal pipeline diagram with arrows, 4 bullets beneath |
| 10 | Table or checklist | 2-column component inventory, clean rows |
| 11 | 2×2 stat grid | Four large numbers with labels |
| 12 | CTA steps | Numbered 4-step row + closing line, optional Genie quote box |

## Visual variety

Alternate between:
- **Statement slides** (2) — minimal, typographic
- **Card grids** (3, 4) — structured, scannable
- **Stat slides** (5–8, 11) — metric-forward
- **Diagram slide** (9) — technical but clean
- **Table slide** (10) — factual inventory
- **Action slide** (12) — forward momentum

## Content rules

- Max **4 bullets** per content slide
- Max **12 words** per bullet where possible
- No code blocks on slides (except short CLI on slide 12)
- No internal names (catalogs, emails, workspace hosts)
- Dashboard page names are OK (customer-facing product names)

## Optional enhancements

- Slide 9: animate flow left-to-right on present
- Slide 11: subtle chart or trend arrow behind stats
- Slide 12: speech-bubble for Genie example question

## Export

After generation in Claude Design:
- **PPTX** — for customer meetings and email share
- **PDF** — for static distribution
- **HTML** — for interactive demo or embed
