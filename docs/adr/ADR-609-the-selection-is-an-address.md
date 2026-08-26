# ADR-609 — The member's selection is an ADDRESS, not a description

**Status**: Implemented (2026-08-26)
**Completes**: [ADR-522](ADR-522-the-focus-declaration-what-the-member-is-looking-at.md) · [ADR-606](ADR-606-the-pane-sees-what-the-member-sees.md) · [ADR-607](ADR-607-the-steward-hears-the-typed-focus.md) — the AWARENESS arc told the colleague *where the member stands*; this ADR lets it *act there*.
**Amends**: [ADR-337](ADR-337-file-layer-verb-completion.md) D1 — `EditFile` gains an optional `anchor`; `old_string` becomes optional in that mode.
**Related**: [ADR-579](ADR-579-three-verbs-that-write-one-act-that-doesnt.md) D7 (the typed seed — this carries its extent) · [ADR-589](ADR-589-update-is-a-door-over-the-selection-matrix.md) (the MECHANICAL door, untouched) · [ADR-571](ADR-571-the-text-app-a-dedicated-surface-for-the-prose-currency.md) D4 (the Text posture)

---

## 1. The observation

The operator, on the app-native chat: *"the existing update feature especially
in slides app, and a similar notion in text, is fundamentally broken right
now."*

They are right, and the measurement is a funnel. A member points at a thing;
the browser knows exactly which thing; and every stage below discards part of
that knowledge:

| Stage | What it knows |
|---|---|
| `scopeOf` (FE) | five scopes — `document · page · container · object · range` |
| `FocusScope` (wire) | **four** — `range` cannot cross |
| `_compose_focus_section` | **one English sentence** |
| the colleague | a noun and a quoted **prefix** |
| `EditFile` | an exact, unique **string** it must reconstruct |

Each stage is individually defensible. Composed, they mean the system holds a
durable address (`data-block-id`, or source offsets) at the moment of the
click, renders it to prose, and then asks the model to re-derive an address by
fuzzy means — failing as `old_string_not_found` / `old_string_not_unique`, whose
cheapest recovery is rewriting the whole file.

Two media, one defect, different surfaces:

- **Slides** HAS an address and does not use it. `seed.block_id` reaches the
  server and renders as decorative prose — `(id b7)`.
- **Text** has NO address at all. `ProseCanvas` reports exact `[from, to)`
  offsets; `onCanvasSelection` used them to slice a 120-char string and dropped
  them on the next line. It has no gesture door either: the whole ADR-579 D7
  `SeedTarget` protocol existed and Text produced no seeds, so its strongest
  targeting sentence — *"that is this turn's target"* — was unreachable there.

The excerpt compounds it. Text is clipped to 120 chars at capture and 80 at
render; only the second clip was marked. ADR-606's click-pass caught the
consequence in production: the Editor told a member their selection *"cuts off
right after 'first it'"*, asserting a clip boundary as a fact about the
document. The `…` added there made the model's ignorance HONEST; it did not
make it INFORMED. **An excerpt names a target; it can never state its extent.**

## 2. What this is NOT

**Not a new surface.** The considered alternatives were a richer chat-with-a-
visual pane, and a screenshot/print-screen channel. Both are UI answers to a
WIRE problem: the member would see their selection better while the colleague
kept receiving a prefix. The screenshot option is worse than neutral — pixels
are strictly LESS addressable than the `data-block-id` we already hold and
discard, it gives up citation semantics (ADR-538 D2's "charts cite data, never
a picture", one level down), and in Text there is no address for it to improve
on. **Refused, and recorded.**

**Not a change to ADR-589.** That door is MECHANICAL — arrangements, tokens,
palette, design system, no model. It is sound. The broken path is the JUDGED
one (`Rewrite… / Check… / Ask about this…`), which is a composer seeder.

**Not durable focus, and not an extension of focus.** ADR-522 D2 fixed focus as
volatile and per-turn; the extent rides the SEED — the deliberate gesture that
already means "act on this" — not the ambient declaration.

## 3. Decisions

### D1 — `EditFile` gains an optional `anchor`; it CONFINES the edit

One verb, one write path (no 11th primitive, no second write door). The anchor
carries the address the medium already has:

- `{"block_id": "b7"}` — HTML artifacts. Resolves to that element's span,
  **depth-counted**, so a nested same-tag child cannot end the span early. A
  regex to the first `</div>` is exactly how a "surgical" edit eats a sibling.
- `{"start": 12, "end": 40}` — prose. Half-open source offsets, as reported.

The resolved span is the ONLY region an edit may touch. With `old_string`, the
search is confined to it — so the same words elsewhere are neither a collision
nor a casualty. **WITHOUT `old_string`, the span is replaced wholesale** — the
"rewrite THIS" case, which needs no reconstruction at all and is the reason the
anchor exists. Hence `old_string` leaves `required`.

**Failures are NAMED, never clamped.** An out-of-range span or a missing block
id is refused with the numbers, because a silent clamp edits a region the
member never selected — the ADR-373 D6 incorrect-success class.

The unanchored contract is **byte-identical**: this adds a mode, it does not
edit one. The model's trained Claude-Code-Edit prior still works unchanged.

### D2 — The extent travels on the SEED, and Text gets the door it never had

`SeedTarget` / `LaneSeed` gain `range: {start, end} | null`. Prose carries the
range; a Slides gesture carries `block_id` — the same address in the medium
that has one. Text keeps the offsets it was discarding and gains a `Rewrite`
gesture door, shown only while a selection is held (the act it names is
"rewrite THIS", and without a selection there is no this).

> **PLACEMENT superseded by [ADR-612](ADR-612-the-judged-act-is-one-gesture-at-the-selection.md) D1/D3
> (2026-08-26).** This door shipped as a header-toolbar button; it is now a
> floating affordance at the selection, and the header button is DELETED
> rather than kept beside it. The seed, the chip and the anchor are unchanged
> — only where the member reaches the act moved.

### D3 — The frame hands over the ADDRESS, not just the name of the thing

`_seed_line` appends the anchor to use. Describing the target and leaving the
colleague to re-find it is the funnel; naming the anchor closes it.

### D4 — One clip marker, never two

The capture marks its own clip, and both server renderers are idempotent. A
90-char block used to arrive already silently shortened, then receive an `…`
describing the SECOND cut while implying the text ended at the first.

## 4. What is still owed

- **A production receipt.** This is verified by gates and a clean build, not by
  driving a Rewrite in the browser. The click-pass is owed, and per the eval
  discipline it is what converts this from a read of the code to evidence.
- **The ADR-579 D7 receipt turn** (diff/History) and the artifact-grain plan
  turn remain named-but-unbuilt: a judged artifact-wide update still lands with
  no preview or consent while ADR-589's page-grain re-arrange gets the ADR-479
  plan. That asymmetry is unchanged here.
- **Multi-block selections** still carry one primary. The set is dropped for
  the rail deliberately (ADR-519 D4.1); it is dropped on the WIRE incidentally,
  and closing that needs its own decision about what "rewrite these five"
  means.

## 5. Verification

`api/test_adr609_anchored_edit.py` — EXECUTION-ANCHORED on the resolver and the
edit core (imported and driven, not grepped: a grep passes when an assertion
matches its own comment). Defends: the nested-child span, the void element, the
refusals, that the anchor CONFINES (the proof case — an edit ambiguous
file-wide succeeds when anchored and leaves the sibling untouched), wholesale
span replacement, the unchanged unanchored contract, the extent on the wire,
Text's retained offsets and its door, the rendered postures, and the single
clip marker.

Falsified six times against real breaks: depth counting gutted · the anchor
ceasing to confine · Text dropping its offsets again · the door omitting the
extent · the posture template raising at render · the module-level `re` import removed.

**A falsifier that PASSED first, and what it taught.** The initial nested-block
assertion (`endswith("</div>") and "NESTED" in got`) passed against a gutted
depth-counter, because the truncated span still ended in `</div>` and still
held the child. The fixture gained a `<span>TAIL</span>` after the nested
close — content only a real depth count reaches. The assertion was matching the
DEFECT's shape, which is the failure mode the falsify-first rule exists to
catch.

**A green gate over a broken runtime.** Exec'ing the pure core in isolation
supplied `re` from the GATE's namespace, so a missing module-level import in
`workspace.py` passed every assertion and raised `NameError` on the first real
anchored edit — found only by driving the handler end-to-end against a stubbed
substrate. The gate now asserts the import the way the runtime resolves it.
This is the import-green trap: a runtime-shaped break ships when the test
supplies what production does not. The duplicate `import re as _re` found
beside it was collapsed — one dependency, one spelling.

ADR-337's schema gate was AMENDED (not loosened) to state the new required set
and why. Green: 337 · 522 · 543 · 545 · 562 · 571 · 579 D7 · 589 · 606 · 607 ·
533 · verb-families · trashed-file · prompt ratchets 3/3 · `next build`.
