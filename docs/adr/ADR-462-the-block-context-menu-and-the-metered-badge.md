# ADR-462 — The block context menu: two entrances, one badge, a neutral page

- **Status**: **Accepted** (2026-07-16, operator-ratified through the 2026-07-16 right-click discourse — "think now we can implement, while documenting in process")
- **Dimension**: Channel (primary — where the member reaches) + Mechanism (the free/metered line made visible)
- **Amends**: ADR-458 D4 (the "one home for verbs" clause is narrowed to *settings*) · ADR-453 D7 (the accent inventory — selection goes neutral)
- **Preserves**: ADR-443 D2 (no eighth operation — every row is an existing op) · ADR-443 R1 (the DOM is the model) · ADR-461 D4 (the frame gate, now driving a third affordance) · ADR-440 D7 (gestures compose ops) · ADR-367 D3 (deliberate tiered redundancy) · ADR-456 D5 (mechanical is free; judgment is metered)
- **Derivation**: the 2026-07-16 discourse (Figma / Notion / PowerPoint menus scored against the shipped stack)

---

## 1. The question

The operator, from the right-click menus of Notion, PowerPoint and Figma: *can we use the
right-click menu, with a feature scope architected toward the discipline we already have for
clicks and blocks — but filesystem-native, AI-native, HTML-native? Figma's feature set feels
close, though ours should be much more compact.*

## 2. What was already true (the findings that shaped the answer)

Three facts, verified before designing, each of which removed work rather than adding it:

- **The menu component exists and is already mounted in the Studio.** `useFileContextMenu`
  (`FileContextMenu.tsx:184`) does right-click, anchoring and extra items. It is mounted on the
  Studio *landing recents* (`StudioSurface.tsx:1732`) — not on the canvas. Canvas right-click is
  **wiring, not building**. (This also explains the stale ADR-458 gate check "the Studio's
  FileContextMenu mount is deleted": it was not deleted, it was *relocated* by ADR-400
  Amendment 1. The pin is corrected here.)
- **The verbs exist.** `StructVerb = 'duplicate' | 'up' | 'down' | 'delete'`, `convertBlock`
  (turn-into), `duplicateBlock`, `deleteBlock`, `moveBlock`. No row in this menu is a new
  capability.
- **Re-arrange already ships, and it is MECHANICAL.** The `Re-arrange` thumbnail gallery
  (`StudioDesignTab.tsx:616`) swaps `data-arrange`; the kernel's CSS does the rest. **Zero LLM
  calls.** It is also not deck-scoped — `STUDIO_ARRANGEMENTS` carries rows for all four layouts.
  The operator's hypotheses (that it needs an AI call, and that it is deck+media only) were both
  false: the judgment was spent when the arrangement was authored into the registry; picking one
  is just picking. The **frame gate is for geometry**, and an arrangement is a token swap.

## 3. Decisions

### D1 — Right-click is a second ENTRANCE to existing verbs, never a second write path

Every row is an existing op reached from a new place. ADR-443 D2's closed seven-operation set is
untouched; no eighth operation, no new mechanism. A row that would require one is presumptively
out of scope.

The duplication with the Design tab and the toolbar is **deliberate**, and it is already ratified:
ADR-367 D3's macOS tiered-access principle (Control Center and System Settings hold the same
dials on purpose). **Right-click is the fast path; the Design tab is the dwell.** One
implementation underneath, two postures over it.

### D2 — ADR-458 D4 is narrowed: the Design tab is the one home for SETTINGS; verbs are reachable where the thing is

D4 read *"the Design tab is the one home for verbs and settings."* That clause is narrowed rather
than reversed. The distinction that survives:

- **Tune is a dwell** — open the tab, adjust a token, watch it change. Settings stay in the tab.
- **Act is a verb-and-gone** — duplicate, delete, rewrite. A verb does not want a tab.

Forcing "delete this block" through a panel that also holds typography is the same ergonomic
error as a hover-scoped resize handle that vanishes when reached for (ADR-461, fixed 2026-07-16).
D3's *consolidation* argument (stop having two places for one thing) is honoured for settings,
where dwell is the posture, and set aside for verbs, where it never applied.

### D3 — The compact set (~10 rows), scored against the reference wall

**Copy · Paste here** — *(sep)* — **Duplicate · Delete** — *(sep)* — **Turn into ▸ ·
Re-arrange slide ▸ · Bring forward** *(frame-gated)* — *(sep)* — **WRITE WITH AI: Rewrite… ·
Check this…** — *(sep)* — **THIS BLOCK: Copy link to block · History ▸**

Refused, with reasons (the inclusion test, so the next request is answered in advance):

| Reference item | Verdict | Why |
|---|---|---|
| Cut | **No** | Copy+Delete with extra failure modes. Ships when asked for. |
| Paste to replace | **No** | Figma has it because shapes are interchangeable; blocks are not. |
| Group / Frame selection | **No** | A container in a shadow tree — ADR-443 R1. |
| Create component / Plugins / Widgets | **No** | ADR-443 D7 refuses a widget ABI outright. |
| Flatten / Outline stroke / Use as mask | **No** | Raster/vector ops on shapes; we author blocks. |
| Add auto layout | **No** | Arrangements *are* auto-layout. |
| Font… / Paragraph… / Format Shape… (PowerPoint) | **No** | Dialogs onto a property inspector — that is the Design tab. Copying them yields two inspectors. |
| Bring to front / Send to back | **Frame-gated** | Z-order is geometry (ADR-461 D3/D4). On a reflowing layout it is the `left:40px`-at-40rem problem. Reuses `measurableFrame` — the **third** affordance on that one gate. |

**Copy link to block** and **History** are the two rows no reference can ship: `data-block-id` is
a durable address in a file on a real filesystem, and the revision chain joins by that same id
(`trace`). Their objects have no path; their history has no per-object join. The differentiator
surfaces in the most ordinary affordance there is.

### D4 — The metered badge, and why "Ask AI about this" was refused

The first draft carried one row, `Ask AI about this ▸`. The operator refused it as ambiguous, and
the reason generalizes: **it is a category, not an act.** Every other row is a verb with a
predictable outcome; that one was a door to a room where something unspecified happens, asking the
member to decide what they wanted *after* committing to the click.

So the AI door is **named acts under a group header**, each carrying a badge:

- **`AI` badge** (ochre, filled dot) on every metered row. **Free rows carry nothing** — silence
  is the signal; most of the menu is free, so marking the exception is cheaper than marking the
  rule. A badge only means something if its neighbours lack one (which is precisely why
  `Re-arrange` sitting un-badged one row up is load-bearing).
- **Three redundant signals**: group header (`WRITE WITH AI`) · per-row badge (survives if the
  group is ever split) · hue (the row's icon and hover state, so it reads before the eye arrives).
  Redundancy is correct here: this is the free/metered line, and it must be impossible to miss at
  a glance or mistake at speed.
- **The badge means METERED, not MUTATING.** `Check this…` writes nothing and is badged anyway —
  it costs a turn.

The operator's observation, recorded because it inverts the intuition: **a visible badge on
explicit verbs is *less* alarming and *more* intuitive than one vague unbadged row.** Ambiguity
was doing the scaring, not the meter. This is DP28's consent line (ADR-338) rendered at menu grain.

### D5 — The page is the member's; the accent is the system's

Selection was `2px solid #6366f1`. It goes **neutral** (`1px solid rgba(60,58,54,0.5)`), and the
corner grip follows it (an 8px square, neutral border, white fill — the PowerPoint/Keynote form).

The principle, which is the reusable part: **a saturated outline on the member's own content reads
as the app asserting itself over the page.** Every reference draws selection as a thin neutral
rule and reserves colour for what is *not* your content. So the accent survives exactly where it
says something the page cannot say for itself:

- **the editing state** (`contenteditable` — "you are typing into this" is a genuinely different
  fact from "this is selected"),
- **transient gesture chrome** (drop-line, column divider — predictions, not content),
- **the `+ Add here` affordance on hover** (empty scaffolding, not authored content).

### D6 — Two AI verbs, not four; the seed is a head start on a sentence, not a button

The draft carried four (`Rewrite… · Make shorter · Expand this · Check this`). The operator cut it
to two. **`Make shorter` and `Expand this` are rewrites with a pre-typed adjective** — menu rows
pretending to be verbs, and an open invitation to grow a third and a fourth by attrition. The two
that survive are irreducible:

- **`Rewrite…`** — *change this* (the lane writes the block)
- **`Check this…`** — *judge this* (the lane reads and answers; writes nothing)

**All AI rows are ellipsis verbs; nothing fires on click.** `seedComposer`
(`StudioSurface.tsx:381`) sets text *into* the composer and flips to the Chat tab — unsent, cursor
after it. The member types and presses enter. So the row is a **head start on a sentence, not a
button**, and shorter/longer/sharper are things the member *types*, which is strictly more
expressive than two rows would have been.

**No modal input.** The composer IS the input box: already on screen, already carrying the model
picker and the lane's history. A modal would be a second place to type at the AI.

### D7 — Right-click selects

Right-clicking an unselected block selects it, then opens the menu — matching Figma, PowerPoint,
Notion and Finder. The menu always acts on the thing under the cursor; requiring left-click-then-
right-click would be two gestures for one intent.

**The named consequence**: since ADR-461's grip follows the selection, right-clicking a block on a
slide also raises its corner grips. That is correct — it is selected, so it shows its grips — and
it is recorded here so it reads as design rather than as a surprise.

## 4. Falsifiers

1. Every menu row resolves to an op that existed before this ADR (no eighth operation).
2. No metered row is unbadged, and no free row is badged.
3. `grep` shows no saturated accent on a selection outline; the editing state keeps its accent.
4. `Bring forward` is absent on `document`/`article`/`page` and present on a slide — the same
   `measurableFrame` gate that decides handles-vs-gutter.
5. An AI row seeds the composer and sends nothing; the lane fires only on the member's enter.
6. Right-click on an unselected block selects it (one gesture, not two).

## 4a. Implementation notes (what the build changed about the design)

Two deviations from §3, recorded because a doc that quietly disagrees with its code is worse
than no doc:

- **`Bring forward` did not ship; `Move up` / `Move down` did.** D3 scored z-order as
  frame-gated geometry and was ready to ship it — but the only op in reach is
  `moveBlock(html, id, 'up'|'down')`, which **swaps DOM siblings**: document order, not
  stacking. The kernel ships no `z-index` token, so a row labelled *Bring forward* would have
  moved a block up the FLOW and called it *front*. The honest verb is the one the op performs.
  **Real z-order arrives with a token, if it ever earns one** — and at that point it is
  frame-gated exactly as D3 says. The `framed` flag is already carried on the payload, so the
  gate is wired ahead of the row that will need it.
- **`FileContextMenu` was NOT reused.** Its contract is file-shaped (`path`, `name`, file
  verbs) and a block is not a file; bending it would have made one component serve two
  substrate grains. `StudioBlockMenu` borrows its dismissal behaviour and visual conventions
  and nothing else. (This is the ADR-462 §2 finding restated: the *component* exists, but what
  it is a menu OF is the wrong noun.)

**The block clipboard** is session-scoped (`useRef`), and its unit is a block's `outerHTML`,
not its text — so a pasted block arrives whole (kind + tokens + citation islands intact)
instead of smearing characters into whatever received it. `pasteBlock` rides
`materializeFragment`, which re-stamps ids, so **a paste is a new block rather than a second
element wearing an address the trace already knows**. A cross-artifact block clipboard is a
substrate question, not a menu one; it is not taken here.

**The ADR-458 gate's `FileContextMenu mount is deleted` check remains red**, and it is left
that way deliberately: it asserts a deletion ADR-400 Amendment 1 *reversed* (the menu moved to
the landing recents). Correcting it belongs to ADR-400's cascade, not to this arc — recorded
here so the next reader knows it is canon-stale rather than code-broken.

## 5. Cascade

`web/components/workspace/viewers/projection.ts` (neutral selection + grip; contextmenu →
`yarnnn-point` with `menu: true`) · `StudioCanvas` (the menu flag passthrough) · `StudioSurface`
(the canvas menu mount + the two seeds) · `docs/design/STUDIO.md` (the interaction model line) ·
ADR-458 (amendment banner: D4 narrowed) · gate `api/test_adr462_context_menu.py` · the ADR-458
gate's stale `FileContextMenu` pin corrected. No backend change, no registry change, no posture
change, no CHANGELOG entry (nothing LLM-facing moves — the seeds are member-authored text).

## 6. The one-line statement

**A right-click is a second entrance to verbs that already exist, never a second write path: the
Design tab keeps settings because tuning is a dwell, the menu takes verbs because acting is not,
every metered row wears a badge so the free/metered line is impossible to miss, the two AI verbs
are irreducible (change this, judge this) and seed a sentence rather than fire a button — and the
selection outline goes neutral, because the page belongs to the member and the accent belongs to
the system.**
