# Session handoff — 2026-08-16: ADR-572 shipped, click-passed, then RE-CUT to one canvas

`origin/main` at the ADR-572 click-pass commit. **The Text↔Docs parity arc is
closed and DRIVEN on production.** The reading face, outline, task lists,
tables, fences, save and the CAS 409 all pass on a real document. Two defects
were found by driving; one is fixed, one is handed off below because it belongs
to a different layer.

> The prior handoff (ADR-571 phase 2 — the canvas gap) is **ABSORBED**. Its
> audit ran, its table is in ADR-572 §1, and the build landed. Two of its
> starting-table rows were **wrong about Docs** and are corrected below so the
> mistake is not re-inherited.

## What shipped (ADR-572, as re-cut by D8)

**ONE canvas** (`ProseCanvas`, CodeMirror-grade): always editable, always
styled, no mode toggle. A permanent markdown toolbar (⌘B/⌘I/⌘K + heading /
list / **task list** / quote / table / link / rule), zoom, find via
`@codemirror/search`, a heading outline in Properties, Print/PDF, a rendered
landing thumbnail, a single-pane bottom tab bar, and a load-error retry.

### ⭐⭐⭐ Why D8 exists — the correction that matters most this arc

The operator looked at the shipped app and said **"i don't see them"** about
the formatting controls. They were all real and all gated green — and all
**behind Write mode, on a surface that opened in Read**. The feature set was
invisible on arrival.

And the split was never required: **ADR-456 D1 permits
"textarea/CodeMirror-grade"** — I read that *ceiling as a floor*, built the
textarea, then split the canvas to get styling back. CodeMirror is the option
the ADR names.

**Carry this forward: a feature behind a mode the surface does not open in is
a feature the member does not have.** And: read a constraint for what it
PERMITS, not only for what it forbids.

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

## The click-pass RESULT (driven on production, 2026-08-16)

**Passed** — canvas renders as a document (serif headings, bordered table,
bold/italic/strike, mono code, quote, divider); **task lists render as real
checkboxes** with checked state; a fenced `#` stays literal and is **absent
from the outline** (4 headings, not 5); the outline indents and updates live;
New → name → create → open works; Save lands a signed revision; the **CAS 409
fires**, preserves the member's text, and merges nothing silently.

### ⭐⭐⭐ Defect found and FIXED: the 409 envelope (ADR-572 D7)

The conflict banner appeared and was wrong **in two ways at once**. The API
serves the detail at `error.hint.current_head`; the client read FastAPI's older
`detail.current_head`. Both fields came back `undefined`, so the banner said
the generic **"Someone else"** instead of naming who moved the head — and
**the "Save mine over theirs" button VANISHED**, because it is conditional on
`currentHeadId`. One exit where the design promises two, and the silent half.

**103 gate checks, `tsc`, and `next build` were all green over it** — a field
read that yields `undefined` is not a type error, and the fallback string reads
like intended copy. `readConflict` now accepts either envelope; the gate replays
the **verbatim production 409 body** (§8) and falsifies.

### ⭐⭐ The stale surface param — FIXED (ADR-572 D9)

Diagnosed as a **registration omission, not a mechanism bug**. `reconcileUrl`
merges `{...incoming, ...remembered, ...delivered}`, so `remembered`
deliberately outranks the URL — which is exactly why document-identity params
are stripped from the remembered set. Every peer was listed (`docs.file`,
`studio.file`, `files.path`, `radar.file`, `strings.file`); **ADR-571 registered
`text` as OWNED and missed the EPHEMERAL registry.**

⭐⭐ **Third surface to miss a registry at birth** (radar, files before it), so
the gate asserts the **invariant** over all seven document surfaces rather than
the single row.

## Still OWED

1. **Print/PDF** — not driven: the print dialog is a native modal the harness
   cannot dismiss. Needs a human eye on the A4 output.
2. **ADR-571 D6, the MCP half** — not driveable in this environment: the
   connector and the browser session resolve to **different workspaces**, so
   connector writes 404 for the session and vice versa. The CAS 409 itself was
   proven via a second principal moving the head; what remains unproven is
   specifically the *connector-attributed* 409.

## Deferred, deliberately — named so it is not re-discovered as novel

**`context-brief`** exists in `api/services/derive_recipes.py`, targets
**markdown**, resident `scout`, and has **zero FE consumers**. It is the Docs
"Learn from…" analog for prose and Text is its natural home. Left out because it
is a *creation* flow, not a reading/editing gap, and it needs its own decision
about where a derived brief lands.

## Verification that must stay green

```
cd api && python3 test_adr571_text_app.py             # 119/119, SCRIPT-STYLE (pytest = false pass)
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
