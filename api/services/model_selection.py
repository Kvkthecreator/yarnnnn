"""Model SELECTION — which model serves each Freddie trigger shape (ADR-402).

⚠️ TWO MODULES, ONE JOB EACH (ADR-463 D1.a — this file was `model_routing.py`
until 2026-07-16, one letter from `model_router.py` and never touching it):

    services/model_selection.py  (this file) — WHICH model, for which wake.
    services/model_router.py                 — HOW to call any model (LiteLLM
                                               transport, provider-blind).

They COMPOSE: selection names, transport calls. The old name made them read as
rivals; a session reaching for one kept landing in the other.

Which model tier + round budget serves each trigger shape is a routing
DECISION — kernel config (data), not behavior scattered through the occupant's
tool-use loop. Before ADR-402 the selection lived as two hardcoded constants +
an inline branch in `agents/freddie_agent.py` (`use_sonnet = trigger ==
"reactive" and not is_recurrence_fire`); this module replaces that with one
table so:

- the production routing is legible + auditable in one place,
- a deployment can override any cell by env var (no redeploy-to-experiment —
  the Part-B tier probes flip env vars against the same code),
- the provider-optionality boundary holds: model ids live ONLY here; the
  Anthropic client usage stays inside the occupant module; nothing outside
  `freddie_agent.py` branches on model. The ADR-315 occupant contract
  (`agents/occupant_contract.py`) remains the seam a future non-Anthropic
  occupant implements — this is deliberately a TABLE, not a provider
  abstraction.

WHY THE VALUES CARRY PROVIDER PREFIXES (ADR-463 D1). They were bare Anthropic
ids (`claude-sonnet-4-6`) — so the module whose ADR says "model routing is
kernel DATA" could not spell a foreign model, and `YARNNN_MODEL_ADDRESSED=
gemini/gemini-2.5-pro` would have been read from env and handed to the Anthropic
SDK. **A dial whose every position is the same vendor is not a dial.** The
prefix is the `provider/model` form LiteLLM and `LANE_MODELS` already speak.

⚠️ AND WHAT IT DOES *NOT* MEAN. Freddie still calls Anthropic DIRECTLY, by
decision, not by debt (ADR-463 D3): it uses `cache_control: ephemeral` (prompt
caching — the saving accrues as platform margin, ADR-363) and beta
`context_management`, and `model_router.py` carries NEITHER. Routing Freddie
through the transport today would silently drop prompt caching on the system's
most frequent LLM call — a cost regression wearing an architecture win. The
prefix makes the table HONEST and the dial REAL; `strip_provider` is what keeps
the Anthropic SDK fed until the transport can serve this caller without loss.

Trigger shapes (the routing key — ADR-263's two triggers, with reactive split
by its two context sub-shapes exactly as `invoke_freddie` differentiates them):

- ``addressed``  — operator chat turn (`trigger="addressed"`).
- ``proposal``   — reactive wake WITHOUT recurrence keys (proposal arrival,
  substrate-event review — the discrete decision call).
- ``recurrence`` — reactive wake WITH `recurrence_prompt`/`recurrence_slug`
  (judgment-recurrence fire — the read-heavy real-time loop).

`max_rounds` is a COST CEILING, not a behavioral constraint (trust-the-model,
Claude Code-aligned): the model decides when it's done via ReturnVerdict; the
budget caps cost-per-wake. History: 20 was raised from 12 after the 2026-05-21
round-budget population audit (70% silent rate at round 6 under a since-deleted
mid-loop nudge); 3 on proposals predates ADR-403's thin envelope and is
re-examined by the ADR-402 Part-B tier experiment.

Env overrides (read at resolve time, per deployment):

- ``YARNNN_MODEL_{SHAPE}``  — model id override for that shape.
- ``YARNNN_ROUNDS_{SHAPE}`` — round-ceiling override (positive int).

e.g. ``YARNNN_MODEL_ADDRESSED=claude-sonnet-4-6`` routes operator chat to
Sonnet without touching code.

The occupant's static self-identity (`FREDDIE_MODEL_IDENTITY`, ADR-315) is NOT
derived per-wake from this table: identity names the occupant VERSION (seat
rotation protocol); the model actually used on an invocation is recorded
honestly in `execution_events.model` (a real column since migration 204,
2026-07-06 — before that the kwarg fed only the rate lookup). One identity,
one ledger — no per-wake attribution fragmentation.
"""

from __future__ import annotations

import logging
import os
from typing import NamedTuple

logger = logging.getLogger(__name__)


class ModelRoute(NamedTuple):
    model: str
    max_rounds: int


#: The three routing shapes. String values double as env-var suffixes.
SHAPE_ADDRESSED = "addressed"
SHAPE_PROPOSAL = "proposal"
SHAPE_RECURRENCE = "recurrence"

#: The production routing table — the ONLY place model ids appear on the
#: Freddie occupant path (gate: test_adr402_model_selection.py).
#:
#: ADR-402 Part B decision (2026-07-03, stabilization prior): ONE model for
#: all shapes. Evidence (docs/evaluations/2026-07-03-rung4-part{A,B}-*):
#: Sonnet 6/6 first-pass vs Haiku's stochastic silent exit; Sonnet caught the
#: seeded attribution mismatch Haiku missed (Haiku claimed "well-attributed"
#: — a false report); Sonnet deduped against the pending proposal queue where
#: Haiku re-proposed; HALF the tool rounds (mean 3.3 vs 6.2), so observed
#: cost/turn was 1.4x, not the 3x sticker. The pre-table Sonnet/3 proposal
#: split was retired: proposal_arrival has zero live fires ever, and the
#: 3-round cap was a behavioral constraint contradicting trust-the-model —
#: the ceiling is now uniform (the verdict-early ask rule is the proposal
#: behavior control, ADR-403).
#:
#: ADR-463 D1: values are `provider/model` — the form LiteLLM, `LANE_MODELS`,
#: and the Agent registry already speak. At N=1 this is byte-identical
#: (`strip_provider` feeds the Anthropic SDK the same id it got before); what
#: changes is that the table can now NAME a model it does not yet call.
DEFAULT_ROUTES: dict[str, ModelRoute] = {
    SHAPE_ADDRESSED: ModelRoute(model="anthropic/claude-sonnet-4-6", max_rounds=20),
    SHAPE_PROPOSAL: ModelRoute(model="anthropic/claude-sonnet-4-6", max_rounds=20),
    SHAPE_RECURRENCE: ModelRoute(model="anthropic/claude-sonnet-4-6", max_rounds=20),
}


#: `anthropic/claude-sonnet-4-6` → `claude-sonnet-4-6` — the seam between the
#: table's honest name and a provider SDK that wants its own bare id. Freddie
#: calls Anthropic directly (ADR-463 D3: prompt caching the transport cannot
#: carry), so it selects a prefixed id and strips it at the call.
#:
#: WHERE THIS LIVES, AND WHY NOT IN model_router.py. `ledger_model_name` there
#: does the identical split, and re-exporting it was the first attempt — it is
#: the Singular-Implementation move. It was REVERSED: it puts
#: `services.model_router` on Freddie's import path, and ADR-408 D4 is explicit
#: that **Altitude 1 never routes** (model_router.py's own header: "freddie_agent
#: must never import this module"). An architectural boundary outranks
#: de-duplicating a one-line string split.
#:
#: So the split lives HERE, in the module both sides already depend on for the
#: prefix convention, and `model_router.ledger_model_name` delegates to it —
#: one implementation, no boundary crossed, and the dependency points the way
#: the altitudes already do (transport may know selection; selection must not
#: know transport).
#:
#: NOT a shim to remove later: a vendor SDK naming its own models without a
#: prefix is correct on its side of the seam.
def strip_provider(model: str) -> str:
    """`anthropic/claude-sonnet-4-6` → `claude-sonnet-4-6`; bare names pass
    through. The seam between the table's honest name and a provider SDK that
    wants its own bare id. Pure."""
    return model.split("/", 1)[1] if "/" in model else model


def classify_shape(trigger: str, is_recurrence_fire: bool) -> str:
    """Map (trigger, sub-shape) → routing shape.

    Mirrors the pre-ADR-402 branch exactly: only a reactive non-recurrence
    wake is a proposal; every non-reactive trigger routes as addressed
    (byte-identical to the legacy else-branch for any hypothetical future
    trigger value).
    """
    if trigger == "reactive":
        return SHAPE_RECURRENCE if is_recurrence_fire else SHAPE_PROPOSAL
    return SHAPE_ADDRESSED


def resolve_route(trigger: str, is_recurrence_fire: bool) -> ModelRoute:
    """Resolve the model + round ceiling for a wake. Env overrides are read
    at call time (not import time) so probes and deployments can flip a cell
    without process restart or code change."""
    shape = classify_shape(trigger, is_recurrence_fire)
    route = DEFAULT_ROUTES[shape]

    model = os.environ.get(f"YARNNN_MODEL_{shape.upper()}", "").strip() or route.model

    max_rounds = route.max_rounds
    raw_rounds = os.environ.get(f"YARNNN_ROUNDS_{shape.upper()}", "").strip()
    if raw_rounds:
        try:
            parsed = int(raw_rounds)
            if parsed >= 1:
                max_rounds = parsed
            else:
                logger.warning(
                    "[MODEL-ROUTING] YARNNN_ROUNDS_%s=%r ignored (must be >= 1)",
                    shape.upper(), raw_rounds,
                )
        except ValueError:
            logger.warning(
                "[MODEL-ROUTING] YARNNN_ROUNDS_%s=%r ignored (not an int)",
                shape.upper(), raw_rounds,
            )

    return ModelRoute(model=model, max_rounds=max_rounds)
