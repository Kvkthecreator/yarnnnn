# ADR-539: The vocabulary declares behavior — a kind carries its tier, its tags, its conversions, and its citation; a heading carries its rung

> **Status**: **Accepted** (2026-08-09) — operator-ratified through the hierarchy/docs-app audit discourse ("singular approach to avoid future downstream ambiguity"); implementation delegated in full.
> **Date**: 2026-08-09
> **Dimension**: **Substrate** (what the block vocabulary IS) primary; a **Channel** consequence (every offering surface derives from one declaration).
> **Authors**: KVK (operator) + Claude (collaborator)
> **Relates to**: ADR-443 R4 (one component vocabulary), ADR-511 D8 (attributes are inert names), ADR-525 D1/D4 (the selection carries its tier; `block-flow`), ADR-526 (the document shows its shape), ADR-528 D5 (the `apps` dimension — the precedent this ADR generalizes), ADR-536 (the list is a kind — the defect class this ADR ends), ADR-538 D1 (classification by citation — promoted here from rule to field), FOUNDATIONS DP33 (collapse the category into data).

---

## 1. Context — the audit, and the one generator under five ADRs

The operator asked for an audit of hierarchy and docs-app data handling
(2026-08-09), with the thesis that OUTLINE / blocks / prose / headers /
scoped-features / multi-select handling is "fundamentally fragmented." The
audit (four parallel sweeps: backend registry, Studio FE, Docs app, ADR
record) confirmed the thesis and found the generator:

**`STUDIO_BLOCKS` answers "what can be inserted," never "what can be done" —
so every behavioral question got answered by a hand-list at the site that
first asked it.**

The shadow registries, at audit (receipts abridged; each verified at `d99dbf8`):

| Question | Hand-list answering it | Site |
|---|---|---|
| Which kinds are text-tier? | `TEXT_BLOCK_KINDS` (8 kinds) | `projection.ts:380` |
| Which kinds can Turn into? | `TURN_INTO_KINDS` (8 kinds) | `StudioDesignTab.tsx:92` |
| Which tag is which kind? | `PROMOTE_KIND` | `artifactOps.ts:324` |
| Which kinds open the citable picker, and onto what? | `PICKER_KINDS` + `CSV_KINDS` + three inline union types + a narrowing ternary — **five spellings of one set** | `StudioCitablePicker.tsx:28,31`; `StudioSurface.tsx:2236,2361,2394,2439` |
| Which kinds take media tokens? | `MEDIA_BLOCK_KINDS` (backend) — a near-duplicate of `PICKER_KINDS`, since diverged | `studio.py:814` |

The proof this is the generator: **ADR-538's `component` became object-tier
and non-convertible *by omission*** — a new registry row joins none of the
shadow lists, so its behavior is whatever falling through every filter
produces. And the shape is a repeat: ADR-528 D5 found the same missing
dimension for `apps` (*"`STUDIO_LAYOUTS` rows have carried `app` since
ADR-473; `STUDIO_BLOCKS` rows carried nothing — there was nowhere to say
it"*). `apps` fixed one instance. Tier, tags, convertibility, and citation
are four more instances of the same disease, fixed the same way.

**The second fracture: "what is a heading?" had four different answers across
eight sites.** `PROMOTE_KIND` admits h1–h6; the member outline walks h1–h3;
the AI outline (`extract_outline`) and the heading crumb (`headingAboveOf`)
read h1–h2; the turn-into harvest reads h1–h4. Consequence, reproduced from
the operator's screenshot: an h4 pasted into Docs is called "Heading" by the
pane's FILE section, misreported as "Text" by the Typography select, omitted
silently from OUTLINE, skipped by the crumb, and invisible to the AI. ADR-526
§1.1's parity claim ("the member sees what the AI sees") is false in both
directions today. The ADR-526 gate cannot catch it — its mock DOM ignores the
selector (`adr526_docs_structure.mjs:34`).

## 2. Decisions

### D1 — A block row declares its behavior: `tier`, `elements`, `convertible`, `cites`

Every `STUDIO_BLOCKS` row gains four fields, all served:

| Field | Values | The question it retires |
|---|---|---|
| `tier` | `"text"` \| `"object"` | Is a click on flow a caret or a box? (`structure` is a property of containers/pages, never of a kind — ADR-525 D1's tier taxonomy unchanged) |
| `elements` | tuple of tags, first = the authored tag | Which DOM tags ARE this kind? The tag→kind promotion map is **derived** from this, never hand-written |
| `promote` | bool (default `True`) | May a bare tag be *guessed* into this kind? `checklist` declares `False` — ADR-536's deliberate refusal preserved as data instead of by omission |
| `convertible` | bool | Does Turn-into offer it? |
| `cites` | `"none"` \| `"source"` \| `"picture"` | ADR-538 D1's classification rule, promoted from prose to field |

**`group` becomes a derivation, not a field**: `source → data`, `picture →
media`, `none → content`. ADR-538 found `chart` and `metrics` mis-filed
because group and citation could disagree; after this ADR they structurally
cannot. The wire shape is unchanged (the route still serves `group`).

### D2 — One declaration, three consumption lanes; the static seams get executing parity gates

The singular source is the Python registry. Consumers split by what the
architecture allows:

1. **Served-vocabulary derivations (React-land)** — every consumer with the
   fetched vocabulary in scope derives instead of enumerating: Turn-into
   membership from `convertible`, picker routing from `cites` (`source` →
   CSV list, `picture` → image list), the pane's tier fallback and the
   navigator reach's tier re-derivation from `tier`. The hand-lists
   (`TURN_INTO_KINDS`, `PICKER_KINDS`, `CSV_KINDS`, the union-type spellings)
   are **deleted**.
2. **Structurally static FE constants** — two sites cannot read a fetch:
   `TEXT_BLOCK_KINDS` (interpolated into the runtime IIFE at module scope)
   and the promotion map at the normalize seam. These remain module
   constants, and each is pinned to the registry by an **executing
   cross-language parity gate** (the `test_adr536` pattern: the Python gate
   parses the TS source and compares against the registry's declared fields).
   A divergence fails CI naming the registry as the source of truth.
3. **Backend derivations** — `MEDIA_BLOCK_KINDS` becomes
   `{k for k,r in STUDIO_BLOCKS if r["cites"] == "picture"}`; the `/studio/citable`
   split and `_blocks_grammar` keep reading what they read, now from declared
   fields.

### D3 — The heading rung is a kernel constant: `HEADING_RUNGS = (1, 2, 3)`

Declared once in the registry module, served in the vocabulary payload
(`heading_rungs`). Every consumer reads it: the member outline walk, the AI
outline (`extract_outline` moves from h1–h2 to the full rung set — closing
ADR-526 §1.1's parity claim honestly), the heading crumb (`headingAboveOf`,
via the same parity-gate treatment as D2's static constants), the Typography
ramp rows, and the turn-into harvest. Four answers become one.

### D4 — Intake clamps to the rung set: h4–h6 arrive as h3

A document must not hold a rung the system does not speak. Two seams, both
citing the constant:

- **Paste**: the allowlist maps `H4/H5/H6 → H3` instead of admitting them.
- **Normalize (migration-by-use)**: `normalizeStructure` renames an
  out-of-rung heading to the deepest rung on the artifact's next write —
  never a sweep, never a write-on-open (the ADR-511/519 migration pattern).

This is a deliberate mutation at the normalize seam, which until now only
annotated. The alternative — making all six rungs real everywhere — was
considered and refused: the ramp offers three, the benchmarks (Notion: 3)
offer three, and six-rung support would widen every consumer for a case with
zero observed demand. The clamp direction (h4–h6 → h3, preserving relative
prominence as "deepest spoken rung") loses sub-structure a member pasted from
elsewhere; that cost is accepted and stated.

### D5 — The outline is one rule

*A heading whose rung is in `HEADING_RUNGS`, holding a `data-block-id`, with
nonempty text.* Stated in AUTHORING.md as the definition of Docs' structural
grain. The FE walk and the BE extraction each implement it against the served
constant, and a parity gate asserts both speak the same levels.

### D6 — What this ADR does NOT do

- No selection/scope changes — the selection algebra is ADR-540's ruling.
- No token `applies` split — that is ADR-541 territory (with the standing
  `test_adr453` `valid_applies` debt repaired there, where it is honest).
- No housing rename — ADR-518 §6's trigger has fired (the audit's receipts),
  but the rename is hygiene and rides separately.
- No new kinds, no kernel CSS change, no substrate schema of any kind —
  `data-block` stays an inert annotation (ADR-511 D8).

## 3. What this amends

| Canon | Change |
|---|---|
| ADR-443 R4 | The one vocabulary now declares behavior, not only existence. Still singular, still one home. |
| ADR-525 D1 | Tier taxonomy unchanged; the *declaration* of which kinds are text moves from an FE list to the registry (the FE list becomes a pinned projection of it). |
| ADR-526 §7 | The "h1/h2/h3 only" accepted cost is re-cut: the rung set is declared, intake clamps to it, and member/AI parity becomes true (both read the full set). |
| ADR-528 D5 | The `apps` precedent generalized: four more missing dimensions become fields. |
| ADR-536 | `checklist`'s promotion refusal moves from a comment on an omission to `promote: False`. |
| ADR-538 D1 | The citation rule becomes the `cites` field; `group` becomes its derivation. |
| AUTHORING.md | Gains the block-descriptor table and the outline rule (D5). |

## 4. Consequences

**Positive.** A new kind's full behavior is its row — the `component`-by-
omission failure mode becomes structurally impossible. The screenshot defect
class (h4 invisible to outline/crumb/AI, misreported by the ramp) is closed
by construction, not by six synchronized selectors. Net-negative FE line
count: five picker spellings, two kind lists, and three heading enumerations
are deleted.

**Costs, stated.** The two static constants are pinned by gates, not derived
— a gate is weaker than a derivation, and that residual is named here rather
than hidden (the runtime IIFE and the normalize seam would need a
vocabulary-threading refactor to close it fully; not worth the churn today).
The intake clamp mutates pasted content (h4–h6 → h3); a member pasting a
six-level document loses depth distinctions below h3. `extract_outline`
gains h3 entries, so the AI lane posture grows slightly for deep documents.

## 5. Falsifiers

1. **The parity gates must be executing, not grep.** If either static
   constant can diverge from the registry while its gate stays green, D2's
   third lane is broken and the vocabulary-threading refactor it deferred
   becomes due. Falsify at build time: mutate a registry row's `tier`, run
   the gate, expect red.
2. **The clamp's cost.** If a real member workflow surfaces that needs h4+
   distinctions (legal documents, academic exports), D4 re-opens on that
   evidence — widen `HEADING_RUNGS` at the single declaration and every
   consumer follows; that is the point of D3.
3. **Derivation completeness.** If a future PR adds a kind-behavior hand-list
   anywhere in `web/`, D1's field set was insufficient — add the missing
   field, never the list.

## 6. The one-line statement

**A kind's row is its behavior — tier, tags, conversions, citation — and a
heading's rung is a kernel constant; every surface derives or is gate-pinned
to the one declaration, so the next kind and the next rung resolve without a
debate.**
