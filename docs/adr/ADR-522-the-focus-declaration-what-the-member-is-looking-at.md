# ADR-522: The focus declaration — what the member is looking at, declared once, spoken by every app

> **Status**: **Proposed** (2026-08-06). Derived from a live Studio session in which the
> operator wrote "tidy up this slide" and the agent had to ask *which slide* — the deck was
> open, a slide was on the stage, and none of that left the browser. The audit that followed
> found the gap is structural, not a regression: the lane wire has no field for view context
> and never has. Operator-ratified in framing after naming the polymorphism directly ("could
> it not be a slide, or a section within a doc? or something else, the screen itself?") —
> which corrected a Studio-shaped assumption in the first draft of D1.
> **Date**: 2026-08-06
> **Dimension**: **Channel** (what the chat surface knows about where the member stands).
> Nothing at the Substrate dimension changes — no new file, no new write door, no revision
> semantics. The declaration is transient view state, never authored.
> **Relates to**: ADR-398 D2 (the operator locator — the thin shared string this ADR leaves
> intact and does *not* extend), ADR-441 D1/D2 (the two-renderer altitude seam this ADR
> respects, and the named-slot contract it extends by one), ADR-446 D5 (the selection→chat
> auto-seed that was cut for cause — the failure this ADR must not resurrect), ADR-519 D1
> (the four-grain hierarchy this ADR reuses as its scope vocabulary), ADR-511 D3 (the
> structural grain + operator-word labels), ADR-518 (the Docs/Studio housing split),
> ADR-520 D1 (the stage view — the case that makes viewport load-bearing),
> ADR-514 (LaunchServices — the push direction this ADR completes with a pull).

---

## 1. Context — the agent knows the document, never the place

Three findings from the audit, each with receipts.

**1. The two chat surfaces are different wires, and only one carries view context.**
ADR-441 D1 ratified the A1/A2 split as a genuine wire-protocol split. The consequence
nobody priced: the steward rail (`POST /api/feed`) accepts an `operator_locator`
(`api/routes/feed.py:93-100`), and the lane wire (`POST /api/lanes/{id}/messages`) accepts
`{content, replace_from_message_id?, attachments?}` and nothing else
(`api/routes/lanes.py:75-85`). **Studio, Docs, and `/chat` all run on the lane wire.** There
is no field to put "where I am" into. The gap is structural.

**2. What context Studio does have arrives by a different mechanism, at a different
lifetime.** Studio binds a lane row to an artifact path once
(`context_metadata.lane.artifact_path`, `api/routes/lanes.py:418-420`), and
`api/services/lane_runner.py:396-406` re-reads that file and injects `build_studio_posture`
on every turn. This is genuinely good — the agent knows *the document* and its current
outline. It cannot know *the place inside it*, because a durable 1:1 lane↔file binding has
no room for a per-turn reading.

**3. The place is computed, and then discarded.** Two signals already exist in the
projection runtime and both dead-end in the FE parent:

- **Selection** — `yarnnn-point` (`projection.ts:581-593`) carries the full grain:
  `blockId`, `blockKind`, `label`, `slideIndex`, `pageIndex`, `slot`, `arrange`, `text`.
  It reaches React state at `StudioSurface.tsx:500`. Its only route to chat is
  `askAboutSelection` (`StudioSurface.tsx:569-585`), which **types English prose into the
  member's composer** — the agent receives it as indistinguishable user text, and it is
  lost if the member retypes.
- **Viewport** — `yarnnn-scroll-pos` (`projection.ts:1075-1080`) reports
  `{ y, slide }` on every scroll, where `currentSlideIndex()` (`projection.ts:1052-1067`)
  returns the *shown* slide on the stage and the *viewport-center* slide off it. It
  reaches `StudioCanvas.tsx:510-517` and is parked in a `useRef` (`:361`) that **no prop
  exposes**. It is consumed only to restore scroll after a reload.

The originating session is exactly case 3's second bullet: a deck in stage view, slide on
screen, nothing selected. ADR-520 D1 asserts "the surface owns the current index" — the
audit found that aspirational: when the member pages with PgUp/PgDn or the ‹ › buttons,
only the runtime knows.

**Why the locator does not solve this.** ADR-398 D2's `locator` is composed at exactly one
site (`ChatDrawer.tsx:149-161`) by **scraping URL params** for keys prefixed with the
foregrounded slug. It works for Studio only because Studio happens to store its file in
`studio.file`. Radar contributes `radar.topic` **without having opted in** — it has no chat
integration at all (`RadarSurface.tsx` imports only `useSurfaceParam`). A mechanism that
works for apps that never adopted it is a coincidence, not a contract. It is also
`[:200]`-truncated (`feed.py:1088`) and opaque by explicit design at every hop
(`wake.py:1462-1465`, `addressed.py:49`, `freddie_agent.py:553-557`). It cannot carry a
grain, and it does not reach lanes.

---

## 2. D1 — The focus declaration: one type, app-declared, grain-scoped

An app **declares** its focus; the shell never scrapes it. The type reuses ADR-519 D1's
four-grain hierarchy and STUDIO.md's already-named scope slugs verbatim — this ADR mints no
new taxonomy.

```ts
/** What the member is looking at. Transient view state — never authored,
 *  never persisted. Declared by the app, read by the chat mount. */
export interface SurfaceFocus {
  /** The app declaring it — the ADR-441 mount, not the file type. */
  app: string;
  /** The object in view. Workspace-relative; null for appless surfaces. */
  path: string | null;
  /** ADR-519 D1's hierarchy. 'document' = the whole object, nothing finer. */
  scope: 'document' | 'page' | 'container' | 'block';
  /** Identity at the scope. blockId for block/container; null for page. */
  id: string | null;
  /** 0-indexed page position when scope is 'page' (or a page encloses the
   *  finer grain). Rendered 1-indexed for the member — never leak the 0. */
  pageIndex: number | null;
  /** The operator word (ADR-511 D3's render-time label map): 'slide',
   *  'heading', 'columns'. Never a DOM word. */
  label: string | null;
  /** A short excerpt naming the thing, so the agent can say it back. */
  excerpt: string | null;
  /** What is on screen, distinct from what is selected (D3). */
  viewport: { pageIndex: number | null } | null;
}
```

**The scope vocabulary is ADR-519 D1's, not ADR-453's.** ADR-453's `block → slot → page`
ladder is dead — superseded by ADR-511 D3's structural grain (`ADR-511:19-20`), and the slot
grain is dissolved in the code itself (`StudioToolbar.tsx:94`). Reusing the live vocabulary
is the point: a second grain taxonomy would be the drift this ADR exists to prevent.

**Declaration, not derivation.** The app calls one hook to publish; the shell holds the
latest declaration per app and reads the foregrounded one. An app that declares nothing
contributes nothing — silence is honest and explicit, where the locator's URL-scrape made
every app contribute by accident.

**Every field is populated today.** Studio's `StudioSelection`
(`StudioToolbar.tsx:90-105`) already carries `blockId`, `blockKind`, `slideIndex`,
`pageIndex`, `label`, `text`. This is a projection of existing state, not new state.

---

## 3. D2 — The lane wire gains one optional field; the locator is left alone

`LaneTurnRequest` (`api/routes/lanes.py:75-85`) gains one optional `focus` object. Server
side it renders into the posture (D4). Three constraints:

**Per-turn, not durable.** Focus is volatile — it changes between turns and *within* a
turn. The lane↔artifact binding is durable. Different lifetimes, different homes: focus
never touches `context_metadata.lane`.

**The locator is not extended.** ADR-398 D2's string stays exactly what it is — opaque,
~20 tokens, steward-rail-only. Focus is the typed channel for lanes. Making one string
serve both altitudes would put two contracts behind one field, which is the fork ADR-441
refuses at the renderer level and this ADR refuses at the payload level.

**The renderers do not merge.** ADR-441 D1 stands: `ConversationPanel` (A1) and `LanePanel`
(A2) keep their protocols. D1's `SurfaceFocus` is shared *FE state*; D2's wire field is
lane-side only. Nothing here is a step toward merging the two chat surfaces.

---

## 4. D3 — The viewport is a first-class reading, distinct from the selection

The member can be *looking at* something they have not *selected*. On a deck in stage view
this is the normal case: ADR-520 made one slide the whole surface, and paging changes what
is shown without touching selection (`projection.ts:955-972` — `ensureStageNav` calls
`stageShow()` → `reportScroll()` and emits no point).

**Decision**: `StudioCanvas` gains an `onScrollPos` prop lifting the `{ y, slide }` payload
it already receives (`:510-517`) out of its ref and into surface state. `SurfaceFocus.viewport`
carries the page index; `y` stays in the ref (a pixel offset is restore state, not something
to tell an agent).

Precedence when composing the declaration: **selection wins where it exists; viewport fills
where it doesn't.** A member with slide 4 on the stage and nothing selected declares
`scope:'page', pageIndex:3, viewport:{pageIndex:3}`. A member with a block selected on
slide 4 declares `scope:'block'` with the block's identity — the viewport is redundant
there and the finer grain is the truer answer.

No runtime change: `currentSlideIndex()` already returns the shown slide on the stage and
the viewport-center slide off it. This is one prop.

---

## 5. D4 — Docs' section is the nearest heading above the caret

Docs has **no section unit**. Headings are flat siblings (`api/services/docs.py:56-60`);
there is no containing `<section>`, no heading→body nesting, no navigator (deleted with the
mode split, `StudioSurface.tsx:2024-2031`), no breadcrumb (paged-gated, `:2618`), and
`extract_outline` (`api/services/studio.py:1900`) returns bare strings with **no ids**.
Docs is `mode:'flow'` (`docs.py:38`), so `slideIndex`/`pageIndex`/`slot`/`arrange` are
structurally always null there.

**Decision**: in flow, the focus declaration names the **nearest `h1`/`h2` at or above the
caret block in document order**, derived in the projection runtime (which already walks the
DOM for `yarnnn-point`) and carried as an added field on that existing message. It declares
`scope:'block'` with the heading's id and its text as `excerpt` — because the heading block
*is* what exists. It does not claim `scope:'container'`: there is no container, and
declaring one would be a lie the substrate cannot back.

**"Section" therefore means "from this heading to the next"** — a reading convention, not
a structure. That is a real limitation and it is stated rather than papered over.

**Explicitly deferred**: emitting real `<section data-block>` wrappers in Docs. That is the
truer model and it is a substrate change — it touches the docs scaffold, ADR-521's flow
mechanics, and the shape of every existing docs artifact. It earns its own ADR, on evidence
that the heading convention is insufficient. Not bundled here.

---

## 6. D5 — Rendering: one bullet in the posture, in the posture's own register

The focus renders as **one bullet** in `build_studio_posture` (`api/services/studio.py:1913-1943`),
placed immediately after `{outline_section}` — a sibling of the existing bullets at
`_POSTURE_FRAME` (`studio.py:1618-1643`), before the first `- PATCH` line.

It matches that frame's register: operator words, "the member" as actor, prose not
key-value, **1-indexed for the member** (the precedent is `pageNoun` at
`SelectionBreadcrumb.tsx:59-61` and `askAboutSelection` at `StudioSurface.tsx:571-585`,
both of which already render 0-indexed state as 1-indexed prose).

```
- The member is viewing slide 4.
- The member has the heading block "Pricing" selected — "Pricing".
- The member is writing under the heading "Pricing".
```

**This is not ADR-446 D5's failure resurrected.** That decision cut selection→chat because
auto-seeding **appended prose to the member's composer on every click** — visible spam in
the member's own text, which they then had to edit or delete. This is categorically
different: a structured field the *server* renders once per turn, into the system posture,
which the member never sees and never has to clean up. The distinction is stated here so
the next session does not re-litigate it from the ADR-446 headline alone.

**Budget**: one line, ~15 tokens, sized to survive an envelope diet on the same logic
ADR-398 D2 used for the locator.

---

## 7. Consequences

- "Tidy up this slide" resolves. So does "rewrite this section," "what's wrong with this
  block," and "summarize what I'm looking at" — the deictic asks that are natural in an
  authoring surface and were previously unanswerable.
- The reference is **polymorphic by construction**: one type spans slide, block, container,
  heading-as-section, whole document, and screen. A fifth grain (ADR-519 D4's declared-not-
  shipped `multi`) extends the `scope` union without touching the wire.
- **Radar's accidental contribution becomes a deliberate one** — or an explicit silence.
  Radar's honest focus is `{app:'radar', path: declaration_path, scope:'document',
  label: topic}` (`RadarSurface.tsx:97-102`). It has no chat pane today, so it declares and
  nothing consumes it yet. That is the correct shape for the fourth app to inherit.
- Docs inherits D1–D3 free (same component, `app={DOCS_APP}`) and D4 specifically.
- **What this does not do**: it does not merge the chat renderers (ADR-441 D1 stands), does
  not extend the locator (ADR-398 D2 stands), does not make Docs sections real (§5,
  deferred), and does not give the agent a tool that *takes* focus as an argument — focus
  is situational context the agent reads, not an addressable handle it calls.

---

## 8. Implementation scope

| # | Change | Site |
|---|---|---|
| 1 | `SurfaceFocus` type + declare/read hook | `web/lib/shell/` (beside `useSurfacePreferences`) |
| 2 | `onScrollPos` prop lifting `{y, slide}` out of the ref | `StudioCanvas.tsx:361,510-517` |
| 3 | Nearest-heading walk on the flow point payload | `projection.ts:581-593` |
| 4 | Studio/Docs declare focus from `selection` + viewport | `StudioSurface.tsx` |
| 5 | Radar declares `{scope:'document', label:topic}` | `RadarSurface.tsx` |
| 6 | `focus` slot on the lane mount contract (ADR-441 D2) | `LanePanel.tsx` + `LaneMountSlots` |
| 7 | `focus` optional field on `LaneTurnRequest` | `api/routes/lanes.py:75-85` |
| 8 | Focus bullet rendered into the posture | `api/services/studio.py:1913-1943` + `_POSTURE_FRAME` |
| 9 | Prompt CHANGELOG entry (posture is LLM-facing) | `api/prompts/CHANGELOG.md` |

**Gates**: FE `next build` from `web/`; studio python gates via `python3` from `api/`; the
prompt ratchets (`test_adr383_trigger_framing_recarved.py`, `test_adr323_frame_collapse_finished.py`)
since D5 touches the LLM-facing posture.

**Click-pass**: the originating case is the acceptance test — open a deck, page to slide 4
in stage view, select nothing, ask "tidy up this slide," and confirm the agent acts on
slide 4 without asking. Then the Docs case: caret under a heading, ask "rewrite this
section." Both are human-driven — the flow runtime lives in an opaque-origin iframe that
synthesized keys cannot drive (ADR-521's finding).
