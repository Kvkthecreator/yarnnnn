# ADR-452: The Studio Landing — "Learn From" Is a Creation Path, Not a File Operation

**Status**: Accepted (2026-07-13, operator-ratified — the framing correction from the ADR-450
review: *"it shouldn't be a right click on files… we should treat learn from explicitly within
studio."*). Re-homes the Learn-from entrance from the Files context menu to the Studio's front
door, and gives the Studio a real landing (the Claude-Design shape: create · learn from · recents
with thumbnails · **no chat**).
**Date**: 2026-07-13
**Dimension**: Channel (where the verb lives) + Mechanism (the studio-bound derive).

**Amends**: ADR-450 D5 (the Files kebab entrance is **removed** — a creation act does not belong
in a file's organize menu; the registry/binding/citation machinery is untouched, which is why the
correction is cheap) · ADR-440 (the start state grows from a template picker into the landing).
**Preserves**: ADR-450 D1–D4 (the kernel recipe registry, the derive binding, the source-leg
sequencing) · ADR-443/444/446/447 (the workbench once an artifact is open — the landing is
pre-artifact chrome only) · ADR-449 (the design-system recipe; its Studio consumption stays the
447-D7 inspector's).

---

## D1 — The landing: the Studio's front door, pre-artifact

When no artifact is open, the Studio shows the landing — three sections, no chat (the lane belongs
to an *open* artifact; pre-artifact there is nothing to be hands for):

1. **Create** — the existing template cards (document · deck · article), meaning-placed naming
   (unchanged).
2. **Learn from a source** — the creation path this ADR adds (D2).
3. **Recents** — recent artifacts as real **thumbnails** (the ADR-447 navigator technique: a
   sandboxed, CSS-scaled `srcDoc` render), opening per ADR-451's contract.

## D2 — Learn-from-in-Studio: source + target → artifact + double-bound lane

The section offers the studio-shaped targets; picking one opens a source picker (the workspace
recents feed + filter — a source is usually a fresh arrival), then:

- **Document from a source** (the `prd` recipe) / **Deck from a source** (the new `deck` recipe):
  create the artifact skeleton (meaning-placed, named from the source) + **one lane carrying both
  bindings** — `artifact_path` AND `derive_recipe`/`derive_source` (they were built to coexist,
  ADR-450 D3) — then open the artifact in the Studio. The lane arrives with a Learn-from starter
  chip (click fills, the member sends).
- **Design system from a source** (the ADR-449 recipe): the output is a folder, not a canvas — a
  derive-bound chat lane, landing the member in Chat (the pre-452 flow, reached from creation
  instead of a right-click).

`context-brief` is **not** a landing card — the Studio creates artifacts; a plain note is a
chat-side derive. Template-vs-learn-from stay two sections over one creation grammar; collapsing
them into one composer (source + design system + template as attachments to a single ask — the
Claude-Design composer) is the named later pass, already supported by the data model.

## D3 — The studio-mode derive section

`build_derive_section(recipe, source, artifact_path=None)`: when the lane is also
artifact-bound, the section carries a **target override** — *the target is the bound artifact;
author it there in the artifact's format (the authoring posture owns the grammar); any recipe
instruction about creating a separate file is superseded; the citation discipline (`derived_from`)
and content constraints stand.* One override block beats duplicated recipe rows; splitting
recipes into content-vs-mechanics halves is the refactor if a third mode ever appears.

## D4 — The `deck` recipe (kernel registry, fourth row)

Studio-shaped: derive a deck whose every slide earns its claim from the source — title as claim
(not topic), one idea per slide, evidence lines cited, bounded length. Registry discipline
unchanged (LLM-facing → prompt CHANGELOG; Hat-B probe as it matures).

## D5 — The Files entrance is removed; the menu becomes Finder-flat

`onLearnFrom` leaves `FileVerbs`/`FileContextMenu`; `LearnFromModal` is deleted (superseded by the
landing). And the observed menu defect is fixed at its root: a tile's context menu did not stop
the event, so the **canvas menu stacked on top of the file menu** (hiding Open/Properties — the
operator's screenshot); the canvas handler now ignores already-claimed events. One gesture, one
menu, Finder-flat.
