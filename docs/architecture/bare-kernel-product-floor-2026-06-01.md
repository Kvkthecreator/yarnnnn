# Framing: Is bare-kernel-without-a-program a supported product, or is program-activation the floor?

> **Status**: **Direction A RATIFIED 2026-06-01.** Program-activation is the product floor.
> The bare kernel is an inspect-only resting state; you activate a program to begin operating.
> Implementation is *subtractive* — the dead conversational-onboarding layer is deleted, the
> Settings empty state is reframed. See "Implementation" at the end.
>
> **Date**: 2026-06-01
> **Hat**: A (system canon — touches workspace_init, feed routing, onboarding prompt, Settings surface)
> **Companion**: `agent-composition.md` §4.4 (two-axis authority/vocabulary frame — the conceptual
> hardening that made this question answerable). Prior art: `docs/evaluations/2026-05-20-011700-cold-start-governance-self-amend/`
> (self-amend *mechanics*; this memo is the *product-floor* question, broader).

## The question

A workspace with **no program activated** (bare kernel) has the kernel-universal floor only —
`_workspace_guide.md`, `PRECEDENT.md`, `_token_budget.yaml`, memory skeletons, the review-seat
scaffold (`_principles.yaml`, `calibration.md`, `handoffs.md`, `OCCUPANT.md`), and the System
Agent `AGENT.md`. It does **not** have MANDATE, AUTONOMY, `_pace.yaml`, `_preferences.yaml`,
`_recurrences.yaml`, shared IDENTITY/BRAND, or the Reviewer persona files (`review/IDENTITY.md`,
`review/principles.md`, `standing_intent.md`) — those are bundle-owned (ADR-286 single-writer).

Can such a workspace become an *operating* workspace through conversation, the way the
onboarding prompt and the Settings "no program" state both imply it can?

## The answer the code already gives: no — and program-activation is the de facto floor

Three facts, each with a receipt, settle it.

**FACT 1 — YARNNN-the-LLM is not a live conversational caller.**
`api/routes/feed.py:51`: *"ContextBundle and YarnnnAgent removed — ADR-257: System Agent LLM
stream deleted."* The live feed has two dispatch paths (`feed.py:1343-1357`):
1. `route_execution` — **pure regex pattern-match, zero LLM** (`execution_router.py:42`:
   `_patterns: list[tuple[re.Pattern, Any]]`).
2. `_dispatch_reviewer_turn` → `invoke_reviewer` — the Reviewer.

The `YarnnnAgent` class still exists (`api/agents/yarnnn.py:48`) and its onboarding prompt
(`prompts/chat/onboarding.py`, with the full mandate-first elicitation posture) still exists —
but **nothing in the feed path instantiates the class or loads that prompt.** It is dead code in
the runtime. The mandate-first posture is a prompt with no caller.

**FACT 2 — `review/IDENTITY.md` has exactly one writer: bundle-fork.**
Grep for writers of `REVIEW_IDENTITY_PATH` finds only `fork_reference_workspace` (Phase 5).
`workspace_init.py:191-204` states it three times: the Reviewer persona files *"are written
exclusively by `fork_reference_workspace` in Phase 5."* There is **no freehand path to a Reviewer
persona.** A no-program operator cannot obtain a judgment seat with a character.

**FACT 3 — the Reviewer is the only conversational intelligence in the live system.**
Everything else is deterministic regex. There is no general-purpose onboarding agent.

### Consequence

The live bare-kernel workspace is **structurally incapable of starting an operation through
conversation**:
- No live agent can elicit-and-author a first MANDATE (FACT 1 — the agent that knew how is dead-coded).
- No path produces a Reviewer persona without activating a program (FACT 2).
- The Reviewer — the only mind (FACT 3) — is a *self-amending* agent over an *existing*
  constitution (per §4.4 Axis 1). At tenure-0 there is no constitution to amend, and authoring
  the *first* one is constitution-creation, which is the operator's act captured by Orchestration —
  an Orchestration surface that no longer exists in the live path.

**Program-activation is therefore the de facto product floor.** The bare kernel renders surfaces
but cannot begin an operation on its own.

## Why this is a decision worth ratifying (not just a bug)

This floor was set by the ADR-257 deletion (System Agent LLM stream), not by an intentional
product ruling. The result is **drift**: the codebase *behaves* as "program-activation is the
floor," while three artifacts still *pretend* freehand bare-kernel is a supported path —
- `prompts/chat/onboarding.py` — full mandate-first elicitation posture (dead-coded).
- The Settings → Workspace `activation_state == "none"` state — presents bare-kernel as a
  legitimate resting state with a "start without a program" affordance.
- `workspace_init.py`'s "honest unconfigured" framing — correct as far as it goes, but it
  describes a state the operator cannot *leave* conversationally.

A real operator who lands bare-kernel and types into the feed reaches the Reviewer, which wakes
into an envelope of empty strings with nothing to judge. Honest-empty becomes honest-*stuck*.

## The two ratifiable directions

### Direction A — Ratify the floor: program-activation is required to operate.
Bare kernel is an inspect-only resting state; you *must* activate a program to begin. Then:
- Delete the dead onboarding-elicitation prompt (`prompts/chat/onboarding.py` mandate-first
  posture) — singular implementation, no dead code.
- Reframe the Settings "no program" state from "start without a program" to "activate a program
  to begin" — the bare kernel is a lobby, not an office.
- The cold-start "gap" dissolves: there was never meant to be conversational bootstrap; the
  entry point is program activation (which forks the full constitution + Reviewer persona).
- **GTM consequence**: programs are the product. "Empty YARNNN" is not a standalone offering.
  This matches the OS framing (ADR-222): an OS with no application loaded does nothing useful;
  you launch an app. It also matches the agent-native thesis (programs ship the persona + the
  operation shape).

### Direction B — Reverse the floor: build a freehand bootstrap path.
Bare-kernel-without-a-program is a first-class product. Then we must build what FACT 1 + FACT 2
say is missing:
- A live conversational onboarding surface (resurrect a thin YARNNN-LLM call, or extend the
  Reviewer's envelope with a tenure-0 constitution-drafting posture — but §4.4 + Axiom 2 say the
  Reviewer must *not* author the operator's *first* intent, so this is Orchestration's job, which
  means resurrecting an Orchestration LLM).
- A freehand path to a Reviewer persona (a generic default `review/IDENTITY.md` + `principles.md`
  writable without bundle-fork — an ADR-286 single-writer amendment).
- This is materially more build, and it partially un-does ADR-257.

## Recommendation (for discussion, not yet committed)

**Direction A**, because it ratifies what the code already does, deletes dead code rather than
resurrecting it, and aligns with the OS framing (ADR-222) and agent-native thesis (programs are
the unit of value). Direction B is only warranted if "empty YARNNN as a standalone product" is a
GTM commitment — and nothing in the current thesis docs makes that commitment; they consistently
frame *programs* (alpha-trader, alpha-author) as the product.

If Direction A: the work is *subtractive* (delete the dead onboarding prompt, reframe the Settings
empty state, make activation the single entry point) — which is the cleaner, lower-risk path and
honors the Singular Implementation discipline.

## Implementation (Direction A, 2026-06-01)

A pre-deletion dependency audit found the pretense is backed by a **whole dead chat-profile
chain**, and surfaced one finding beyond the original three sites:

**The ADR-226 activation overlay is ALSO dead.** `ACTIVATION_OVERLAY` (the post-activation
walk-through that guides an operator through bundle-authored files in the `post_fork_pre_author`
state) is consumed *only* by the dead `YarnnnAgent` via the dead `build_system_prompt()`
(`prompts/__init__.py:113` ← `yarnnn.py:184-195`). The live Reviewer/wake path never checks
`activation_state == "post_fork_pre_author"`. So ADR-257 killed *all* conversational onboarding —
freehand (tenure-0 mandate elicitation) AND post-activation (the ADR-226 bundle walk-through).

**Product consequence, recorded honestly:** after this sweep there is **no conversational
onboarding at all.** This is consistent with Direction A: program activation *forks the bundle's
pre-authored substrate* (MANDATE, IDENTITY, principles, AUTONOMY, recurrences all arrive authored
from `reference-workspace/`). The operator does not author a constitution from scratch — they
*inherit* one from the program and then refine it via (a) the Reviewer's self-amendment (§4.4
Axis 1) and (b) the Files surface. The guided walk-through is not replaced; it is removed, because
the operating model no longer needs it. If post-activation guidance is later desired, it returns as
a *Reviewer-led* first-wake posture (the Reviewer reading freshly-forked substrate and narrating
what it found) — not as a resurrected Orchestration LLM. That is a future ADR if pressure surfaces.

**Subtractive sweep (this commit):**
- DELETE `api/agents/yarnnn.py` (`YarnnnAgent` — no live caller since ADR-257).
- DELETE `api/agents/prompts/chat/` entirely (onboarding, workspace, entity, activation, behaviors,
  task_scope — all chat-profile-only, all consumed only by dead `build_system_prompt()`).
- DELETE `api/routes/feed.py` `resolve_profile()` + `SURFACE_PROFILES` + the vestigial `profile`
  arg threaded (and ignored) in `_dispatch_reviewer_turn`.
- DELETE the dead chat half of `api/agents/prompts/__init__.py` (`build_system_prompt`,
  CONTEXT_AWARENESS / WORKSPACE_BEHAVIORS / ENTITY_BEHAVIORS / ACTIVATION_OVERLAY imports,
  SIMPLE_PROMPT / TOOLS_CORE / PLATFORMS_SECTION). PRESERVE the headless path (`build_prompt`,
  `build_headless_system_block`, HEADLESS_POSTURES, the three headless postures, BASE_PROMPT,
  PROFILE_KEYS) — the DispatchSpecialist surface depends on it.
- REFRAME the Settings → Workspace `no program` empty state from "start without a program" to
  "activate a program to begin."

**Preserved (audit-confirmed live or out-of-scope):** `BaseAgent` type definitions
(`agents/base.py` — `ContextBundle`/`Memory`/`AgentResult` used by reviewer_agent); the headless
specialist prompt path; `ChatAgent` (ADR-124 — also dead, but separate concern, not swept here);
the FE `surface_context` request field (harmless; Reviewer ignores it).

## What this memo does NOT decide

- Whether `daily-update` or any other default should seed at signup (separate, ADR-206/ADR-261 territory).
- The §4.4 two-axis frame (that's settled canon-hardening, drafted separately in agent-composition.md).
- Implementation sequencing — that follows the A/B ratification.
