# ADR-482 — The flow completion pass: insert parity, chrome scope, and the mode race

- **Status**: **Accepted** (2026-07-23, operator-ratified — *"confirmed in full, let's first
  implement then ensure we have some documentation doing version control, changelog
  associated to these surfaces and decision as we now need to stabilize + harden the
  direction both in documentation and code."*)
- **Date**: 2026-07-23
- **Dimension**: Channel (primary — the flow surface's chrome and input path). No new
  substrate, no new write path, no schema, no migration, no new primitive.
- **Amends**:
  - **ADR-481 D2** — the premise is *completed*, not reversed. D2 deleted the gutter on flow
    on the stated ground that *"insert on flow is `/` at the caret and right-click — both
    already built."* §2 shows `/` was **not** working on flow at the moment D2 shipped. D2's
    ruling stands; this ADR makes its premise true.
  - **ADR-480 D4** — the simulation deleted on flow took three affordances with it that were
    never part of the simulation (§3). They are restored on flow at the correct grain.
  - **ADR-462 D5 / ADR-481 D3** — the neutral-selection and hover-cue rulings are extended to
    the two blues they did not name (§4).
  - **ADR-453 D4** — the Properties inspector's section ORDER becomes scope-descending
    (file → selection). The tab's content and mode-invariance are untouched.
- **Preserves**: ADR-209 (one attributed write door — this ADR adds no writer) · ADR-443 R1
  (the DOM is the model) · ADR-443 D2 (no eighth operation) · ADR-448 (`data-ref` edges
  untouched) · ADR-480 D1–D3 (the flow editing grain, ids-normalized-on-write) · ADR-481
  D1/D4/D5 (flat scaffolds, navigator, projection-time flattening) · **every `paged` surface
  in full** — deck, page and IMAGES are not touched by any decision here.

---

## 1. Why this ADR exists

ADR-480 moved the editing grain to the document root. ADR-481 rebuilt the chrome drawn around
it. Both were correct in isolation. This pass is the **audit of what fell between them** —
commissioned when the operator brought a click-pass screenshot and six specific complaints,
which turned out to be six symptoms of four causes, one of them a regression that neither
prior ADR could see from inside its own scope.

The governing observation:

> Two individually-correct decisions composed into a hole neither could see alone.

ADR-480 D1 stopped calling the per-block `enter()` on flow — correctly; that is precisely what
buys cross-block drag-selection. ADR-481 D2 deleted the gutter `+` on flow — correctly; the
caret is the insertion point. Neither noticed that the slash palette's terminal step reads a
variable that **only `enter()` assigns**. The first ADR emptied it; the second removed the
alternative that was masking it.

This is the second time in this arc that a defect lived in a premise rather than in code
(ADR-480 §1 was the first). The lesson is recorded in §7.

## 2. The finding: flow had no working insert path

Three facts compose into one regression:

**F1 — `yarnnn-slash-take` bails on a variable flow never sets.**
`projection.ts:1858` — `if (slashStart < 0 || !slashNode || !editingEl) return;`
`editingEl` is assigned in exactly one place: `enter()`, `projection.ts:1055`.

**F2 — flow never calls `enter()`.**
`projection.ts:508-514` returns from the click handler before reaching `__yarnnnEnter`, under
ADR-480 D1. Therefore `editingEl` and `editingId` are **permanently null in `FLOW_MODE`**.
Line `:1871` compounds it — `var id = editingId;` sends null as the target block.

**F3 — the alternative entrances were removed on flow.**
The gutter `+` (`projection.ts:1936`) lives inside `GUTTER_SCRIPT`, injected only when
`opts?.edit && opts?.mode !== 'flow'` (`projection.ts:2991`). The toolbar's insert affordances
are `isPaged &&`-gated (`StudioToolbar.tsx:222`, `:230`).

**Therefore**: on a flow document the palette opens, filters, and silently does nothing on
pick. `yarnnn-slash-taken` is never posted; the parent's `onSlashTaken`
(`StudioSurface.tsx:1513`) never runs. **Insert was unreachable on the document type by every
route.** The operator's request for a centered insert button was a correct reading of a real
absence — and is answered here by repairing `/` rather than by adding chrome, because ADR-481
D2's reasoning about the caret remains sound.

### D1 — `yarnnn-slash-take` resolves its host and target from the caret

The handler stops reading the per-block edit-session variables and uses the seam ADR-480
already built for exactly this: `editHost()` (`projection.ts:1305`), which returns the flow
root on flow and `editingEl` on paged.

- the guard becomes `!editHost()` — true in both grains
- the target block is resolved from the caret's own ancestry
  (`slashNode.parentElement.closest('[data-block]')`), not from `editingId`
- `exit(false, true)` is called only when a per-block session is actually open — on flow there
  is none to exit, and calling it is a no-op that misleads the reader

The one-gesture-two-ops discipline is unchanged: the runtime still exits SILENT and the
parent's op remains the sole writer of the resulting head.

## 3. The affordances that fell into `GUTTER_SCRIPT`

`GUTTER_SCRIPT` (`projection.ts:1900-2865`) is a ~965-line block that accreted three things
with different lifetimes: the gutter itself, the selection box, **and** the keyboard verb
handler. ADR-481 D2 deleted the first on flow and unavoidably took the third with it.

**F4 — the keyboard verbs are dead on flow.** `⌘C`/`⌘V`/`⌘D`/`⌫` are handled at
`projection.ts:2754-2792`, inside that script. `StudioBlockMenu.tsx:167-180` renders those
exact shortcut hints unconditionally. On flow the menu **advertises keys that do nothing** —
the precise defect the file's own comment at `:2714-2718` describes as already fixed. It was
fixed for paged only.

**F5 — left-click selection is invisible on flow.** The flow branch (`:509-514`) sets `cur`
but never applies `.yarnnn-pointed`; the right-click handler (`:585-589`) has no flow branch
and does apply it. So right-click outlines and left-click does not. No comment claims this is
deliberate; it is an omission.

### D2 — Keyboard verbs and pointer selection leave `GUTTER_SCRIPT`

Both move to the pointer runtime, which is injected in **both** modes. The gutter script keeps
only what is genuinely gutter: the `+`/`⋮⋮` chrome and the selection box.

This is a scope correction, not a feature: an affordance's injection site should follow its
lifetime, not the historical accident of which script it was first written into. `GUTTER_SCRIPT`
being mode-gated is correct; the keyboard verbs being *inside* it was not.

`.yarnnn-pointed` is applied on flow left-click, matching right-click. The neutral 1px rule
(ADR-462 D5) is already defined in both sheets (`:271-273` flow, `:323-325` paged) — only the
application was missing.

## 4. The three blues, and the race that made one of them visible

**F6 — `#6366f1` appears at four independent sites** with no shared token: `:825` (the EDIT
outline, 2px + fill), `:889` (the selbox border), `:908` (the handles), `:869` (a column
divider). Nothing derives them from one constant.

**F7 — the mode race.** `resolvedMode` is `undefined` until the vocabulary fetch returns
(`StudioSurface.tsx:582`), and is passed straight to the canvas (`:2170`), where it is a
**projection input** (`StudioCanvas.tsx:310` — the effect re-runs on `mode`). So a flow
document's **first frames project as paged**: `data-yarnnn-mode` is unstamped, `GUTTER_SCRIPT`
is injected, `POINTER_CSS` and the paged `EDIT_CSS` apply. Then the vocabulary lands and the
entire iframe re-projects.

This is the blue box in the operator's screenshot, and it is why the audit's first reading
("the artifact must be paged") was wrong: the artifact is flow, and was rendering paged
chrome for the first frames. `StudioSurface.tsx:577-581` anticipated exactly this hazard for
the *editing grain* and chose `undefined` deliberately to avoid putting `contenteditable` on a
deck's root. That reasoning is correct and is preserved. What it did not anticipate is that
the same `undefined` also selects the paged **chrome**.

### D3 — The mode gates the grain; the chrome waits for the mode

The two consumers of `mode` are separated:

- **The editing grain** keeps `resolvedMode`'s conservative `undefined` → per-block behavior.
  Defaulting a deck to flow would put `contenteditable` on its root and let a whole-region
  write land against a paged artifact. That hazard is real and unchanged.
- **The chrome** (gutter injection, pointer CSS, edit CSS, selbox) renders **nothing
  mode-specific until the mode is known.** No gutter, no hover cue, no selection box on an
  unresolved projection — matching the `layoutMode` default's own stated principle
  (`StudioSurface.tsx:571-573`: *"the safe direction is the one that shows LESS chrome, so
  nothing flashes in and back out"*).

### D4 — `EDIT_CSS`'s indigo outline is paged-only, and the blues share one token

The 2px indigo edit outline is a **paged** affordance: it says *this object is live*, which is
meaningful when one block at a time is editable. On flow the `contenteditable` lands on
`main`/`article`, so the selector cannot match — the rule is dead code on flow today, and
gating it makes the intent legible rather than accidental.

The four `#6366f1` sites collapse to one CSS custom property. This is hygiene, not behavior:
it makes a future accent change one edit instead of four, and it makes the *count* of blues
auditable.

## 5. The right-click menu is mode-blind

**F8 — `StudioBlockMenu` has no `mode` prop and no flow/paged branch anywhere in the file.**
Gating is by `hasBlock` / `target.positioned` / kind-legality only. So on a flow document the
menu offers **Move up**, **Move down**, **Duplicate**, **Copy**, and **Paste here** against a
surface where a block is an annotation, not an enclosure (ADR-480 D2). Only the z-order rows
self-gate, and only incidentally (`positioned` requires `.slide`).

### D5 — The menu is scoped by mode, and the scope is derived, not enumerated

The menu receives `mode`. On flow, rows whose meaning depends on the block being an
**enclosure** are withdrawn:

| Row | flow | Why |
|---|---|---|
| Copy · Paste here · Duplicate · Delete | **keep** | act on an addressable region; meaningful on an annotation |
| Turn into ▸ | **keep** | ADR-480 D2 names it as a surviving block-addressed act |
| Move up / Move down | **withdraw** | reordering enclosures; on prose the member edits text directly |
| Bring forward / backward | already hidden | `positioned` requires `.slide` |
| Rewrite… · Check this… | **keep** | AI acts on an addressed region |
| Copy link to block · History | **keep** | addressing and attribution, both file/region-grained |

The keyboard hints render only where D2 has made the key live.

## 6. Properties: file identity leads

**F9 — the invariant tail renders LAST.** `File` / `Share` / `Export`
(`StudioDesignTab.tsx:911-1007`) is mode- and scope-invariant by deliberate design
(`:905-910`), but sits *below* the scope-following half — so on a block selection the panel
reads `HEADING · T1 → WIDTH → ALIGN → TONE → FILE`, and file identity is buried under
block properties.

**F10 — a latent no-op.** `Rename…` (`:923`) sets `renaming` state whose input lives in a
*different component's* subtree (`StudioSurface.tsx:2060-2085`). Where the crumb is not
rendered — narrow viewport, or the mobile pane where `canvasActive` is false (`:1966`,
`:2016`) — the button silently does nothing.

### D6 — The panel is ordered by scope: file, then selection

The invariant tail moves **above** the scope-following half. The panel reads outermost-in:
*this file* → *this selection*. Nothing else about the tab changes — same sections, same
mode-invariance, same verbs.

This also resolves the operator's stated goal directly ("consistency for file details is
maintained there"): rename is already Singular — Properties' button and the crumb click arm
one input with one commit path (`commitRename`, `StudioSurface.tsx:407`). The problem was
never two implementations; it was that the one implementation was at the bottom of the panel.

D6 does **not** relocate the rename input into Properties. F10 is real but is a separate
defect with its own fix (render the input where the button is, or disable the button when the
crumb is absent); folding it into a reorder would conflate a layout change with a control-flow
change. It is recorded in §8 as owed.

### D7 — The breadcrumb carries the document-type glyph

`studioShapeStyle()` (`studioShapes.ts:28-33`) already maps `document`→`FileText`,
`deck`→`Presentation`, `article`→`Newspaper`, `page`→`LayoutTemplate`, with a neutral `File`
fallback, and already has three consumers. The crumb is the one place that should carry it and
does not. The workbench has `template` in scope (`StudioSurface.tsx:551`).

Two adjacent gaps close with it: `image` gains a registry row (IMAGES currently falls to the
neutral glyph), and the crumb's hardcoded literal `"Studio"` (`:2052`) becomes app-aware,
matching the landing (`:2762`) so IMAGES no longer reads "Studio / …" in the workbench while
reading "Images" on its landing.

## 7. What is NOT decided here

**Paste fidelity is deliberately excluded.** Both handlers (`projection.ts:1109-1115` paged,
`:1164-1170` flow) `preventDefault()` and re-insert `text/plain`; no `text/html` path exists
anywhere. This is a **security decision**, not an oversight — the comment names it
("no HTML injection through the clipboard"), and it is the same reasoning that rejected the
same-DOM ceiling (stored XSS via the citation graph).

Loosening it to preserve formatting requires an allow-list sanitizer (which tags, which
attributes, what happens to `data-ref` and `data-block-id` on inbound HTML) and is a carve of
its own. Sweeping it into this pass would bury a security-relevant change under six cosmetic
ones and make its reasoning invisible to the next reader.

Recorded honestly: **ADR-480 D1's promise of "copy of a multi-paragraph span with structure
intact" holds for copy OUT of the document only.** Paste IN is flat in both grains. A second
asymmetry belongs with it: the menu's ⌘C writes an in-memory `blockClip` ref
(`StudioSurface.tsx:1059-1067`), not the OS clipboard — so ⌘C here then ⌘V in another app does
nothing, and vice versa. Two clipboards that present as one. Both belong to the paste ADR.

**Also not decided**: a centered on-canvas insert button (D1 makes `/` work, which was D2's
premise; revisit only if `/` proves insufficient in use), and pagination (ADR-480 D6's
standing refusal is untouched).

## 8. Falsifiers

1. On a flow document, typing `/` and picking an item **inserts** — `yarnnn-slash-taken` is
   posted with a non-null `blockId` resolved from the caret.
2. On a flow document, `⌘D` duplicates and `⌫` deletes the pointed block; the hints in the
   right-click menu correspond to live keys in both modes.
3. A left-click on a flow block applies `.yarnnn-pointed`, matching right-click.
4. A projection with `mode === undefined` injects no gutter, no selbox, and no hover-cue rule;
   a resolved projection injects per its mode.
5. `EDIT_CSS`'s indigo rule is absent from a flow projection and present on a paged one.
6. `#6366f1` appears as a literal at most once in `projection.ts`; the other sites read the
   custom property.
7. `StudioBlockMenu` renders no Move up/down on flow and both on paged.
8. Properties renders `File` before the scope section in every mode and at every scope.
9. The crumb shows the type glyph for all five layouts and reads "Images" in the IMAGES
   workbench.
10. Every `paged` gate still passes: bounding box, handles, navigator strip, add-here, slots.

## 9. The owed work (recorded, not done)

- **F10 rename no-op** — the button arms an input in another subtree that may not be rendered.
  *Still owed.* Investigated 2026-07-23 as the prime suspect behind an operator report that
  a new document offered "nowhere to type the name" — and **exonerated**: the substrate
  ledger showed the crumb input had rendered, been typed into, and committed. That report's
  actual causes were the two in [ADR-483](ADR-483-the-name-is-what-the-member-typed.md) (a
  path-derived crumb + an unguarded IME Enter). The split-subtree fragility is real and
  unfixed; it is simply not what bit here.
- **The paste ADR** — sanitizing paste + the two-clipboard asymmetry (§7).
- ~~**Dead code** — `StudioDesignTab.tsx:356`'s `document-canvas` branch, unreachable since
  ADR-472 moved canvas to `image`; `StudioToolbar.tsx:11-12`/`226-230`'s comments describing a
  Re-arrange gallery deleted 2026-07-21.~~ **Done** (ADR-483 cleanup pass, 2026-07-23). The
  `canvas` branch was verified dead against the served registry before deletion — no layout
  slug is `canvas`, no token declares `document-canvas` — rather than deleted on the note's
  word. The toolbar's *header* was the stale half (it still called the verb "Layout"); the
  inline comment at the button was already current.

## 10. The lesson, recorded

ADR-480 §1 found a defect that recurred across five passes because it lived in a premise all
five shared. This ADR found one that lived in the **seam between two premises**, each sound
alone. The generalization:

> When an ADR deletes an affordance because *"the replacement is already built,"* the
> replacement must be **exercised in that mode**, not merely present in the codebase.

ADR-481 D2 named `/` as the replacement for the gutter. `/` existed, was reachable, opened,
and filtered — every check short of completing the gesture passed. The falsifier that would
have caught it is #1 above, and its shape is *"the act completes,"* not *"the affordance
appears."*

## 11. The one-line statement

**A mode does not merely hide the other mode's chrome — it must be handed its own, and every
affordance a deletion leans on must be exercised in the mode that inherits it.**
