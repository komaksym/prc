---
layout: structural-breakdown
layout_variant: exploded
style: technical-schematic
style_variant: isometric
aspect: 16:9
language: en
backend: codex-imagegen
---
Create a professional infographic following these specifications:

## Image Specifications

- **Type**: Infographic
- **Layout**: structural-breakdown (Exploded variant: parts separated outward, component relationships)
- **Style**: technical-schematic (Isometric variant: 30 degree blocks, clean fills)
- **Aspect Ratio**: 16:9
- **Language**: en

## Core Principles

- Follow the layout structure precisely for information architecture
- Apply style aesthetics consistently throughout
- Keep information concise, highlight keywords and core concepts
- Use ample whitespace for visual clarity
- Maintain clear visual hierarchy
- Render on an opaque light gray canvas (#F3F5F8) with a faint blue isometric grid and a thin clear outer border, so it reads on light or dark pages. High text contrast on its own surface. No transparent text or lines.

## Text Requirements

- All text must match the specified style treatment
- Main titles should be prominent and readable
- Key concepts should be visually emphasized
- Labels should be clear and appropriately sized
- Use English for all text content
- Render only the text labels listed below, spelled exactly; add no other words, numbers or captions

## Layout Guidelines

Internal structure visualization with labeled parts. Central subject: one pull request shown as a flat isometric base plate. Exploded view: five isometric blocks lifted outward and upward from the plate, each joined to its spot on the plate by a thin dashed vertical lift line. Callout lines with dots run from the plate to label boxes at the left and right edges. Title at top. Part labels sit on or beside each block. Brief text in callout boxes only.

## Style Guidelines

Technical diagram with engineering precision and clean geometry. Isometric 30 degree blocks with clean flat fills: blues (#2563EB) and teals for the five parts, gray for the base plate, white edge highlights. Amber accent (#F59E0B) for the single flow arrow and the two open-item callouts; one green check for the passed callout. Consistent stroke weights, clean vector shapes, small dimension ticks and technical annotation marks as decoration without text. Typography: clean sans-serif, all-caps labels for the parts, sentence case in callouts.

---

Generate the infographic based on the content below:

Top: the title and subtitle exactly as given in the text labels below.
Center: base plate "swarm-deploy #116"; five floating isometric blocks "gitops/git", "compose loader", "init job check", "shared/faults", "compose errors". One amber arrow from the "compose loader" block to the "compose errors" block, labelled "returns one type".
Left callouts (how it was built): a small icon of three cards with one checked, box "Arena: 3 layouts" with second line "parts map won"; a small icon of a play button beside a page, box "81-second video + page".
Right callouts (status): green check box "1129 tests pass"; amber box "Open: summary picture step"; amber box "Open: bent arrows".

Text labels (in en):
- Title: "System View: one PR, five parts"
- Subtitle: "Draft PR #11 · no code on screen"
- "swarm-deploy #116"
- "GITOPS/GIT", "COMPOSE LOADER", "INIT JOB CHECK", "SHARED/FAULTS", "COMPOSE ERRORS"
- "returns one type"
- "Arena: 3 layouts", "parts map won"
- "81-second video + page"
- "1129 tests pass"
- "Open: summary picture step"
- "Open: bent arrows"
