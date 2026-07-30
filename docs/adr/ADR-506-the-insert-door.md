# ADR-506 — The insert door: a button in the centre, one gesture underneath

- **Status**: **Accepted + Implemented** (2026-07-30, operator-ratified — *"insert should be a
  studio wide (all document types), but than, button details differe depending on the document
  type… it should be the center (where deck like type has the re-arrange)"*). The operator's
  centre-and-studio-wide framing is taken in full; the *per-type button details* half is
  **declined with reasons** (§3, D3) because ADR-505 D4 deleted exactly that matrix hours
  earlier, and the operator's own governing instinct in that discourse was *"we need to
  simplify."*
- **Date**: 2026-07-30
- **Dimension**: Channel (primary — how a member reaches the insert act). No new substrate, no
  new write path, no schema, no migration, no new op.
- **Amends**:
  - **ADR-482 §7** — the one explicitly-deferred item (*"a centered on-canvas insert button
    (D1 makes `/` work, which was D2's premise; **revisit only if `/` proves insufficient in
    use**)"*). The condition was met; this is the revisit.
  - **ADR-505 D4** — the insert grammar gains a **door**, not a mechanism. The five-mechanism
    table is unchanged; `/` remains the only block-insert route, and the button is a second
    way to *reach* it.
  - **ADR-482 D3** — *the chrome waits for the mode* reaches the **toolbar**, which D3 never
    touched (it fixed the projection and the block menu; the toolbar kept a `?? 'flow'`
    boolean).
- **Preserves**: ADR-466 D4 (insert is located, with no exceptions — the door lands the caret
  at the location before it opens anything) · ADR-505 D4 (`/` universal and ungated; no
  per-type kind subsetting) · ADR-480 (the editing grain; the door is grain-blind because it
  routes through `editHost()`) · ADR-209 (no write path added — the button posts no op) ·
  ADR-443 R1 (the DOM is the model).

---

## 1. The question

The operator asked for an Insert button spanning all document types, positioned by reference to
where Re-arrange sits on a deck. ADR-482 §7 had
already considered one and deferred it behind a named condition. So the question is not *would
a button be nice* — it is **whether the condition ADR-482 set has now been met**, and if so,
what shape the button takes without re-opening what ADR-505 closed.

## 2. What the audit found

An audit of every insert entry point across the studio (9 routes at the time of reading, run
against a tree that already carried ADR-505) returned one fact that decides this ADR:

**ADR-505 D4 deleted the hover gutter on *every* mode.** ADR-481 D2 had removed it on `flow`;
D4 removed the `paged` remainder along with the `⋮⋮` reorder. The gutter's `+` was the last
*visible* block-insert affordance anywhere in the studio.

What remains, per type:

| Type | Block insert | Page insert |
|---|---|---|
| `document` | `/` only | — (no page grain) |
| `deck` | `/` only | New slide + · Re-arrange |
| `web` | `/` only | New section + · Re-arrange |

So `/` is now the **sole** block-insert route in all three types, discoverable only by already
knowing it. The one cold-start hint (`projection.ts` — *"Type / for blocks, or just start
writing"*) renders only on a genuinely `:empty` root, which is exactly the state a document
leaves after its first keystroke and never returns to.

ADR-482's condition — *"if `/` proves insufficient in use"* — was written when `/` was one of
several routes on `paged` and the only one on `flow`. It is now the only one anywhere. The
condition is met by a wider margin than when it was set, and the operator's request is the
use-evidence it asked for.

**A second finding, smaller and worth fixing while here.** `StudioToolbar` took
`isPaged: boolean`, derived in the surface as `…?.mode ?? 'flow'`. Every other mode-conditional
surface (`StudioCanvas`, `StudioBlockMenu`, the projection) had already moved to the tri-state
`mode` per ADR-482 D3, precisely so an unresolved mode withholds rather than guesses. The
toolbar was the one holdout: on a deck, it rendered zero buttons for the frames before the
vocabulary landed, then grew two. A boolean cannot express *don't know yet*.

## 3. Decisions

### D1 — The centre of the row is INSERT, and the button is a DOOR

A button labelled **Insert** on the toolbar row (placed by D4), present in **every**
document type with no mode gate.

**It types the slash.** The button does not post its own insert op, does not open its own
panel, and does not know what a block kind is. It sends one message (`yarnnn-slash-invoke`);
the runtime resolves an insertion point, focuses it, calls `document.execCommand('insertText',
false, '/')`, and opens the palette through the ordinary path. Everything downstream — the
anchor, the live filter, the run-splice on pick, the citation-picker branch, the chart-seeds-
the-lane branch — is the gesture the member could have typed, **because it is that gesture**.

This is what makes the button compatible with ADR-466 D4 (*"insert is located, with no
exceptions"*) and ADR-505 D4 (*"`/` is deliberately universal and ungated"*). A door onto a
located act is still located: the runtime places the caret *first* and inserts *there*. The
invariant that keeps it honest is asserted in the gate: **there is exactly one sender of
`yarnnn-slash-open` in the codebase.** A second sender would mean the button had grown its own
path, which is the thing this decision exists to prevent.

**The one thing a click has that a keystroke does not is the absence of a caret.** A member may
click Insert having never focused the document. So `slashFromToolbar()` resolves an insertion
point in three falling steps: the live caret if it is inside the edit host; otherwise the end
of the host's content; and on `paged` with nothing being edited, `enter()` on the last block
first — which is the anchor a click-then-type would have produced. `insertText` rather than a
manual text-node splice, because the browser then moves the caret past the character for us and
leaves exactly the post-input state the existing opener re-reads.

**Placement: see D4.** This shipped absolutely centred on the row and was re-placed the same
day, on sight, into the left cluster. The reasoning for both is in D4 rather than here, because
the correction is the more instructive half.

**The shared opener is extracted, not duplicated.** The typed `/` and the door call one
`openSlashAtCaret()`. Two bodies would drift, and the drift would be invisible until one route
silently stopped anchoring correctly — which is the ADR-482 failure mode exactly.

### D2 — The toolbar takes the TRI-STATE mode

`isPaged: boolean` → `mode: 'flow' | 'paged' | undefined`, with `const isPaged = mode ===
'paged'` derived inside — the **affirmative test** idiom ADR-482 D3 established. The surface
hands it `resolvedMode` (which is `undefined` until the registry answers), never the
`?? 'flow'` chrome default.

`isPaged` survives in `StudioSurface` for the navigator and the row layout, where the
show-less-on-unknown default is the right one. Only the toolbar, which renders *page-grain
buttons* on the answer, needs to tell *document* from *don't know*.

### D3 — Insert is NOT subsetted per type; the button details do NOT differ

The operator asked for per-type button details. **Declined, with the reasoning stated so the
next reader can reverse it if the evidence changes.**

ADR-505 D4 had, hours before this ADR, deleted precisely this: *"Insert is one sentence per
grain with **no per-type subsetting** — the 4×4 matrix with mode-conditional cells that produced
the ADR-482 hole is gone."* Re-introducing per-type kinds would mean:

1. **Rebuilding the deleted matrix.** The registry has no `applies` column on blocks (tokens and
   measures have one; blocks deliberately do not). Adding one, then filtering the palette by
   mode, is the mode-conditional cell structure ADR-505 removed — and the ADR-482 hole was born
   in exactly that structure.
2. **Re-opening the ADR-482 D3 race.** `StudioSlashPalette` takes no `mode` prop **by design**.
   Giving it one means the palette's *contents* depend on an async value, so a member who opens
   it in the first frames after load sees a different list than one who waits.
3. **Contradicting the ratified reading of `/`.** ADR-505 D4 gates the slash runtime on
   `opts.edit` alone, *"with no `paged`/`flow` branch."* The door inherits that ungatedness
   structurally — `slashFromToolbar` lives inside `EDIT_SCRIPT`, which is gated on nothing else.
   Per-type contents would require a branch the ADR says must not exist.

**What DOES differ per type is already correct and stays**: the page-grain pair to the left
(New ‹slide|band› + Re-arrange) renders on `paged` only, because a `document` has no page unit
to offer. That is the real per-type difference, it is where the operator saw Re-arrange, and the
Insert button sits beside it in every type. The types differ where they actually differ.

### D4 — Insert is LAST IN THE LEFT CLUSTER, not centred on the row

D1 shipped the button `absolute inset-x-0 flex justify-center`, arguing that a laid-out button
would "drift under the member's cursor" when the page-grain pair mounts or the crumb's name
changes length. **Rendered, that reasoning inverted**, and the operator caught it on sight:
*"the insert button should be aligned right next to left buttons (for reference, thus
re-arrange for deck)."*

**The original brief already said this**, and D1 read it too literally. It was *"it should be
the center (where deck like type has the re-arrange)"* — and the parenthetical is the operative
clause: **the place where Re-arrange lives**, i.e. the toolbar's control cluster, not the
geometric midpoint of the row. "Center" named the *region between the crumb and the zoom*, which
is where the whole cluster already sits. Taking the word and dropping the gloss produced a
button centred in a region rather than placed in a cluster.

Absolute centring does not stabilise the button — it **detaches** it from the controls it
belongs with. On a `document` (no page-grain pair) it floats alone in the middle of an
otherwise empty row, reading as unrelated chrome rather than a toolbar verb. On a `deck` it
sits across a visible gap from Re-arrange, so the eye parses two clusters where there is one
toolbar.

The corrected principle: **the toolbar's verbs are ONE cluster, scanned left-to-right, and the
ordering that carries meaning is GRAIN, not position on the row** — New ‹noun› (page) ·
Re-arrange (page) · Insert (block). On a flow document the pair is absent and Insert is simply
the first button: the same cluster, one verb shorter. The mount-time shift D1 feared is a
one-time settle, which is what every other button in this row already does.

**The cost the re-placement carries, and pays.** Moving inside `menuRef` means moving inside
the **click-away boundary**, so a press on Insert no longer counts as "outside" and an open
New-‹noun› gallery would survive — the palette would then open underneath a stale panel. The
button therefore closes the panel explicitly (`setOpen(null)` before `onInsert()`). Centred and
outside the cluster, this was free; joining a cluster means inheriting its dismissal duty. That
is the kind of cost a placement change quietly carries, and it is why the gate now pins both
halves (not-centred, and closes-the-gallery).

**The general lesson**, recorded because this arc keeps re-learning it: a layout argument made
from the code is a hypothesis about what the member will SEE. D1's was internally coherent and
wrong, and one screenshot settled it. Chrome decisions want a render before they want an ADR
paragraph.

Two candidate narrowings were considered concretely and rejected: `metrics`/`button` as
`paged`-shaped (a document can legitimately carry a metrics row or a CTA link), and `divider` as
`flow`-shaped (a slide can carry a rule). Neither survived a first-principles pass, which is
itself evidence the subsetting was cosmetic.

## 4. What this deleted

Nothing. This ADR is purely additive at the affordance layer — one message, one button, one
extracted function, one prop widened. The absence of a deletion ledger is the tell that it is a
door and not a mechanism.

## 5. Gates

`api/test_studio_slash_anywhere.py` — **46/46** (was 36). Seven new checks under
*"the toolbar door"*: the invoke message exists across all three layers; **exactly one
`yarnnn-slash-open` sender**; the door reuses the shared opener rather than posting its own;
the button carries no mode/`isPaged` test **within its own JSX** (sliced from the label back to
its tag — the region a guard would have to appear in); `slashFromToolbar` lives inside
`EDIT_SCRIPT` (asserted with a new brace-blind `_script_body()` helper, because "is X inside
runtime Y" is a real question a substring search cannot answer — the ADR-505 D6 lesson); and
the two D4 halves — **not** absolutely centred, and Insert closes an open gallery.

The ungated check was itself re-cut once, for the same reason as the proximity proxy below: it
pinned `onClick={onInsert}` verbatim and broke the moment D4 gave the handler a body. A literal
is not the invariant; *"no mode test guards this button"* is.

One check in that gate was **re-cut, not merely widened**. It regexed `e.key !== '/' … yarnnn-
slash-open` inside a character window (1200, widened to 2000 by ADR-480) — a proximity *proxy*
for the path being intact that was really a length budget, and it broke the moment the opener
was extracted. The code was correct; the proxy described a shape it no longer had. It now
asserts the two hops by name (keydown → opener, opener → message), each still bounded, so a
refactor that keeps the path honest no longer fails for its distance.

`api/test_studio_layout_mode.py` — **36/36** (was 34). The check pinning `isPaged: boolean;`
becomes three: the tri-state prop, the affirmative derivation, and the surface handing over
`resolvedMode` rather than the defaulted boolean.

**Full studio sweep after: 5 gates carry failures, all verified PRE-EXISTING** by re-running
them against a stashed clean tree — byte-identical results (`test_studio_chrome_and_load` 15/17,
`test_studio_name_is_one_fact` 31/32, `test_studio_split_merge` 18/20,
`test_adr480_flow_editing_grain` 27/30, `test_adr475_decomposed_generation` 0/1). The first four
are the set ADR-505 §5 already named; each still deserves its own pass. `next build` passes.

**Not verified by these gates, and stated honestly**: no gate exercises the *click*. These are
static-text gates — they prove the path is wired, not that it fires. The falsifier below is a
live-click check, and it is owed.

## 6. Falsifiers

In ADR-482 §10's shape — **the act completes**, not the affordance appears:

1. On a `document`, clicking **Insert** with the caret mid-sentence opens the palette at that
   line, and picking an item inserts there — not at the end.
2. On a `document` with the canvas never focused, clicking **Insert** inserts at the end of the
   content rather than doing nothing.
3. On a `deck` with no block being edited, clicking **Insert** enters the last block and the
   palette anchors on it.
4. `grep -c "type: 'yarnnn-slash-open'"` over `projection.ts` returns **1**.
5. The button renders identically on all three types, and the palette offers the same kinds in
   each.
6. On a `deck`, the toolbar does not render the page-grain pair before the vocabulary lands and
   then grow it (D2 — watch a cold load with the network throttled).
7. **(D4)** On a `deck`, Insert sits immediately right of Re-arrange with the row's ordinary
   `gap-1` — no gap, no centring. On a `document` it is the row's first button, hard left.
8. **(D4)** With the New ‹noun› gallery OPEN, clicking Insert closes it and the palette opens
   over a clean row — not underneath a stale panel.

## 7. What is NOT decided here

- **Grouping the palette by provenance** (*from thin air* / *from the workspace* / *from
  inference* — the ADR-466 D4 grammar). The registry already carries a `group` column
  (`content` / `data` / `media`) that the palette renders flat. If that grouping is worth
  surfacing, it belongs in `StudioSlashPalette` where **both** doors inherit it — not behind
  the button, which would give the typed gesture the worse list. Named, not taken.
- **A `⌘K` shortcut.** `/` types at the caret and the button is now discoverable; a third door
  needs its own justification.
- **The IMAGES stage's missing page-grain buttons.** `routes/studio.py` builds the served
  `arrangements` map from `STUDIO_ARRANGEMENTS` directly rather than through
  `resolve_arrangements()`, so an `image` stage (`mode: paged`, one declared `free` arrangement)
  resolves to `[]` and loses both buttons. Real, one line, and **unrelated to insert** — it is a
  registry-bypass bug, and burying it here would hide it. Recorded for its own pass.

## 8. Key files

`web/components/workspace/viewers/projection.ts` (`slashFromToolbar` + the extracted
`openSlashAtCaret` + the `yarnnn-slash-invoke` handler, all inside `EDIT_SCRIPT`) ·
`web/components/studio/StudioCanvas.tsx` (the `slashInvoke` prop + its post) ·
`web/components/studio/StudioSurface.tsx` (`invokeSlash` + the nonce; `mode={resolvedMode}`) ·
`web/components/studio/StudioToolbar.tsx` (Insert, last in the left cluster; the tri-state
`mode`) · `api/test_studio_slash_anywhere.py` (+10, two re-cut) ·
`api/test_studio_layout_mode.py` (+2) ·
`docs/design/STUDIO.md` · `api/prompts/CHANGELOG.md`.
