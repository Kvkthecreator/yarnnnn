# Session handoff — 2026-08-16: ADR-572 shipped; the Text click-pass is owed

`origin/main` at the ADR-572 commit. **The Text↔Docs parity arc is closed in
code and canon; what is owed is driving it.**

> The prior handoff (ADR-571 phase 2 — the canvas gap) is **ABSORBED**. Its
> audit ran, its table is in ADR-572 §1, and the build landed. Two of its
> starting-table rows were **wrong about Docs** and are corrected below so the
> mistake is not re-inherited.

## What shipped (ADR-572)

The Text canvas no longer shows raw markdown source. Read|Write toggle (Read
default), zoom, a doc-grade serif reading skin, a markdown toolbar
(⌘B/⌘I/⌘K + heading/list/task-list/quote/table/link/rule), find/replace (⌘F), a heading
outline in Properties, Print/PDF, a rendered landing thumbnail, a single-pane
bottom tab bar, and a load-error retry.

New modules under `web/components/text/`: `ProseReader.tsx`,
`MarkdownToolbar.tsx`, `FindReplaceBar.tsx`, `markdownEdits.ts`, `outline.ts`,
`printProse.ts`. `MarkdownRenderer` gained one opt-in prop (`scale`).

**ADR-456 D1 is intact and now gated as an absence over the whole app
directory** — no block ids, no `data-*`, no Studio machinery. The file stays a
plain `.md`.

## The one defect this arc found, and how

⭐⭐⭐ **`prose-sm` vs `prose-base` — two font-size rules on one element resolve
by STYLESHEET ORDER, not class order.** The document skin won *by luck* (the
compiled sheet happened to emit `prose-base` later); any unrelated file changing
which utilities Tailwind emits could have silently dropped every document to
chat size. **`next build`, `tsc`, and all 83 source-level gate checks were green
across it.** Only *rendering the pipeline and reading the output* caught it.

Fixed with an opt-in `scale?: 'chat' | 'inherit'` that **withholds** the class
rather than out-specifying it. Default `'chat'`, so all ~20 existing
`MarkdownRenderer` mounts are byte-identical (gated, §7o).

**Carry this forward: a class-attribute override is never proof of a cascade
override.**

## The Properties-pane question, settled with evidence (ADR-572 §3.1)

The operator asked whether dismissing `StudioDesignTab` wholesale was too
coarse. **It was**, so it was re-audited at CONTROL grain. The finding:

⭐⭐⭐ **Everything that is a TAG or a semantic type has a markdown equivalent;
everything that is PRESENTATION persists as `data-*`, an inline custom
property, or a `<head>` stylesheet.** That line is the same one ADR-456 D1
drew, reached independently from the write paths.

- Already shipped (tag-shaped): bold/italic/strike/code, the **typography
  ramp** (a tag swap `p ↔ h1..h6` that sets *no token* — it is literally
  `onTurnInto`), turn-into list/quote.
- Refused, with the write path quoted in the ADR: colour →
  `<span data-mark="accent">`, align → `data-align`, **document font →
  `data-font` on the artifact's `<html>`** (a `.md` has no root element).

Two things not to re-derive: **bold is a tag only because `projection.ts`
forces `styleWithCSS` off** (flip it and even bold has no markdown
equivalent); and **Docs already refuses point size / line spacing / font family
from itself** (ADR-449 — "those are METRICS and the design system owns them").

**If the reading face should look different, change the app's SKIN**
(`PROSE_READING_SKIN`, one place, every document) — never per-span state in the
file. The refusal is the feature; it protects the round-trip.

**Insert had one real gap: checklist** — GFM `- [ ] `, already renderable by
`remark-gfm`. Shipped. Everything else in the 16-kind palette needs `data-*`,
`data-ref` citations, or raw HTML.

## Two corrections to the old handoff's table — do not re-inherit them

- **"Docs has an outline nav"** — it has one *in the Properties pane*
  (ADR-526 D2), **not** a rail. ADR-542 D5 deleted flow's outline tab as "a dead
  doorway." Building a navigator rail would *exceed* Docs.
- **"Docs has find/replace"** — **it has none, anywhere.** Text's ⌘F is an
  addition beyond parity, taken because the medium needs it.

Also: Docs has **no markdown export**, and its right-click **"History" row is a
dead end** (`menuHistory` just calls `setRightTab('design')` onto a pane with no
history section). Not worth porting.

## What is OWED

1. **⭐ The operator click-pass** — the whole point, and the thing gates cannot
   do. ADR-572 §4 lists nine falsifiers. The sharpest four:
   - open a real 1,000-word `.md` → it reads as a **document** (serif headings,
     a real table, no visible `#`/`**`), not a source dump;
   - ⌘B over a selection wraps, pressing again **round-trips to the original
     bytes**;
   - the Properties outline jumps to the right line;
   - Export → Print/PDF looks like the Read view on A4.
2. **ADR-571 D6 click-pass** — still owed from the prior arc: launcher → Text →
   open a connector-authored `.md` → Editor lane speaks → save → **a 409 driven
   by a real MCP edit**.

## Deferred, deliberately — named so it is not re-discovered as novel

**`context-brief`** exists in `api/services/derive_recipes.py`, targets
**markdown**, resident `scout`, and has **zero FE consumers**. It is the Docs
"Learn from…" analog for prose and Text is its natural home. Left out because it
is a *creation* flow, not a reading/editing gap, and it needs its own decision
about where a derived brief lands.

## Verification that must stay green

```
cd api && python3 test_adr571_text_app.py             # 103/103, SCRIPT-STYLE (pytest = false pass)
node web/lib/file-types/__gate_adr514_d2.mjs          # 41/41, from REPO ROOT
cd api && python3 -m pytest test_lane_artifacts.py test_adr570_member_prose_door.py -q   # 19
cd api && python3 test_adr562_app_owned_config.py     # script-style
cd api && python3 test_adr297_navigation_enactment.py # 22/5 is the PRE-EXISTING baseline
cd web && node_modules/.bin/next build                # `pnpm` NOT on PATH; 171/171 pages
```

## Traps this arc paid for — do not re-pay them

- ⭐⭐⭐ **A green gate is not a rendered surface.** The scale collision passed
  every static check. When the claim is *visual*, **render it and inspect the
  output** — §7 of the gate now does this permanently.
- ⭐⭐⭐ **A gate can pass its own falsification by asserting its own argument.**
  7n's first spelling called `MarkdownRenderer` with `scale:'inherit'` itself,
  so it tested the probe's input, not the wiring. It now renders `ProseReader`.
  **Falsify every new check — a gate you have not broken is a gate you have not
  written.**
- ⭐⭐ **Never pin a spelling** (third time this arc): 6k first asserted the copy
  `"the request failed"` and went red because JSX had *wrapped it across a
  newline* — it was testing prettier, not the affordance. It now asserts the
  error branch contains a control that re-runs the fetch.
- ⭐ **Audit the reference implementation before copying it.** Two of the prior
  handoff's "Docs has…" rows were false; building them would have exceeded the
  app being mirrored while feeling like parity.
- ⭐ **Vercel FE deploys lag the push by minutes**, and client markers live in
  hashed chunks, so `curl` cannot detect them. Confirm the NEW bundle in the
  browser before concluding anything.
- The ADR-297 gate has **5 pre-existing failures** (`sources`, `system-agent`,
  `program`, `/openapi`). Do not chase them.

## Owed from earlier arcs (unrelated to Text, still open)

- **ADR-570 D8 click-pass** — the connector round-trip end to end, including a
  real MCP-driven 409. All pieces live; never driven as one pass.
- **ADR-495**: click-pass the quiet default (`b82d7b3`) — placeholder should
  read "Message Thinker…"; FE @-autocomplete for mentions is unbuilt.
- **ADR-514**: `DuplicateFile` is path-addressed but NOT gate-queueable, so its
  path branch is unreachable and the verb gates on nothing. ADR-514's to close.
