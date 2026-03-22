"""
Agent Framework — ADR-117 Phase 3 + ADR-126 Phase 5

Canonical registry for agent development mechanics. Determines what an agent
can do (duties), what tools it gets (output skills), how often it senses
(pulse cadence), and when it earns expanded responsibilities (seniority).

Key concepts:
  - Role: seed identity, never changes (digest, monitor, research, etc.)
  - Duty: a responsibility within the role — expands with seniority
  - Seniority: new → associate → senior (derived from feedback history)
  - Role Portfolio: pre-configured career track per role × seniority
  - Output Skills: RuntimeDispatch access per duty role (ADR-118)
  - Pulse Cadence: role-based sensing frequency (ADR-126)

Canonical reference: docs/architecture/agent-framework.md
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional, Union


# ---------------------------------------------------------------------------
# Output Skills — roles that get RuntimeDispatch access (ADR-118)
# ---------------------------------------------------------------------------
# When a duty fires, its role determines whether the agent gets SKILL.md
# injection and can invoke the render service. Moved here from
# agent_execution.py to be the single source of truth.
SKILL_ENABLED_ROLES = frozenset({"synthesize", "research", "monitor", "custom"})


# ---------------------------------------------------------------------------
# Role Pulse Cadence — how often each role type senses (ADR-126 Phase 5)
# ---------------------------------------------------------------------------
# The role defines the natural sensing pace. Think personification:
#   - monitor = watchdog → senses frequently (every 15 min)
#   - pm = coordinator → needs responsiveness (every 30 min)
#   - digest = summarizer → senses on daily rhythm
#   - synthesize = pattern-finder → senses on its delivery rhythm
#   - research = investigator → senses on its schedule
#   - prepare = pre-meeting worker → senses on daily rhythm
#   - custom = user-defined → defaults to schedule-derived
#
# pulse_cadence is the MAXIMUM interval between pulses. The agent's schedule
# (delivery rhythm) may be slower — that's fine. Pulse is about sensing,
# not generating. An agent that senses every 15 min but delivers daily
# will pulse frequently (Tier 1: cheap, zero LLM) and only generate
# when conditions are right.
#
# "schedule" means: use the agent's configured schedule as pulse cadence.
# This is the conservative default — the agent senses as often as it delivers.

ROLE_PULSE_CADENCE: dict[str, Union[timedelta, str]] = {
    "monitor":    timedelta(hours=1),      # Watchdog — hourly sensing (was 15min, relaxed for API cost)
    "pm":         timedelta(hours=2),      # Coordinator — bi-hourly (was 30min, relaxed for API cost)
    "digest":     timedelta(hours=12),     # Summarizer — senses twice per delivery cycle
    "synthesize": "schedule",              # Pattern-finder — senses on delivery rhythm
    "research":   "schedule",              # Investigator — senses on schedule
    "prepare":    timedelta(hours=12),     # Pre-meeting — senses twice daily
    "custom":     "schedule",              # User-defined — conservative default
}

# Fallback if role not in registry
_DEFAULT_PULSE_CADENCE = "schedule"


def get_pulse_cadence(role: str) -> Union[timedelta, str]:
    """Return the pulse cadence for a role.

    Returns a timedelta for fixed-interval roles, or "schedule" for
    roles that pulse on their delivery rhythm.
    """
    return ROLE_PULSE_CADENCE.get(role, _DEFAULT_PULSE_CADENCE)


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
