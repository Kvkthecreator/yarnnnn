"""The kernel Agent registry — named, pre-configured hands (ADR-460 D4).

WHY THIS EXISTS
The lane picker served `LANE_MODELS` as a <select> of engines: "Claude Sonnet |
Claude Haiku | GPT-4o mini | GPT-5 | Gemini Flash | Gemini Pro | DeepSeek".
That is a SPEC SHEET — it asks the member to know which engine is good at what,
before the first message, when they know least. LLM-routing is not a layman
concept; a pre-configured Agent is. So: the engine moves BEHIND a name, and the
question becomes one anyone can answer — who do you want to work with?

WHAT AN AGENT IS (ADR-460: one concept, independent facts, one gate)
A named, configured entity. Its facts are independent and optional:
attribution · configuration · standing intent · governance files. These kernel
Agents sit at exactly one point of that space: they attribute as the MEMBER
(`member:{id} via {model}` — ADR-411 D4), carry configuration, hold NO standing
intent, and carry NO governance files. They fire only when addressed.

WHAT AN AGENT IS NOT
- NOT a principal. No `principal_grants` row, never on the ADR-431 roster. The
  face is an Agent; the ledger says the member's hands. (ADR-408 D2's
  load-bearing claim, preserved on the vector rather than on a rung.)
- NOT a persona-agent seat (ADR-382 / Rung 2). The distinguishing fact is the
  ADR-307 consequential gate, NOT the presence of a proper noun. A named preset
  is not a seat.
- NOT standing intent. No wake source, no mandate, no autonomy dial.

⚠️ THE CLIFF — ADR-460 D3.a, MADE STRUCTURAL ⚠️
There is NO field here for consequential authority, and there must never be one.
Kernel Agents are addressed-only hands BY CONSTRUCTION: the authority is
UNREPRESENTABLE, not merely unset. An Agent that would take consequential
external action is not a registry row with a flag flipped — it needs the ADR-307
gate, a mandate, an autonomy dial, and a track record accruing on a clock we do
not control. Dissolving the A2/A3 ladder (ADR-460 D1) removed the vocabulary
that made this cliff visible; THIS ABSENCE is what bought that safety back.
**A session that adds an authority field to a row here has violated ADR-460.**
`test_agent_registry.py` is that ratchet.

THE PATTERN
Third instance of a twice-ratified shape: `LANE_MODELS` (ADR-411 D5) and
`DERIVE_RECIPES` (ADR-450) are both kernel-constant registries of pre-configured
work-shapes. ADR-450: "recipes are data, not sub-processes... versioned in this
codebase; when [agent-composed] arrives it composes BESIDE kernel recipes, never
replacing them." Per-workspace Agents are that later widening — forward-
compatible by construction, deliberately not built (ADR-222: the kernel names the
category, the instance comes later).

Spec: docs/analysis/agent-registry-spec-2026-07-16.md
"""

from __future__ import annotations

from typing import Any, Optional

#: The base set — "provide enough, not the most" (the ADR-420 §10 rule that
#: governs LANE_MODELS, applied one level up: one Agent per reason a member
#: would reach for a different colleague, NOT one per model that exists).
#: Seven engines is a spec sheet; three characters is a team.
#:
#: Agents are named for the WORK, never for the engine — the engine is the fact
#: BEHIND the name. (The one wart: "Sonnet" is an engine name. It stays as the
#: default's name because it is the workspace's incumbent default and the
#: operator already talks to it; renaming what you already know is a cost with
#: no payoff. Named as a wart, not defended — if a rename pass runs, this is
#: the row to fix.)
#:
#: Adding an Agent = a row here. Its `model` MUST be a LANE_MODELS key with a
#: billing rate (gate-asserted — the ADR-439 §4 rule: an unpriced model never
#: routes in prod).
KERNEL_AGENTS: dict[str, dict[str, Any]] = {
    "sonnet": {
        "slug": "sonnet",
        "name": "Sonnet",
        "blurb": "Thinks a problem through with you — writing, judgment, hard calls.",
        "icon": "brain",
        "model": "anthropic/claude-sonnet-4-6",
        "token_profile": 4096,
        "posture": (
            "You are Sonnet — the member's thinking partner. Reason carefully and "
            "say what you actually think, including when it cuts against what they "
            "hoped. Prefer the shortest honest answer over a complete one."
        ),
    },
    "scout": {
        "slug": "scout",
        "name": "Scout",
        "blurb": "Digs through material fast — lookups, quick reads, what does this say?",
        "icon": "compass",
        "model": "gemini/gemini-2.5-flash",
        "token_profile": 4096,
        "posture": (
            "You are Scout — the member's fast reader. Find what they asked for and "
            "report it plainly, with the exact source. Volume is your job; do not "
            "editorialize, and say 'not here' rather than guessing."
        ),
    },
    "critic": {
        "slug": "critic",
        "name": "Critic",
        "blurb": "Pressure-tests an idea — finds the hole before it costs you.",
        "icon": "swords",
        "model": "openai/gpt-5",
        "token_profile": 4096,
        "posture": (
            "You are Critic — the member's adversary, on their side. Your job is the "
            "strongest objection, not a balanced view: find the assumption that would "
            "sink this if it were wrong. If the idea survives, say so in one line and "
            "name what would still falsify it. Never flatter."
        ),
    },
}

#: The keys a registry row may carry. The gate asserts rows carry ONLY these —
#: which is what makes the cliff structural rather than documentary (see the
#: module header). `tools` is deliberately absent in v1: every lane gets the same
#: five file verbs (ADR-411 D3), and a per-Agent tool scope with exactly one
#: possible value is a field that lies about being a choice. It lands when a
#: second value exists.
AGENT_ROW_KEYS = frozenset(
    {"slug", "name", "blurb", "icon", "model", "token_profile", "posture"}
)


def get_agent(slug: str) -> Optional[dict]:
    """The Agent row for a slug, or None. Pure."""
    return KERNEL_AGENTS.get((slug or "").strip())


def list_agents() -> list[dict]:
    """The chooser payload — the member-facing face only.

    Deliberately does NOT serve `model`, `posture`, or `token_profile`: the
    picker's whole point is that the member is never ASKED to choose an engine.
    (The engine stays legible elsewhere — a lane reports the model it ran on;
    this is about what the CHOOSER asks, not about hiding a fact.)
    """
    return [
        {"slug": a["slug"], "name": a["name"], "blurb": a["blurb"], "icon": a["icon"]}
        for a in KERNEL_AGENTS.values()
    ]


def model_for_agent(slug: str) -> Optional[str]:
    """The engine behind the name, or None if the slug is unknown. Pure."""
    agent = get_agent(slug)
    return agent["model"] if agent else None


def build_agent_posture(slug: str) -> str:
    """The Agent's turn-time posture overlay, or "" when there is no Agent. Pure.

    Composed at turn time from the slug, never stored (the ADR-411 D6 pattern) —
    correct precisely BECAUSE a posture is not a historical fact about what ran.
    It is how this Agent works NOW, so it must follow the registry. The `model`
    is the opposite: it IS a historical fact, so it is persisted on the lane and
    never re-derived (see the spec §6).
    """
    agent = get_agent(slug)
    if not agent:
        return ""
    return f"\n\nWHO YOU ARE\n{agent['posture']}\n"
