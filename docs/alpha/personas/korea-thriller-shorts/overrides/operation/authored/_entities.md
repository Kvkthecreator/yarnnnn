# Entities — korea-thriller-shorts roster

> Workspace entity roster authored 2026-05-18 by operator on behalf via ADR-283 step 6 dogfood. Character canon SHARED with netflix-script-author. Visual canon (specific staging conventions, recurring location depictions) may emerge from this workspace and sync back to netflix's series-bible. Operator-attributable per ADR-209.

## What this file is

This file is the **roster index** — a flat list of every entity the corpus commits to, plus shared-canon notes (which entities mirror netflix-script-author and which are workspace-specific). The detailed entity substrate lives in `entities/{slug}.md`.

The Reviewer reads this index at every pre-ship audit to know which entities exist in the canon. When a short introduces a name not in this roster, Reviewer flags it.

## Shared canon with netflix-script-author

The following entities are **canon-mirrored** — the file here is a copy of the corresponding file in netflix-script-author's overrides, kept in sync via operator PR discipline. When the canon evolves in either workspace, the operator updates both and re-runs `activate_persona.py` for both personas.

| Slug | Source of canon | Status |
|---|---|---|
| jaewon | Shared with netflix-script-author; copy at `entities/jaewon.md` | Authoritative file in netflix workspace; mirror here for shorts-Reviewer to audit against |

## Visual canon (workspace-specific)

This workspace may produce visual canon that the series bible should respect — specific staging conventions, recurring location depictions, color-palette declarations per character / setting. When a short establishes visual canon worth syncing, operator PRs the convention back to netflix-script-author's entity file or series-bible.

Visual canon notes accumulate as `entities/{slug}.md` "Visual canon" sections — staged as updates to the shared entity file or in a workspace-local visual-canon doc.

Initial visual canon declarations:

- **Jaewon visual canon (initial)**: never front-on full-face close-up unless the short is specifically a canon-piece declared in `profile.md`. Default depictions: back three-quarters, edge-of-frame profile, foregrounded silhouette. The visual identity is "the one you don't quite see clearly." See `entities/jaewon.md` Visual canon section.

## Roster

### Principal characters

| Slug | Role | Status | File |
|---|---|---|---|
| jaewon | The mastermind | Shared with netflix-script-author | `entities/jaewon.md` (mirrored) |

> *More principals accumulate as netflix-script-author canonizes them OR as this workspace establishes visual-canon-only characters that the screenplay later picks up.*

### Recurring characters (shared canon)

*(none yet — netflix-script-author will canonize as the screenplay develops; this workspace mirrors)*

### Recurring characters (visual-canon-only)

*(this workspace may establish visual-canon recurring characters — e.g., a recurring proxy whose silhouette is canonical even though the screenplay hasn't named them yet. Declared here when established.)*

### Locations (shared canon)

*(operator-declared as netflix-script-author + this workspace reference them. Each gets `entities/{slug}.md` mirrored across both workspaces.)*

### Locations (visual-canon-only, this workspace)

*(this workspace may establish visual-canon locations not yet in screenplay — a specific Han River underpass for handoff shots, a specific Gangnam alley for transition shots. Declared here when established; may later sync back to netflix.)*

### Institutions, plot canon

*(operator declares as both workspaces reference them. Currently empty.)*

## Sync discipline

The Reviewer in this workspace reads its OWN canon files. It does not reach into netflix-script-author's workspace. Sync is operator-driven via PR:

1. New canon (character, location, plot fact) established in **netflix-script-author** workspace's chat-authored substrate.
2. Operator PRs the entity file from `/workspace/context/authored/entities/{slug}.md` (or equivalent) into `docs/alpha/personas/netflix-script-author/overrides/context/authored/entities/{slug}.md`.
3. Operator PRs the same file into `docs/alpha/personas/korea-thriller-shorts/overrides/context/authored/entities/{slug}.md`.
4. Re-run `activate_persona.py --persona korea-thriller-shorts` (and similarly for netflix if reverse direction).
5. Both workspaces' Reviewers now read the updated canon at all subsequent audits.

The discipline cost is real: two PRs per canon evolution. Cost is paid for the cross-workspace canon integrity payoff.

## Entity-continuity discipline (workspace-specific)

Two failure modes the entity substrate prevents in this workspace:

1. **Visual-character-drift** — Jaewon's depiction in shorts must match his visual canon (back three-quarters default, no shouting visually, etc.) AND his character canon (the personality and behavior the entity file declares). Without the entity substrate as audit anchor, AI-video-gen produces median Asian-businessman-in-suit shots.

2. **Cross-workspace canon drift** — netflix's Jaewon evolves; shorts' Jaewon doesn't get the update; the two workspaces start producing inconsistent canon. Reviewer can only audit what's in its workspace; operator must enforce sync.

`corpus-coherence-check` runs twice-weekly and audits cross-short canon-consistency within this workspace. Cross-workspace audit is operator's responsibility, not Reviewer's.

## What does NOT go in `entities/`

- Per-short staging detail that doesn't recur (a one-off bystander, a one-off transition location).
- Author voice / prompt format declarations (those live in `_voice.md`).
- Editorial principles (those live in `_editorial.md`).
- Cadence preferences (those live in `_preferences.yaml`).
- Live audit findings (those live in `_signal.md`).
- Per-tool generation patterns (those live in `_signal.md` over time).
