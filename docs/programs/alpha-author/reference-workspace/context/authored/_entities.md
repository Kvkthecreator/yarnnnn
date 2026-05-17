---
schema_version: 1
last_updated: null   # operator updates manually or via UpdateContext when entities change
entity_count: 0
---
# Entities — operator-authored continuity ledger

> **Operator**: author this file (with the Reviewer's help via `Clarify`). This is the **aggregate index** of persistent entities the Reviewer reads at every continuity audit. Per-entity detail lives at `entities/{slug}.md` (one file per entity). The Reviewer reads both the index and the relevant per-entity files when auditing drafts for entity-level continuity breaks.

## What "entity" means in this workspace

Anything **persistent** across pieces that the Reviewer needs to know about when auditing continuity. For different author archetypes, "entity" instantiates differently:

- **Novelist / screenwriter**: characters (Sarah, Detective Marquez), locations (the apartment, the precinct), key objects (the locket), established facts (Sarah's mother died in chapter 3)
- **Academic / longform essayist**: concepts (the principle of charity, the substitution heuristic), positions (the operator-authored claim that X is a category error), citations (the 2019 paper the corpus relies on), defined terms
- **Founder-content author**: theses (build-in-public is operator-bearing, not pageview-bearing), positions (we will not ship feature X because Y), recurring references (the alpha-trader bundle as exemplar)
- **Podcaster**: guests (Maria Sanchez), recurring themes, prior on-show commitments

The entities are *whatever the operator commits to*. The Reviewer enforces consistency against operator-declared entities; it does not author them.

## Per-entity discipline

Each entity declared in this index has a matching file at `entities/{entity-slug}.md`. The per-entity file declares:

- **What the entity is** (one-paragraph definition)
- **What's been established** (canonical facts / positions / state — the things the corpus has committed to)
- **What's open** (questions the corpus hasn't resolved; tensions deliberately left unresolved)
- **First-piece introduction** (which piece in the corpus introduced this entity)
- **Recent appearances** (last 5-10 pieces that touched this entity; updated as pieces ship)

See `/workspace/specs/entity-continuity.md` for the per-entity file schema in full.

## Entity index

> Each entity declared here has a matching file at `entities/{slug}.md`. Add entries as the corpus accumulates entities; the Reviewer surfaces drift between this index and corpus reality via `Clarify` at quarterly-voice-audit time.

Empty at activation. Format when populated:

```markdown
## {entity-slug}
- **Type**: character | concept | location | thesis | citation | recurring-reference | other
- **One-line**: {what this entity is in 12 words or fewer}
- **First piece**: {piece-slug — link to the piece that introduced this entity}
- **Per-entity file**: `entities/{slug}.md`
- **Last touched**: {piece-slug + date — most recent piece that referenced this entity}
```

## How the Reviewer uses this

At every `pre-ship-audit`, the Reviewer:
1. Scans the draft for entity references (proper nouns, declared concepts, citations).
2. Reads matching `entities/{slug}.md` files for each entity the draft touches.
3. Compares the draft's treatment of each entity against the per-entity file's `What's been established` section.
4. Flags unacknowledged contradiction (per `principles.md` Hard rejection rule on entity-continuity) — character X said Y in chapter 3; draft has X saying ¬Y without bridge.

At every `corpus-coherence-check`, the Reviewer:
1. Reads this index + all entity files.
2. Cross-references against published corpus for entity-level drift (an entity's "established" position has shifted across recent pieces without acknowledgment).
3. Surfaces patterns via `Clarify` to operator at `quarterly-voice-audit` cadence.

## When to update this file

- **Operator-driven**: when authoring a piece that introduces a new persistent entity, add the entity here and create its matching file at `entities/{slug}.md`.
- **Reviewer-suggested**: the Reviewer may surface unindexed entities via `Clarify` ("the last 3 pieces reference 'the substitution heuristic' as a recurring concept — should this be declared as an entity?"). Operator decides whether to add.
- **Quarterly-voice-audit cycle**: review the entity ledger for entities that have gone dormant (no recent appearances), entities whose `What's been established` section has drifted, or entities that should be retired.

## What this file is NOT

- Not a character bible or research notebook. Per-entity detail beyond canonical facts lives in `entities/{slug}.md`; deeper research notes live in `/workspace/uploads/`.
- Not the corpus itself. Pieces live at `/workspace/context/authored/{piece-slug}/content.md`.
- Not Reviewer-authored. Reviewer surfaces; operator authors.
- Not load-bearing for every author archetype. A short-corpus founder-content workspace may have 2-3 entities; a novel-in-progress workspace may have 30+. The schema scales; the bundle does not prescribe entity count.
