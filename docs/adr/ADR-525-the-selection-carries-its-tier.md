# ADR-525: The selection carries its tier — one answer, read by every surface

> **Status**: **Accepted + Implemented** (2026-08-06). All eleven sites in §4 shipped.
> Gates: `adr525_selection_tier.mjs` **29/29** (the tier derivation and both falsifiers
> execute the real extracted bodies); `adr484_flow_chrome_leak.mjs` re-pointed at the
> chokepoint and grown a **completeness assertion with its own falsifier** — 19/19, up
> from 14/14 over a narrower extent; `test_adr521_flow_format_tier.py` 35/35 (its
> TEXT_KINDS assertion follows the named export, intent unchanged); ADR-519 16/16,
> ADR-520 23/23, and the FE script gates green; `next build` **exit 0**, 169/169 pages,
> from an isolated worktree (the main tree was under concurrent ADR-524 edit).
> **The operator click-pass is the one open item** — human-driven by necessity (the flow
> runtime lives in an opaque-origin iframe that synthesized keys cannot drive; ADR-521's
> finding, re-confirmed by 522 and 523). Acceptance in §6.
> Derived from an operator report made from live use
> against a real document: *"i can't tell if that black like outline on a single line within
> a flowing doc is the right approach, or if that's legacy … if you take as a reference the
> recent hierarchical object handling considerations in recent commits to the studio app, i
> think we have to reapply a similar discipline, but obviously one that is technically true
> to the framing that in which we're trying to achieve with docs specifically."* The audit
> found the operator's read exactly right, and the cause one layer beneath the symptom: the
> chrome is not medium-blind by oversight at each site — **the selection message the chrome
> reads carries no tier**, so every consumer re-derives one and they disagree.
> **Date**: 2026-08-06
> **Dimension**: **Channel** (the interaction contract of the two media). Nothing at the
> Substrate dimension changes — no new file, no new write door, no revision semantics, no
> new op. One artifact format, one write door (ADR-518 D2 holds); every mechanism below is
> projection-runtime payload + FE chrome composition.
> **Relates to**: ADR-480 (the editing grain — the per-medium axiom this ADR finishes
> applying), ADR-484 (the cue that boxed prose — the fix this ADR completes past the two
> click sites it reached), ADR-521 D2/D6 (the tier law this ADR promotes from a keyboard
> gate to the payload), ADR-519 D1 (the four-grain hierarchy, explicitly Studio-scoped —
> the exclusion this ADR makes true in code), ADR-518 (the Docs/Studio split — one
> component, two grammars), ADR-481 D1/D3 (flow flattening + the retired hover box),
> ADR-516 D5 (the parent-side selection reach whose flow half was never gated),
> ADR-522 D4 (the `headingId` precedent — the payload's last field addition).

---

## 1. Context — three surfaces, three answers, one ambiguous message

### 1.1 What the operator saw

Clicking a heading in a Docs artifact draws a black outline around that one line and fills
the right pane with **Duplicate · Up · Down · Delete**, **WIDTH: Auto | Hug | Fill**, and
**ALIGN: Auto | Center | Right** — box-geometry verbs and box-geometry properties, on a
paragraph in a continuous writing surface.

Canon already forbids every one of those. ADR-484 D1: on flow the selection cue applies to
**objects only** — *"Prose gets the caret and nothing else."* ADR-521 D1 + `STUDIO.md`
normative rule 10: Docs' scope is Notion-class — *"no pagination, no layout surface."*
ADR-519 D1, closing sentence: *"document is Docs' housing (ADR-518) and outside this ADR."*
`docs/gitbook/apps/docs.md`: a document is *"captured and revised forever, not laid out:
there are no slides, no bands, no positioning."*

So this is not a canon gap at the level of intent. The intent is stated four times. It is a
**delivery** gap, and the delivery gap has one cause.

### 1.2 The cause — ADR-484 withheld the cue, never the selection

`projection.ts:651-671`, the flow branch of the left-click handler:

```js
if (flowMode) {
  if (cur) cur.classList.remove('yarnnn-pointed');
  cur = blk || null;                              // ← the block IS selected
  if (cur && TEXT_KINDS.indexOf(cur.getAttribute('data-block')) === -1) {
    cur.classList.add('yarnnn-pointed');          // ← only objects get the cue
  }
  parent.postMessage(payload, '*');               // ← the payload is unchanged
  return;
}
```

Read those lines together. ADR-484 fixed what is **drawn**. It did not touch what is
**selected**, and it did not touch what is **posted**. The `yarnnn-point` payload
(`projection.ts:605-617`) is byte-identical in shape for *prose clicked on flow* and
*object clicked on a deck*: same `blockId`, same `blockKind`, same `label`.

`StudioCanvas.tsx:498-513` forwards it verbatim; `StudioSurface` sets `selection` from it;
and then **every parent-side consumer independently decides what that means**:

| Surface | Taught the tier? | Receipt |
|---|---|---|
| Runtime cue | ✅ yes | `TEXT_KINDS` guard, both click paths (`:667`, `:766`) |
| Keyboard verbs | ✅ yes | `verbSubjectAllowed()` / `selectedBlock()` (`:1146-1186`, ADR-521 D6) |
| `__yarnnnSelect` | ❌ **no** | `:892-897` — adds the class unconditionally |
| Right-click menu | ⚠️ **half** | `StudioBlockMenu.tsx` — Insert (`:255`) + Move (`:346`) gated on `isPaged`; Duplicate (`:290`), Delete (`:293`) not |
| Design pane | ❌ **no** | `StudioDesignTab.tsx` — one `mode` branch in the whole file (`:1007`), document scope only |

Three surfaces, three answers, to one question about one block. The member experiences
that directly: **the pane offers Move up / Move down on a Docs paragraph, which the
right-click menu on the same paragraph explicitly refuses** — with the reasoning written
out at `StudioBlockMenu.tsx:337-345` (*"Reordering is an enclosure verb… On flow the member
edits one continuous surface"*). One op, two contradictory answers, same block, same
instant.

### 1.3 Why it re-opened after ADR-484 fixed it

`678f579` (2026-08-04) added the ADR-516 D5 effect at `StudioCanvas.tsx:438-441`: a
parent-side selection now re-commands the live runtime, so a navigator-tree or pane click
draws its box. That was a real Studio fix for a real Studio defect (*"the selection was
real and invisible"*). Its commit message records the verification honestly —
*"Live-verified: tree-select of the title container draws the static box"* — on Studio.
Docs was not in the pass.

The path it opened lands at `__yarnnnSelect` (`:892-897`), which has no tier guard. One day
later the operator reported the box.

This is the diagnostic that matters for the shape of the fix: **ADR-484's guard was placed
at the two click sites rather than at the chokepoint, so a new selection route inherited
nothing.** `__yarnnnSelect` has four callers; only `:581` is guarded (via `gstaged`, and
only incidentally). `:1048` (parent re-command), `:2629` (backspace-merge), `:2789`
(Esc-from-edit) are not, and `:838` (Esc-walk) boxes `up` directly without going through
the function at all.

The gate `web/scripts/gates/adr484_flow_chrome_leak.mjs` passes **14/14**, including
*"clicking a HEADING draws no outline"* — because it executes the two click branches. It
cannot see the other five sites. A green gate over the wrong extent.

### 1.4 The canon half is under-specified too

`docs/design/AUTHORING.md`'s pane matrix (the "The pane (Design tab)" section) columns by
**grain** — `document | page | container | block` — while every other matrix in that
document columns by **medium** (`deck | document | web`). There is therefore no way to
express *block-on-flow ≠ block-on-deck*, and the Layout row reads
`size Hug|Fill · width/align tokens` for the block column with no medium qualifier.

**The doc currently sanctions the leak.** That is why this is an ADR and not a bug commit:
there is a decision to record, not merely a defect to repair.

### 1.5 The registry has no term for it either

`api/services/studio.py:635-648` defines the `applies` vocabulary. It has `document-flow`
and `block-staged` — but **no `block-flow`**. A token literally cannot declare "flow blocks
only." So `size` and `align` are declared `applies: ["block"]` (`:694`, `:703`) — the widest
grain — and the pane's block filter (`StudioDesignTab.tsx:963-975`) has nothing to filter
on. The `size` token's own comment gives the game away: *"Absence = the flow's natural
width"* — written for a staged block, wearing a universal label.

Note the contrast that proves the discipline was known: `x/y/w/h` **were** correctly
narrowed to `block-staged` (`studio.py:879,888,922,931,946`), which is exactly why W/H
fields correctly do *not* appear on a Docs paragraph today. The measure half was done. The
token half was not.

---

## 2. Decisions

### D1 — The tier is a property of the selection, declared once by the runtime

> **The projection runtime — the only party that can see the DOM and the medium — declares
> the selection's TIER on the payload. No consumer re-derives it.**

Three tiers, the vocabulary ADR-521 D6's closing sentence already named:

| Tier | What it is | Who speaks for it |
|---|---|---|
| `text` | a stretch of prose — prose/heading/callout/quote/checklist/toggle **on flow** | the caret |
| `object` | figure/table/chart/gallery/metrics/divider/button — anywhere; **and every block on paged** | nothing else; it needs the box |
| `structure` | a container or page | its own frame |

The rule is one line, and it is the rule the runtime already applies to the cue:

```
tier = flow && TEXT_KINDS.includes(kind) ? 'text' : (blockKind ? 'object' : 'structure')
```

On paged, every block is an `object` — ADR-480 D1's axiom, unchanged. On flow, prose is
`text` and figures stay `object`. This ADR **mints no new judgment**; it moves an existing
one from five scattered call sites to the payload.

`tier` joins `yarnnn-point` exactly as ADR-522 D4's `headingId` did: one optional field,
plumbed through `StudioCanvas.onPoint` into `StudioSelection`.

### D2 — The chokepoint owns the cue; the call sites lose the choice

> **`__yarnnnSelect` applies the cue only when the tier earns it. Every other site that
> boxes an element is deleted in favour of calling it.**

The ADR-484 guard moves *into* `__yarnnnSelect` (`:892-897`) and out of the two click
branches. The Esc-walk site (`:838`) stops adding the class directly and calls the function.
After this, there is exactly **one** place in the system that can draw a selection box, and
it cannot draw one on prose.

This is ADR-521 D6's own shape re-applied: that fix put the gate at `selectedBlock()` —
*"the single chokepoint every verb reads"* — rather than at each verb. Same discipline, the
selection layer instead of the verb layer.

The `adr484_flow_chrome_leak.mjs` gate re-points at `__yarnnnSelect` and gains a
**completeness assertion**: no site outside the function may contain
`classList.add('yarnnn-pointed')`. A counting gate cannot defend a per-site invariant —
enumerate, assert completeness, falsify.

### D3 — The pane composes by tier, and Docs loses the Layout section

> **`StudioDesignTab`'s block scope reads `selection.tier`. A `text` selection renders
> Identity → Style → Content. Layout and the structural verb row do not render.**

For a Docs paragraph the pane becomes:

**File → Identity (name only) → Typography → Tone → Turn into**

What is withdrawn, and why each is not a question a `text` tier can answer:

- **The verb row** (`:1802`, `VerbRow` at `:540-566`) — Duplicate/Up/Down/Delete are
  enclosure verbs. `Up`/`Down` are the ones the right-click menu already refuses on flow;
  the other two are what ADR-521 D6 retired from the keyboard. Withdrawn whole, which
  resolves the pane-vs-menu contradiction by making both say the same thing.
- **The Layout section** (`:1863-1884`) — Width Hug|Fill and Align. `Hug`/`Fill` is a
  *container* row (ADR-516 D4) and flow has no containers by derivation (ADR-481 D1). This
  is `STUDIO.md` rule 10's "no layout surface", finally true at the surface.

What is **kept**, and why it is not layout:
- **Typography** — the type ramp is turn-into by another door (ADR-487 D3), a structure-tier
  act on the block the caret sits in. Notion has exactly this.
- **Tone** — a palette token, meaning not geometry (ADR-449: *"never raw color"*).
- **Turn into** — ADR-521 D2 places turn-into in the **structure** tier, which addresses the
  blocks a selection intersects. It is reachable from a caret and belongs to Docs.

Structure and object tiers are **untouched** — Studio's pane is byte-identical after this
ADR. That is the ADR-518 D2 test: one implementation, two grammars, and only the grammar
that was wrong changes.

### D4 — `block-flow` enters the `applies` vocabulary; `size` and `align` are re-keyed

> **The registry gains the term it was missing, and the two tokens that were wearing the
> wrong grain are re-keyed to `block-staged`.**

`api/services/studio.py`: add `block-flow` to the `applies` vocabulary + its machine-readable
half; move `size` and `align` from `applies: ["block"]` to `applies: ["block-staged"]`.

This is not belt-and-braces over D3 — it is the honest home for the fact. D3 stops the pane
from *rendering* the rows; D4 stops the registry from *claiming* they apply, which is also
what the **lane** reads (`studio.py`'s posture serves one grammar to both hands, R4). Without
D4 the AI hand keeps being told a Docs paragraph has a width.

`block-staged` (not a new `block-flow` gate on these two) is correct because that is what
they always meant: the comment at `:690` says so in its own words.

### D5 — The right-click menu reads the tier, completing the half-cut

`StudioBlockMenu` gates Insert and Move on `isPaged` today. It gains the tier for
**Duplicate** and **Delete** — unit verbs on prose, exactly what D6 retired from the
keyboard — while **Turn into** stays (structure tier, D3's reasoning) and the AI rows stay
(they act on text, and a caret is a fine subject for "rewrite this").

After D3 and D5 the pane and the menu are derived from one field and cannot disagree.

---

## 3. What this ADR refuses

- **No new selection mode.** ADR-521 D7's refusal stands: the browser range IS flow's
  selection. `tier` describes the selection that already exists; it does not add one.
- **No fork of Docs from Studio.** ADR-518 D2 holds — one component, parameterized. The
  tier is the parameter the component was missing. Forking 2,500 lines is the dual-approach
  smell the discipline forbids.
- **No removal of the selection itself on flow.** The block stays *addressable* (ADR-480:
  *"the block remains ADDRESSABLE, it just stops being an enclosure"*) — the pane still
  scopes to it, Typography and Turn into still act on it, ADR-522's focus still reads it.
  Only the enclosure affordances go.
- **No new grain.** ADR-519 D1's four grains are reused verbatim; `tier` is orthogonal to
  grain, not a fifth level.

---

## 4. Implementation scope

| # | Site | Change |
|---|---|---|
| 1 | `projection.ts:605-617` + 3 sibling emitters | stamp `tier` on `yarnnn-point` |
| 2 | `projection.ts:892-897` | `__yarnnnSelect` gains the tier guard (the chokepoint) |
| 3 | `projection.ts:651-671`, `:759-769` | click branches drop their local guards (now redundant) |
| 4 | `projection.ts:838` | Esc-walk calls `__yarnnnSelect` instead of adding the class |
| 5 | `StudioCanvas.tsx:498-513` | forward `tier` |
| 6 | `StudioToolbar.tsx:95-110` | `StudioSelection.tier` |
| 7 | `StudioDesignTab.tsx:1802`, `:1863-1884` | block scope composes by tier (D3) |
| 8 | `StudioBlockMenu.tsx:290,293` | Duplicate/Delete read the tier (D5) |
| 9 | `api/services/studio.py:635-648,694,703` | `block-flow` term; re-key `size`/`align` (D4) |
| 10 | `web/scripts/gates/adr484_flow_chrome_leak.mjs` | re-point at the chokepoint + completeness assert (D2) |
| 11 | `docs/design/AUTHORING.md` | the pane matrix gains a medium axis (§1.4) |

New gate: `web/scripts/gates/adr525_selection_tier.mjs` — executes the real tier derivation
and the real `__yarnnnSelect` body, with falsifiers for each of: prose-on-flow is `text`,
figure-on-flow is `object`, prose-on-paged is `object`, and the completeness assertion.

---

## 5. Consequences

**The member gets one answer.** A Docs paragraph offers writing affordances; a deck object
offers box affordances; nothing offers both, and no two surfaces disagree about which.

**Docs' declared framing becomes true in code.** "No layout surface" stops being a sentence
in `STUDIO.md` and becomes the pane's actual composition.

**The next selection route inherits the guard for free** — the failure mode that produced
this ADR (a Studio fix re-opening a Docs hole) is structurally closed, because there is one
place left that can draw the box.

**Accepted cost**: `tier` is derived at the runtime and travels on a message, so a consumer
that ignores it can still misbehave. The completeness assertion in D2's gate defends the cue;
the pane and menu are defended by ordinary review. A future consumer is one more reader of an
existing field, not a new derivation — which is the whole point.

---

## 6. Owed

- **The operator click-pass** — human-driven by necessity: the flow runtime lives in an
  opaque-origin iframe that synthesized keys cannot drive (ADR-521's finding, re-confirmed
  by ADR-522 and ADR-523). Acceptance: in Docs, click a heading — no box, and the pane shows
  no Layout section and no verb row; right-click it — no Duplicate/Delete; click a figure —
  box present, verbs present. Then open a deck and confirm every block still boxes and the
  pane is unchanged.
- **ADR-484 §6's own owed click-pass** (*"a human click-pass confirming prose no longer
  outlines"*) is subsumed by the above — it was never run, which is why this regression went
  unseen for a day.
