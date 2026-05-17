# Entity Continuity Spec

Spec for the operator-authored entity ledger at `/workspace/context/authored/_entities.md` + `entities/{slug}.md` per-entity files. Read by the Reviewer at every `pre-ship-audit` and `corpus-coherence-check` for entity-level continuity checking.

## Purpose

Surface **persistent-entity contradictions** as structural continuity breaks, not just textual ones. The `continuity-audit.md` spec covers position-level contradictions (this draft contradicts a prior published claim). Entity-continuity is one layer below: it tracks the *things the corpus has committed canonical facts about* — characters, concepts, locations, theses, citations — and audits drafts against those commitments.

Without entity substrate, the Reviewer can catch "the draft contradicts last month's piece" (textual). With entity substrate, the Reviewer can catch "character X said Y in chapter 3; draft has X saying ¬Y" (structural — even if the draft never explicitly references chapter 3).

## File layout

**Aggregate index** (one per workspace):
- `/workspace/context/authored/_entities.md`

**Per-entity files** (one per persistent entity, slug-cased filename):
- `/workspace/context/authored/entities/{slug}.md`

The aggregate index is the Reviewer's *navigation surface* — it lists every entity the operator has declared. Per-entity files are the Reviewer's *detail surface* — read selectively when a draft touches the named entity.

## Aggregate index schema

Frontmatter:
```yaml
---
schema_version: 1
last_updated: <ISO-8601 timestamp | null>
entity_count: <int — number of entities declared>
---
```

Body: prose narration of what "entity" means in *this* workspace (the author's particular instantiation) + the entity index. Each indexed entry includes: slug, type, one-line, first-piece, per-entity-file path, last-touched.

See `_entities.md` template for the canonical body shape.

## Per-entity file schema

Frontmatter:
```yaml
---
schema_version: 1
entity_type: character | concept | location | thesis | citation | recurring-reference | other
first_piece: <piece-slug | null>
last_touched: <piece-slug + date | null>
status: active | dormant | retired
---
```

Body sections (in order):
1. **`## What this entity is`** — one-paragraph operator-authored definition
2. **`## What's been established`** — canonical facts / positions / state. **This is what the Reviewer enforces against.** Updates require operator authoring.
3. **`## What's open`** — questions deliberately left unresolved. Drafts may close them, but must acknowledge prior open state.
4. **`## First piece (introduction)`** — piece-slug + section where this entity was introduced
5. **`## Recent appearances`** — last 5-10 pieces (newest first) that touched this entity. Bounded list; older history recoverable via `SearchFiles` over corpus.
6. **`## Operator notes`** — operator's working scratch. Reviewer reads but does not enforce against.

See `entities/_example.md` for the canonical body shape.

## How the Reviewer reads entity substrate

### At `pre-ship-audit` fire

The Reviewer:
1. Reads the draft at `/workspace/context/authored/{piece-slug}/content.md`.
2. Reads `_entities.md` aggregate index.
3. Scans the draft for entity references — proper nouns, declared concepts, citations — and matches against the index.
4. For each entity the draft touches, reads `entities/{entity-slug}.md`.
5. Audits the draft's treatment against the per-entity file's `What's been established` section.
6. **Flags as hard rejection** (per `principles.md` Hard rejection rule on entity-continuity): draft contradicts an established fact without bridge.
7. **Flags as soft note** (defer with directive): draft implicitly closes an open question (from `What's open`) without acknowledgment.

### At `corpus-coherence-check` fire (periodic, twice-weekly)

The Reviewer:
1. Reads `_entities.md` + all entity files.
2. Cross-references against recent corpus (last 30 days of published pieces).
3. Detects entity-level drift: an entity's `What's been established` section is being contradicted across multiple recent pieces (suggesting either operator drift OR the established section needs revision).
4. Surfaces via `Clarify` when threshold crossed (per `_principles.yaml` thresholds): "the `Sarah` entity's `What's been established` says X; last 3 pieces have treated X as ¬X. Reviewer cannot tell which is canon. Operator: clarify the entity, or amend the prior pieces."

### At `quarterly-voice-audit` fire

The Reviewer:
1. Reviews the full entity ledger.
2. Flags entities that have gone `dormant` (no `Recent appearances` updates in 90+ days).
3. Flags entities whose `What's been established` section has accumulated more `What's open` than `established` — suggesting the entity is structurally underdetermined.
4. Surfaces retirement / refinement / consolidation candidates as `Clarify` proposals to operator.

## Output structure (Reviewer's audit findings)

When the Reviewer detects entity-continuity issues, findings land:

1. **`/workspace/review/judgment_log.md`** — append-only, per the standard audit-finding shape. Each entry includes:
   ```yaml
   piece_slug: <slug>
   audit_timestamp: <ISO-8601>
   audit_type: entity-continuity
   entity_slug: <entity-slug>
   issue_type: established-contradiction | open-implicit-close | unindexed-entity-reference
   draft_excerpt: "..."
   entity_file_excerpt: "..."
   overall_verdict: reject | defer | note
   defer_directive: <if defer> specific bridge or acknowledgment needed
   ```

2. **Draft's `profile.md`** updated with the entity audit state alongside voice + continuity audit state.

3. **`/workspace/context/authored/_signal.md`** — entity-continuity flag rate folds into the rolling-window calibration data.

## Quality criteria

- Reviewer cites the specific entity file + the specific `What's been established` line being contradicted. Vague "this contradicts the canonical Sarah" rejected.
- Reviewer never silently updates `What's been established` or `What's open` — operator authors all entity-file content per the `operator-canon` role policy in `_workspace_guide.md`.
- Reviewer may propose entity declarations via `Clarify` when it detects an unindexed entity reference appearing across 3+ pieces ("you've referenced 'the substitution heuristic' across 4 pieces; should this be declared as a concept entity?"). Operator decides.
- Entity-continuity is `audit_type` distinct from `voice-audit` and `continuity-audit` (text-level). The three audit types compose at `pre-ship-audit` time — all three run; reject verdict if any fires hard-reject.

## Out of scope

- Entity *creation* is operator-authored, not Reviewer-generated. The Reviewer never adds entries to `_entities.md` or creates `entities/{slug}.md` files autonomously. Suggestions land via `Clarify`.
- Entity *deletion* is operator-authored. The Reviewer never retires entities autonomously. Retirement candidates surface at `quarterly-voice-audit` for operator decision.
- Per-entity research notes / character bibles beyond canonical facts live in `/workspace/uploads/`, not in `entities/{slug}.md`. The entity file is *what the Reviewer enforces against*; uploads are *operator's working substrate*.
