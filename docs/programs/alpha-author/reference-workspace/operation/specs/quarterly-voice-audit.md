# Quarterly Voice Audit Spec

Spec for the quarterly `quarterly-voice-audit` deliverable. Operator declares cadence in `_preferences.yaml` (default quarter-end at 18:00 UTC); the Reviewer authors the actual Schedule call per ADR-275.

## Purpose

Quarter-end deep audit on voice fingerprint drift vs the operator's declared `_voice.md`. The weekly-corpus-review surfaces tactical drift signals; the quarterly-voice-audit asks the strategic question: **does the declared voice still match the operator's actual voice as it has evolved through 90 days of authorship?**

The answer might be:
- **Yes, no revision needed**: `_voice.md` declaration still accurately fingerprints the operator's voice.
- **Yes, with minor refinement**: declared anti-patterns or positive markers need one-line additions.
- **Operator's voice has evolved**: declaration needs material revision authored by operator (Reviewer surfaces the gap via `Clarify`, operator authors the revision).
- **Drift detected, voice not evolved**: operator was unintentionally drifting; `_voice.md` is correct; tighten enforcement.

## Output target

`/workspace/operation/reports/quarterly-voice-audit/{date}/output.md`

## Required sections (in order)

### 1. `## Quarter Headline`
- 2-3 sentence narrative: quarter's volume (pieces shipped), voice-audit accuracy state, headline answer to "does `_voice.md` still match the corpus?"

### 2. `## Voice Fingerprint Match Analysis`
- Per-anti-pattern enforcement: which anti-patterns triggered most this quarter, with operator-override rate.
- Per-positive-marker compliance: which positive markers from `_voice.md` are reliably present vs drift toward absence.
- Surface anti-patterns that triggered <2 times this quarter — candidates for removal from `_voice.md` (no longer load-bearing).
- Surface anti-patterns NOT in `_voice.md` that the Reviewer observed accumulating in published pieces — candidates for addition.

### 3. `## Corpus Coherence State`
- Cross-piece continuity audit results aggregated for the quarter.
- Unresolved threads (pieces published with continuity breaks the operator hasn't yet addressed).
- Quarter-on-quarter evolution: did the operator's positions evolve coherently, or are there abandoned threads?

### 4. `## Cadence Discipline State`
- Quarter's actual cadence vs declared cadence per `_preferences.yaml`.
- Distribution of on-time / behind / ahead ships.
- Operator's preference revision proposals (Reviewer surfaces patterns: "you declared weekly, you shipped fortnightly for the last 6 weeks — do you want to revise the declared cadence or recommit?").

### 5. `## Audience Compounding State` (when audience-bearing)
- Quarter's subscriber/follower trajectory.
- Engagement-z-score trend (improving, stable, declining).
- Audience cohort retention if measurable.
- For pre-audience workspaces: section reads *"Internal-coherence only — phase progression from Accumulation to Cadence Discipline can be evaluated against MANDATE success criteria."*

### 6. `## Proposed Revisions`
- For each surfaced gap above, a structured proposal:
  - `_voice.md` additions/removals (specific anti-pattern or positive marker)
  - `_editorial.md` refinements (criteria that worked, criteria that need tightening)
  - `_preferences.yaml` cadence revisions
- Each proposal is operator-actionable — operator can accept, modify, or reject. Reviewer does NOT author the revisions itself.

### 7. `## Decisions Pending Operator Authoring`
- A check-list of operator-authoring tasks the quarterly audit surfaced.
- Operator can address these inline (edit `_voice.md` etc.) or schedule a dedicated authoring session.

## Quality criteria

- Strategic, not tactical — the weekly-corpus-review covers tactical drift; this report asks structural questions about voice + framework.
- Reviewer's proposals are concrete enough to act on. Vague "consider revising voice declaration" is rejected; "add `'fascinating'` to the adverb-intensifier anti-pattern list — triggered 6 times this quarter, operator overrode only twice" is accepted.
- Reference `_signal.md` quarterly windows as numerical source.
- Length: ~1500-3000 words.
- Section partials in `/workspace/operation/reports/quarterly-voice-audit/{date}/sections/`:
  `1-quarter-headline.md`, `2-voice-fingerprint-match.md`, `3-corpus-coherence.md`, `4-cadence-discipline.md`, `5-audience-compounding.md`, `6-proposed-revisions.md`, `7-decisions-pending.md`.
