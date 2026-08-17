# ADR-572: The reading face — Text reaches Docs' depth without block grade

> **Status**: **Accepted + Implemented** (2026-08-16, operator-directed:
> *"essentially all the Docs features and look-and-feel that can sensibly apply
> to plain prose. A direct comparison against the Docs implementation is fine —
> mimic it."*)
> **Date**: 2026-08-16
> **Dimension**: **Channel** (the surface's depth) primary.
> **Relates to**: ADR-571 (the app whose depth this completes), ADR-456 D1 (the
> grade constraint — the one thing this ADR must not break), ADR-518 (Docs, the
> app being mirrored), ADR-526 D2 (the outline's home is the pane, not a rail),
> ADR-542 D5 (flow ships no nav tab), ADR-466 D6 (the print-as-projection
> technique), ADR-570 (the write door, unchanged).
> **Amends**: ADR-571 D1 (the app's affordance set), and retires ADR-571's
> stated reason for withholding Print/PDF.

---

## 1. Context — the gap ADR-571 left

ADR-571 gave prose a dedicated app with the right *shape*: a landing, a naming
dialog, a renaming crumb, boundary acts, a Properties|Chat rail. Every gate was
green. Beside Docs it still read as thin, and the operator named why with a
screenshot: **the canvas showed raw monospace source.** `# Creative Brief`,
`**not**`, `---` — a 1,062-word brief rendered as a source dump while Docs
renders a document with serif headings and styled tables.

That is a *look-and-feel* gap on the surface and a *depth* gap behind it: Docs
is ~5,600 lines across 26 modules, Text was ~1,100 across 4.

### The audit, and two corrections to the premise

Before building, Docs was audited feature by feature. Two findings changed the
target:

1. **Most of the 5,600 lines are ineligible by construction.** `StudioDesignTab`
   alone is 2,856 lines of design-system/skin/token machinery — the machinery
   ADR-456 D1 forbids here. The line-count gap overstates the *feature* gap
   badly.
2. **Docs itself lacks several things the gap was assumed to include.** Docs has
   **no find/replace anywhere**, **no left navigator on flow** (ADR-542 D5
   deleted the outline tab as "a dead doorway"), **no markdown export** (its own
   panel says so), and its right-click **"History" row is a dead end** — the
   handler just calls `setRightTab('design')` onto a pane with no history
   section. Parity with Docs would have meant *not* building some of these.

So "mimic Docs" resolved to: **take everything that survives the medium
translation, decline the block machinery out loud, and add the two things the
medium genuinely needs that Docs happens not to have.**

## 2. Decisions

### D1 — The canvas has two faces, and a rendered view is not a block model

> **SUPERSEDED BY D8** (same day). This shipped a Read/Write toggle: a rendered
> view you could not type into, and a textarea you could. It hid every
> formatting control behind a mode the surface did not open in, and it was not
> required by the constraint. Kept here because the *reasoning below* about what
> makes a view legal is what D8 builds on — the mode split is what was wrong,
> not the "a rendered view is not a block model" argument.

**Read** renders the markdown (`ProseReader`); **Write** is the textarea ADR-456
D1 requires. One source of truth (`text`), one direction of flow (source →
render). **Read is the default on open** — an existing document is something you
arrive to read.

The grade constraint is honored *because the render never writes*: it holds no
ids, mints nothing, annotates nothing, and maps no node back to an offset.
Delete `ProseReader` and the file is byte-identical. That is the test a view
passes and a block model fails, and it is gated as an absence over the whole app
directory (`data-block-id`, `data-block=`, `StudioCanvas`, `FlowEditor`,
`prosemirror`, `resolveArtifactHtml` — §6L).

**Live-render/edit-in-place was considered and rejected**: transforming markdown
in place as you type requires mapping every rendered node back to a source
offset, which is the annotation table this app is not allowed to keep. The
toggle was chosen precisely because it needs no such map.

**One pipeline, not two.** `MarkdownRenderer` is the workspace's single markdown
implementation and stays that; Text adds a *skin*, not a parser.

> **The scale collision (found by rendering, invisible to every other check).**
> `MarkdownRenderer`'s resting face is `prose-sm` — tuned for chat bubbles.
> Passing `prose-base` alongside it put **two font-size rules on one element**,
> and CSS resolves that by **stylesheet order, not class order**. Measured in
> the compiled sheet: `prose-base` was emitted later and won — *by luck*. Any
> unrelated file changing which utilities Tailwind emits could have silently
> dropped every document to chat size. Fixed by adding an opt-in
> `scale?: 'chat' | 'inherit'` prop that **withholds** the scale classes rather
> than out-specifying them. `'chat'` is the default, so all ~20 existing mounts
> are byte-identical (gated, §7o). `next build`, `tsc`, and all 83 source-level
> checks were green across this defect.

### D2 — View controls: zoom, and a thumbnail that tells the truth

Zoom is ported with Docs' own clamp (0.25–2, click-to-reset), applied to both
faces. It rides CSS `zoom` rather than `transform: scale` so the column reflows
at its scaled measure — a "zoom" that needs horizontal scrolling to read one
line is a crop.

The landing's `ProseThumb` now **renders** its preview as markdown instead of
showing raw source, which is the honest analog of Docs' scaled-iframe
`ArtifactThumb`. A card reading `# Creative Brief` while the document it opens
reads *Creative Brief* is the landing telling a small lie about the app. No
extra fetch — `recent-revisions` already computes `preview`.

### D3 — The outline is addressed by SOURCE LINE, not by block id

Docs carries an outline in its Properties pane (ADR-526 D2: "the pane is the
structure's home" — the same reading that deleted Studio's navigator rail). Text
mirrors it, and **must not mirror its addressing**: Docs walks
`data-block-id`, the banned mechanism.

**A line number is a coordinate into the bytes; a block id is an annotation on
them.** The outline is parsed from the source (ATX + setext, fence-aware,
CommonMark's space rule), and jumping selects a character range in the textarea.
Nothing is written. This is the distinction that lets the feature exist at all,
and it is gated by execution (§6ah).

No navigator rail is built. Docs deliberately has none on flow, and adding one
would exceed the app being mirrored.

### D4 — The boundary acts reach full parity; Print/PDF becomes possible

ADR-571 withheld Print/PDF on honest grounds — *"a prose document has no
rendered form, so print-to-PDF would be printing a textarea."* D1 removes that
blocker, so Docs' technique (ADR-466 D6: render to an HTML string, inject an A4
print sheet, hand it to a hidden iframe's `print()`) ports directly. What you
print is what you were reading — the same renderer produces both.

The print sheet is a **paper** face, not the screen face: real serif families
(the screen's `font-serif` token does not exist inside the iframe), black on
white, and the orphan/widow/`break-after` rules a screen never needs.

Markdown export needs no row: **the file already is markdown**, so Download
answers the sentence Docs' own panel defers to "the interchange wave."

### D5 — Source affordances Docs does not have, taken because the medium needs them

- **Find/replace (⌘F).** Docs has none. Text's documents are the long ones, and
  a 1,000-word brief without find is worse to work in than a 200-word artifact.
  It searches the **source**, and reveals matches by *selecting* them — the
  browser's own position map — rather than painting a highlight layer, which
  would need exactly the offset table D1 forbids.
- **A markdown toolbar (⌘B/⌘I/⌘K + heading/list/quote/table/link/rule).** This
  is the legal half of Docs' Insert menu: Docs inserts *blocks*; this inserts
  *characters*. Every button routes through pure `string → string` functions,
  and the result is the markdown a member would have typed by hand — a connector
  cannot tell a toolbar press from a keystroke. That property is why it is
  allowed, and it is gated by **calling** the functions, not by grepping them.

### D6 — What stays deliberately UNLIKE Docs

**Docs autosaves** (2s idle + blur + beforeunload, no Save button, no dirty
state, 409 auto-retried silently). **Text keeps explicit Save + ⌘S + a dirty
indicator**, because the CAS conflict here is a *product surface*: a connector
may hold the same file, and ADR-570's 409 names who moved the head. A member
needs to know which bytes are theirs before that conversation starts. Recorded
as a divergence rather than drifted into.

### D8 — ONE canvas: CodeMirror-grade, the option D1 should have taken

> **Operator correction, same day**: *"do we need to split the modes? like docs
> app can we just have one mode"* — and before that, plainly: *"i don't see
> them"* (the formatting controls).

**D1's Read/Write toggle is deleted.** It was wrong twice over:

1. **It hid the app.** The toolbar, the task-list button and find all lived in
   Write mode, and the surface *opened in Read*. Every control ADR-572 shipped
   was invisible on arrival. The operator looked at the app and did not see the
   features — because they were behind a mode.
2. **It was not required by the constraint.** ADR-456 D1 permits
   *"textarea/**CodeMirror**-grade, never block-grade"*. I read that ceiling as
   a floor, built the textarea, and then split the canvas to get styling back.
   CodeMirror is the option the ADR names, and it gives one always-editable,
   always-styled canvas.

`ProseCanvas` is that canvas: `@codemirror/lang-markdown` for the grammar, a
`HighlightStyle` carrying the same serif hierarchy `PROSE_READING_SKIN` defines,
the toolbar as a permanent row above it, and `@codemirror/search` for find.

**Why this is not block-grade** — the property the whole thesis rests on:
CodeMirror's document is a **plain string**, and styling is a decoration layer
recomputed from it on each update. Nothing enters the document; no node maps
back to a source position; no id is minted. A block editor stores a tree with
identity and serializes it back out. Gated in §9 by **executing** the round
trip: deliberately awkward markdown (mixed `*`/`+` bullets, setext underlines,
tabs, trailing spaces, a fence) comes back **byte-identical**, and §9f1 asserts
this component's own change handler emits the document unmodified.

> That second check exists because the first one **passed a falsification**: a
> normalizing `.replace()` inserted into the update listener left §9f green,
> since §9f tested CodeMirror's state in isolation rather than my wiring. The
> "gate tests the library, not the caller" shape, caught by falsifying.

**D8 CLICK-PASSED on production** (2026-08-16, cold load — no clicks first,
which is the arrival state the mode split failed): the toolbar's 13 buttons are
visible immediately with **no mode toggle** anywhere; headings render large and
serif with the `#`/`##` dimmed beside them, `**bold**` bold, `~~strike~~`
struck, `` `code` `` mono, the table aligned. Driven end to end: click into the
canvas → type → press **Heading 1** → the source gains `# ` and the Properties
outline updates → press **Task list** → the line becomes `- [ ] `. **Bold
round-trips**: pressing it twice returns the original bytes exactly. Throughout,
the file on disk stayed **byte-identical and free of any `data-*`** — the canvas
never wrote (verified against the API, not the DOM).

> **A probe artifact worth recording**, because it nearly produced a false
> negative: a synthesized `window.getSelection()` is **ignored** by CodeMirror,
> which reads `view.state.selection`. Scripted selection made the toolbar act on
> a *stale caret* and looked like a broken button. Only a real click + real
> keystrokes exercise the actual path — the same lesson as driving the surface
> at all, one level down.

**Deleted, not kept beside it** (singular implementation): `FindReplaceBar` and
the `findAll`/`replaceOne`/`replaceAll` helpers — `@codemirror/search` is the
better find (incremental, match-highlighted, regex-capable) and two searches
would be a dual implementation. `ProseReader` **survives** for the two places
that need a rendered document with no editor attached: the landing thumbnail
and Print/PDF.

**The honest limitation**: the markdown marks stay **visible** — `## Heading`
renders large and serif with a dimmed `##` still present (the Obsidian/iA
Writer face). Hiding them requires knowing which rendered node owns which
source range, i.e. the node↔offset map that is the banned shape. Named here so
the absence does not read as an oversight. Print/PDF and the landing thumbnail
still show the fully-clean render, because neither has a caret.

### D9 — `text.file` is document identity: owned, but never replayed

The stale-param defect the D8 click-pass surfaced, diagnosed and fixed. **It is
a registration omission, not a mechanism bug.**

`reconcileUrl` merges `{...incoming, ...remembered, ...delivered}` — the
remembered set deliberately **outranks** the incoming URL. That is why
document-identity params are stripped from `remembered`
(`SURFACE_EPHEMERAL_PARAM_KEYS`): a drill-in must never become a permanent
landing target. Every peer surface is listed — `docs.file`, `studio.file`,
`images.file`, `files.path`, `radar.file`, `strings.file`. **ADR-571 registered
`text` in `SURFACE_PARAM_KEYS` (owned) and missed the ephemeral one**, so a
stored document id beat whatever the member asked for.

Symptoms, all one cause: `/text?text.file=A` landed on B; a bare `/text`
reopened the last document; an explicitly emptied `?text.file=` was refilled;
and a **trashed** document kept reopening.

**Text is the third surface to miss a registry at birth** (radar 2026-08-13,
files before it), so §10 gates the **invariant**, not the row: every surface
owning a `file`/`path` key must strip it from the remembered set. All seven
document surfaces are asserted, so the next document app that forgets names
itself instead of shipping the same bug.

### D10 — The operator's second click-pass: one reading face, Docs' file handling, and a refusal made visible

**Five findings from driving the D8/D9 build (2026-08-17).** All five were
invisible to `next build`, to `tsc`, and to all 128 checks then in the gate —
the arc's fourth consecutive demonstration that **a green gate is not a
rendered surface**. Two were structural; three were surface defects.

#### D10.a — ONE reading face, declared once (the table finding)

The operator: *"the table render on the tool bar doesn't show the rendered
style on the editor (ensure similar concept is streamlined)."* The instinct
behind "streamlined" was the real finding.

**Cause 1 — the parent-tag trap.** `@lezer/markdown` styles a table header
with the **generic** `tags.heading`, while `PROSE_HIGHLIGHT` mapped
`heading1…heading6`. Those are **children** (`heading1: t(heading)`), and tag
inheritance flows parent→child only — so a rule on the child never matches the
parent node. Measured by resolving the real `HighlightStyle`, not by reading
it: `heading (table header) -> NO CLASS`. Table cells (`tags.content`) and
task markers (`tags.atom`) had no rule at all.

**Cause 2 — two hand-maintained descriptions of one face.**
`PROSE_READING_SKIN` (Tailwind, → thumbnail + print) and `PROSE_HIGHLIGHT`
(CodeMirror, → the canvas) were independent, and had already drifted: the skin
styled tables, quotes, rules and task checkboxes; the highlight styled none of
them. **The landing thumbnail and the print sheet were more styled than the
canvas the member types in.** Tables were merely where it became visible; it
would have recurred control by control.

**Decision**: `components/text/readingFace.ts` owns the type scale, the faces,
the measure and the table treatment. Both renderers derive from it. The canvas
additionally gets a `tableRows` **line decoration** so a table reads as a
table — syntax highlighting can colour pipes but cannot draw a grid.

**This is not the banned node↔offset map.** ADR-456 D1 forbids mapping a
rendered node *back* to a source position — what a block editor needs to
serialize an edit. This runs the other way and never round-trips: the tree is
read to decide which LINES get a CSS class, the classes are discarded on the
next update, and nothing they touch is serialized. Gated: §11c asserts no
`data-*` reaches the source, and §9f's byte-identical round-trip still passes
with the decoration live.

#### D10.b — Type tokens: the canvas was reading Docs' vocabulary

`ProseCanvas` read `var(--font-serif)`; `PROSE_READING_SKIN` used Tailwind's
`font-serif`. Neither `--font-serif` nor `--font-mono` was declared **anywhere**
in `globals.css`, and `tailwind.config.ts` extended `fontFamily` with `brand`
only.

The deeper point: `--font-serif` **is** a real token — an **artifact-skin**
token (`skinVars.ts`), declared by an applied design system and parsed at
runtime by `skinVarMap()`. It exists only inside a skinned Docs artifact. **A
`.md` has no skin and no root element to carry one**, so in Text that var could
never resolve; the inline fallback always won, silently, while Tailwind's
utility resolved to its stock stack. One document, two faces, by construction.

**Decision**: declare `--font-serif` / `--font-mono` in `globals.css` as the
**app** type vocabulary (distinct from the artifact vocabulary), and point
Tailwind's `serif`/`mono` at them, so a utility class and a `var()` read cannot
diverge. Same shape as ADR-561: code naming a token that was never defined and
quietly taking a private fallback.

#### D10.c — The toolbar was dead on an empty line

Operator: *"the tool bar inserts don't work for an empty line."* Executed the
pure functions: **list, numbered list, checklist and quote were no-ops on a
blank line**; heading, table, divider and bold worked.

One cause, three sites. The "already marked?" test was
`lines.every(l => /marker/.test(l) || !l.trim())`. The blank-line clause exists
so a gap **inside a multi-line selection** does not veto toggling off — but
when the span is blank *entirely*, it makes the predicate vacuously **true**,
so the toggle takes the **un-mark** branch and strips a marker that was never
there. The button did nothing on precisely the line where pressing a button
beats typing `- `.

Fixed with a named `allLinesMarked()` helper: an all-blank span is **not**
marked. §11j gates the multi-line-with-gap case in both directions, because
that is what the naive fix breaks.

#### D10.d — File handling is Docs', and **D5's premise was false**

Operator: *"do we need a distinct save button? like other apps like docs or
studio APPs can we not explore similar approach on the file handling."*

**D5 justified Text's Save button on a factual claim about Docs that does not
hold.** D5 said Docs "autosaves on a 2s idle timer with no Save button and no
dirty state", and inferred Text needed a manual Save because *its* CAS conflict
is a product surface. But Docs' `writeAndAdvance` is a **queued CAS commit per
operation** — `writeArtifact(path, html, baseHead, message)`, CAS base read
inside the queue, a 409 handler that refetches the head and re-applies **once**,
an honest reload only on a second conflict.

Docs has everything the Save button was justified by — CAS, conflict handling,
attributed revisions — **and still has no button, no dirty flag, no manual
gesture**. Text was therefore not *more careful* than Docs; it was *less
capable*, and it handed the member the difference as a chore. The ADR-550→551
shape again: a live, correct mechanism in the wrong housing.

**Decision** (operator-approved): autosave on idle-2s (Docs' own
`COMMIT_IDLE_MS`) plus blur/visibility/teardown flush, over the unchanged
ADR-570 CAS path, serialized through a `writeTail` so two commits cannot race
their CAS base. **The Save button is DELETED**, not kept beside it — two save
models in one surface is the dual-approach shape CLAUDE.md §2 forbids. ⌘S
survives as a force-commit. The header reports ("Editing… / Saving… / Saved")
rather than asks.

**What survives from D5 is the 409 banner**, and the asymmetry justifying it is
real: Docs commits *operations* it can replay onto a fresh head; Text commits
*whole text*, which cannot be re-applied without inventing a merge. So a
conflict asks the member. That is the honest residue of D5's reasoning.

#### D10.e — The `⋯`, and a refusal nobody could read

Two findings in one pane, with opposite verdicts.

**The `⋯` was a genuine gap.** It exists on the landing cards and **vanished
once a document was open** — the open state wired rename only, behind clicking
the crumb. The moment the member is actually working on a document was the one
moment they could not act on it as a file. Fixed by reusing the **shared**
`useFileContextMenu` (Docs hand-rolls ~90 lines of inline popover for this;
deliberately not copied), with Copy link added through the documented
`extraItemsFor` point. `openMenuFromButton` is now returned from the hook so
any pane can anchor the menu — previously it was internal, reachable only via
`Kebab`, which renders on coarse pointers only.

**Colour and Highlight stay refused — but §3.1 executed its own decision
badly.** The reasoning holds: both persist as `<span data-mark>` /
`<span data-highlight>`, which is `data-*` written into the source, forfeiting
the round-trip. §3.1 explicitly said it wanted the absence *"named rather than
leaving the absence to look like an oversight"* — **and then named it only in
this ADR**, where no member reads it. Docs prints its refusals **in the pane**
("emphasis via the palette variables — never raw color"; ADR-449's metrics
refusal). Text now does the same, in an **Appearance** section, in the member's
language.

**Carry this forward: a refusal documented only in canon is invisible. If the
absence is deliberate, the surface has to say so where the absence is felt.**

#### D10 gate craft — two checks passed their own falsification

Both were caught only because every new check was falsified, and both are the
*same* error one screen apart:

- **11h** asserted `"var(--font-serif)" in tailwind.config.ts`. Repointing
  `serif` at a hardcoded `["Georgia","serif"]` left the string present **in the
  check's own explanatory comment** and in the `mono:` line beside it. Now
  extracts the per-key value and asserts *that*.
- **11L** required `openMenuFromButton` **and** the string `"File actions"`.
  Deleting the `aria-label` left `title="File actions"` behind and the check
  stayed green. Now matches the wired `onClick` handler and the mounted menu
  node.

**Fourth and fifth occurrences this arc of an assertion matching a decoration
of the behaviour rather than the behaviour.** The rule stands and needs no
restating: name the BEHAVIOUR, strip comments before asserting an absence, and
break every check you write.

## 3. Not done / explicitly out of scope

Named rather than worked around, per the operator's instruction.

### 3.1 The Properties pane's typography / colour / alignment controls

**Audited at control grain, not module grain** (2026-08-16, after the operator
asked whether dismissing `StudioDesignTab` wholesale was too coarse — it was).
The finding is a clean split, and the line it falls on is not a coincidence:

| Docs control | Persists as | Verdict |
|---|---|---|
| Bold / Italic / Strike / Code | **HTML tag** (`<strong>`/`<em>`/`<s>`/`<code>`) | ✅ **shipped** as `**` `_` `~~` `` ` `` |
| Typography ramp (H1/H2/H3 ↔ Text) | **tag swap** `p ↔ h1..h6` — sets no token | ✅ **shipped** as `#`/`##`/`###` |
| Turn into → list / numbered / checklist / quote | tag + `data-block` | ✅ **shipped** (the tag half) |
| Underline | `<u>` | ❌ markdown has no underline |
| **Colour** (5 roles) | `<span data-mark="accent">` | ❌ `data-*` on a minted span |
| **Highlight** (4 roles) | `<span data-highlight="warn">` | ❌ `data-*` on a minted span |
| **Align / Indent** | `data-align="center"` / `data-indent="2"` | ❌ `data-*` on the block |
| **Document font face** | `data-font` **on the artifact's `<html>`** | ❌ markdown has no root element |
| Document width (`measure`) | `data-measure="wide"` on `<html>` | ❌ same |
| Design system apply/remove | a `<style data-skin>` element in `<head>` | ❌ the machinery ADR-456 D1 names |
| W/H measure fields | `data-w` marker + inline `style="--yw: 60%"` | ❌ (also media-blocks-only on flow) |

**Everything that is a tag or a semantic type has a markdown equivalent and is
shipped. Everything that is presentation persists as `data-*`, an inline
custom property, or a `<head>` stylesheet — the mechanisms this app may not
write.** That is the same line ADR-456 D1 drew, arrived at independently from
the write paths.

Two details worth keeping, because they are load-bearing and non-obvious:

1. **Bold is a tag only because a flag says so.** `projection.ts` forces
   `execCommand('styleWithCSS', false, 'false')`, so the engine emits `<b>`
   rather than `<span style="font-weight:bold">`, and `artifactOps.ts`
   normalizes `B→strong`. Flip that flag and even bold becomes inline-style and
   loses its markdown equivalent. The parity here rests on a deliberate choice
   upstream, not on a property of rich text.
2. **Docs already refuses this category from itself.** `StudioDesignTab.tsx`:
   *"Deliberately NOT here: point size, line spacing, font family. Those are
   METRICS and the design system owns them (ADR-449) — §4 records the refusal
   rather than leaving the absence to look like an oversight."* And colour is
   *"a ROLE, never a value … ADR-449 forbids a picker."* Giving Text these
   controls would mean giving it what Docs withholds from itself, in a medium
   with nowhere to store them.

**A prose document has no element to carry presentation.** A `.md` has no root,
no class attribute, no stylesheet. Expressing a colour role would mean writing
raw `<span data-mark>` HTML into the markdown — which forfeits the
byte-for-byte connector round-trip that is the product thesis. **The refusal is
the feature.** If the reading face needs to look different, that is the app's
skin to change (one place, every document), never per-span state in the file.

> **Amended by D10.e (2026-08-17).** The refusal above is UNCHANGED and still
> correct — but this section only ever stated it *here*. The operator opened
> the pane, saw Docs' Colour and Highlight swatches absent, and read a
> considered refusal as a gap, which is the exact outcome the paragraph above
> says it wants to avoid. **Docs prints its refusals in the pane; Text now does
> too** (the "Appearance" section). A refusal documented only in canon is
> invisible to the person it is being explained to.

### 3.2 The Insert palette, kind by kind

Docs' palette serves 16 kinds. Classified by the markup each writes:

- ✅ **Shipped**: heading, list, numbered, quote, divider, table — and
  **checklist**, added by this audit (`- [ ] `; GFM, and `remark-gfm` was
  already in the pipeline rendering real checkboxes). Docs persists checklist
  as `<ul data-block="checklist">` plus a kernel `☐` CSS rule; markdown says
  the same thing natively with no annotation. **Leaving it out was an
  oversight, not a constraint** — corrected here.
- ❌ **Out, with reason**: `callout` (`<aside data-block>`), `button`
  (`<p data-block="button">`), `metrics` (`<div class="metric">`), `component`,
  and the citation kinds `figure` / `gallery` / `chart` / `table`-from-source
  (all carry `data-ref` + `data-ref-rev` — the citation machinery). `toggle` is
  `<details><summary>`, expressible only as raw embedded HTML.

### 3.3 The rest

- **Design systems, skins, tokens** — that IS Studio machinery (ADR-456 D1).
- **Block insertion, per-block Properties, arrangements, citation pins** — all
  require annotating the source.
- **Live edit-in-place rendering** — needs a node→offset map (D1).
- **In-surface revision history** — Docs' own affordance is a dead end; Text
  continues to point at Files → Get Info, which works.
- **Learn-from-a-source on the landing.** The `context-brief` derive recipe
  exists in the kernel registry, targets markdown, and has **zero FE consumers** —
  Text is its natural home. Deferred deliberately: it is a creation flow, not a
  reading/editing gap, and it deserves its own decision about where a derived
  brief lands. Noted here so it is not re-discovered as novel.

### D7 — The conflict envelope: read BOTH shapes, because the surface owns neither

Driven in production on 2026-08-16 (a second principal moved the head while the
editor held a stale base). **The 409 fired correctly and the banner appeared —
and it was wrong in two ways at once.**

The API serves the stale-write detail at `error.hint.current_head`; the client
read only FastAPI's older `detail.current_head`. Both fields came back
`undefined`, so:

1. the banner said the generic *"Someone else"* instead of naming who moved the
   head — the ADR-570 D5 promise that a 409 **names** the actor; and
2. **the "Save mine over theirs" button vanished entirely**, because it is
   conditional on `currentHeadId`. The member was left with one exit where the
   design promises two — the strictly worse failure, and the silent one.

`readConflict` (`components/text/conflict.ts`) now accepts either envelope and
degrades to a usable banner on an unreadable body. Both shapes rather than the
new one alone: **the envelope is not this component's to pin**, and a reader
that survives either cannot break again on the next migration.

**Invisible to every static check** — 103 gate checks, `tsc`, and `next build`
were all green over it, because a field read that yields `undefined` is not a
type error and the fallback string reads like intended copy. The gate now
replays the **verbatim production 409 body** (§8) and falsifies: restoring the
`detail`-only read fails 8a and 8b with exactly the production symptom.

**Verified on the deployed surface** (re-driven after the fix shipped): the
banner now carries **both** exits, names the actor, and "Save mine over theirs"
lands the member's text on the moved head — after which the banner clears, Save
returns to disabled, and the file on disk is **still plain markdown with no
block annotation**.

## 4. Falsifiers / click-pass

(1) A 1,000-word `.md` opens in Read and renders as a document — serif headings,
a real table, no visible `#` or `**`. (2) Write shows the source; the toggle
round-trips with no byte change. (3) ⌘B over a selection wraps it; pressing
again unwraps to the original bytes. (4) ⌘F finds, ⏎/⇧⏎ cycles, Replace All
works. (5) The Properties outline lists the headings and jumping selects the
right line. (6) Export → Print/PDF produces an A4 document that looks like the
Read view. (7) A landing card shows rendered prose, not `# `. (8) At a phone
width the bottom bar switches Document|Editor and neither pane is unreachable.
(9) Saving still lands a signed revision; a concurrent MCP edit still 409s with
the connector's attribution.

### 4.1 Click-pass RESULT (2026-08-16, driven on production)

**Passed**, on a document authored through the app's own New gesture:

- the canvas renders as a **document** — serif headings, a real bordered table,
  bold/italic/strikethrough, monospace inline code, a styled quote, a divider;
- **task lists render as real checkboxes**, checked state carried and aligned
  in the gutter;
- a fenced block stays literal, and its `#` line is **not** in the outline —
  the outline showed 4 headings, not 5;
- the Properties outline indents by level and updates live as the source
  changes; word count, heading count and reading time all track;
- New → naming dialog → create → open works; Save lands a signed revision;
- the CAS 409 fires on a concurrently-moved head, preserves the member's text,
  and merges nothing silently.

**Two defects found, one fixed:**

- **D7 above** (fixed): the conflict envelope mismatch.
- **A stale surface param** (NOT ADR-572's, pre-existing): navigating to
  `/text?text.file=A` can be **overwritten by the remembered param** from the
  member's shell state, landing on document B. Reproduced twice; the browser
  ends on a URL it was not sent to. This is the ADR-297-family
  "remembered state races the param" shape and belongs to the surface-param
  layer, not to Text. **Left unfixed and handed off** rather than patched
  inside this app, because the fix belongs where the param is restored.

Not driven: **Print/PDF** (the print dialog is a native modal the harness
cannot dismiss) and the **MCP-authored round-trip**, because the connector and
the browser session resolve to **different workspaces** in this environment —
the connector's writes 404 for the session and vice versa. Both remain owed.

## 5. Verification

`api/test_adr571_text_app.py` (script-style — `python3 test_adr571_text_app.py`;
pytest reports a false pass) extends 37 → **160 checks**. §6 gates the depth and
the grade constraint; §7 **renders the real pipeline** and inspects the output —
the only check that could have caught the D1 scale collision. **§11 mounts the
real `ProseCanvas` in jsdom** and reads what CodeMirror produced, which is the
only way D10.a's finding is visible at all.

Every new section was **falsified**: breaking fence handling fails 6ai; a
smuggled `data-block-id` fails 6L; dropping `scale="inherit"` fails 7n. The
first spelling of 7n asserted its own argument and stayed green through that
last falsification — it now renders `ProseReader` itself, so it checks the
wiring rather than the probe's own input.

**D10's five fixes were each falsified** (removing the table plugin fails 11a
while 11b stays green, proving 11a tests the table and not "did anything
render"; restoring the buggy blank-line predicate in `toggleQuote` alone fails
11i3 and nothing else; re-adding a Save button fails 11k; deleting the kebab
fails 11L; deleting the Appearance section fails 11M). **Two checks passed
their own falsification and were rewritten** — see D10's gate-craft note.

Full set green at the D10 commit: **160/160** here, 19 pytest
(`test_lane_artifacts` + `test_adr570_member_prose_door`), ADR-562 green,
`__gate_adr514_d2.mjs` 41/41, `next build` 171/171 pages with `tsc` clean.
