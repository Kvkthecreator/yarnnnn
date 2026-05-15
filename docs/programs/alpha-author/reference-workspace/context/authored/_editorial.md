# Editorial — what gets shipped, what doesn't

> **Operator**: author this file. The Reviewer reads this when deciding ship/defer/reject on pre-ship audits. Distinct from `_voice.md` (how it sounds) — this is *what gets to the audience at all*.

## Declared editorial principles

> 4-8 short principles, each in operator's own voice. Specific is better than aspirational. The Reviewer applies these literally.

Example shapes (overwrite):

- *"Every shipped piece advances a thesis I'm willing to defend in 6 months. No hot takes, no contrarian-for-attention, no engagement-bait framings."*
- *"Continuity over volume. If shipping this piece this week means contradicting a piece from last month without acknowledgment, hold the piece until I've authored the bridge."*
- *"Reader respect over reach. I'd rather lose 5% of subscribers monthly to people I'm not serving than dilute the work for retention."*
- *"Cadence is a floor, not a ceiling. If I have nothing on-thesis to ship in a given week, the newsletter goes out late or skips — not flattened to fit the slot."*

## What gets shipped

> Specific criteria. The Reviewer reads these literally at pre-ship audit.

Examples:
- Piece advances a declared thesis or contributes a new datapoint to one.
- Voice fingerprint matches `_voice.md` (Reviewer auto-checks).
- No unacknowledged contradiction with prior corpus (Reviewer continuity-audit).
- No anti-slop signature (Reviewer `_voice.md` anti-pattern check).
- Operator's self-audit complete (the `ship_self_check` field in piece profile.md).

## What gets held / rejected

> Specific criteria. Reviewer rejects when matched.

Default reject triggers:
- **Voice drift beyond tolerance**: voice fingerprint mismatch flagged by Reviewer's voice-audit.
- **Anti-slop signature detected**: Reviewer flags AI-shaped patterns (`_voice.md` anti-patterns) that operator hasn't explicitly overridden.
- **Unacknowledged continuity break**: piece contradicts prior corpus without explicit bridge.
- **Hot-take detection**: piece framing optimizes for reaction, not corpus thesis advancement.
- **Engagement-bait**: piece uses curiosity-gap headlines, list-of-N constructions, or "you won't believe" framings.

## Categorical posture (relevant for multi-piece-type workspaces)

> Operators with diverse piece types (newsletter + essays + social posts) may declare per-category editorial posture here.

Example:
- *"Newsletter weekly edition: 1200-2400 words, one thesis advanced or one datapoint contributed, links cited inline. Reviewer hard-rejects shorter."*
- *"Twitter/X posts: optional; never the primary surface. When posted, must be standalone (no engagement-bait threading)."*
- *"Long-arc essays: minimum 4 weeks of substrate accumulation in `/workspace/uploads/` before drafting begins. Reviewer rejects essays whose substrate-citation lineage doesn't trace back at least 4 weeks."*

## What this file is NOT

- Not the voice fingerprint. Voice lives in `_voice.md`.
- Not Reviewer's principles. Those live in `/workspace/review/principles.md` (operator-authored framework the Reviewer applies).
- Not cadence preferences. Those live in `/workspace/context/_shared/_preferences.yaml`.
- Not author identity. That lives in `IDENTITY.md`.

## How this file evolves

Editorial principles evolve through use. The `quarterly-voice-audit` recurrence may surface drift between declared `_editorial.md` and actual ship/hold pattern — at that point, operator authors a revision (per ADR-209 revision chain). Reviewer does NOT write to this file; it surfaces drift via `Clarify`.
