# Reviewer Prompt-Strategy Audit — Stub (Open for Future Session)

**Hat**: External Developer of the System (Hat B per CLAUDE.md §"The Two Hats"). This folder is a **stub** — it preserves the open thread for a broader audit motivated by findings from prior sessions, with the open questions enumerated and the candidate scope listed. It is NOT a completed audit. Operator decides when to engage.

**Created**: 2026-05-21T02:12Z, opened by the same session that landed Option D ([fix(reviewer-agent) commit `e8017d3`](https://github.com/Kvkthecreator/yarnnnn/commit/e8017d3)) after the resolution canary surfaced a sibling symptom that fits the broader pattern this audit was designed to catch.

## Why this stub exists

The Reviewer's tool-use loop + prompt surface has accumulated coaching mechanisms over ~20+ ADR iterations (ADR-194 v2 → ADR-216 → ADR-247 → ADR-252 → ADR-256 → ADR-260 → ADR-274 → ADR-275 → ADR-276 → ADR-281 → ADR-289 → ADR-296 v2 + more). Each addition was individually sound. Whether the accumulated surface is *coherent* and *Claude-Code-aligned* is a separate question.

Two empirical data points already motivate the audit:

### Data point 1 (Option D, just landed)
- Counter-based mid-loop nudge at `_round >= 4` was added in earlier sessions to prevent runaway loops.
- Population audit ([2026-05-21-014009-reviewer-round-budget-population-audit](../2026-05-21-014009-reviewer-round-budget-population-audit/findings.md)) showed it was solving a problem we don't have (zero wakes reached round 11+ in N=28 history) while causing the silent-wake problem we do have (70% silent at round 6).
- Option D deleted the nudge + raised budget. Canary v3 validated the structural fix.

### Data point 2 (sibling symptom, just surfaced)
- Canary v3 used 13 rounds (Option D worked) but produced a text-only response at round 13 (no tool call). Framework fell through to a dormant safety-net branch at `reviewer_agent.py:1391-1404` that auto-converts text to `stand_down` reasoning. Zero substrate writes.
- Cross-checked against N=28 historical wakes: ZERO text-only fallback events ever fired before. This is a class-of-failure that was MASKED by the now-deleted counter nudge (which provided "ReturnVerdict next" coaching that kept the model on the tool-call path). Removing the nudge exposed the gap.

The pattern that suggests a broader audit: **the framework has accumulated mid-loop coaching mechanisms that do two jobs at once — preventing runaway loops AND keeping the model on the structured tool-call path. Disentangling those two jobs requires looking at the whole prompt surface, not just one nudge.**

## Candidate scope

Not all of these are necessarily in scope — the audit should triage them once data is collected. Listed here so they don't get lost.

### A. Counter-based mid-loop nudges (status: 1 of N audited)

- ✅ `elif _round >= 4` nudge — deleted by Option D (commit e8017d3)
- ❓ `clarify_called_this_round` nudge — preserved by Option D as signal-based. Re-check: does the Clarify path consistently produce desired close behavior? Population query: how many Clarify-calling wakes existed historically, and what was their substrate-write rate?
- ❓ Any other `_round >= N` patterns in `reviewer_agent.py` that survived the Option D edit. Single grep would surface them.

### B. Text-only response handling

- The fallback at `reviewer_agent.py:1391-1404` converts text-only response to `stand_down` with prose as reasoning. This SHOULD be a rare edge case but Option D has now made it the dominant exit branch for read-heavy hooks. Two paths to consider:
  - (a) Tighten hook prompts so the model never produces text-only responses (force ReturnVerdict + WriteFile as the structured close)
  - (b) Make the text-only fallback parse the prose into structured verdict + substrate writes (framework-side intelligence) — likely wrong direction per the trust-the-model philosophy

### C. Hook + recurrence prompt shapes

Read against the post-Option-D context: every hook + recurrence prompt that asks for "decide and emit one of: X / Y / Z" — does it explicitly bind to ReturnVerdict + WriteFile as the close signal, or is the binding implicit?

Candidates:
- `docs/programs/alpha-author/reference-workspace/_hooks.yaml` (pre-ship-audit — the one canary v3 hit text-only fallback on)
- `docs/programs/alpha-author/reference-workspace/_recurrences.yaml` (corpus-coherence-check, revision-audit, outcome-reconciliation)
- `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` (signal-evaluation, outcome-reconciliation)
- Plus all Reviewer-authored Schedule entries

### D. Persona frame redundancy

`_PERSONA_FRAME` has accumulated:
- "Hard rule: call ReturnVerdict last to close the turn" (line ~850)
- "A proposal wake that times out before ReturnVerdict..." (line ~461)
- "**Call `ReturnVerdict` BEFORE any" (line ~457)
- Multiple variations on the same theme

Are these saying the same thing in different ways (good — reinforcement) or saying subtly different things (bad — model has to reconcile)? Read the full persona frame end-to-end and judge.

### E. Cross-framework comparison

The Option D rationale invoked Claude Code's trust-the-model design. Is the broader prompt surface coherently aligned, or does it mix 2024-era coaching with 2026-era trust-the-model in inconsistent ways?

- Check against Anthropic's published Claude Code system prompt patterns (public examples in their cookbook + agent SDK docs)
- Check against Anthropic Agent SDK conventions
- Identify any artifacts that smell like compensating for older model limitations

### F. ADR-trace audit

Each Reviewer prompt edit in the last 6 months traces back to an ADR. Read the ADR history and surface: which ADRs added prompt rules that may now be redundant or contradictory under the trust-the-model philosophy?

- ADR-247 (three-party narrative model — Reviewer naming)
- ADR-252 (Reviewer as primary intelligence — chat routing inversion)
- ADR-253 (Reviewer as substrate-native agent — execution authority, heartbeat)
- ADR-256 (unified Reviewer invocation — round bound declared per sub-shape)
- ADR-258 revised (Reviewer as personified chat-mode operator — REVIEWER_PRIMITIVES curated)
- ADR-260 (real-time Reviewer loop — three triggers)
- ADR-274 (trigger-authoring implementation — cadence self-awareness)
- ADR-275 (introspection cadence Reviewer-authored)
- ADR-276 (reactive-trigger envelope governance pre-load)
- ADR-281 (likely — material-outcome gate)
- ADR-289 (invocation-id taxonomy)
- ADR-296 v2 (wake architecture)

Each may have added a sentence to the persona frame. The audit checks whether the accumulation reads as one coherent voice or as a layered patchwork.

## What this audit needs before it can run

- **Data**: at least 2-3 post-Option-D wakes to characterize whether text-only fallback is the dominant exit pattern or specific to pre-ship-audit. Right now N=1 (canary v3). The discipline that fired earlier in this session ("check the DB population before deferring") applies — wait until natural wakes accumulate, then re-query.
- **Tooling**: a way to read the full Reviewer persona frame end-to-end as one artifact (it's currently spread across multiple files). Pre-audit setup: `cat` all the relevant prompt-bearing files into one document for review.
- **Cross-references**: read the Anthropic Agent SDK + Claude Code cookbook patterns for comparison baselines.

## What this audit does NOT do

This is a **scoping stub**, not an audit. No fixes recommended here. No conclusions drawn. The actual audit:

- Lives in a new observation folder when operator chooses to open it
- Should produce per-candidate-section evidence + recommendations
- Probably warrants its own ADR (Reviewer prompt design principles — doesn't exist today)
- May span multiple sessions

## Cross-references

- Round-budget population audit (the predecessor): [`2026-05-21-014009-reviewer-round-budget-population-audit/findings.md`](../2026-05-21-014009-reviewer-round-budget-population-audit/findings.md)
- Option D Hat-A fix commit: `e8017d3`
- Sibling symptom evidence: round-budget audit §"Resolution addendum 2026-05-21T02:11Z"
- Reviewer agent loop: [`api/agents/reviewer_agent.py`](../../../api/agents/reviewer_agent.py)
- Persona frame: [`api/agents/reviewer_agent.py::_PERSONA_FRAME`](../../../api/agents/reviewer_agent.py) (search for `_PERSONA_FRAME =`)
- Tool definitions: [`api/agents/reviewer_agent.py::RETURN_VERDICT_TOOL`](../../../api/agents/reviewer_agent.py) + REVIEWER_PRIMITIVES registry
- ADR-216 (orchestration vs judgment vocabulary — current Reviewer framing canon)
- ADR-296 v2 (wake architecture — most recent prompt-affecting layer)
- CLAUDE.md §"The Two Hats" (the discipline this audit will operate under)

## Status

**OPEN — awaiting operator engagement.** Touch this folder when ready to begin the audit; otherwise let it sit. The stub is cheap (one file, no fixes) and preserves the thread.
