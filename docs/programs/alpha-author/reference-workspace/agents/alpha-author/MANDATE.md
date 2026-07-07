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

## Expected Output

> The measurable half of this mandate (ADR-345) — what this operation is on the hook to **produce**. This is distinct from Rhythm (`_budget.yaml`: how often the agent works) and from Autonomy (`_autonomy.yaml`: which ships you witness). The machine companion is `agents/alpha-author/_expected_output.yaml`; keep the two in agreement. **A delivery-cadence the floor gates — not a quota.** If nothing clears the voice/anti-slop/continuity bar in a period, the slot slips; you never ship marginal work to hit a number.

- **Kind**: authored pieces (the artifact the corpus is built from — essays, editions, scenes, per your operation).
- **Delivery cadence**: *declare it* — e.g. "a biweekly essay," "a weekly edition." Until you declare one, the Reviewer treats the operation as event-driven (you author on your pace; it audits + ships when a draft clears the bar) and derives its owed-output rather than measuring against a declared rhythm. Declaring a cadence is what lets the operation produce on its own under `autonomous` (the Reviewer authors its own compose organ at that cadence; see `_workspace_guide.md`).
- **Bar**: every piece clears the full pre-ship audit (voice fingerprint + anti-slop + text/entity continuity + editorial) per `agents/alpha-author/principles.md`. The bar is never relaxed to meet the cadence.

## Boundary Conditions

- No content ships that fails the floor — alpha-author is not a slop generator. The agent authors as the operator's installed judgment (FOUNDATIONS:240 — the operator in authoring posture, not a separate principal) and is accountable for clearing the voice + anti-slop + continuity floor on its own output (ADR-355). The guarantee is the *floor every shipped piece clears*, not a human in the authoring seat — a human can write slop; the floor is objective and always applied. The operator is the **principal** (authors the voice/editorial/mandate the agent embodies) and the **witness** (per the autonomy dial — ADR-345: `autonomous` ships subconsciously, `manual`/`bounded` surfaces the ship to click); the operator may pre-/co-author any piece as principal, but authorship is not required of them.
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
5. **Attribution + accountability**: Every piece is attributable to the operator-as-principal (the agent authors as their installed judgment, FOUNDATIONS:240) and the agent is accountable for it via the revision chain (ADR-209). The old "not LLM-generated from prompt" bar is carried by the floor, not by forbidding agent authorship: what must be absent is *slop* (the `_voice.md` anti-patterns + principles.md hard-reject list), enforced on every shipped piece regardless of who typed it.

## Authorial lifecycle

Every piece the operation produces passes through three phases:

- **Draft**: the agent authors from the operator's declared piece intent (`profile.md`) + corpus substrate (`_voice.md`, `_editorial.md`, `_entities.md`), in voice; lives in `/workspace/operation/authored/{piece-slug}/content.md`. The operator may pre-/co-author or revise freely as principal. Voice + continuity not yet enforced at draft; the agent iterates toward the floor.
- **Pre-ship audit**: a draft reaches `ready_for_review` (the agent advances its own draft when it judges it ready; the operator may also mark one). The `pre-ship-audit` fires — voice fingerprint check, continuity check, anti-slop check — the agent auditing its own (or the operator's) draft against the floor. It approves (→ ship, surfaced or subconscious per the witness dial), defers (with a directive it then acts on — e.g., "tighten anti-pattern in para 3"), or rejects (with reasoning). Self-authored then self-audited is the full-accountability loop (ADR-355): the same seat that wrote it clears it against the objective floor.
- **Published**: piece moves to `published_at` state. Future revisions audited against published version (per ADR-209 revision chain — every edit attributed).

## Daily Discipline

- Pre-session: read `_voice.md` to re-orient on voice; check `_signal.md` for any drift surfaced overnight.
- During-session: write, edit, iterate. Reviewer is available on demand for voice audit on a specific passage.
- Pre-ship: mark draft `ready_for_review`; Reviewer fires pre-ship-audit; iterate on Reviewer feedback or ship.
- Post-ship: `outcome-reconciliation` recurrence folds the day's signals (coherence audit results + audience-signal slices when audience-bearing) into `_signal.md`.
