# Entities — netflix-script-author roster

> Workspace entity roster authored 2026-05-18 by operator on behalf via ADR-283 step 6 dogfood. Entity-continuity is the load-bearing audit substrate for this workspace per ADR-283 step 2. Each entity gets a file at `entities/{slug}.md`. Operator-attributable per ADR-209.

## What this file is

This file is the **roster index** — a flat list of every entity the corpus commits to, with one-line descriptions. The detailed entity substrate (backstory, voice for characters, capabilities, relationships) lives in individual files at `entities/{slug}.md`.

The Reviewer reads this index at every pre-ship audit to know **which entities exist in the canon**. When a scene introduces a name the Reviewer doesn't find here, the Reviewer flags: "this is a new entity — is it intended to be canonical, or is it incidental?"

The Reviewer reads individual entity files when auditing scenes that involve those entities — checking continuity (this character did X in episode 2; does scene Y contradict that?) and (for characters) voice fingerprint.

## Roster

### Principal characters

| Slug | Role | One-line | File |
|---|---|---|---|
| jaewon | The mastermind | Affluent, mid-30s, never executes directly. Layered through proxies. The center of the series. | `entities/jaewon.md` |

> *More principal characters will accumulate as the corpus is authored. Add roster entries here as `entities/{slug}.md` files are created. The Reviewer flags scenes that introduce un-rostered characters.*

### Recurring characters (operator authors as corpus develops)

*(none yet declared)*

### Institutions

*(operator declares Korean exchanges, financial institutions, government agencies, criminal organizations as the corpus references them. Each gets `entities/{slug}.md` with declared facts: founding year, leadership, capabilities, relationship to plot canon.)*

### Locations

*(operator declares specific recurring locations — Jaewon's office, the underbridge meeting point, specific Gangnam venues — as the corpus references them. Locations get `entities/{slug}.md` with declared facts: physical description, who has access, plot-canonical events that occurred there.)*

### Plot canon

*(operator declares load-bearing plot facts that scenes depend on — "the bridge of 1997 happened on March 14", "the first heist target was the Daejeon cold-storage" — as entity-style files at `entities/plot-canon-{slug}.md` so the Reviewer can audit consistency. Alternative: a single `plot-canon.md` file at workspace root. Operator decides per accumulation pattern.)*

## Entity-continuity discipline

This workspace's load-bearing audit is **entity-continuity**. The series is long-arc; over 12-18 months of authoring, the canon will grow large enough that no single operator session holds the whole thing in working memory. The entity substrate is the corpus's external memory — the Reviewer reads it at every audit to detect what the operator can't track unaided.

Two failure modes the entity substrate prevents:

1. **Character-voice drift across scenes** — Jaewon's voice in episode 7 should be auditable against his voice declaration in `entities/jaewon.md`. Without the declaration, drift becomes the corpus's accidental evolution rather than operator-authored evolution.

2. **Silent plot contradiction** — if episode 2 says the bridge was rigged at 3am and episode 5 has the bridge timing at 11pm, the Reviewer should catch it. The plot canon entity files are the substrate against which scenes audit.

## What does NOT go in `entities/`

- Per-scene staging detail that doesn't recur (a one-off bartender who appears in one scene).
- Author-voice declarations (those live in `_voice.md` author voice section).
- Editorial principles (those live in `_editorial.md`).
- Cadence preferences (those live in `_preferences.yaml`).
- Live audit findings (those live in `_signal.md`).

If a character or location or institution appears once and never again, it doesn't need an entity file. If it appears twice with consistent treatment, declare it (the second appearance is the signal it's recurring). If it appears twice with inconsistent treatment, the Reviewer should have flagged the inconsistency — declare it and resolve the canon.

## Cadence

Entity files are operator-authored organically as the corpus grows:

- New character introduced in a scene → operator authors `entities/{slug}.md` during the post-scene editing pass, OR Reviewer's `pre-ship-audit` flags "this is a new character — declare voice and continuity facts before canonizing the scene".
- New institution / location referenced → same pattern.
- Plot canon facts that load-bear later episodes → declared the moment the scene canonizes the fact.

`corpus-coherence-check` runs twice-weekly and audits the whole entity substrate against the whole scene corpus — surfaces patterns the per-scene audits miss (e.g., a character's voice has slowly homogenized across 5 scenes; no single scene shows enough drift to fail but the trend is real).
