# Conventions — alpha-author

> Structural rules every agent in this workspace honors. Universal across the program; operator may edit but most operators leave defaults.

## Substrate conventions

- **Voice fingerprint** (operator-authored): `/workspace/operation/authored/_voice.md`. Declared once, refined as voice evolves through use. Read by Reviewer for every pre-ship audit.
- **Editorial principles** (operator-authored): `/workspace/operation/authored/_editorial.md`. What gets shipped, what doesn't. Read by Reviewer for ship/defer/reject decisions.
- **Per-piece content**: `/workspace/operation/authored/{piece-slug}/content.md` — the piece itself. Operator authors; Reviewer reads at pre-ship audit.
- **Per-piece profile**: `/workspace/operation/authored/{piece-slug}/profile.md` — type, status, voice fingerprint match, continuity thread refs.
- **Corpus signal** (multi-signal ground-truth substrate, ADR-282/283 instance): `/workspace/operation/authored/_signal.md`. Coherence-audit-owned for the corpus-coherence slice. Never hand-edited.
- **Audience signal** (per-platform, when audience-bearing): `/workspace/operation/audience/{platform}/_signal.md`. Mechanical-recurrence-owned (track-linkedin / track-x / track-newsletter when those capabilities ship per ADR-283 step 2). Never hand-edited.
- **Cross-domain signal rollup**: `/workspace/operation/_signal_summary.md`. Cross-domain aggregate per ADR-195-instance pattern (parallel to alpha-trader's `_money_truth_summary.md`).

## Pre-ship audit envelope conventions

Every draft submitted for pre-ship audit carries:
- **Piece slug** (matches `/workspace/operation/authored/{piece-slug}/`)
- **Piece type** (newsletter | post | essay | episode | scene | other)
- **Voice fingerprint declaration** (which `_voice.md` fingerprint this piece expresses — relevant for operators with multiple voices)
- **Continuity threads** (which prior pieces this draft extends, references, or depends on)
- **Anti-slop precheck** (operator's self-audit; Reviewer verifies)
- **Cadence context** (is this on declared cadence, ahead, behind)

For revision proposals on already-published pieces (per ADR-209 revision chain):
- **Reason** (typo | factual_correction | continuity_amendment | voice_correction | retraction)
- **Diff scope** (which revisions to compare against in `workspace_file_versions`)

Drafts missing required envelope fields are rejected at Reviewer with a structured reason.

## Vocabulary discipline

- "Engagement" used as success measure → flagged. Engagement is signal, not goal. Compound corpus is goal.
- "Hot take" → flagged. Compounds-with-corpus framing required, not flash framing.
- "Algorithm-friendly" → flagged. Voice is the priority; algorithm shape is downstream.
- "AI-assisted" used without specifying *how* → flagged. Operator authors; Reviewer audits; what does AI assist with specifically?

## Time conventions

- All timestamps UTC in substrate; rendered in operator's local time at surfaces.
- "Cadence" means operator's declared cadence in `_preferences.yaml`, measured from operator's local timezone.
- "Recently" means rolling 30 days; "current" means within last 7 days; "long-arc" means rolling 6+ months.

## Recurrence mode discipline (ADR-263)

Every recurrence in `/workspace/_recurrences.yaml` declares `mode: judgment | mechanical`:
- **`mechanical`** — `prompt` is a `@primitive: ...` directive; dispatcher executes deterministic Python; no Reviewer wake; zero LLM cost. Used for substrate mirroring (track-linkedin, track-x, track-newsletter when those ship in ADR-283 step 2).
- **`judgment`** — `prompt` is a Reviewer message; wakes the Reviewer with the prompt as the addressed-equivalent envelope. Used for everything that requires editorial judgment — pre-ship audits, corpus-coherence checks, outcome reconciliation, weekly reviews.

Operators authoring new recurrences via YARNNN are guided to declare mode at create time. Default at parse time when absent: `judgment` (preserves backward compatibility).
