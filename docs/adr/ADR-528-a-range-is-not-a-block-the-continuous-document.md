# ADR-528 — A range is not a block: the continuous document

**Status**: Accepted · 2026-08-06
**Supersedes**: nothing. **Amends**: ADR-519 D3 (the pane spine), ADR-525 D3 (the text-tier
withdrawals), AUTHORING.md rules 10/11 + the pane matrix.
**Context**: [ADR-521](ADR-521-the-flow-benchmark-notions-scope-the-continuous-surfaces-mechanics.md)
· [ADR-525](ADR-525-the-selection-carries-its-tier.md) ·
[ADR-526](ADR-526-the-document-shows-its-shape.md) ·
[ADR-527](ADR-527-the-emphasis-tier-read-off-the-bar.md) ·
[ADR-518](ADR-518-docs-and-studio-the-writing-app-and-the-layout-app.md)

> **The number was already claimed.** `d878242` shipped the multi-block-range withdrawal
> and stamped it `ADR-528` in eight code sites and two gates, deferring the reasoning to
> "ADR-528 §the open question" ([StudioDesignTab.tsx:1095](../../web/components/studio/StudioDesignTab.tsx#L1095)).
> This ADR is that section. The code was ahead of the canon; this closes the gap and then
> goes one step further than the fix could.

---

## 1. The question that was actually asked

The operator, from live use:

> *"we may need this block composition style approach for docs, because my thesis is also
> that given our attribution and file system native, we may actually be under-weighting
> that capability … and thus, the documents itself need not be so granular and closer to
> google docs"*

Read as two claims (per the carry-over brief §1):

- **(a)** Docs is too granular.
- **(b)** The substrate — attribution, parent-pointered revisions, the filesystem, citation
  edges — already carries what block granularity was implicitly buying.

Claim (b) had never been probed. It is the load-bearing one, and probing it changed the
answer to (a).

## 2. The receipt: the substrate has no relationship to block identity

A full sweep of the Python side for `data-block-id`:

| Site | Hits | What they are |
|---|---|---|
| `api/services/studio.py` | 68 | Seed markup, vocabulary examples, lane-posture prose telling the model to stamp ids. **Zero functional reads.** |
| `api/services/docs.py` | 4 | The four literal lines of the document skeleton ([docs.py:56-59](../../api/services/docs.py#L56-L59)). |
| `api/services/authored_substrate.py` | **0** | — |
| `workspace_file_versions` schema | **0** | No block-aware column exists. |

`write_revision` ([authored_substrate.py:614](../../api/services/authored_substrate.py#L614))
takes `path`, `content`, `authored_by`, `expected_parent_version_id`, `derived_from` — and
no block parameter. The citation lift is **path-grain**: `_DATA_REF_RX`
([:245](../../api/services/authored_substrate.py#L245)) matches `data-ref="…"` and
`normalize_workspace_ref` resolves it to a workspace path. AUTHORING.md's own refusal list
confirms the design intent: *"no synced blocks (that is `data-ref` at block grain,
**later**)"*.

**D0 (the finding).** The substrate does not under-use block identity. It has never seen it.
Attribution, revisions, parent pointers and reference edges are **whole-file** facts.
`data-block-id` is a browser-side editing handle that has never crossed the write door.

This makes claim (b) correct and **stronger than the brief credited** — it was framed as
"we are under-weighting the substrate," and the truth is the substrate was never weighted
into this question at all.

**The corollary, stated so it is not mistaken later**: because per-block attribution never
existed, making Docs continuous *costs* nothing — and equally, it does not *buy* progress
toward "this sentence was Freddie's, that one was mine." That remains unbuilt and is a
separate bet (see §7).

## 3. Then blocks are not the conflict

The brief's outgoing session proposed stripping ids from prose. An inventory refuted it on
three receipts, all re-verified at HEAD after the concurrent `67f0025` lane:

1. **Internal-paste provenance** — `isInternalPaste`
   ([projection.ts:2212](../../web/components/workspace/viewers/projection.ts#L2212))
   distinguishes the member's own cut prose from foreign HTML *only* by finding a
   `data-block-id` that exists in this document. Without it every internal paste degrades
   to the foreign path and drops `data-mark`/`data-highlight`/`data-align`/`data-indent`
   — reintroducing the exact ADR-526 D4 defect.
2. **The patch channel (ADR-524)** — `projectBlock` is *awaited*, then posted to a runtime
   whose DOM may have moved on. The id is the stable handle across that window.
3. **`mergeBlock`** ([artifactOps.ts:1147](../../web/components/studio/artifactOps.ts#L1147))
   needs two ids that agree across the frame/source boundary, and the merge removes one.

All three are **browser-side**: a clipboard, an async round-trip, a frame edge. None is
about provenance. Identity is not about *findability* — it is about **referability across
a boundary**, and prose crosses three.

Independently, the axiom check comes back negative. `PROMOTE_KIND`
([artifactOps.ts:318](../../web/components/studio/artifactOps.ts#L318)) maps
`P → prose`, `H1..H6 → heading`, `TABLE → table`, `FIGURE → figure`. On flow a "block" is a
**paragraph or heading with a name written on it**. `normalizeStructure` annotates real DOM;
it imposes no parallel tree (rule 1). **Google Docs is itself block-structured** — a list of
structural elements, each a paragraph carrying a named style. A paragraph is a real unit: it
is what a style applies to, what an outline is built from, what Enter creates.

**D1.** Blocks are the correct model for a continuous document and are RETAINED —
`data-block-id`, `data-block="kind"`, the vocabulary, `normalizeStructure`. Stripping prose
identity is **refused**, on the three receipts above.

## 4. `block` as a SELECTION SCOPE is the conflict

The mismatch is one word doing two jobs across two media.

On a stage, `block` genuinely *is* a selection scope — a slide object is a thing with a box.
On a continuous surface the selection is a **range**, which may cover half a paragraph or
six. There is no "the selected block."

The tier already knows this. `tierOf`
([projection.ts:515-521](../../web/components/workspace/viewers/projection.ts#L515-L521)) is
six lines and returns `'text'` for prose on flow. ADR-525 shipped it; the runtime declares
it; rule 11 makes the runtime the only party that may.

**But the pane never consults it when computing scope.** [StudioDesignTab.tsx:1019](../../web/components/studio/StudioDesignTab.tsx#L1019):

```ts
const scope: 'document' | 'block' | 'container' | 'page' = !selection
  ? 'document'
  : selection.blockId && selection.blockKind
    ? 'block'
    : …
```

Scope is committed from `blockId && blockKind`. Tier arrives 56 lines later
([:1075](../../web/components/studio/StudioDesignTab.tsx#L1075)) and is used only to
*subtract* — which is why the file reads "withheld on the TEXT tier" at
[:2129](../../web/components/studio/StudioDesignTab.tsx#L2129) and
[:2248](../../web/components/studio/StudioDesignTab.tsx#L2248).

The evidence that this is a grammar fault and not a set of gaps is the pane matrix itself.
AUTHORING.md's `block (text)` column is defined almost entirely by absence: no path, no
verb row, no Hug|Fill, no W/H, no Position. **A column of withdrawals is a scope that was
never meant to be entered.** Four ADRs in three days each removed one more affordance from
it:

| ADR | Shipped as | What it actually was |
|---|---|---|
| 525 | the selection carries a tier | teaching a scope-pane that some selections aren't objects |
| 526 | outline + heading crumb | giving Docs a structure the object grammar couldn't express |
| 527 | the Text section | putting a *range*-following control into a *scope*-based surface |
| `d878242` | multi-block withdrawal | the pane admitting it has no answer |

Four fixes, one unaddressed premise. This ADR addresses the premise.

**D2 (the decision).** On the `flow` medium the pane's scope set becomes
**`document | range | object`**. `block` is no longer a scope a continuous document can
produce.

- **`range`** — a text selection, collapsed (a caret) or not, spanning one block or many.
  Its sections are Text (emphasis, ADR-527 D4), the enclosing-heading crumb (ADR-526 D2),
  turn-into and the typography ramp **at structure tier** — addressing the blocks the range
  intersects, per rule 10's second axis. It has no path, no verb row, no geometry, because
  a range has no box. It withdraws nothing: there is nothing to withdraw from.
- **`object`** — a figure, table, chart, gallery or divider on flow. Keeps the unit verbs
  and the neutral outline. Google Docs treats an inserted image exactly this way.
- **`document`** — unchanged.

`container` and `page` never applied to flow anyway (ADR-481 D1 — flow has no containers by
derivation; no page unit).

**D2.1 — the derivation, not a second rule.** Scope is derived FROM the tier the runtime
already declares, at the one site that computes it. `tier === 'text' → 'range'`;
`tier === 'object' → 'object'`. The pane does not re-derive the medium, and rule 11 is
preserved intact: the runtime remains the only party that reads the DOM and the medium
together.

## 5. Why this is not an ADR-518 fork

ADR-518 D2 refuses forked machinery per app. This is not one.

`FLOW_MODE` ([projection.ts:1639](../../web/components/workspace/viewers/projection.ts#L1639))
reads `data-yarnnn-mode === 'flow'` from the artifact root, so `tierOf` can only return
`'text'` on a flow medium. A deck **cannot emit `range`**. The shared pane grows a scope one
medium never sends — structurally identical to `page` existing while flow never sends it.
One implementation, per-medium branches that were always there.

**D3.** No fork. The pane, the ops registry, the write door and the runtimes remain one
implementation with three consumers.

## 6. What is streamlined

Per the operator: *"can, should delete legacy code since post commit we'll have it recorded
in legacy."* Deleted, not deprecated (CLAUDE.md §2, ADR-511 §2).

**D4 — the text-tier withdrawal apparatus is DELETED, not re-gated.** Every
`isTextTier &&` guard that exists to *suppress* an enclosure section
([:2129](../../web/components/studio/StudioDesignTab.tsx#L2129),
[:2248](../../web/components/studio/StudioDesignTab.tsx#L2248), the verb-row and Hug|Fill
withdrawals) becomes unreachable once those sections are not composed for `range` at all.
A suppression guard behind a scope that cannot reach it is dead code that reads as live
policy.

**D5 — callout and toggle are dropped from the vocabulary** (operator, settled in the
brief §5; Google Docs has neither). Both are prose in a container (`<aside>`, `<details>`)
and both sit in `TEXT_BLOCK_KINDS` while being containers — they are the two kinds that
most muddy the text/object line, so removing them makes `tierOf` sharper, not merely
shorter. Existing instances survive as **inert names** (ADR-511 D8): they render, nothing
gates on them, nothing writes them. Removed from `VOCABULARY`, from `TEXT_BLOCK_KINDS`,
from the insert menus.

**D6 — metrics stay with the design system.** Restated because "closer to Google Docs" is
exactly the phrase that would reopen it. Google Docs gives the writer a point-size box;
yarnnn does not, because a yarnnn document wears a **workspace** design system (ADR-449)
rather than being self-contained. Rule 13 and ADR-527 §4 are unchanged. **"Google Docs-like"
is a claim about granularity and selection model, never about typography controls.**

**D7 — the benchmark line, restated in one sentence.** *Notion for what a document is made
of; Google Docs for how selection and editing feel; neither for what it looks like — that
is the workspace's design system.* This is rule 10's two axes plus rule 13, said once.

## 7. What this ADR does NOT do

- **It does not add per-block attribution.** §2 established that the substrate is
  whole-file. Making Docs continuous neither costs nor advances that. Per-principal
  attribution *inside* a document is a genuine and much larger bet; AUTHORING.md files its
  mechanism under "`data-ref` at block grain, later."
- **It does not reopen `<section>`.** ADR-526 §6 named the two affordances that would —
  collapsible headings, move-a-whole-section. Neither is met here: `range` addresses the
  blocks it intersects, which is the heading-tree derivation (rule 12), not a wrapper.
- **It does not move emphasis off the pane.** ADR-527 D4 shipped emphasis into the pane's
  Text section at the operator's instruction, and it is the one section that survives a
  multi-block range ([:2175](../../web/components/studio/StudioDesignTab.tsx#L2175)). Under
  D2 it becomes the *primary* section of `range` scope rather than a guest in a block
  scope. Whether the bar and the pane are one surface too many is a **separate question**,
  deliberately left open — it is a question about member habit, not about grammar.

## 8. Gates

The current model is encoded in gates that must be **re-cut with intent preserved**, never
deleted (brief §3.4): `test_adr443_studio_model.py:61,85,140`, `test_adr481_flow_chrome.py:75`,
`test_studio_split_merge.py:69`, `test_adr456_studio_wave2.py:100`,
`adr482_flow_promote.mjs:138,140`, `adr526_docs_structure.mjs:158`,
`adr527_emphasis_tier.mjs:180-205` (the eight ADR-528 assertions `d878242` already landed).

New gate `adr528_range_scope.mjs` must **execute the extracted body**, not grep a spelling
(the discipline that broke six assertions this week), and must **falsify** — inject a
`block` scope on flow and confirm the gate trips. A counting gate cannot defend a per-site
invariant.

---

**In one line**: the substrate never knew about blocks, so the granularity question was
never a substrate question — blocks stay as the document's real units, and what goes is
the object grammar the chrome composed over prose because a paragraph happened to have
an id.
