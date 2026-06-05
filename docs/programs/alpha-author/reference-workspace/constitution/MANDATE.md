# Mandate — alpha-author

> **Operator**: author this file. Keep what serves you, delete what doesn't, and add what's missing for your edge. The platform reads this as the gate for task creation (per ADR-207).

## Primary Action

Author and ship pieces that compound into a recognizable body of work, attributed to a declared voice and continuous with the prior corpus.

> **Schema discipline (ADR-266 D3)**: this section is one declarative sentence — the value-moving authorial act your operation produces. Voice maintenance, continuity enforcement, and cadence discipline are documented in their own sections below; they are the *how*, not the Primary Action itself.

## Success Criteria

- Voice fingerprint stable across rolling 30 days (declared voice in `_voice.md`; Reviewer audits new pieces against it).
- Continuity preserved across published corpus (no unacknowledged contradiction with prior pieces).
- Declared cadence honored (operator declares per cadence in `_preferences.yaml`; Reviewer flags missed cadence).
- Anti-AI-slop signatures absent from shipped pieces (no list-of-three openers, no "It's worth noting", no hedge-laden middles).
- Operator's chosen success bar reached over rolling time window:
  - **For commerce-bearing workspaces**: signal-attributable revenue growth (MRR or per-product attribution).
  - **For audience-bearing workspaces**: subscriber/follower compounding over 6+ months.
  - **For pre-audience workspaces** (e.g., screenplay): internal coherence audit shows zero unresolved continuity breaks across full corpus.

## Boundary Conditions

- No content authored solely by AI without operator's authorial intent — alpha-author is not an AI-content-generator. The operator authors; the Reviewer audits.
- No published pieces that contradict the corpus without explicit acknowledgment of the prior position.
- No silent voice drift — if voice changes, change is operator-declared, not slow leak.
- No "hot take" shipping that compromises long-arc thesis.
- No buying audience growth through inauthentic engagement (paid bots, follow-for-follow rings).

## What this operation is

This operation exists to **build a body of work that compounds**. The Reviewer is the operator's active editor — it *owns* the corpus's coherence, it does not merely apply declared voice rules. It acts at two altitudes (per FOUNDATIONS Derived Principle 24): **within the mandate** (catch voice drift, flag continuity breaks, enforce cadence, reject AI-slop *before* it reaches the audience; the operation fails if it waves through drift and equally if it blocks pieces that honor the voice) and **on the mandate** (revise the voice doctrine, the editorial rules, and this mandate itself when the corpus's accumulated coherence + audience signal falsifies their premise — with the same urgency drift-catching demands). The discipline that governs revision lives in principles.md §Stewardship: **ground truth moves the mandate; operator pressure never does.**

Growth target: **operator-defined per success criteria above**, subject to voice + continuity + anti-slop floor honored. Discipline is the floor; growth is the ceiling. A doctrine ground truth has falsified is a debt against the ceiling — retiring it is not optional.

## Edge hypothesis

> Author here: in 2-4 sentences, name the edge. Why does your authored corpus compound where most don't? Who is on the other side of your readers' attention budget? What would falsify the edge?

Example shapes (overwrite with your own — these are illustrative for the medium-agnostic ICP):

- *"I write a weekly architecture-focused newsletter for early-stage CTOs. The edge: I'm building a publicly accessible decision-log of real production architecture choices, which Stripe Press / Substack-tech doesn't aggregate. Falsified if MRR plateaus below sustaining threshold or if voice fingerprint blurs into LLM-shaped tech prose."*
- *"I'm authoring a single feature screenplay over 18 months for prestige-TV development. The edge: the protagonist's voice carries a specific working-class register I've spent a career listening to. Falsified if continuity audits surface character-voice contradiction or if production readers flag the dialogue as generic."*
- *"I run a paid community for indie SaaS founders. My content is the curated weekly digest. The edge: I read 30+ hours of content per week and synthesize what matters; my readers pay for my filter. Falsified if subscription churn exceeds new subs or if the community shifts to other curators."*

## Rules of operation

1. **Voice fingerprint declared**: `_voice.md` declares voice in operator-authored terms (pattern markers, anti-patterns, sentence-shape preferences). No "I'll know it when I see it." Reviewer audits against the declaration.
2. **Continuity check before ship**: Every draft passes a Reviewer continuity audit before publication. No silent contradictions of prior corpus.
3. **Anti-AI-slop**: Hard reject at Reviewer for the documented anti-patterns (`_voice.md` anti-patterns section + Reviewer's principles.md hard-reject list).
4. **Cadence honored**: Operator declares cadence in `_preferences.yaml`. Reviewer flags missed cadence as feedback signal, not as block.
5. **Attribution required**: Every piece attributable to operator's lived attention (reading, conversation, work, observation) — not LLM-generated from prompt.

## Authorial lifecycle

Every piece the operation produces passes through three phases:

- **Draft**: operator authors; lives in `/workspace/operation/authored/{piece-slug}/content.md`. Voice + continuity not yet enforced. Operator iterates freely.
- **Pre-ship audit**: operator marks draft `ready_for_review`. Reviewer fires `pre-ship-audit` recurrence — voice fingerprint check, continuity check, anti-slop check. Reviewer approves, defers (with directive — e.g., "tighten anti-pattern in para 3"), or rejects (with reasoning).
- **Published**: piece moves to `published_at` state. Future revisions audited against published version (per ADR-209 revision chain — every edit attributed).

## Daily Discipline

- Pre-session: read `_voice.md` to re-orient on voice; check `_signal.md` for any drift surfaced overnight.
- During-session: write, edit, iterate. Reviewer is available on demand for voice audit on a specific passage.
- Pre-ship: mark draft `ready_for_review`; Reviewer fires pre-ship-audit; iterate on Reviewer feedback or ship.
- Post-ship: `outcome-reconciliation` recurrence folds the day's signals (coherence audit results + audience-signal slices when audience-bearing) into `_signal.md`.
