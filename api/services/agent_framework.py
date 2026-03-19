"""
Agent Framework — ADR-117 Phase 3: Role Portfolios, Seniority & Duties

Canonical registry for agent development mechanics. Determines what an agent
can do (duties), what tools it gets (output skills), and when it earns
expanded responsibilities (seniority progression).

Key concepts:
  - Role: seed identity, never changes (digest, monitor, research, etc.)
  - Duty: a responsibility within the role — expands with seniority
  - Seniority: new → associate → senior (derived from feedback history)
  - Role Portfolio: pre-configured career track per role × seniority
  - Output Skills: RuntimeDispatch access per duty role (ADR-118)

Canonical reference: docs/architecture/agent-framework.md
"""

from typing import Optional


# ---------------------------------------------------------------------------
# Output Skills — roles that get RuntimeDispatch access (ADR-118)
# ---------------------------------------------------------------------------
# When a duty fires, its role determines whether the agent gets SKILL.md
# injection and can invoke the render service. Moved here from
# agent_execution.py to be the single source of truth.
SKILL_ENABLED_ROLES = frozenset({"synthesize", "research", "monitor", "custom"})


# ---------------------------------------------------------------------------
# Role Portfolios — pre-configured career tracks
# ---------------------------------------------------------------------------
# Deterministic, versioned, testable. Composer promotes along known tracks.
# Each entry: list of {duty, trigger} dicts available at that seniority.

ROLE_PORTFOLIOS = {
    "digest": {
        "new":       [{"duty": "digest",  "trigger": "recurring"}],
        "associate": [{"duty": "digest",  "trigger": "recurring"}],
        "senior":    [{"duty": "digest",  "trigger": "recurring"},
                      {"duty": "monitor", "trigger": "reactive"}],
    },
    "monitor": {
        "new":       [{"duty": "monitor", "trigger": "recurring"}],
        "associate": [{"duty": "monitor", "trigger": "recurring"}],
        "senior":    [{"duty": "monitor", "trigger": "recurring"},
                      {"duty": "act",     "trigger": "reactive"}],
    },
    "synthesize": {
        "new":       [{"duty": "synthesize", "trigger": "recurring"}],
        "associate": [{"duty": "synthesize", "trigger": "recurring"}],
        "senior":    [{"duty": "synthesize", "trigger": "recurring"},
                      {"duty": "research",   "trigger": "goal"}],
    },
    "research": {
        "new":       [{"duty": "research", "trigger": "goal"}],
        "associate": [{"duty": "research", "trigger": "goal"}],
        "senior":    [{"duty": "research", "trigger": "goal"},
                      {"duty": "monitor",  "trigger": "proactive"}],
    },
    "prepare": {
        "new":       [{"duty": "prepare", "trigger": "recurring"}],
        "associate": [{"duty": "prepare", "trigger": "recurring"}],
        "senior":    [{"duty": "prepare", "trigger": "recurring"}],
    },
    "pm": {
        "new":       [{"duty": "pm", "trigger": "proactive"}],
        "associate": [{"duty": "pm", "trigger": "proactive"}],
        "senior":    [{"duty": "pm", "trigger": "proactive"}],
    },
    "custom": {
        "new":       [{"duty": "custom", "trigger": "recurring"}],
        "associate": [{"duty": "custom", "trigger": "recurring"}],
        "senior":    [{"duty": "custom", "trigger": "recurring"}],
    },
}


# ---------------------------------------------------------------------------
# Seniority Classification
# ---------------------------------------------------------------------------

def classify_seniority(total_runs: int, approval_rate: float) -> str:
    """Derive seniority level from feedback history.

    Thresholds:
      senior:    ≥10 runs AND ≥80% approval
      associate: ≥5 runs AND ≥60% approval
      new:       everything else
    """
    if total_runs >= 10 and approval_rate >= 0.8:
        return "senior"
    if total_runs >= 5 and approval_rate >= 0.6:
        return "associate"
    return "new"


# ---------------------------------------------------------------------------
# Portfolio Queries
# ---------------------------------------------------------------------------

def get_eligible_duties(role: str, seniority: str) -> list[dict]:
    """Return all duties available for a role at the given seniority level."""
    portfolio = ROLE_PORTFOLIOS.get(role, {})
    return portfolio.get(seniority, portfolio.get("new", []))


def get_promotion_duty(
    role: str,
    seniority: str,
    current_duties: list[dict],
) -> Optional[dict]:
    """Return the next duty to promote, or None if already at full portfolio.

    Compares eligible duties at current seniority against current_duties.
    Returns the first eligible duty not yet held.
    """
    eligible = get_eligible_duties(role, seniority)
    current_duty_names = {d.get("duty") for d in (current_duties or [])}
    for duty in eligible:
        if duty["duty"] not in current_duty_names:
            return duty
    return None
