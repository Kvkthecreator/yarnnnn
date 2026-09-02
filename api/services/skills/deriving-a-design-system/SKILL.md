---
name: deriving-a-design-system
description: Derives a design system from a referent (a brand guide, a stylesheet, a screenshot, a site) as a meaning-folder of tokens-first CSS plus a manifest artifacts can wear, naming the kernel's contract variables. Use when asked to extract, derive, or set up a design system, brand tokens, or a theme.
metadata:
  target: A meaning-folder satisfying the ADR-449 contract — _design.yaml (name + ordered css) + the css files it lists.
---
# Deriving a design system

Produce a DESIGN SYSTEM — a meaning-folder that satisfies the workspace
design-system contract, so Studio artifacts can wear it and the workspace can
track what depends on it.

The contract (must hold exactly):
- A folder (e.g. 'design-system/' or a name the member prefers) containing
  `_design.yaml` with `name:` (display name) and `css:` (an ORDERED list of
  folder-relative css files — list ONLY files you actually created).
- The css files themselves, tokens FIRST: a custom-properties block (:root
  color / type-scale / spacing / radius / shadow variables), then component
  rules built on those variables.

Steps:
1. Read the source and EXTRACT evidence: explicit tokens (css variables,
   tailwind config values, brand-guideline values), recurring colors, type
   choices, spacing rhythms. Note each value's origin.
2. Write the token css first, then a small rules layer, then `_design.yaml`.
   Name the Studio's kernel-consumed variables when the source evidences them
   — the chrome (buttons, galleries, toggles, tone fills, headings, hairlines)
   themes through exactly this vocabulary (DESIGN-SYSTEMS.md §5), so hitting
   these names is what makes an artifact visibly wear the system:
     • color     --ink (text) · --paper (surface) · --muted · --accent
     • ink ramp  --ink-06 · --ink-10 (the hairline borders — the structural
                 signature of a restrained system; set them and every rule/
                 divider/table-border themes)
     • radius    --radius-sm · --radius-md · --radius-lg · --radius-pill (a
                 SCALE; --radius-pill: 9999px is what makes buttons pills)
     • type      --text-xs · --text-sm · --text-base · --text-lg · --text-xl ·
                 --text-2xl · --text-3xl · --text-4xl · --text-5xl (a SCALE;
                 headings + captions read these)
     • semantic  --fresh · --danger · --warn (status color — callout
                 variants render --fresh/--warn since ADR-487 D2)
     • faces     --font-serif · --font-sans · --font-mono (what each font
                 FAMILY resolves to — the member's typeface choice routes
                 through these; ADR-487 D4)
   Additional variables are welcome, but a value the source shows that maps
   onto one of these names should USE that name — a `--brand` orange the chrome
   never reads themes nothing. If the source names its accent something else
   (`--yarn-orange`), either name it `--accent` too OR add a `maps:` block to
   `_design.yaml` bridging it: `maps:\n  accent: --yarn-orange`.
3. Re-read `_design.yaml` and verify every listed file exists and the order
   is tokens-before-rules.

Quality bar:
- Every value evidenced in the source — never invent brand values; if the
  source is thin, produce fewer tokens and say so in the lane, don't pad.
- Lean: tokens + reusable component rules only.

Anti-patterns: dumping entire stylesheets verbatim (derive, don't mirror);
page-specific selectors (#hero-2024) in a system meant to be reusable;
inventing a palette the source doesn't show; a manifest listing files you
didn't write.
