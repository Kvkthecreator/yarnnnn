# ADR-256: Unified Reviewer Invocation

**Status**: Implemented 2026-05-08  
**Supersedes**: ADR-218 (reflection mode), ADR-252 (addressed mode / action_instruction), ADR-253 D2 (directives-as-string)  
**Amends**: ADR-229 (verdict routing — callers updated), ADR-248 (heartbeat — caller updated), ADR-253 D1/D3/D5 (execution authority, lifecycle, heartbeat — preserved, caller unified)

---

## Problem

Four separate functions accumulated in `reviewer_agent.py` — `review_proposal()`, `run_reflection()`, `address_turn()`, `heartbeat_turn()` — each with its own system prompt, tool schema, return type, and substrate-loading logic. They were added trigger-by-trigger as each new ADR arrived, making them four partial implementations of the same agent.

The structural consequence: `address_turn()` (the chat path) had no tool-use loop and could only output a free-text `action_instruction` string that the execution router pattern-matched with regex. If the pattern didn't match, the directive silently became "Directive noted:" in the narrative. The Reviewer had no hands — it could talk about acting but couldn't act.

Root cause: mode proliferation prevented seeing the agent clearly. One entity, one job (read state → apply framework → decide → act), four implementations.

---

## Decision

### D1 — One function: `invoke_reviewer()`

`review_proposal()`, `run_reflection()`, `address_turn()`, `heartbeat_turn()` are all deleted. One entry point:

```python
async def invoke_reviewer(
    client, user_id, *,
    trigger: Literal["proposal", "reflection", "heartbeat", "addressed"],
    context: ReviewerContext,
) -> ReviewerOutput | None
```

Trigger is a dimension (FOUNDATIONS Axiom 4), not a mode. Four callers pass the same entry point with different `trigger` + `context`. The function builds the user message from context, selects model by trigger, runs a bounded tool-use loop (≤3 rounds), returns `ReviewerOutput`.

### D2 — One system prompt, loaded from persona at runtime

Four hardcoded system prompt constants deleted. One base system prompt declares the Reviewer's role structure and operating posture. The persona character comes from `IDENTITY.md` read at runtime — already injected into the user message. Trigger-specific framing (what the Reviewer is being asked to do this invocation) is a short block in the user message, not a separate system prompt.

This is what the ADRs already say ("persona-read at reasoning time is load-bearing") — now the implementation matches.

### D3 — Tool-use loop: the Reviewer gets hands

`address_turn()` was a single-shot LLM call. The Reviewer had no tools — it could only return a `response` string and an `action_instruction` string. If the router didn't recognize the string, nothing happened.

`invoke_reviewer()` runs a bounded tool-use loop (max 3 rounds). The Reviewer's tool set:

| Tool | What it does | Scope |
|---|---|---|
| `ReadFile` | Read any workspace file | `/workspace/` (read-only) |
| `FireInvocation` | Fire an existing recurrence by slug | Declared recurrences only |
| `ProposeAction` | Submit a structured trade/action proposal | ACTION_DISPATCH_MAP allow-list |
| `WriteFile` | Write a file | `/workspace/review/` only |
| `ReturnVerdict` | End the loop, return structured output | Always last |

The Reviewer reads what it needs (round 1), acts on what it decides (round 2), returns verdict (round 3 or earlier). `action_instruction` as a free-text string is deleted. `ProposeAction` is a structured tool call — it either dispatches or errors visibly.

### D4 — Model by trigger, not by mode

| Trigger | Model | Rationale |
|---|---|---|
| `proposal` | Sonnet | Capital decision — reactive, time-sensitive |
| `heartbeat` | Sonnet | Capital decision — proactive, after signal fires |
| `reflection` | Haiku | Framework self-assessment — periodic, cheap |
| `addressed` | Haiku | Operator conversation — if escalates to ProposeAction tool call, that's cheap too; the action dispatches regardless of model |

Cost preserved. Haiku for thinking, Sonnet for capital decisions.

### D5 — One output type: `ReviewerOutput`

`ReviewDecision`, `ReflectionVerdict`, `AddressedAssessment` deleted. One TypedDict:

```python
class ReviewerOutput(TypedDict, total=False):
    verdict: str          # approve | reject | defer | no_change | stand_down
    reasoning: str        # persona-voice explanation, written to decisions.md
    confidence: str       # low | medium | high
    actions_taken: list   # tool calls the agent made during the loop (audit record)
    # reflection-only
    proposals: list       # framework change proposals (reflection trigger only)
    evidence_summary: str # substrate citations (reflection trigger only)
```

Callers route on `verdict`. Reflection-specific fields present only when `trigger="reflection"`.

### D6 — Token caller strings preserved (2 total)

- `"reviewer"` — Sonnet calls (proposal + heartbeat triggers)
- `"reviewer-reflection"` — Haiku calls (reflection + addressed triggers)

Ledger integrity maintained. Previously 4 callers; now 2 matching the actual model split.

### D7 — Autonomy cadence unchanged

`_autonomy.yaml` `heartbeat_triggers` still drives `_maybe_fire_reviewer_heartbeat()` in `invocation_dispatcher.py`. The heartbeat check fires `invoke_reviewer(trigger="heartbeat", ...)` instead of `heartbeat_turn()`. Same cadence, same substrate, unified entry point.

Reflection cadence unchanged — `back_office/reviewer_reflection.py` gates still apply (≥5 decisions, ≥1 new, ≥24h). Calls `invoke_reviewer(trigger="reflection", ...)`.

### D8 — Operator chat is the interrupt trigger

`addressed` trigger fires when the operator speaks in chat. The Reviewer reads the compact index (workspace state) + IDENTITY + principles + conversation window + operator message. If it needs signal files to answer, it calls `ReadFile` in round 1. If conditions are met, it calls `ProposeAction` in round 2. If it needs substrate commissioned, it calls `FireInvocation`.

The operator is not driving the Reviewer — they're interrupting it. The primary triggers are `heartbeat` and `reflection` (the Reviewer's own cadence). `addressed` is the interrupt.

---

## Deleted

- `review_proposal()`, `run_reflection()`, `address_turn()`, `heartbeat_turn()` — four functions
- `_SYSTEM_PROMPT`, `_REFLECTION_SYSTEM_PROMPT`, `_ADDRESSED_SYSTEM_PROMPT`, `_HEARTBEAT_SYSTEM_PROMPT` — four constants
- `_REVIEW_TOOL`, `_REFLECTION_TOOL`, `_ADDRESSED_TOOL` — three tool schemas
- `ReviewDecision`, `ReflectionVerdict`, `AddressedAssessment` — three TypedDicts
- `_build_user_message()`, `_build_reflection_user_message()`, `_build_addressed_user_message()` — three builders
- `_ADDRESSED_TOKEN_CALLER`, `_HEARTBEAT_TOKEN_CALLER`, `_REFLECTION_TOKEN_CALLER` — three caller strings
- `execution_router._handle_propose_action()` — ProposeAction regex handler (added 2026-05-08, deleted same day)
- `chat.py` `action_instruction` extraction and router dispatch — string-based directive parsing
- `REFLECTION_MODEL_SLUG` constant from `reviewer_agent.py` (model constants unified)

---

## Preserved

- `/workspace/review/` substrate structure (IDENTITY.md, principles.md, decisions.md, reflections.md)
- `reviewer_audit.py` — decisions.md append, unchanged
- `reviewer_chat_surfacing.py` — write_reviewer_message(), called after every invoke_reviewer()
- `review_proposal_dispatch.py` — approve/reject/defer routing logic, now routes on `output.verdict`
- `reflection_writer.py` — write-back for reflection proposals, unchanged
- `REVIEWER_MODEL_IDENTITY` constant — occupant identity string, bumped to v8
- ADR-229 judgment-first dispatch order — Reviewer reasons before AUTONOMY gate
- ADR-248 periodic pulse cadence — gate logic in reviewer_reflection.py unchanged
- ADR-253 D1 execution authority, D3 lifecycle posture, D5 heartbeat trigger

---

## Cost model

| Trigger | Before | After | Delta |
|---|---|---|---|
| `proposal` | 1 Sonnet call, ~1K tokens | 1 Sonnet call, ≤3 rounds, ~1.5K avg | +~50% on proposal path (acceptable — gets signal files if needed) |
| `heartbeat` | 1 Sonnet call, ~1.5K tokens | Same, ≤3 rounds | Flat |
| `reflection` | 1 Haiku call, ~2K tokens | Same, ≤3 rounds | Flat |
| `addressed` | 1 Haiku call, ~1K tokens | 1 Haiku call, ≤3 rounds, ~1.2K avg | +~20% but now actually works |

Net: marginal cost increase on proposal path (Reviewer can fetch signal files if absent). Addressed path cost increases slightly but the Reviewer now executes directives directly rather than requiring operator retry cycles.
