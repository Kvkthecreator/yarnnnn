# ADR-586 — One insert door: categories with galleries, and Update goes contextual

> **Status**: **Accepted** (2026-08-19) — the operator's UX lock, ratified through the
> three-fork decision (one [+ Add] button · one marked Components gallery · schematic
> SVG previews). Build **phased** (D1–D7 below); nothing implemented in this commit.
> Operator-directed: *"the existing center pane buttons are need another depth of
> handling. ie., new slide -> than show details nested. much like the image screen
> [PowerPoint's SmartArt gallery]. this same approach needs to follow for right click
> as well, and thus, the positioning should be accomodative. consider mobile screen
> size as well… ALL current ADD essentially become part of New… we could just absorb
> it into on +Add button, collapsing the two into one. thus, Update, needs conditional
> to either the slide, or object or group, etc. this is where the nuance and fuse of
> LLM related calls and actual change related becomes combined."*
>
> **Supersedes in part**: [ADR-579](ADR-579-three-verbs-that-write-one-act-that-doesnt.md)
> D5.a/D6/D6.a's **toolbar topology** (the [+ Add][+ New][Update] triad and the
> verb-filtered doors). What SURVIVES of 579 — and must survive every phase — is its
> deeper law: the seam is WHO (the meter badge marks the colleague's paid acts, labels
> never name a mechanism, ADR-579 D3); one grouping module under every door
> (ADR-506 D3 — ordering and labeling, never subsetting); ONE landing
> (`landInsertPick`) and one write path; the door names its target.
> **Preserves**: [ADR-581](ADR-581-the-medium-regroup-deck-first-vocabulary.md)
> (family derives; the medium orders) · [ADR-583](ADR-583-a-component-is-a-workspace-file.md)
> (components as files; catalog capped) · [ADR-509](ADR-509-the-insert-route-follows-the-medium.md)
> (every kind mouse-reachable) · [ADR-462](ADR-462-the-block-context-menu-and-the-metered-badge.md) D4 (meter badge).
>
> **Dimensional classification** (Axiom 0): **Channel** (door topology + gallery
> depth + a second housing). The substrate and write paths are untouched.

---

## 1. Context — provenance was a door decision, and depth was missing

The ADR-579 triad asked the member to know a thing's *provenance* (exists in the
workspace vs. minted fresh) before stating their *intent* (put a comparison on this
slide). The operator's PowerPoint reference shows the shape that works: **intent
categories, each opening a visual gallery** — SmartArt's List/Process/Cycle rows each
open a thumbnail grid. Depth teaches; provenance is an implementation fact the door
should absorb, not export.

## 2. Decisions (operator-locked 2026-08-19)

### D1 — ONE insert door: the toolbar is [+ Add] [Update]

[+ New] is deleted; [+ Add] is the single insert door on every medium. Provenance
stops being a door decision entirely — it survives only as *pick behavior* (a cited
kind opens its picker; a minted kind lands its fragment) and as the small "shared"
marker inside the Components gallery (D7).

### D2 — The category tier (derived, never hand-kept)

The door's top tier is categories by WHAT IS BEING INSERTED, each derived from
fields the registry already declares (the ADR-539/581 discipline — a derivation
cannot drift):

| Category | Derivation | Opens |
|---|---|---|
| **Slide** (or Section) | page grain — the arrangement roster | the arrangement gallery (exists as `pageSection`) |
| **Components** | composed family (`tier=object, cites=none`) + `cites="fragment"` + the workspace library | thumbnail gallery (D7) |
| **Text** | prose family (`tier=text`) | the text kinds, heading rungs nested |
| **Media** | `cites="picture"` | image · gallery · logo row → picker |
| **Data** | `cites="source"` | table · chart → CSV picker |

The medium orders the categories (deck: Slide → Components → Text…; flow: Text
leads, no page category on a flowing document) — ADR-581 D3 one level up. **No
subsetting**: every kind remains reachable from every door (ADR-506 D3 stands);
categories are an ORDER AND A NESTING, never a filter.

### D3 — Gallery depth, schematic previews

A category opens a nested gallery of **schematic SVG thumbnails** (operator-locked;
the PowerPoint approach — drawn schematics, instant, legible at 64px, no iframes in
a menu). `ArrangementThumb` is the shipped precedent; a sibling `BlockThumb` module
draws one schematic per kernel kind. Live mini-renders are deliberately refused for
v1 (dozens of sandboxed frames inside a popover; a real cost on mobile). Library
components fall back to the generic component glyph until a generated static
preview exists (named, not taken).

### D4 — Right-click parity, accommodative positioning

The right-click menu's insert tiers become the SAME categories (one grouping module,
N mounts — the drift-proofing that already holds). Positioning becomes
accommodative: nested panels measure themselves and FLIP (left of the anchor near
the right edge, above near the bottom) instead of only clamping the root box —
the current inline tiers only push downward, which is exactly what breaks in the
lower third of the window.

### D5 — Mobile housing: the same door, as a sheet

Under the narrow breakpoint the door renders as a **bottom sheet** (full-width
category drill, same list, same landing) instead of an anchored popover — nested
popovers do not survive a phone. One component, two housings; the housing is chrome,
never a second list or a second write path.

### D6 — UPDATE goes contextual: one door, keyed to the selection

One [Update] door whose CONTENTS follow the selection grain:

- **nothing / page selected** → page acts: re-arrange (mechanical apply + the
  judged refinement, ADR-479/524), layout, page tokens;
- **block (object)** → move/stacking, tokens, turn-into (where legal), Rewrite;
- **group/set** → the set acts (single-subject rows withdraw and say so, ADR-541 D4);
- **cited block** (table/chart/figure/component) → *edit the source* + swap the
  citation + refresh the pin;
- **text selection** → marks, turn-into.

This is the door where mechanical change and LLM judgment FUSE — deliberately, per
the operator's ruling. The seam inside stays WHO/cost: the meter badge marks every
paid act (ADR-462 D4/ADR-579 D3), and that badge is now the ONLY spelling of the
mechanical/metered distinction. ASK is untouched (it never writes; it stays its own
tier on right-click).

### D7 — The Components gallery de-silos (operator-locked; sequenced LAST)

One gallery holds BOTH the kernel's per-instance composed kinds AND the workspace's
cited `*.component.html` library, presented identically (thumbnail + name); library
items carry one honest marker — *"shared — edits at source reach every use"* — and a
library pick lands its citation DIRECTLY (the gallery item IS the file; no picker
hop). The silo dissolves at presentation while the pick behavior keeps the
content-residence distinction (§3).

**Insert-as-copy** (detach a library component into per-instance markup — the
template act, and the eventual bridge by which generated components can replace
kernel skeletons) is NAMED and deferred to its own ADR: it needs the
reference-vs-copy honesty worked out (a copy is the thing ADR-440 D5 exists to
prevent, so the act must be explicit, labeled, and never the default).

## 3. The components ruling, recorded (the conceptual question answered)

The operator asked whether tables, charts, and the composed defaults should be
absorbed into the component logic. The axis that decides is **where the content
lives**, and it is structural, not stylistic:

- **In the instance** (a stat's number, a person's name — typed per use) → kernel
  kind: in-place editing is the point; a shared file here would make one slide's
  edit change every slide.
- **In a cited data source** (rows/numbers) → projection kind (table/chart): these
  are not compositions, they are RENDERINGS of a CSV at render time; a static
  fragment would freeze the rows (the ADR-572 D17/D18 line).
- **In a shared file** (the same everywhere, by design) → the ADR-583 component.

Text kinds are additionally the editing grammar itself (caret, turn-into, patch by
id) and cannot be opaque citations. So: **no absorption of the grammar; full
convergence at the presentation layer** (D7). The skeleton-vs-generated opposition
dissolves there: the gallery does not care who drew a component or where its content
lives — the pick behavior does, and the marker says so.

## 4. Build order and gate surgery (the phases)

D1+D2 (door collapse + categories) → D3 (thumbnails) → D4 (right-click + flip
positioning) → D6 (contextual Update) → D5 (mobile sheet) → D7 (library in the
gallery). Each phase re-anchors the gates it touches: `test_adr579_verb_grammar.py`
(the toolbar checks re-anchor from the triad to the one door; the WHO-seam checks
stand), `test_adr509_insert_route.py` (coverage claim re-anchored to the category
tier — the LIVE-registry derivation must still prove every kind reachable),
`test_adr462_context_menu.py` (the tier re-house; 5 pre-existing fails are another
arc's), `test_adr581_medium_regroup.py` (medium ordering moves one level up). A new
`test_adr586_one_door.py` pins: one insert button; categories DERIVED from declared
fields; no kind unreachable (executed against the live registry); the flip
positioning; the sheet housing renders the same list; Update's grain keying.
