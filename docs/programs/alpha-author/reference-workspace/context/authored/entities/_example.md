---
schema_version: 1
entity_type: character    # character | concept | location | thesis | citation | recurring-reference | other
first_piece: null         # operator fills with piece-slug of introducing piece
last_touched: null        # operator (or Reviewer via Clarify) updates as pieces touch this entity
status: active            # active | dormant | retired
---
# {Entity Name} (example template)

> **This file is a template example.** Real entities live at `entities/{slug}.md` (one file per entity, slug-cased filename). Delete this file when authoring real entities; keep the schema shape.

## What this entity is

> One-paragraph definition. What is this entity in the corpus? Why is it persistent? What role does it play across pieces?

Example shapes per entity type:
- **Character (novelist)**: *"Sarah Chen, the 34-year-old systems engineer protagonist. Working-class register at the dialogue level; clinical register in inner monologue. Primary arc: from technical competence to moral certainty."*
- **Concept (academic)**: *"The substitution heuristic — the cognitive pattern where the operator-author substitutes a hard question with an easier related one. Used as a recurring diagnostic throughout the corpus."*
- **Thesis (founder-content)**: *"build-in-public is operator-bearing, not pageview-bearing. The corpus's standing position: shipping in public is for the operator's accountability + corpus accumulation, not for audience reach."*
- **Recurring reference**: *"the alpha-trader bundle as exemplar of the autonomous-execution archetype. Used across multiple pieces as the canonical reference when contrasting with substrate-continuity archetype work."*

## What's been established

> The canonical facts / positions / state the corpus has committed to about this entity. The Reviewer reads this section at every pre-ship-audit to check the draft against. Updates require operator authoring — Reviewer surfaces drift via `Clarify`, never edits directly.

Example shapes:
- **Character**: *"Sarah's mother died of cancer in 2011 (established in piece-slug-1, chapter 3). Sarah does not drink (established piece-slug-3). Sarah's sister is named Mei (established piece-slug-2). Sarah's relationship with her father is unresolved (deliberately open per arc design)."*
- **Concept**: *"The substitution heuristic always operates below conscious awareness (established piece-slug-1). It is not the same as motivated reasoning (distinction established piece-slug-4 — substitution is cognitive, motivation is volitional)."*
- **Thesis**: *"Build-in-public obligations are operator-self-imposed, not audience-imposed (established piece-slug-2). The corpus is the accountability mechanism, not the audience (established piece-slug-5)."*

## What's open

> Questions the corpus hasn't resolved; tensions deliberately left unresolved. The Reviewer treats these as *acceptable* for drafts to address either way (no contradiction flag), but flags drafts that *implicitly* close an open question without acknowledgment.

Example shapes:
- **Character**: *"Whether Sarah ever forgives her father is open. Drafts that resolve this in either direction must explicitly acknowledge the prior open state."*
- **Concept**: *"Whether the substitution heuristic is universal or culturally bounded is unresolved across the corpus. A draft taking either position needs to engage with the prior unresolved state."*

## First piece (introduction)

> The piece-slug + section where this entity was introduced to the corpus. Links to `/workspace/context/authored/{piece-slug}/content.md`.

`null` until populated.

## Recent appearances

> The last 5-10 pieces (newest first) that referenced this entity. The Reviewer maintains this list via post-publication update after `outcome-reconciliation` recurrence fires; operator may also update manually. Older appearances drop off (the per-entity file does not become an unbounded append log; appearance history is recoverable via `SearchFiles` over the corpus).

Empty at activation. Format when populated:

```markdown
- {piece-slug} ({date} — {one-line note on how this piece touched the entity})
```

## Operator notes

> Operator's own scratch for this entity. Reviewer reads this section but does not enforce against it (distinct from `What's been established` which is canon). Use for: working theories, alternative directions considered, references to research notes in `/workspace/uploads/`, etc.

Empty by default.
