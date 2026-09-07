# Carry-over prompt — composition-by-reference: Stage 1 answered, three decisions on the table

> Written 2026-09-07 after driving Stage 1 of the previous carry-over prompt
> (`98a22b9`). **Nothing shipped this session** — this is a finding, with the
> receipts, and the decisions it leaves. Paste the block below as the next
> session's opening prompt.

---

## The prompt

Continue the composition thread from the findings below. **Verify, don't
trust** — front-load `docs/SESSION-HANDOFF.md` Part R, then
`docs/adr/ADR-572-*.md` §D17/§D18 and `docs/adr/ADR-590-*.md` §1 before acting.
A PARALLEL SESSION also commits here; check `git log --oneline -8` authorship.

### Stage 1 is answered: which render pass a Text document goes through

**Neither pass is `projection.ts`.** A `.md` is drawn by exactly two things:

| surface | file | what it renders | since |
|---|---|---|---|
| the editing canvas (the ONE surface) | `web/components/text/ProseCanvas.tsx` | headings, marks, lists, quotes, rules, links, `<table>` (D15), mermaid + code fences (ADR-590 D3) | ADR-572 D8, `f392323`, 2026-08-16 |
| the reading face | `web/components/shared/MarkdownRenderer.tsx` via `ProseReader` | the same, plus `![alt](path)` resolved to a CAS URL (`MarkdownImage`) | demoted to **thumbnail + print only** by D8 |

`projection.ts` is imported only by the Studio/authoring tree (StudioSurface,
StudioCanvas, FlowEditor, PagedNavigator, artifactOps). So the first falsifier
in the old prompt **fired**: a `data-ref` inside a `.md` is inert markup, and a
body-level `data-ref` rule for Text would author citations nothing resolves.
That part of the old thesis is dead and should stay dead.

### But the markdown grammar was already RULED — and it answers the "claim-grain" question

ADR-572 D17/D18 (2026-08-17, `8a195db` + `931df22`) decided, kind by kind, what
composition-by-reference looks like when the file is markdown, on the test
*"does its content survive in the file"*:

| kind | markdown form | pin | ruling |
|---|---|---|---|
| image | `![alt](workspace/path.png)` | none — **the deliberate loss** (a moved image says "Image not found: path") | ✅ D17 |
| diagram | a ```` ```mermaid ```` fence | the source IS the file | ✅ D17 |
| table from CSV | rows written as GFM under `_From \`path\` · snapshot YYYY-MM-DD_` | the provenance LINE | ✅ D18 |
| automatically-live table | a pointer (`<div data-ref>`) | — | ❌ refused: empty in the file, ADR-574's reason |

So the claim-grain citation the old prompt was reaching for **exists in
markdown and is the provenance line** — D18: *"Provenance in the file, not in
a convention."* The two bound Text drives that retyped `1,850 / 2,310 / 3,040`
into a table produced **exactly the shape the Text toolbar's own
`csvToMarkdownTable` writes, minus the provenance line.** The defect is not
that the agent copied (D18 says copy) — it is that nothing told it the copy
must say where it came from.

### What the engines are told, measured

```
text_pane_posture (composed, 1,349 B):
  derived_from ✅     mermaid ✗   ![ ✗   csv ✗   snapshot ✗   "From `" ✗   data-ref ✗
skills index for app=text (3,118 B): lists assembling-a-composite-document ✅
  — its step 3 says "name the source of every figure, inline" but names NO shape
lane_runner.py:        composes PARTICIPANT_CITATION_RULE (derived_from) only; "data-ref" absent
build_standing_frame:  PARTICIPANT_CITATION_RULE only
mcp_server/server.py:  PARTICIPANT_CITATION_RULE + PARTICIPANT_ARTIFACT_CITATION_RULE (.html);
                       "![" / mermaid / snapshot: absent
```

The engine census the old prompt asked for:

| engine | `derived_from` (ledger) | `.html` grammar (`data-ref`) | `.md` grammar (image-by-path · mermaid · snapshot+provenance) |
|---|---|---|---|
| bound lane — slides / images / blogger | ✅ | ✅ (`_POSTURE_FRAME` §Citing) | n/a |
| bound lane — **text** | ✅ | ❌ (correct: inert) | **❌ nowhere** |
| open lane | ✅ | ❌ | ❌ |
| standing run | ✅ | ❌ | ❌ |
| MCP connector | ✅ | ✅ (kernel constant, ADR-617 D2) | ❌ — and `marketing/` is almost entirely connector-authored `.md` |
| the Text **toolbar** (a human's hand) | — | — | ✅ `insertImage` / `insertMermaid` / `insertCsvTable` — **the only home** |

**This is the Stage 2 answer.** Composition-by-reference *is* substrate-native
at the ledger (`derived_from` reaches every engine). The in-document grammar is
**per format**, and that is correct — the format decides what survives in the
file. The asymmetry is that the `.html` grammar is a kernel constant every
write-capable surface can be handed, while the `.md` grammar lives only in
three FE insert functions. No engine can be told it because it is written
nowhere an engine reads.

### The operator's live observation, reproduced on prod (2026-09-07)

Driven on `/agents/_adr427-phase2-test/scratch.md` through CodeMirror's own
input path (`execCommand('insertText')` — the DevTools keyboard tool scrambles
markdown punctuation; the doc was restored to its original line afterwards):

```
```mermaid graph TD …```          → .cm-mdDiagram widget, <svg viewBox="0 0 111 174">, 2 nodes   ✅ renders
_From `operation/q3.csv` …_ + GFM  → italic line + a real <table>                                    ✅ renders
![laptop](marketing/assets/…png)   → the underlined word "laptop"; real <img> count: 0              ❌ NO picture
```

⭐⭐⭐ **The image door has never drawn a picture on the surface it was added
to.** D8 (2026-08-16) collapsed Text to the CodeMirror canvas and demoted
`MarkdownRenderer` to thumbnail + print. D17 (the NEXT day) shipped Insert →
Image and gated it with **17g: "the renderer RESOLVES a workspace image path"**
— asserting `MarkdownRenderer`, the surface the canvas no longer mounts.
`ProseCanvas` has six widget classes (Bullet, Rule, TaskBox, Table, Mermaid,
CodeLabel) and no image; the lezer `Image` node is treated as a link (marks
hidden, text underlined). ADR-590's census of *"eleven rendered things"* has no
image row, so the omission was never a decision. Three weeks, gate green.

So "graphs" render; **"referring to a new sub-file" does not, for images** —
and the agent side is worse: a Text lane is never told mermaid is the diagram
form, so *"add a graph"* has no grammar at all, and a graph of DATA (bar/line)
has no markdown form except mermaid's `xychart-beta` (mermaid 11.14 is
bundled; untested here).

**"Make an image in Images, put it in a Text doc" is unbuilt by name.** An
artboard is `.html`; its raster leaves only as a browser download
(`rasterExport.ts`), and ADR-475 §13 records posting it back as a
`revision_kind="derivation"` as *"opt-in, not required, and not built at
launch."* The generated LEAVES (`{artboard}/assets/*.png`, ADR-475) ARE real
files and ARE citable by `![]()`; `/studio/citable` lists png/jpg/gif/webp/svg.

A receipt on the other side: `operation/fundraising/market-sizing-reference.md`
(a Text-lane write, 2026-08-18) carries a Source column for every figure. The
agent cites the WORLD fine (DP31); it is a figure lifted from a WORKSPACE FILE
it leaves unsourced.

---

## The three decisions, separable — do not bundle them

**1. The canvas draws an image (FE defect).** ADR-590 D1 already states the
rule (*rendered stays rendered*); this is the row its census missed. An
`ImageWidget` beside `MermaidWidget`, resolving the path the way `MarkdownImage`
does (per read, never stored — the CAS URL has a 1-hour TTL). The gate must
**exercise the canvas** — mount `ProseCanvas` (or drive prod) and count real
`<img>`s, not grep `MarkdownRenderer`. Recommend: fix, its own commit.

**2. The engines are told the markdown grammar.** Three homes, in rising
reach and rising cost:
- (a) the composite-document skill only — zero frame bytes; reach measured
  at 58% / 0-of-2 on this exact ask;
- (b) `text_pane_posture` — text lanes only, ~300 B, the app's own job overlay
  (ADR-606 D3: the posture is where an app says how its artifact works);
- (c) a kernel constant (`PARTICIPANT_PROSE_CITATION_RULE`, sibling of the
  artifact rule) composed into the Text posture + the standing frame + the
  connector — ADR-617 D2's own argument (*"HOW A DOCUMENT WORKS, kernel-
  universal"*) applies symmetrically, and the connector authors more `.md`
  than any lane.
Evidence bar (DP22/ADR-306): a repeated observed failure — n=2 on one
fixture plus the operator's live report; **the failure is SILENT** (a retyped
figure looks perfect and drifts when the source moves), which is the arc's own
profile for a contract, not craft. Recommend (b) now with the shape stated
(the three forms + the provenance line, ≤ 400 B), pre-registered A/B
(`provenance_line_present` per figure-bearing document, n≥3/arm, purge
between runs), and promote to (c) only if the connector shows the same
failure in its own writes — measure `marketing/*.md` for unsourced figures
first; that is one query.

**3. Images → Text: the raster lands in the workspace.** ADR-475 §13's opt-in
POST-back, unbuilt. Product decision, not a defect. If wanted: the export
button gains "save to workspace" beside "download", landing
`{artboard}/exports/{name}.png` as a derivation of the artboard's revision —
then `![]()` and the picker reach it with nothing else built.

### What would falsify decision 2

- An A/B where the treated arm writes the provenance line at the same rate as
  control → prose we pay for every turn; drop it.
- The connector's `.md` writes already carry sources → (c) is unneeded; (b)
  suffices.
- A Text lane that is told the shape retypes a WHOLE CSV under a provenance
  line → the skill's step 4 ("keep the document's numbers to the few the
  argument uses") is the missing half, and it is craft, not contract.

### Method notes from this drive

- ⚠️ **The DevTools `type_text` tool drops/reorders markdown punctuation**
  (`![`, `](`, backticks) in CodeMirror; drive the canvas with
  `document.execCommand('insertText')` from `evaluate_script`. The prod bundle
  does not expose `cmView`, so `view.dispatch` is not reachable.
- Screenshots to the scratchpad are refused by the DevTools MCP (outside its
  roots); take them inline.
- A search for syntax (`![`, ```` ```mermaid ````) through the connector's
  semantic `search` returns noise — enumerate with `list` and `open`.

### Also still open (unrelated; keep them unbundled)

The composite-document skill is unmeasured (rank 1) · `agent-composition.md`
§3.2.1 re-cut · the standing run's reach receipt · the GitHub aperture · the
`ADR-411 D4` phantom (33 sites / 26 files → ADR-408/460) · ADR-640 D2's two
derived rows.

**Pick up with decision 1 (a bug with a receipt) and the one query behind
decision 2, and drive them rather than reading about them.**
