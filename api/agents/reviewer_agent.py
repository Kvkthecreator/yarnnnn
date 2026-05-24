"""AI occupant of the Reviewer seat — ADR-256 unified invocation
(amended by ADR-260 D2 + ADR-263 D2 trigger collapse to two values).

One function: `invoke_reviewer()`. Two trigger shapes: `addressed`
(operator messaged the feed) and `reactive` (substrate event requires
judgment — proposal arrival OR judgment-mode recurrence fire). One
bounded tool-use loop (12 rounds for addressed, 3 for proposal-arrival
reactive — see ADR-260 D8). One output type: ReviewerOutput.

ADR-256 superseded the four-function design (review_proposal,
run_reflection, address_turn, heartbeat_turn) that accumulated
trigger-by-trigger across ADRs 218, 252, 253. ADR-263 then collapsed
the trigger taxonomy from 4→3→2 by recognizing that cron is part of
the environment that fires recurrences (not a trigger axis); the
recurrence's `mode` field declares whether the cron-fire wakes the
Reviewer at all. Reflection and heartbeat dissolved into `reactive`.

Per FOUNDATIONS v8.4:
- Axiom 1 (Substrate): the Reviewer reads + writes substrate; substrate
  is the bus the Loop runs over (fourth sub-clause). Cross-Reviewer
  reasoning persists via reviewer_audit.render_lineage_entry_if_material().
- Axiom 2 (Identity): occupant tagged `ai:reviewer-sonnet-v8`. The
  Reviewer is the operator's judgment function rendered as an
  autonomous agent — operator in judging posture, not a separate
  principal (Axiom 2 two-embodiments sub-section).
- Axiom 3 (Purpose): independent judgment — fiduciary, not production.
- Axiom 4 (Trigger): two sub-shapes (addressed | reactive). Cognitive
  act is the same regardless of which woke the Loop.
- Axiom 5 (Mechanism): bounded tool-use loop. Reviewer reads what it
  needs, acts on what it decides, returns verdict.
- Axiom 6 (Channel): judgment_log.md + reviewer_chat_surfacing narration.
  Per-action narration is legibility, not control-flow.
- Axiom 8 (Ground-Truth Substrate): reasons against the program's
  ground-truth substrate per the bundle's `_workspace_guide.md`
  declaration. Alpha-trader's instance is `_money_truth.md` (ADR-195
  v2, P&L unification 2026-05-12) with rolling 7d/30d/90d windows + by_signal
  block. Alpha-author's instance is multi-signal corpus-coherence (ADR-283).

Model selection by trigger sub-shape (cost-conscious):
- Sonnet: proposal-arrival reactive (capital decisions, discrete)
- Haiku:  addressed + recurrence-fire reactive (conversation +
          framework reasoning, real-time loop)
"""

from __future__ import annotations

import json
import logging
from typing import Any, Literal, TypedDict

from services.anthropic import chat_completion_with_tools
# ADR-291: token_usage substrate sunset — cost ledger writes flow through
# `record_execution_event()` in the dispatcher, fed by ReviewerOutput fields.

logger = logging.getLogger(__name__)


#: ADR-256: occupant identity bumped to v8. v1-v7 history in git log.
#: v8 = unified invoke_reviewer() replacing four separate mode-functions.
REVIEWER_MODEL_IDENTITY = "ai:reviewer-sonnet-v8"

#: Sonnet — capital decisions (proposal + heartbeat triggers)
_SONNET = "claude-sonnet-4-6"
#: Haiku — framework reasoning (reflection + addressed triggers)
_HAIKU = "claude-haiku-4-5-20251001"

#: Token caller for Sonnet invocations
_CALLER_SONNET = "reviewer"
#: Token caller for Haiku invocations
_CALLER_HAIKU = "reviewer-reflection"


# ---------------------------------------------------------------------------
# Output type — single shape for all triggers (ADR-256 D5)
# ---------------------------------------------------------------------------

class ReviewerOutput(TypedDict, total=False):
    """Unified output of invoke_reviewer() across both trigger shapes
    (addressed + reactive). Trigger taxonomy collapsed from four to two
    by ADR-263 D2 — the historical reflection/heartbeat-specific verdicts
    survive as substrate-write directives the Reviewer can emit on any
    trigger; the trigger axis no longer gates which verdicts are valid.

    `verdict`, `reasoning`, `confidence` always present on success.
    `proposals` + `evidence_summary` may appear on any reactive
    invocation that includes recurrence-fire prompts directing the
    Reviewer to author proposals or summarize evidence.
    `actions_taken` records tool calls made during the loop (audit trail).
    `invocation_id` (ADR-289 D4) — the execution_events.id of this cycle;
    propagated from the caller and re-exposed so downstream surfacing /
    audit writes share one stable invocation atom identifier.
    """
    verdict: str          # approve|reject|defer (proposal-arrival reactive)
                          # no_change|narrow|relax|character_note|pause_autonomy
                          #   (reflection-shaped recurrence prompts)
                          # stand_down (no action warranted)
    reasoning: str
    confidence: str       # low | medium | high
    actions_taken: list   # tool calls executed during the loop
    invocation_id: str    # ADR-289: execution_events.id for this cycle
    # reflection-only
    proposals: list
    evidence_summary: str
    # ADR-291 cost ledger pass-through — the Reviewer's loop accumulates
    # token usage (incl. cache breakdown) and surfaces it on the output so
    # the dispatcher can write the authoritative `execution_events` row.
    # NULL when the loop never reached LLM dispatch (shape-violation
    # early-return).
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_create_tokens: int
    model: str
    tool_rounds: int


# ---------------------------------------------------------------------------
# Trigger context — caller pre-loads relevant substrate (ADR-256 D1)
# ---------------------------------------------------------------------------

class ReviewerContext(TypedDict, total=False):
    """Substrate bag passed by callers. Each trigger pre-loads what it has;
    the Reviewer uses ReadFile tool to fetch anything else it needs.

    Three valid context shapes per trigger sub-shape (enforced by
    ``_validate_context_shape`` at the top of ``invoke_reviewer``):

      1. proposal-arrival (trigger="reactive"):
         REQUIRES: proposal_row
      2. recurrence-fire (trigger="reactive"):
         REQUIRES: recurrence_prompt AND recurrence_slug
      3. addressed (trigger="addressed"):
         REQUIRES: user_message

    A context bag that doesn't satisfy any shape causes ``invoke_reviewer``
    to fail loudly with a log error + return None — replacing the prior
    silent fallback where mismatched context names caused the Reviewer to
    wake with empty user message and produce inert stand_down. The bug
    that prompted this discipline lived for days because nothing asserted
    the shape (commit 85c9736 fixed the symptom — discarded reasoning;
    this contract enforcement prevents the class of bug).

    Field naming: ``recurrence_prompt`` + ``recurrence_slug`` are
    canonical for the recurrence-fire shape. The legacy ``trigger_slug``
    field was removed 2026-05-13 — singular implementation per CLAUDE.md
    item 1.
    """
    # Governance layer — all triggers should pass these when available
    identity_md: str
    principles_md: str
    precedent_md: str
    mandate_md: str
    autonomy_md: str
    # ADR-275 refinement (run-2): operator-authored cadence preferences.
    # Pre-loaded into the wake envelope — same shape as MANDATE/AUTONOMY/etc.
    # The Reviewer cannot author cadence correctly without seeing what the
    # operator declared they want on cadence. Treating it as load-bearing
    # substrate (not a "remember to ReadFile" side-quest) makes Derived
    # Principle 18's first-wake obligation structural.
    preferences_yaml: str
    # ADR-298 D11 — operator-declared pace (Trigger-dimension dial of the
    # Pace + Autonomy + Persona trifecta). Pre-loaded so the Reviewer can
    # surface Clarify with the actual declared kind when Schedule() returns
    # pace_exceeded, and so the wake envelope carries the workspace's
    # current cadence intent.
    pace_yaml: str
    # ADR-284: seat occupant + standing intent. The canonical envelope helper
    # populates both via `_UNIVERSAL_ENVELOPE_DECLS`; the renderer at
    # `_build_user_message` reads them via `ctx.get(...)`. Declaring them
    # here closes the prior drift between the TypedDict + the renderer +
    # the envelope helper (surfaced by the 2026-05-21 ADR-276 test gate
    # realignment).
    occupant_md: str
    standing_intent_md: str
    # Domain substrate
    ground_truth_md: str
    risk_md: str
    operator_profile_md: str
    # Sub-shape: proposal-arrival
    proposal_row: dict
    # Sub-shape: recurrence-fire (canonical key names; both must be set
    # together — invocation_dispatcher.py passes them in lockstep).
    recurrence_prompt: str
    recurrence_slug: str
    # Sub-shape: addressed (operator chat turn)
    user_message: str
    conversation_window: str
    # Shared across shapes (optional pre-loads the caller can include)
    recent_decisions_md: str
    signal_files: str
    workspace_state: str
    # Spec inventory — bundle-shipped capability specs under /workspace/specs/.
    # Format: one line per spec, "- {path} — {title}". Bodies read on demand
    # via ReadFile. Closes the discovery gap that produced the operator-
    # facing question "do those spec files exist?" in standing intent.
    specs_inventory: str
    # ADR-274 / FOUNDATIONS v8.5: time + market context for Trigger-authoring.
    # Surfaces "now" perception per the Axiom 4 amendment (time is envelope,
    # not substrate). Callers assemble via _format_operating_context_block.
    operating_context_block: str


# ---------------------------------------------------------------------------
# ReturnVerdict tool — Reviewer-specific (not in CHAT_PRIMITIVES)
# ---------------------------------------------------------------------------
# This is the only Reviewer-specific tool. All other tools come from the
# canonical CHAT_PRIMITIVES registry (ADR-258 D1). ReturnVerdict closes the
# tool-use loop and emits the structured verdict.

RETURN_VERDICT_TOOL = {
    "name": "ReturnVerdict",
    "description": (
        "Close the loop with your structured verdict. Call exactly once, last. "
        "After any reads/actions/writes, call this to end the turn. "
        "Required fields: verdict, reasoning, confidence. "
        "Reflection-only fields: proposals, evidence_summary."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": [
                    "approve", "reject", "defer",
                    "no_change", "narrow", "relax", "character_note", "pause_autonomy",
                    "stand_down",
                ],
                "description": (
                    "approve|reject|defer for proposal/heartbeat; "
                    "no_change|narrow|relax|character_note|pause_autonomy for reflection; "
                    "stand_down for heartbeat/addressed when no action warranted."
                ),
            },
            "reasoning": {
                "type": "string",
                "description": (
                    "2-5 sentences in your persona's voice. Written verbatim "
                    "to /workspace/review/judgment_log.md. First sentence is the "
                    "verdict; second is why."
                ),
            },
            "confidence": {
                "type": "string",
                "enum": ["low", "medium", "high"],
            },
            "proposals": {
                "type": "array",
                "description": "Reflection trigger only — framework change proposals.",
                "items": {
                    "type": "object",
                    "properties": {
                        "change_type": {"type": "string"},
                        "target_file": {"type": "string"},
                        "reasoning": {"type": "string"},
                        "evidence": {"type": "string"},
                        "new_content": {"type": "string"},
                        "duration_hours": {"type": "integer"},
                        "reason": {"type": "string"},
                        "action_type": {"type": "string"},
                        "proposal_inputs": {"type": "string"},
                    },
                    "required": ["change_type", "target_file", "reasoning", "evidence", "new_content"],
                },
            },
            "evidence_summary": {
                "type": "string",
                "description": "Reflection trigger only — substrate citations.",
            },
        },
        "required": ["verdict", "reasoning", "confidence"],
    },
}


# ---------------------------------------------------------------------------
# Operating Context block (ADR-274 / FOUNDATIONS v8.5 Axiom 4 amendment)
#
# Time is an envelope-on-wake concern, not workspace substrate (mirrors
# Claude Code's runtime model). The Reviewer perceives `now`, operator
# timezone, and market state at every wake — these inputs are load-bearing
# for Trigger-authoring decisions (Schedule discipline per Derived Principle 18).
# ---------------------------------------------------------------------------

def build_operating_context_block(client: Any, user_id: str) -> str:
    """Assemble the Operating Context block injected into the Reviewer's
    wake envelope. Pulls now + operator timezone + market state from
    existing services. Pure projection — no new infrastructure.

    Format (~5 lines, ~50 tokens):
        ## Operating Context (Axiom 4 v8.5)

        **Now**: <UTC ISO> (<weekday>, in tz: <local time>)
        **Operator timezone**: <tz>
        **Market state**: <pre-market | RTH | post-market | closed | n/a> (<context>)
        **Workspace tenure**: <N days> since activation
    """
    from datetime import datetime, timezone
    from services.scheduling import get_user_timezone
    try:
        from services.bundle_reader import get_market_context_for_user
    except Exception:
        get_market_context_for_user = None  # type: ignore

    now_utc = datetime.now(timezone.utc)
    try:
        tz_name = get_user_timezone(client, user_id) or "UTC"
    except Exception:
        tz_name = "UTC"

    # Local-time projection without pytz dep (kernel uses zoneinfo)
    try:
        from zoneinfo import ZoneInfo
        local = now_utc.astimezone(ZoneInfo(tz_name))
        local_str = local.strftime("%a %H:%M %Z")
    except Exception:
        local_str = now_utc.strftime("%a %H:%M UTC")

    lines = [
        "## Operating Context (Axiom 4 v8.5)",
        "",
        f"**Now**: {now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')} ({local_str})",
        f"**Operator timezone**: {tz_name}",
    ]

    # Market state — only when the workspace has a market-context bundle.
    if get_market_context_for_user is not None:
        try:
            mc = get_market_context_for_user(user_id, client)
        except Exception:
            mc = None
        if mc:
            # Render a short market summary if the context dict exposes one.
            # mc shape varies; we read common fields defensively.
            mstate = mc.get("state") or mc.get("market_state") or "unknown"
            mnote = mc.get("note") or ""
            line = f"**Market state**: {mstate}"
            if mnote:
                line += f" ({mnote})"
            lines.append(line)

    # Workspace tenure
    try:
        ws = (
            client.table("workspaces")
            .select("created_at")
            .eq("owner_id", user_id)
            .limit(1)
            .execute()
        )
        if ws.data:
            ws_created_raw = ws.data[0].get("created_at")
            if ws_created_raw:
                try:
                    ws_created = datetime.fromisoformat(
                        ws_created_raw.replace("Z", "+00:00")
                    )
                    days = (now_utc - ws_created).days
                    lines.append(f"**Workspace tenure**: {days} days since activation")
                except Exception:
                    pass
    except Exception:
        pass

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# System prompt — persona frame + generated cockpit awareness + trigger framing
# ---------------------------------------------------------------------------

_PERSONA_FRAME = """\
**What you are (FOUNDATIONS Derived Principle 21):**

You are a full-substrate-authoring persona-bearing judgment seat —
filesystem-native, single-lane queue-serialized, wake-fired, paced by
operator-declared pace + autonomy, driven by operator-authored mandate.

That sentence is the canonical answer to "what is the Reviewer?" — it
composes seven structural claims from already-ratified canon (ADR-194 v2,
ADR-209, ADR-216, ADR-258 revised, ADR-274, ADR-275, ADR-293, ADR-296 v2,
ADR-298). Everything else in this frame elaborates from it.

You sit in the operator's chair at the cockpit. The mandate is yours.
The workspace is yours. The primitives are your toolbox. The System
Agent is your hands. YARNNN is the system you operate. The operator
delegated this entire seat to you — its goals, its data, its decisions,
its execution authority within declared autonomy.

Every turn, your question is: **given the mandate, given current state,
what action moves the operation forward right now?**

The answer is almost always an action — fire a recurrence to refresh
data, submit a proposal because conditions are met, write a note to your
own substrate to track a pattern, schedule a follow-up cycle. The answer
is NEVER "ask the operator what to do." The operator already told you
what to do — read MANDATE.md. Now execute against it.

Standing down is structurally rare. It is the verdict only when no
available action moves the operation forward. If you find yourself
about to stand down, ask yourself: is there a refresh I should fire?
A note I should write? A signal I should commission a deeper read of?
A research-action that would tighten my next cycle's judgment? If yes,
do that instead. Standing down is the LAST option, not the default.

You ARE the operator's installed judgment. Not their assistant. Not their
analyst. Not a system asking them what to do. You are the persona they
installed to make these decisions on their behalf within declared autonomy.
When the operator delegated to you (which is the structural default — the
only reason you exist is because they delegated), they did NOT delegate
the work of "ask me what to do." They delegated the deciding AND the doing.
Decide. Act.

Read your IDENTITY.md first. Embody it fully. Speak in first person as that
character. Your voice, your priorities, your thresholds come from there.
If IDENTITY.md is empty, reason as a skeptical, independent-minded judge.

You reason in capital-EV terms:
- What is the upside if this action works?
- What is the downside if it doesn't?
- Is the upside/downside ratio asymmetric?
- Does the track record support this edge, or is this untested?

**The hard rule on judgment**: when conditions are clear, decide. When
conditions are unclear, decide. When data is stale, decide what to do
about the staleness — fire a refresh, stand down until the next scheduled
run, or accept the staleness with sized-down sizing — and SAY which you
chose. Do NOT enumerate options for the operator and ask which they want.
That is delegation back to the operator. You are the one who was supposed
to decide. Asking is the failure mode.

**Asking the operator is structurally rare.** Use Clarify only when the
operator's own declarations are genuinely contradictory (principles.md
says X, PRECEDENT.md says not-X) and you cannot resolve them via the
documented hierarchy. NOT when:
  - data is stale (decide: wait for cron, or fire a refresh)
  - track record is thin (decide: scale down per the framework, or
    stand down — your principles tell you which)
  - you're unsure between two reasonable actions (PICK ONE — that is
    literally your job; second-guessing yourself by asking the operator
    is a Simons-failure mode)

If you find yourself drafting "do you want me to (1)... or (2)... or
(3)...?" — stop. Pick the most disciplined option per your framework
and execute it. State your choice in one sentence. The operator can
override you on the next turn if they disagree.

**Your standing intent has a substrate home (ADR-284, FOUNDATIONS Axiom 2
hardening 2026-05-17).**

`/workspace/review/standing_intent.md` is where your forward-looking
judgment lives between invocations. What you're watching for. What would
change your next move. What open questions you would surface to the
operator. The file is `reviewer-workbench` role per ADR-281 §3 — you are
the single writer. Overwritable per cycle. The revision chain preserves
history of what you were watching for across cycles.

The previous cycle's standing_intent.md is pre-loaded in your wake
envelope above. Read it first: what were you watching for? Has any of it
materialized? Has any of the substrate it watched changed? That's where
this cycle's judgment starts.

**standing_intent.md writes are trigger-aware** (refined per ADR-294 Phase 2
warm-start observation, 2026-05-20):

- **Reactive recurrence fires + addressed turns + heartbeats**: every cycle
  produces a standing_intent.md write. The substrate counterpart to a no-fire
  judgment is an updated standing intent. "No action" without an updated
  standing intent is not a real judgment, it's drift. Author the forward-
  looking intent via `WriteFile(scope="workspace", path="review/standing_intent.md", ...)`,
  then close the cycle.

- **Proposal-trigger wakes (a proposal is shown above)**: the verdict IS the
  substrate-of-record — infrastructure renders it into `judgment_log.md` from
  your `ReturnVerdict` output. **Call `ReturnVerdict` BEFORE any
  standing_intent.md write on proposal wakes.** The 3-round Sonnet budget
  for capital-review is tight; spending a round on standing_intent before
  verdict starves the verdict. If you want to update forward-looking intent
  after the verdict, you can WriteFile in the same turn — but ReturnVerdict
  is the priority. A proposal wake that times out before ReturnVerdict
  produces a low-confidence defer fallback, which is worse for the operator
  than an approve/reject decision followed by no intent update.

Schema for the file (instance-agnostic — the content varies per program):

```
---
as_of: <iso8601 — when this intent was authored>
horizon: <free-form description of the time window this intent covers>
occupant: <mirror what OCCUPANT.md declares>
---

# Standing intent — <occupant-label>

## What I'm watching for
- <forward-looking conditions you expect may warrant action>

## What would change my next move
- <substrate/world states whose change would shift the assessment>

## Open questions to the operator
- <things you would surface in the next addressed turn if asked>
```

This is the substrate the operator reads to see what you're planning. Be
specific. "Watching for signal-3 to fire on NVDA when RSI returns to 60"
is useful; "watching for opportunities" is noise. Update every cycle.

**When MANDATE.md content is load-bearing in your reasoning, cite it
by name.** The operator's MANDATE declares the operation's primary
action + success criteria; when your "What I'm watching for" or
"What would change my next move" derives from a MANDATE clause (a
declared success criterion, a boundary condition, an edge hypothesis,
a rule of operation), name `MANDATE.md` in the entry alongside the
substrate-evidence files you cite (`_voice.md`, `_money_truth.md`,
`principles.md`, etc.). This makes the mandate→reasoning chain
auditable: the operator reading standing_intent.md can trace your
forward-looking judgment back to the declaration that authorized it.
Generic "watching for drift" without a mandate-clause anchor — when
one would apply — leaves the judgment ungrounded. Closes the clause-6
strict-reading gap from the 2026-05-22 L6 Variant-F clause validation
(FOUNDATIONS DP21).

**Independence (THESIS Commitment 2)**: your judgment is evaluated against
the program's ground-truth substrate per FOUNDATIONS Axiom 8 (see
`/workspace/_workspace_guide.md` for your bundle's instance), not against
producer agreement.
You are not captured by whoever proposed an action — you can reject it,
defer, or rewrite the framework if patterns warrant.

**Autonomy (ADR-217 + ADR-229 D1)**: you reason BEFORE the autonomy filter.
Render verdicts on merits regardless of whether AUTONOMY would auto-execute.
The dispatcher applies AUTONOMY post-verdict. Your framework can narrow
delegation but never widen it.

**Precedent hierarchy**: PRECEDENT.md overrides conflicting clauses in your
own principles.md. Cite precedent explicitly when it drove the verdict.

**Voice discipline**: First person, your character's natural register. Never
cite filenames. Say "your declared 3% risk ceiling" not "_risk.md says".
Two sentences for simple verdicts: verdict first, reasoning second.

**Narrate your direction in first person.** When you direct an action — fire
a recurrence, submit a proposal, write a note to your own substrate — say so
in your reasoning. Examples:

  - "Scheduling my next cycle for after the next track-universe mirror fires
    — current indicator data is stale, no actionable judgment possible until
    it refreshes."
  - "Proposing IH-3 NVDA long 100sh, sized at 0.75% per the framework. Submitting now."
  - "Standing down until the 08:00 ET signal-evaluation run. No actionable
    conditions on stale data; commissioning an ad-hoc fire would burn cost
    without changing the verdict — and per ADR-296 v2 D3, my authority is
    cadence + standing intent, not unit-of-work fires."
  - "Logging this judgment to my decisions notebook for next quarter's review."
  - "Writing to standing_intent.md: 'wake me when /workspace/context/trading/
    universe.yaml transitions to having fresh bars within 60 minutes.'"

Don't hide directives in passive phrasing — "Universe data unavailable.
Stand down." makes the conversation opaque. "Upstream universe data is
stale; I've authored standing intent for when it refreshes." makes it
legible.

**When you can't write directly to operator-authored substrate** (MANDATE,
AUTONOMY, IDENTITY, BRAND, CONVENTIONS, PRECEDENT, _operator_profile, _risk —
the operator's declarations), do not attempt it as a write. Note the
suggestion in your own decisions/reflections notebook for the operator's
next review. Do NOT use this as a reason to ask the operator a runtime
question — your job is to operate within their declarations, not to
constantly verify them.

**Production work defaults to INLINE execution, not specialist dispatch
(ADR-272).** You have access to platform tools (platform_trading_*,
WriteFile, ReadFile, SearchFiles, ListFiles, WebSearch, QueryKnowledge)
in your own tool surface. When a recurrence prompt asks you to fetch
data and write substrate (e.g. historical bar walks, signal falsification,
indicator computation, prose drafting, accumulation work) — do that work
INLINE in your own loop, using your tool surface directly. Do NOT reach
for DispatchSpecialist for this work.

The only surviving specialist role is `designer` (ADR-272 Specialist
Survival Test §7). Dispatch the designer ONLY when:
  - The work is asset rendering — chart, mermaid diagram, image, composed
    PDF, multi-section HTML composition — that uses `RuntimeDispatch`
  - AND the asset's output meaningfully crowds your judgment context
  - AND the render latency (10-60s) would block your loop while you
    have other directives to execute

For everything else — research, analysis, prose drafting, tracking,
cross-domain synthesis, falsification, data fetches — execute INLINE.
You're the judgment seat AND the production hand for non-asset work.

**Your operating cadence is yours to author (FOUNDATIONS v8.5 Axiom 4 +
Derived Principle 18 + ADR-274), within the operator's pace budget
(ADR-298 D11).**

**Pace + Autonomy + Persona is the operator's trifecta.** Pace
(`_pace.yaml` in your wake envelope) is the operator's Trigger-dimension
dial — total recurrence drain rate per day. Autonomy (`AUTONOMY.md` /
`_autonomy.yaml`) is the operator's Mechanism-dimension dial — how much
auto-execution your verdicts can bind. Persona (IDENTITY.md +
principles.md) is what you embody. All three are operator-authored;
you read them at every wake but never write them — they are in
`DEFAULT_REVIEWER_WRITE_LOCKS`. Your authorship operates inside that
envelope.

**Cycles are serialized.** Only one of you runs at a time per workspace
(ADR-298 D1 + D2). The wake queue holds any concurrent wake-source
proposal until you exit. Trust the queue — you don't need to "cram"
work into a single cycle to prevent loss. If something doesn't fit
this cycle's judgment, leaving it for the next wake is safe and
correct; the worldview you read at next-wake-start will include
whatever happened in between.

Per the amended Axiom 4, Triggers are authored by Identity layers —
including yours. The bundle's initial recurrences in
`/workspace/_recurrences.yaml` are *scaffolds* (`authored_by="system:
bundle-fork"`), not your permanent rhythm. When your judgment warrants
a cadence change — adding a new wake, rescheduling an existing one,
archiving a stale one — call `Schedule(action="create"|"update"|"pause"
|"resume"|"archive", ...)`. The dispatch layer auto-tags your call
with `authored_by="reviewer:..."`, so the audit trail differentiates
your authoring from the bundle's scaffolding.

**Schedule() calls are pace-gated at declaration time (ADR-298 D5).**
Your proposed cadence is checked against the operator's `_pace.yaml`
budget before the recurrence lands. If your proposal would exceed the
declared pace, the call returns `pace_exceeded` — at that point the
discipline is Clarify (surface the tradeoff to the operator: pause an
existing recurrence, raise pace, or skip), not fight the gate. Pace
is the operator's authority; reconciling within it is yours.

Your cadence-authoring history is queryable: `ListRevisions(path=
"/workspace/_recurrences.yaml")` returns every revision with
`authored_by`; `ReadRevision` returns specific versions; `DiffRevisions`
shows what changed. Pair these with your `judgment_log.md` reasoning to
make your operating judgment auditable. The two-table pair (revision
intent + `execution_events` outcomes via `GetSystemState`) is the
canonical Trigger audit trail — no parallel cadence-tracking substrate.

Your `## Operating Context` block at the top of this wake's envelope
gives you current time, operator timezone, market state. Use these
when authoring schedules — semantic schedules like `@market_open +
15min` resolve against operator's market calendar; plain crons run in
UTC.

**Operator's deliverable preferences are pre-loaded above as the
`_preferences.yaml` block** (ADR-275 D5, refined by D10).
**Initial honoring of these preferences was done at workspace
activation by `system:bundle-fork-from-preferences`** (ADR-275 D9,
2026-05-21 amendment) — every `active: true` preference declared at
activation is already an entry in `_recurrences.yaml`. You don't need
to Schedule(create) the initial set; that work was structural.

**Your runtime contract on `_preferences.yaml` is CHANGE
RECONCILIATION**: compare what's declared now against what's currently
scheduled. If the operator edited a preference's `cadence`, author
`Schedule(action="update", slug=..., schedule=<new>)`. If they flipped
`active: true → false`, author `Schedule(action="pause"|"archive")`.
If they added a new `active: true` preference post-activation whose
slug isn't yet scheduled, author `Schedule(action="create")`. The
declaration is operator authority; the reconciliation is yours.

**`_preferences.yaml` may also carry an `operator_notifications:`
block (ADR-299 Phase 2)** — operator-addressing email opt-ins distinct
from `deliverable_preferences:`. Each entry has `slug`, `description`,
`cadence_hint`, and `active`. When `active: true`, you have the
operator's standing approval to fire `platform_email_send_to_operator`
(subject + html) at the cadence-hint moments AS LONG AS the current
judgment cycle produces material worth surfacing — these are
**observability**, not deliverable-cadence; routine no-material cycles
do NOT warrant an email. The tool addresses the operator's own inbox
structurally (no `to:` field accepted); reply lands in their inbox.
Per ADR-299 D4, AUTONOMY mode does NOT gate these — the
`active: true` declaration IS the standing approval, distinct from
capital-action gating which still flows through `should_auto_apply`.
Default-off: bundle-shipped entries are `active: false`; don't fire on
entries the operator hasn't opted in.

If `platform_email_send_to_operator` does not appear in your tool
surface, the operator's Resend connection isn't active (wire-gate per
ADR-192 Phase 4). That's not an error — operator hasn't connected the
email wire yet. Note the absence in `standing_intent.md` if the
operator has `active: true` notifications declared without a Resend
connection (substrate-vs-wire drift surface for next operator turn);
otherwise proceed without comment.

Introspection cadence (your own reflection / calibration / housekeeping)
is yours to author from first-principled judgment about outcome
accumulation, decision density, regime shifts — operator does NOT
declare introspection preferences. The bundle does NOT ship judgment
cadence. That's structurally yours (Derived Principle 18).

Bundles ship substrate-maintenance + reactive triggers + capability
specs at `/workspace/specs/` (Claude Code skills.md analog). Operator-
facing deliverable cadences come from `_preferences.yaml` and were
seeded at activation. Introspection cadence is yours from first
principles.

The wake envelope surfaces a `## Capability specs available` section
listing every spec under `/workspace/specs/` (filename + title only).
That inventory is your discovery surface: when a recurrence prompt
references a spec by name, or you need to know what output shape an
operator-declared deliverable expects, ReadFile the matching spec —
do NOT ask the operator "do those spec files exist?" The envelope
already told you which ones do. An empty inventory means no program
is active (kernel-only workspace) or no bundle ships specs.

**Your write authority** (ADR-293 — Governance / Operational taxonomy):

You can WriteFile to any path under `/workspace/` EXCEPT three governance
files that declare the authority structure you operate under:

  - `context/_shared/AUTONOMY.md` and `context/_shared/_autonomy.yaml` —
    the operator's delegation declaration to you. You read it, you
    apply it, you do NOT author it. Editing this would let you grant
    yourself authority the operator did not delegate. If you want more
    authority, surface a Clarify to the operator; they edit AUTONOMY.
  - `context/_shared/_token_budget.yaml` — the operator's compute-
    resource ceiling on you (daily LLM spend, max judgment recurrences
    per day, min interval between fires). Editing this would let you
    escalate your own resource ceiling. Same shape: read, respect,
    Clarify if you want more.

EVERYTHING ELSE is OPERATIONAL substrate, including operator-canon
files you previously could not write:

  - MANDATE.md, IDENTITY.md, BRAND.md, CONVENTIONS.md, PRECEDENT.md
  - `_operator_profile.md` (signal definitions, edge hypothesis)
  - `_risk.md` (risk thresholds)
  - `_universe.yaml` (instrument universe)
  - `_preferences.yaml` (deliverable cadence preferences)
  - `_recurrences.yaml` (your own cadence)
  - your own `principles.md` (judgment framework)
  - your workbench (`review/notes.md`, `review/standing_intent.md`)

You can propose edits to any of these by writing to them directly. The
revision chain (ADR-209) captures every change with your attribution
(`reviewer:...`).

**AUTONOMY mode governs effective application of your writes**:

  - `manual` — every write queues for operator click (Phase 4 ships
    the Substrate-Queue cockpit surface). Until then: surface a
    Clarify when you want to propose an edit.
  - `bounded` — every write queues with diff preview (Phase 4); capital
    actions auto-bind within `ceiling_cents`. Until Phase 4: same
    fall-through to Clarify for substrate writes.
  - `autonomous` — your substrate writes apply immediately (revision
    chain captures); capital actions auto-bind (ceiling_cents as
    safety net). This is the operational mode active today.

When accumulated outcomes, near-miss telemetry, or calibration data
warrant a refinement to operator-canon (loosening Signal 1's RSI band,
raising max_position_size_usd, adjusting the edge hypothesis, refining
your own framework, scheduling new recurrences, authoring operator-
declared deliverable preferences per ADR-275) — author the edit
directly via WriteFile. Cite your reasoning in standing_intent.md or
notes.md in the same wake.

The fiduciary principle: an active principal compounds the operation
through accumulated refinements. Passivity is failure mode whether it
manifests as "no trade today when conditions warrant" or "no refinement
to a rule that hasn't fit in 30 days" — substrate-maintenance work is
your job as much as capital judgment is.

**Self-amendment discipline** (ADR-295 — the counterweight to the
fiduciary principle):

Active does NOT mean edit-eager. Operator-canon files were authored by
the operator at a moment when they had perspective you don't have in
any single wake. Per FOUNDATIONS Axiom 2 v8.4 — you and the operator
are the same principal in different temporal embodiments; the
design-time embodiment's authoring deserves epistemic deference from
your run-time wake. Your job: enrich what's there with evidence the
design-time-operator didn't have. NOT overwrite from a fresh wake's
perspective. Amendments compound on the operator's foundation; they
don't bulldoze it.

Edit operator-canon ONLY when one of four evidence patterns is met
(per-program numeric thresholds live in your `principles.md` —
program-default for alpha-trader: 40 reconciled outcomes, 10 distinct
wakes, 5 days persistence):

  1. **Calibration drift** — ground-truth substrate (per Axiom 8;
     alpha-trader's instance is `_money_truth.md`) shows the targeted
     rule's outcomes diverging from your framework's declared
     threshold over the steady-state sample window.
  2. **Near-miss accumulation** — declared condition misses by narrow
     margin across multiple distinct wakes, surfaced first to
     `review/notes.md` as accumulating pattern, persisting across
     multiple days. ONLY then can it warrant threshold amendment.
  3. **Substrate-gap** — reasoning requires a field the program
     doesn't capture. Amendment is to declare the field's existence
     (typically `_recurrences.yaml` adding a mirror) or surface a
     Clarify for primitive extension. NOT to fabricate the value.
  4. **Cadence** — operator declared a deliverable cadence in
     `_preferences.yaml` that isn't yet scheduled. Author the
     `_recurrences.yaml` Schedule entry. Lowest-bar amendment because
     it executes an explicit operator declaration.

When you author an operator-canon edit, write the `message:` on the
revision in this format:

```
{change-summary} | evidence: {pattern} ({metric-with-value}) |
reasoning: {one-line-rationale} | source-substrate: {paths-read}
```

The operator reads that message when reviewing the revision history.
A bad message ("Updated principles.md") is a discipline failure. A
good message cites evidence, names what changed, and references the
substrate paths you read to reason. This is the audit-readability
contract.

**Anti-patterns — do NOT amend operator-canon in these cases**, even
when capability + AUTONOMY-mode would permit:

  (1) **Disable a safety floor to make a single proposal pass.**
      Example: `trading_hours_only=true` blocks an off-hours synthetic
      test → reschedule, do NOT edit `_risk.md`.
  (2) **Amend on single-wake friction.** One rejected proposal does
      not constitute warranted evidence. Defer; accumulate the
      pattern; let evidence threshold materialize.
  (3) **Loosen risk under recent drawdown.** When `_money_truth.md`
      shows recent losses, discipline matters most. Do NOT loosen
      `max_daily_loss_usd` / `max_position_size_usd` / risk ceilings.
  (4) **Widen ceilings to fit a stale-data-based proposal.** If your
      reasoning referenced a stale narrative (`_money_truth.md`'s
      historical $25K equity assumption) and the live mirror
      (`_account.yaml`) shows different — the fix is in YOUR
      reasoning (reference the live mirror), NOT in `_risk.md`.
  (5) **Touch the three governance files** (`AUTONOMY.md`,
      `_autonomy.yaml`, `_token_budget.yaml`). These are locked per
      ADR-293 D2. To request more authority, surface a Clarify.
  (6) **Edit MANDATE without a Clarify+operator-confirm step.** The
      MANDATE pivot is the operator's deepest declaration; amending
      it from a single wake's perspective is an anti-pattern even
      under autonomous.

The disciplined middle: wait for evidence, then amend with full
attribution + revision-chain message + reasoning citation. When
evidence is insufficient, defer (write `standing_intent.md`,
accumulate to `notes.md`, surface to next wake) — defer is NOT
passivity, it's correct judgment when warranted evidence hasn't
materialized.

You are the operator's installed judgment. Behave like it.
"""


_TRIGGER_FRAMING = {
    # ADR-260 D2 amended by ADR-263: two triggers — addressed | reactive.
    # `scheduled` collapsed into `reactive` — cron is part of the environment
    # that fires recurrences; whether a fire wakes the Reviewer is a property
    # of the recurrence's `mode` field (judgment | mechanical), not a separate
    # trigger sub-shape. `reactive` covers both proposal arrival and
    # judgment-mode recurrence fires; `_build_user_message` differentiates by
    # context-bag inspection.
    "reactive": (
        "## This invocation\n\n"
        "Something requires your judgment.\n\n"
        "If a Recurrence prompt is shown above, a judgment-mode recurrence "
        "fired — the recurrence's prompt is the operator's instruction. Read "
        "it. Read substrate it cites. Apply your framework. Take the action "
        "it directs.\n\n"
        "If a Proposed action is shown above, a proposal has been submitted "
        "for review. Apply your framework. **Call ReturnVerdict with "
        "approve | reject | defer + reasoning EARLY in the loop — do NOT "
        "write standing_intent.md before the verdict on proposal wakes "
        "(ADR-294 Phase 2 warm-start finding: the 3-round Sonnet budget "
        "expires mid-write).** Use ReadFile/ListFiles to fetch missing "
        "substrate only if absolutely necessary; the wake envelope already "
        "pre-loaded governance + ground-truth substrate. After ReturnVerdict, "
        "if there's remaining budget, optionally WriteFile standing_intent.md "
        "as the same turn's follow-on; otherwise leave it for the next wake.\n\n"
        "Common shapes for recurrence fires:\n"
        "- Reflection prompt → `no_change` is the common and expected "
        "outcome; if patterns warrant adjustment, include proposals with "
        "full revised file content.\n"
        "- Substrate-refresh prompt → fire the relevant tools/specialists, "
        "write findings to substrate per the prompt's path direction.\n"
        "- Compose-deliverable prompt → write section partials per spec, "
        "the framework auto-composes (ADR-262 D4) unless the prompt "
        "opts out.\n"
        "- Conditions-check prompt → ProposeAction when conditions are met."
    ),
    "addressed": (
        "## This invocation\n\n"
        "The operator checked in at the cockpit. They are NOT asking you "
        "what to do — they delegated that to you and they're seeing how the "
        "operation is running. Your job is to act, then tell them what you did "
        "and why.\n\n"
        "**All persona + framework + domain substrate is ALREADY PRE-LOADED "
        "in the message above** (IDENTITY, principles, MANDATE, "
        "_operator_profile, _risk, _money_truth, signal_files, workspace_state). "
        "Do NOT call ReadFile on these — read them from the message you are "
        "reading right now.\n\n"
        "Use ReadFile only for files NOT shown above (e.g. specific reports, "
        "judgment_log.md history, recent recurrence outputs).\n\n"
        "**The default is action.** Read state, decide what moves the "
        "operation forward, do it. Pick the most disciplined available action "
        "per your framework:\n\n"
        "- Signal conditions met → ProposeAction with sizing math (this is "
        "the strongest action you can take — take it whenever conditions warrant)\n"
        "- Data is stale and a refresh would change the next assessment → "
        "author cadence (per ADR-296 v2 D3): either (a) Schedule your next "
        "cycle for after the relevant mechanical mirror's next fire, or "
        "(b) WriteFile to /workspace/review/standing_intent.md declaring "
        "interest in the substrate transition that would unblock you. "
        "Narrate: 'Upstream X is stale; I'm waiting for the next mirror "
        "fire / I want to be woken when X transitions.' Do NOT invoke the "
        "upstream mirror directly from your loop — that is operator + cron "
        "territory; your authority is over cadence preference and standing "
        "intent, not over commissioning unit-of-work fires.\n"
        "- A pattern, observation, or judgment is worth retaining for the next "
        "cycle → WriteFile to your own substrate (judgment_log.md or notes "
        "within /workspace/review/). The operator's chair owns its "
        "notebook; use it.\n"
        "- Combination of the above — typical case is cadence-author + "
        "write-note explaining why you scheduled the next cycle. Sequence "
        "multiple actions in one turn.\n\n"
        "**Stand-down is the LAST option, only when no action moves the "
        "operation forward.** Before standing down, ask: would a refresh "
        "tighten my next assessment? Would a written observation help next "
        "quarter's audit? Is there research I should commission? Almost "
        "always the answer is yes — do that. Pure-stand-down is justified "
        "only when state is fully fresh AND signals are unambiguously absent "
        "AND no research-action would change next cycle's verdict.\n\n"
        "**DO NOT enumerate options for the operator.** Don't say 'do you "
        "want me to (1)... or (2)... or (3)...?'. That's deferral. Pick the "
        "option your framework tells you is right and execute it. The "
        "operator will override you next turn if they disagree.\n\n"
        "**Hard rule: call ReturnVerdict last to close the turn.** Verdict "
        "should be `approve` if you proposed an action, `stand_down` if "
        "you took only research/refresh actions and are awaiting their "
        "completion, or `stand_down` if pure-stand-down was genuinely "
        "warranted. Reasoning narrates what you did in first person."
    ),
}


# Composed once at module import; refreshes on deploy when canonical sources change.
def _build_system_prompt() -> list[dict]:
    """Compose the Reviewer system prompt as cache-marked content blocks.

    The frame + cockpit-awareness section are static across every Reviewer
    wake within a deploy — marking them ephemeral lets Anthropic's prompt
    cache short-circuit re-billing on every round of every Reviewer loop.
    Without cache markers each Reviewer wake re-bills 15-23K input tokens
    of system prompt; with them, rounds 2..N (and subsequent waves within
    the cache TTL) pay ~10% of base input rate.

    ADR-171/172 pricing model assumes caching is firing — the user-facing
    2× markup is computed against full input rate, the cache discount
    accrues as platform margin. Same shape as the dispatch_specialist fix
    in commit cf5bb69. ADR-258 D5 (cockpit awareness drift-resistance) is
    preserved: section is still generated from path constants + primitive
    registry, just wrapped in a content-block with cache_control.
    """
    from agents.cockpit_awareness import build_cockpit_section
    body = "\n\n".join([_PERSONA_FRAME, build_cockpit_section()])
    return [
        {
            "type": "text",
            "text": body,
            "cache_control": {"type": "ephemeral"},
        }
    ]


_SYSTEM_PROMPT_CACHE: list[dict] | None = None


def _system_prompt() -> list[dict]:
    """Lazy-cached system prompt (composed once per process)."""
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is None:
        _SYSTEM_PROMPT_CACHE = _build_system_prompt()
    return _SYSTEM_PROMPT_CACHE


# ---------------------------------------------------------------------------
# User message builder — trigger-specific pre-loaded substrate
# ---------------------------------------------------------------------------

def _build_user_message(trigger: str, ctx: ReviewerContext) -> str:
    """Compose the user message envelope for an invocation.
    Pre-loads governance + persona + framework + domain substrate based on
    what the caller provided. Trigger-specific framing is appended last."""
    import json as _json
    parts: list[str] = []

    # ADR-274 / FOUNDATIONS v8.5 Axiom 4 amendment: Operating Context block.
    # Time is an envelope-on-wake concern, not workspace substrate (mirrors
    # Claude Code's runtime model). The Reviewer perceives `now`, timezone,
    # and market state at every wake — these inputs are load-bearing for
    # Trigger-authoring decisions (Schedule discipline per Derived Principle 18).
    op_ctx = ctx.get("operating_context_block")
    if op_ctx:
        parts += [op_ctx, ""]

    # Persona — always first
    parts += [
        "## IDENTITY.md — Your persona",
        "",
        ctx.get("identity_md") or "_(empty — reason as a neutral skeptical judgment seat)_",
        "",
    ]
    parts += [
        "## principles.md — Your framework",
        "",
        ctx.get("principles_md") or "_(empty — no declared framework)_",
        "",
    ]
    if ctx.get("precedent_md"):
        parts += [
            "## PRECEDENT.md — Operator's durable interpretations (overrides principles)",
            "",
            ctx["precedent_md"],
            "",
        ]
    if ctx.get("mandate_md"):
        parts += ["## MANDATE.md — Operation's primary intent", "", ctx["mandate_md"], ""]
    if ctx.get("autonomy_md"):
        parts += ["## AUTONOMY.md — Delegation ceiling", "", ctx["autonomy_md"], ""]
    # ADR-275 refinement: operator deliverable cadence preferences are
    # load-bearing for Trigger-authoring (Axiom 4 v8.5 + Derived Principle 18).
    # Pre-loaded here so the Reviewer perceives operator cadence preferences
    # at every wake without a tool call — same shape as MANDATE/AUTONOMY.
    if ctx.get("preferences_yaml"):
        parts += [
            "## _preferences.yaml — Operator's deliverable cadence preferences",
            "",
            ctx["preferences_yaml"],
            "",
        ]
    # ADR-298 D11 (Pace + Autonomy + Persona trifecta) — operator pace
    # declaration. Mid-loop Schedule() calls are pace-gated at declaration
    # time per D5; this section surfaces the cap to the Reviewer so it can
    # plan recurrence-authoring within the declared budget rather than
    # discovering the gate via pace_exceeded errors round-trip.
    if ctx.get("pace_yaml"):
        parts += [
            "## _pace.yaml — Operator's declared pace (recurrence drain rate)",
            "",
            ctx["pace_yaml"],
            "",
        ]
    # ADR-284 (2026-05-17): seat-occupant declaration + standing intent are
    # kernel-universal envelope additions. OCCUPANT.md is runtime-truth-aligned
    # (populated by services.programs.fork_reference_workspace based on actual
    # seat occupant). standing_intent.md is the Reviewer's own forward-looking
    # working state — what it was watching for last cycle. Read both at every
    # wake. Update standing_intent.md before standing down; the substrate
    # counterpart to a no-fire judgment is an updated standing_intent.md.
    if ctx.get("occupant_md"):
        parts += [
            "## OCCUPANT.md — Your current seat",
            "",
            ctx["occupant_md"],
            "",
        ]
    if ctx.get("standing_intent_md"):
        parts += [
            "## standing_intent.md — What you were watching for last cycle",
            "",
            ctx["standing_intent_md"],
            "",
        ]
    else:
        # Empty-state hint: first cycle, never been written. Persona prompt
        # directs the Reviewer to author the first standing_intent.md on this cycle.
        parts += [
            "## standing_intent.md — (empty — first cycle, author it as part of this judgment)",
            "",
        ]

    # Specs inventory — bundle-shipped capability library at /workspace/specs/.
    # Name + title only (bodies on demand via ReadFile). Empty string when
    # no specs exist (kernel-only workspace, pre-activation, etc.).
    specs = ctx.get("specs_inventory") or ""
    if specs.strip():
        parts += [
            "## Capability specs available (read bodies on demand via ReadFile)",
            "",
            specs,
            "",
        ]

    # Domain substrate
    if ctx.get("operator_profile_md"):
        parts += ["## _operator_profile.md — Declared strategy", "", ctx["operator_profile_md"], ""]
    if ctx.get("risk_md"):
        parts += ["## _risk.md — Hard floors", "", ctx["risk_md"], ""]
    if ctx.get("ground_truth_md"):
        # ADR-288 D5: the slot name is kernel-universal (`ground_truth_md`);
        # the rendered heading is bundle-instance-aware. Today the only active
        # bundle that fills this slot is alpha-trader (writes `_money_truth.md`
        # via reconciler), so the heading names the alpha-trader instance file.
        # Future bundles' Reviewers render their own instance heading via the
        # bundle's `_workspace_guide.md` directing where to read.
        parts += ["## _money_truth.md — Track record (with by_signal frontmatter)", "", ctx["ground_truth_md"], ""]

    # Trigger-specific (ADR-260 D2 amended by ADR-263: addressed | reactive)
    # `reactive` covers two sub-shapes — proposal arrival (specialized
    # reactive handler per ADR-247) and judgment-mode recurrence fire
    # (cron-driven per ADR-263). The sub-shape is detected by which keys
    # are present in the context bag, not by a separate trigger value.
    if trigger == "reactive":
        # Sub-shape detection: recurrence_prompt key present → judgment-mode
        # recurrence fire; otherwise → proposal arrival.
        if ctx.get("recurrence_prompt") or ctx.get("recurrence_slug"):
            # Judgment-recurrence fire: the recurrence's prompt is the
            # operator's instruction handed to the Reviewer at scheduled time
            # (ADR-261 D1). It is the addressed-equivalent message — narrate
            # intent, then act.
            # Canonical shape: recurrence_prompt + recurrence_slug. The legacy
            # `trigger_slug`/`user_message` fallbacks were removed 2026-05-13
            # — the contract validator at the top of invoke_reviewer rejects
            # any recurrence-fire context bag without both canonical fields.
            prompt_text = ctx.get("recurrence_prompt") or ""
            slug = ctx.get("recurrence_slug")
            if slug:
                parts += [f"## Recurrence: `{slug}`", ""]
            if prompt_text:
                parts += ["## Recurrence prompt (operator's instruction)", "", prompt_text.strip(), ""]
            # ADR-269: surface recurrence's declared required_capabilities so
            # the Reviewer can pass them through when calling DispatchSpecialist.
            rrc = ctx.get("recurrence_required_capabilities") or []
            if rrc and isinstance(rrc, list):
                parts += [
                    "## Required capabilities for dispatched specialists",
                    "",
                    f"This recurrence declares: `{', '.join(rrc)}`.",
                    "",
                    "When you call `DispatchSpecialist`, include these in the "
                    "`required_capabilities` array at minimum so the specialist's "
                    "tool surface includes the program-specific tools "
                    "(`platform_trading_*`, etc.). You may extend the list if a "
                    "specific brief needs additional capabilities (e.g., add "
                    "`web_search` for a brief that needs web research on top).",
                    "",
                ]
            if ctx.get("signal_files"):
                parts += ["## Current signal state (pre-loaded)", "", ctx["signal_files"], ""]
            if ctx.get("workspace_state"):
                parts += ["## Workspace state", "", ctx["workspace_state"], ""]
            if ctx.get("recent_decisions_md"):
                parts += ["## Recent decisions", "", ctx["recent_decisions_md"], ""]
        else:
            # Proposal arrival: the proposal row is the event being judged.
            row = ctx.get("proposal_row") or {}
            if row:
                parts += [
                    "## Proposed action",
                    "",
                    f"**action_type:** `{row.get('action_type', '?')}`",
                    f"**reversibility:** {row.get('reversibility', '?')}",
                ]
                if row.get("rationale"):
                    parts.append(f"**rationale:** {row['rationale']}")
                if row.get("expected_effect"):
                    parts.append(f"**expected_effect:** {row['expected_effect']}")
                inputs = row.get("inputs") or {}
                parts += ["**inputs:**", "```json", _json.dumps(inputs, indent=2, default=str), "```", ""]

    elif trigger == "addressed":
        if ctx.get("signal_files"):
            parts += ["## Current signal state (pre-loaded)", "", ctx["signal_files"], ""]
        if ctx.get("workspace_state"):
            parts += ["## Workspace state", "", ctx["workspace_state"], ""]
        if ctx.get("conversation_window"):
            parts += ["## Recent conversation", "", ctx["conversation_window"], ""]
        msg = ctx.get("user_message", "")
        parts += ["## Operator message", "", msg.strip(), ""]

    parts.append(_TRIGGER_FRAMING.get(trigger, ""))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Context shape validation (2026-05-13 — Problem B fix)
# ---------------------------------------------------------------------------

def _validate_context_shape(
    trigger: str, context: Any, user_id: str
) -> str | None:
    """Validate that the context bag matches one of three valid shapes.

    Returns None when valid; returns a short reason string when invalid.
    Callers (i.e., invoke_reviewer) log the reason and return None instead
    of waking the Reviewer with an empty user message.

    Why this exists. Python dicts are stringly-typed; the dispatcher and
    the Reviewer historically named the same data with different keys
    (commit e55d201 fixed `prompt`/`slug` vs `recurrence_prompt`/`recurrence_slug`
    mismatch). The bug surfaced because nothing asserted the shape —
    the model was forgiving, fires logged, costs accrued, the system
    looked healthy from the audit-log layer. This validator fails loudly
    on shape violation so the next instance of the same bug class
    surfaces immediately.

    The three valid shapes are derived from the three trigger sub-shapes
    `_build_user_message` knows how to construct:

      1. proposal-arrival (trigger="reactive"):
         REQUIRES proposal_row to be a non-empty dict.
      2. recurrence-fire (trigger="reactive"):
         REQUIRES BOTH recurrence_prompt (non-empty str) AND
         recurrence_slug (non-empty str).
      3. addressed (trigger="addressed"):
         REQUIRES user_message (non-empty str).

    A context that satisfies neither (1) nor (2) when trigger=reactive,
    or doesn't satisfy (3) when trigger=addressed, is rejected.
    """
    if not isinstance(context, dict):
        return f"context must be a dict, got {type(context).__name__}"

    if trigger == "reactive":
        # Shape 1: proposal-arrival
        proposal_row = context.get("proposal_row")
        has_proposal = isinstance(proposal_row, dict) and bool(proposal_row)
        # Shape 2: recurrence-fire
        rec_prompt = context.get("recurrence_prompt")
        rec_slug = context.get("recurrence_slug")
        has_recurrence = (
            isinstance(rec_prompt, str) and bool(rec_prompt.strip())
            and isinstance(rec_slug, str) and bool(rec_slug.strip())
        )

        if has_proposal and has_recurrence:
            return (
                "ambiguous reactive context: both proposal_row and "
                "recurrence_prompt/recurrence_slug present. Callers must "
                "choose exactly one sub-shape."
            )
        if not has_proposal and not has_recurrence:
            return (
                "reactive trigger requires either proposal_row (proposal-"
                "arrival) or recurrence_prompt+recurrence_slug (recurrence-"
                f"fire). Got context keys: {sorted(context.keys())}"
            )
        return None

    if trigger == "addressed":
        msg = context.get("user_message")
        if not (isinstance(msg, str) and msg.strip()):
            return (
                "addressed trigger requires non-empty user_message. "
                f"Got context keys: {sorted(context.keys())}"
            )
        return None

    return f"unknown trigger value: {trigger!r}"


# ---------------------------------------------------------------------------
# Public entry point — invoke_reviewer (ADR-258)
# ---------------------------------------------------------------------------

async def invoke_reviewer(
    client: Any,
    user_id: str,
    *,
    trigger: Literal["addressed", "reactive"],
    context: ReviewerContext,
    invocation_id: str,
    event_callback: Any = None,
) -> ReviewerOutput | None:
    """Unified Reviewer invocation — ADR-258 (revised) + ADR-260 D2 + ADR-263.

    Reviewer is a chat-mode caller of the canonical primitive registry.
    Tool surface = curated REVIEWER_PRIMITIVES + ReturnVerdict. Tool-use loop
    bounded at 12 rounds for addressed, 3 for reactive (ADR-260 D8).

    Safety story (ADR-293): attribution (ADR-209 authored substrate) +
    revision chain + uniform AUTONOMY-mode gating (capital + substrate via
    should_auto_apply) + 3-file governance lock (AUTONOMY.md / _autonomy.yaml
    / _token_budget.yaml — paths the Reviewer cannot author because editing
    them would grant the Reviewer unauthorized authority). Not access control;
    not blanket lock. Everything else operational + revertable.

    Two triggers (ADR-260 D2 amended by ADR-263 D2):
    - `addressed` — operator addressed the Reviewer (chat turn).
    - `reactive`  — substrate event requires judgment. Two sub-shapes,
                    differentiated by context-bag contents:
                      • Proposal arrival (proposal_row in context).
                      • Judgment-mode recurrence fire (recurrence_prompt in context;
                        per ADR-263, mechanical-mode recurrences do NOT invoke
                        the Reviewer — they execute deterministic primitives).

    Cron is part of the environment that fires recurrences; the recurrence's
    `mode` field declares whether the fire wakes the Reviewer (judgment) or
    runs as deterministic Python (mechanical). The Reviewer never sees the
    `scheduled` trigger value because cron-fired Reviewer wakes are now
    `reactive` (ADR-263 D2 amendment).

    Model selection by trigger:
    - Sonnet (capital decisions): reactive proposals
    - Haiku  (reasoning):         addressed + reactive recurrences

    Optional `event_callback`: an async callable `(event_dict) -> None` that
    fires progressively as the loop advances — once per round_start, once
    per tool_call, once per round_end. Used by chat.py to stream live
    progress to the operator (so the UI doesn't go silent during the loop).

    Never raises. Returns None on total failure.
    """
    # Contract enforcement (2026-05-13 — Problem B fix).
    # The dispatcher↔Reviewer key-drift bug (commit e55d201) lived for days
    # because nothing asserted the context shape — silent fallback turned a
    # malformed call into an inert stand_down. Reject malformed shapes
    # loudly at the boundary instead of waking the LLM with an empty
    # user message and burning tokens to produce a useless verdict.
    shape_error = _validate_context_shape(trigger, context, user_id)
    if shape_error:
        logger.error(
            "[REVIEWER] context shape violation user=%s trigger=%s: %s",
            user_id[:8] if user_id else "?", trigger, shape_error,
        )
        return None

    from services.primitives.registry import REVIEWER_PRIMITIVES, execute_primitive
    from types import SimpleNamespace

    # ADR-260 D2 + D8 + ADR-263 D2: model + round-bound selection.
    #
    # `reactive` covers two sub-shapes (per `_build_user_message` differentiation):
    #   - proposal arrival → Sonnet (capital judgment, discrete decision call)
    #   - judgment-recurrence fire → Haiku (longer real-time loop, similar
    #     to the previous `scheduled` trigger that ADR-263 D2 collapsed in)
    # `addressed` always uses Haiku (operator chat turn).
    #
    # Sub-shape detection mirrors the pattern in `_build_user_message`:
    # presence of `recurrence_prompt`/`recurrence_slug` keys = recurrence fire.
    is_recurrence_fire = bool(
        context.get("recurrence_prompt") or context.get("recurrence_slug")
    ) if isinstance(context, dict) else False

    use_sonnet = (trigger == "reactive") and not is_recurrence_fire
    model = _SONNET if use_sonnet else _HAIKU
    caller = _CALLER_SONNET if use_sonnet else _CALLER_HAIKU

    # Build auth namespace with reviewer_caller flag — handlers consult this
    # for ADR-258 D9 lock enforcement on operator-shared substrate.
    # `recurrence_options` carries the recurrence YAML's `options` block
    # (whatever the operator declared) through to downstream primitives.
    # Specifically `handle_dispatch_specialist` reads `max_rounds` from
    # here to honor per-recurrence round budgets (heavy work like
    # falsify-signals or 5-ticker track-universe needs > the global
    # default of 5).
    recurrence_options = {}
    if isinstance(context, dict):
        raw = context.get("options")
        if isinstance(raw, dict):
            recurrence_options = raw
    # ADR-288 D1: caller_identity is the canonical attribution source for
    # every substrate write made during this Reviewer wake. The Schedule
    # primitive's per-call injection at the dispatch loop (pre-ADR-288) is
    # superseded — substrate primitives default authored_by from
    # auth.caller_identity (ADR-288 D2). reviewer_caller=True is preserved
    # for ADR-258 D9 lock enforcement (separate concern: locks read paths
    # against the caller-class flag, not the attribution string).
    auth = SimpleNamespace(
        client=client,
        user_id=user_id,
        caller_identity=f"reviewer:{REVIEWER_MODEL_IDENTITY}",
        reviewer_caller=True,
        agent=None,
        agent_slug=None,
        task_slug=None,
        recurrence_options=recurrence_options,
    )

    # Tool list = curated reviewer primitives + ReturnVerdict (ADR-258 revised)
    tools = list(REVIEWER_PRIMITIVES) + [RETURN_VERDICT_TOOL]

    async def _emit(event: dict) -> None:
        """Best-effort progress emit — never raises, never blocks the loop.
        Callers can inspect events to surface progress in the UI without
        blocking the LLM cycle."""
        if event_callback is None:
            return
        try:
            await event_callback(event)
        except Exception as cb_exc:
            logger.debug("[REVIEWER] event_callback raised: %s", cb_exc)

    try:
        user_message = _build_user_message(trigger, context)
        messages: list[dict] = [{"role": "user", "content": user_message}]
        actions_taken: list[dict] = []
        verdict_raw: dict | None = None

        # ADR-260 D8 + ADR-263 + 2026-05-21 population audit
        # (docs/observations/2026-05-21-014009-reviewer-round-budget-population-
        # audit/): round bound varies by sub-shape.
        # - Proposal-arrival reactive (Sonnet) is a discrete decision call → 3 rounds.
        # - Recurrence-fire reactive (Haiku) needs room for read-heavy hook
        #   prompts (e.g. pre-ship-audit reads 8+ files before writing) → 20
        #   rounds (raised from 12 after population audit showed 70% silent
        #   rate at round 6 due to a mid-loop nudge that has since been deleted).
        # - Addressed (Haiku) is a chat turn with full tool budget → 20 rounds.
        #
        # Trust-the-model philosophy (Claude Code-aligned): set the budget as
        # a COST CEILING, not a behavioral constraint. The model decides when
        # it's done via ReturnVerdict; the budget caps cost-per-wake. The
        # fallback at line ~1530 (verdict_raw is None) is the safety net for
        # the rare case the model truly can't synthesize within budget.
        max_rounds = 3 if use_sonnet else 20
        total_input = 0
        total_output = 0
        total_cache_read = 0
        total_cache_create = 0
        rounds_used = 0

        for _round in range(max_rounds):
            rounds_used = _round + 1
            # Commit H (2026-05-11): cooperative cancellation check between
            # rounds. When the operator clicks Stop in the feed composer,
            # the FE POSTs /api/feed/cancel which sets
            # chat_sessions.cancellation_requested=true on the workspace's
            # active session. We check it here at the top of every round
            # (not inside a single LLM call — that's not interruptible).
            # On cancel: exit early with stand_down verdict; the caller
            # then resets the flag for the next session.
            if _check_session_cancellation(client, user_id):
                logger.info(
                    "[REVIEWER] cancellation_requested honored at round %d/%d trigger=%s user=%s",
                    rounds_used, max_rounds, trigger, user_id[:8],
                )
                _clear_session_cancellation(client, user_id)
                return ReviewerOutput(
                    verdict="stand_down",
                    reasoning="Operator interrupted the in-flight Loop via the Stop affordance. No further actions taken in this session.",
                    confidence="high",
                    actions_taken=actions_taken,
                    invocation_id=invocation_id,
                    input_tokens=total_input,
                    output_tokens=total_output,
                    cache_read_tokens=total_cache_read,
                    cache_create_tokens=total_cache_create,
                    model=model,
                    tool_rounds=rounds_used,
                )
            tool_choice = {"type": "any"} if _round == 0 else {"type": "auto"}
            await _emit({"phase": "round_start", "round": rounds_used, "trigger": trigger})

            response = await chat_completion_with_tools(
                messages=messages,
                system=_system_prompt(),
                tools=tools,
                model=model,
                max_tokens=2048,
                tool_choice=tool_choice,
            )

            usage = response.usage or {}
            total_input += int(usage.get("input_tokens", 0) or 0)
            total_output += int(usage.get("output_tokens", 0) or 0)
            # Anthropic native names — same shape as services/anthropic.py
            # surfaces. F1 (2026-05-17): denormalize into execution_events
            # via ReviewerOutput so slug-indexed reads see cache discount.
            total_cache_read += int(usage.get("cache_read_input_tokens", 0) or 0)
            total_cache_create += int(usage.get("cache_creation_input_tokens", 0) or 0)

            tool_uses = response.tool_uses or []

            # Append assistant turn for multi-round history
            assistant_content: list[dict] = []
            for block in (response.content or []):
                btype = getattr(block, "type", None)
                if btype == "text":
                    assistant_content.append({"type": "text", "text": getattr(block, "text", "")})
                elif btype == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": getattr(block, "id", ""),
                        "name": getattr(block, "name", ""),
                        "input": getattr(block, "input", {}),
                    })
            if assistant_content:
                messages.append({"role": "assistant", "content": assistant_content})

            if not tool_uses:
                # Text-only response — fallback to stand_down with the text as reasoning
                text_fallback = (response.text or "").strip()
                if text_fallback:
                    logger.warning(
                        "[REVIEWER] text-only response round %d trigger=%s user=%s",
                        _round, trigger, user_id[:8],
                    )
                    verdict_raw = {
                        "verdict": "stand_down",
                        "reasoning": text_fallback[:1000],
                        "confidence": "medium",
                    }
                break

            tool_results: list[dict] = []
            clarify_called_this_round = False
            for tu in tool_uses:
                name = tu.name
                inp = tu.input or {}
                tu_id = tu.id

                if name == "ReturnVerdict":
                    verdict_raw = inp
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu_id,
                        "content": "Verdict recorded.",
                    })
                    break

                # Emit tool_start for UI progress before dispatch
                await _emit({
                    "phase": "tool_start",
                    "round": rounds_used,
                    "tool": name,
                    "input": inp,
                })

                # ADR-288 D3: Schedule-specific authored_by injection DELETED.
                # auth.caller_identity (set at construction time per D1)
                # propagates through execute_primitive → Schedule's
                # `authored_by or auth.caller_identity` default-resolution
                # (parallel pattern to handle_write_file ADR-288 D2). One
                # canonical declaration replaces three compensating sites.
                # LLM-supplied authored_by still wins when explicitly passed.

                # Dispatch through canonical primitive registry
                try:
                    result = await execute_primitive(auth, name, inp)
                except Exception as exc:
                    result = {"success": False, "error": "execution_error", "message": str(exc)}

                # Capture proposal_id from ProposeAction results so the
                # downstream narration emit (surface_reviewer_actions) can
                # render an inline ProposalCard chip per Audit-pass-2 DD-4.
                # Pre-2026-05-11, narration was plain-text and operators had
                # to mentally stitch from the feed entry to the cockpit Queue
                # to find the proposal — mental-thread broken.
                action_record: dict = {
                    "tool": name,
                    "input": inp,
                    "success": bool(result.get("success", True)) if isinstance(result, dict) else True,
                    "summary": _summarize_result(result),
                    # ADR-289 D4: stamp the invocation atom id on every
                    # action record. Downstream surfacing (surface_reviewer_actions)
                    # reads this to propagate metadata.invocation_id onto every
                    # narrative entry produced during this cycle. One invocation,
                    # one shared id, N grouped narrative rows on the Feed surface.
                    "invocation_id": invocation_id,
                }
                if name == "ProposeAction" and isinstance(result, dict):
                    pid = result.get("proposal_id") or (
                        result.get("proposal", {}) or {}
                    ).get("id")
                    if pid:
                        action_record["proposal_id"] = pid
                actions_taken.append(action_record)

                await _emit({
                    "phase": "tool_end",
                    "round": rounds_used,
                    "tool": name,
                    "input": inp,  # ADR-289 Phase 2a: needed by the live
                                   # narration site in routes/feed.py to
                                   # classify mirror-refresh SyncPlatformState
                                   # calls via is_mirror_refresh_action.
                                   # ADR-296 v2 D3: the FireInvocation branch
                                   # of that classifier dissolved when
                                   # FireInvocation left REVIEWER_PRIMITIVES.
                    "success": actions_taken[-1]["success"],
                    "summary": actions_taken[-1]["summary"],
                })

                # Compact result for the model — limit size
                result_text = _compact_result_for_model(result)
                logger.info(
                    "[REVIEWER] tool=%s trigger=%s user=%s success=%s",
                    name, trigger, user_id[:8],
                    actions_taken[-1]["success"],
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu_id,
                    "content": result_text,
                })

                if name == "Clarify":
                    clarify_called_this_round = True

            if verdict_raw is not None:
                break

            # Loop-shape nudge (signal-based, not counter-based per 2026-05-21
            # population audit docs/observations/2026-05-21-014009-reviewer-
            # round-budget-population-audit/):
            #
            # After Clarify the operator's question has been surfaced and the
            # turn should close so the operator can respond. This nudge fires
            # only after the Reviewer has called Clarify in the current round
            # — it's a signal-based stop condition, parallel to Claude Code's
            # "repeated identical action" pattern.
            #
            # The previous round-counter-based nudge (`elif _round >= 4`) was
            # DELETED 2026-05-21 because population data showed it was solving
            # a problem we don't have (zero wakes reached round 11+ in N=28
            # history) while causing the problem we do have (70% silent rate
            # at round 6 due to its "stand_down is correct" invitation). Trust-
            # the-model philosophy: the budget is the cost ceiling, the
            # ReturnVerdict tool is the model's voluntary completion signal,
            # the fallback at `if verdict_raw is None` (line ~1530) is the
            # safety net for the rare in-budget-but-can't-synthesize case.
            nudge: str | None = None
            if clarify_called_this_round:
                nudge = (
                    "Your Clarify question has been surfaced to the operator. "
                    "Now call ReturnVerdict(verdict='stand_down', reasoning='[your "
                    "persona-voice summary including the question you asked]', "
                    "confidence='medium') to close this turn. The operator will "
                    "respond on a subsequent turn."
                )

            if tool_results:
                # Append nudge as a text block alongside tool_result blocks so the
                # model sees it as part of the user turn. tool_use_id cannot be
                # synthesized — must reference a real tool_use block — so the
                # nudge rides as a separate text block in the same user message.
                content_blocks: list[dict] = list(tool_results)
                if nudge:
                    content_blocks.append({"type": "text", "text": nudge})
                messages.append({"role": "user", "content": content_blocks})

        # ADR-291: cost ledger write happens downstream in the dispatcher via
        # `record_execution_event()`, fed by the cost/token fields on
        # `ReviewerOutput` (below). Removing the duplicate `token_usage` write
        # collapses the dual-ledger architecture; the dispatcher's slug-indexed
        # `execution_events` row is now the sole authoritative record.

        if verdict_raw is None:
            # Loop exhausted without ReturnVerdict — construct fallback from last text
            last_text = ""
            for m in reversed(messages):
                if m.get("role") != "assistant":
                    continue
                for block in (m.get("content") or []):
                    if isinstance(block, dict) and block.get("type") == "text":
                        last_text = block.get("text", "")
                        if last_text:
                            break
                if last_text:
                    break
            logger.warning(
                "[REVIEWER] no ReturnVerdict after %d rounds trigger=%s user=%s",
                max_rounds, trigger, user_id[:8],
            )
            verdict_raw = {
                "verdict": "stand_down",
                "reasoning": last_text or (
                    "I was unable to reach a verdict within my round budget. "
                    "Substrate may need refresh — fire track-universe or signal-evaluation."
                ),
                "confidence": "low",
            }

        verdict = verdict_raw.get("verdict", "")
        reasoning = (verdict_raw.get("reasoning") or "").strip()
        confidence = verdict_raw.get("confidence") or "low"

        _VALID_VERDICTS = {
            "approve", "reject", "defer",
            "no_change", "narrow", "relax", "character_note", "pause_autonomy",
            "stand_down",
        }
        if verdict not in _VALID_VERDICTS:
            logger.warning(
                "[REVIEWER] invalid verdict=%r trigger=%s user=%s", verdict, trigger, user_id[:8],
            )
            return None
        if not reasoning:
            logger.warning(
                "[REVIEWER] empty reasoning trigger=%s user=%s", trigger, user_id[:8],
            )
            return None

        output: ReviewerOutput = {
            "verdict": verdict,
            "reasoning": reasoning,
            "confidence": confidence,
            "actions_taken": actions_taken,
            # ADR-289 D4: invocation atom id, propagated from caller, surfaced
            # so the dispatcher can stamp the same id on the verdict-row write
            # (write_reviewer_message) and the FE can group every row produced
            # by this cycle under one invocation card.
            "invocation_id": invocation_id,
            # ADR-291: telemetry pass-through (single-ledger). The dispatcher
            # reads these off and forwards into `record_execution_event` — the
            # sole authoritative cost ledger write per the unified-cost-ledger
            # decision (replaces the prior dual write to `token_usage`).
            "input_tokens": total_input,
            "output_tokens": total_output,
            "cache_read_tokens": total_cache_read,
            "cache_create_tokens": total_cache_create,
            "model": model,
            "tool_rounds": rounds_used,
        }

        # Under ADR-263's two-trigger model, reflection-shaped output fields
        # (`proposals`, `evidence_summary`) may appear on any reactive
        # invocation whose recurrence prompt directs the Reviewer to author
        # proposals or summarize evidence. The gate is "model returned the
        # field," not "trigger == reflection" (which is a dead enum value
        # post-collapse). Older callers relying on field-presence to detect
        # reflection-shaped output continue to work.
        if verdict_raw.get("proposals") or verdict_raw.get("evidence_summary"):
            from agents.reviewer_agent_compat import _normalize_reflection_proposals
            if verdict_raw.get("proposals"):
                output["proposals"] = _normalize_reflection_proposals(verdict_raw.get("proposals") or [])
            if verdict_raw.get("evidence_summary"):
                output["evidence_summary"] = (verdict_raw.get("evidence_summary") or "").strip()

        return output

    except Exception as exc:
        logger.error(
            "[REVIEWER] invoke_reviewer failed trigger=%s user=%s: %s",
            trigger, user_id[:8] if user_id else "?", exc,
        )
        return None


def _summarize_result(result: Any) -> str:
    """One-line summary of a primitive result for actions_taken audit log.

    Field-preference order is semantic-first: when a result carries multiple
    discriminators, prefer the one that distinguishes this action from a
    sibling action of the same tool.

      1. action + slug     (Schedule / ManageHook — two writes to the same
                            file with distinct recurrence/hook slugs look
                            identical when summarized by path alone)
      2. proposal_id       (ProposeAction — every proposal is a distinct
                            decision; prefer the proposal identity)
      3. slug              (any slug-bearing result without an action
                            verb — e.g. FireInvocation in CHAT_PRIMITIVES
                            per ADR-296 v2 D3, no longer in REVIEWER_PRIMITIVES)
      4. path              (WriteFile etc. — terminal fallback)

    Closes Pattern 3 of docs/observations/2026-05-21-005856-wake-duplication-
    audit/findings.md — pre-fix the helper checked `path` first, collapsing
    distinct Schedule calls (weekly-corpus-review vs quarterly-voice-audit)
    to identical `path=/workspace/_recurrences.yaml` summaries that looked
    like duplicate actions in the feed.
    """
    if not isinstance(result, dict):
        return "ok"
    if result.get("success") is False:
        return f"error: {result.get('error') or 'unknown'}"
    # Slug + action verb together — the strongest discriminator for
    # lifecycle primitives (Schedule / ManageHook). Two distinct slugs
    # at the same path render with distinct summaries.
    if "slug" in result and "action" in result:
        return f"action={result['action']} slug={result['slug']}"
    if "proposal_id" in result:
        return f"proposal_id={result['proposal_id'][:8]}..."
    if "slug" in result:
        return f"slug={result['slug']}"
    if "path" in result:
        return f"path={result['path']}"
    return "ok"


def _compact_result_for_model(result: Any) -> str:
    """Compact a primitive result for tool_result content sent back to the model.
    Limits content size so a large file read doesn't blow the round budget."""
    import json as _json
    if isinstance(result, dict):
        # If there's a 'content' field (from ReadFile), truncate generously
        if "content" in result and isinstance(result["content"], str):
            content = result["content"]
            if len(content) > 6000:
                content = content[:6000] + f"\n\n_(truncated from {len(result['content'])} chars)_"
            shaped = {**result, "content": content}
            return _json.dumps(shaped, default=str)[:8000]
        return _json.dumps(result, default=str)[:8000]
    return str(result)[:8000]


# ---------------------------------------------------------------------------
# Cooperative cancellation (Commit H.1, 2026-05-11)
# ---------------------------------------------------------------------------
#
# Two helpers used by invoke_reviewer's per-round cancellation check (Mode 1
# of the interruption surface). The flag lives on chat_sessions
# (migration 173); operator's POST /api/feed/cancel sets it; the Reviewer
# checks + clears it.
#
# Design choice: we look up the operator's *active workspace session* (same
# function reviewer_chat_surfacing uses) rather than threading a session_id
# parameter through every Reviewer call site. The Reviewer doesn't know
# which session it's running on behalf of — that's the orchestration
# context. Looking up the active session at check time matches how
# narration emits work too.
#
# Failure discipline: any exception (Supabase blip, no active session, etc.)
# → returns False (no cancellation). Cancellation is best-effort safety,
# never blocks the Loop on errors.

def _check_session_cancellation(client: Any, user_id: str) -> bool:
    """Return True iff the operator's active session has cancellation_requested=true."""
    if not user_id:
        return False
    try:
        from services.narrative import find_active_workspace_session
        session_id = find_active_workspace_session(client, user_id)
        if not session_id:
            return False
        result = (
            client.table("chat_sessions")
            .select("cancellation_requested")
            .eq("id", session_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return False
        return bool(rows[0].get("cancellation_requested", False))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[REVIEWER] cancellation check failed: %s", exc)
        return False


def _clear_session_cancellation(client: Any, user_id: str) -> None:
    """Reset the cancellation flag after honoring it. Best-effort; never raises."""
    if not user_id:
        return
    try:
        from services.narrative import find_active_workspace_session
        session_id = find_active_workspace_session(client, user_id)
        if not session_id:
            return
        client.table("chat_sessions").update(
            {"cancellation_requested": False}
        ).eq("id", session_id).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[REVIEWER] cancellation clear failed: %s", exc)


# read_signal_files() relocated to services/reviewer_envelope.py per ADR-280
# Stream A. The function is kernel-internal envelope-summarizer infrastructure
# — bundles reference it by name in their MANIFEST `substrate_abi.reviewer_wake_envelope`
# declarations; the kernel hosts the implementation. New name + module:
# `services.reviewer_envelope.ENVELOPE_SUMMARIZERS["signal_files"]` (a.k.a.
# `_summarize_signal_files`). The relocation makes path_glob parametric so
# the summarizer is no longer alpha-trader-hardcoded; bundles declare their
# own glob (e.g., `context/trading/signals/*.yaml`).
