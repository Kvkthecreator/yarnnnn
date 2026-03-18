"""
ADR-111 Phase 3-5 Test Suite — Composer Heartbeat + Lifecycle Progression

Tests (no live LLM calls — pure logic validation):
  Phase 1: heartbeat_data_query() — DB queries, maturity signals
  Phase 2: should_composer_act() — trigger logic with synthetic assessments
  Phase 3: run_lifecycle_assessment() — underperformer pause, expansion, cross-agent
  Phase 4: run_composer_assessment() — routing to correct handler
  Phase 5: Cleanup

Strategy: Mix of real DB queries (heartbeat) and synthetic assessment dicts
(should_composer_act, lifecycle). No LLM calls.
Test agents use prefix TEST_ADR111_ for cleanup isolation.

Usage:
    cd api && python test_adr111_composer.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Test user
TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
TEST_PREFIX = "TEST_ADR111_"


# =============================================================================
# Result tracking (same pattern as test_adr110)
# =============================================================================

@dataclass
class PhaseResult:
    phase: str
    passed: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def ok(self, label: str) -> None:
        logger.info(f"    ✓ {label}")
        self.passed += 1

    def fail(self, label: str, detail: str = "") -> None:
        msg = f"{label}: {detail}" if detail else label
        logger.error(f"    ✗ {msg}")
        self.failed += 1
        self.errors.append(msg)

    @property
    def success(self) -> bool:
        return self.failed == 0


def assert_eq(r: PhaseResult, label: str, actual, expected) -> None:
    if actual == expected:
        r.ok(label)
    else:
        r.fail(label, f"expected {expected!r}, got {actual!r}")


def assert_true(r: PhaseResult, label: str, condition: bool, detail: str = "") -> None:
    if condition:
        r.ok(label)
    else:
        r.fail(label, detail)


def assert_in(r: PhaseResult, label: str, item, collection) -> None:
    if item in collection:
        r.ok(label)
    else:
        r.fail(label, f"{item!r} not in {collection!r}")


# =============================================================================
# Phase 1: heartbeat_data_query() — real DB queries
# =============================================================================

async def phase1_heartbeat_data_query(supabase) -> PhaseResult:
    """Test heartbeat_data_query returns well-structured assessment."""
    logger.info("\n[Phase 1] heartbeat_data_query()")
    r = PhaseResult("Heartbeat Data Query")

    from services.composer import heartbeat_data_query

    assessment = await heartbeat_data_query(supabase, TEST_USER_ID)

    # Top-level keys
    assert_in(r, "Has user_id", "user_id", assessment)
    assert_in(r, "Has timestamp", "timestamp", assessment)
    assert_in(r, "Has connected_platforms", "connected_platforms", assessment)
    assert_in(r, "Has platform_details", "platform_details", assessment)
    assert_in(r, "Has agents", "agents", assessment)
    assert_in(r, "Has coverage", "coverage", assessment)
    assert_in(r, "Has health", "health", assessment)
    assert_in(r, "Has maturity", "maturity", assessment)
    assert_in(r, "Has feedback", "feedback", assessment)
    assert_in(r, "Has tier", "tier", assessment)

    # Agents structure
    agents = assessment["agents"]
    assert_in(r, "agents.total exists", "total", agents)
    assert_in(r, "agents.active exists", "active", agents)
    assert_in(r, "agents.roles_present exists", "roles_present", agents)
    assert_in(r, "agents.active_list exists", "active_list", agents)
    assert_true(r, "agents.total >= 0", agents["total"] >= 0)

    # Coverage structure
    coverage = assessment["coverage"]
    assert_in(r, "coverage.platforms_with_digest", "platforms_with_digest", coverage)
    assert_in(r, "coverage.platforms_without_digest", "platforms_without_digest", coverage)

    # Maturity structure (Phase 5)
    maturity = assessment["maturity"]
    assert_in(r, "maturity.signals exists", "signals", maturity)
    assert_in(r, "maturity.mature_agents exists", "mature_agents", maturity)
    assert_in(r, "maturity.underperformers exists", "underperformers", maturity)
    assert_true(r, "maturity.signals is list", isinstance(maturity["signals"], list))

    # Verify maturity signal structure (if any agents exist)
    if maturity["signals"]:
        sig = maturity["signals"][0]
        assert_in(r, "signal has agent_id", "agent_id", sig)
        assert_in(r, "signal has title", "title", sig)
        assert_in(r, "signal has maturity", "maturity", sig)
        assert_in(r, "signal has total_runs", "total_runs", sig)
        assert_in(r, "signal has origin", "origin", sig)
        assert_true(r, "maturity stage valid",
                    sig["maturity"] in ("nascent", "developing", "mature"),
                    f"got {sig['maturity']}")
    else:
        r.ok("No maturity signals (no active agents) — structure verified")

    # Platform details should have selected_sources from landscape JSONB
    if assessment["platform_details"]:
        pd = assessment["platform_details"][0]
        assert_in(r, "platform_details has selected_sources", "selected_sources", pd)
        assert_true(r, "selected_sources is list",
                    isinstance(pd.get("selected_sources"), list))

    # Tier
    assert_in(r, "tier.can_create exists", "can_create", assessment["tier"])

    return r


# =============================================================================
# Phase 2: should_composer_act() — synthetic assessment dicts
# =============================================================================

def phase2_should_composer_act() -> PhaseResult:
    """Test trigger logic with synthetic assessments."""
    logger.info("\n[Phase 2] should_composer_act()")
    r = PhaseResult("Should Composer Act")

    from services.composer import should_composer_act

    # Healthy workforce — should return False
    healthy = {
        "connected_platforms": ["slack", "gmail"],
        "agents": {"active": 3, "roles_present": ["digest", "synthesize"]},
        "coverage": {"platforms_with_digest": ["slack", "gmail"], "platforms_without_digest": []},
        "health": {"stale_agents": []},
        "maturity": {"signals": [], "mature_agents": [], "underperformers": []},
        "feedback": {"recent_count": 2},
        "tier": {"can_create": True, "limit_message": None},
    }
    should_act, reason = should_composer_act(healthy)
    assert_eq(r, "Healthy workforce → False", should_act, False)
    assert_true(r, "Reason is HEARTBEAT_OK", "HEARTBEAT_OK" in reason, reason)

    # Coverage gap
    gap = {**healthy, "coverage": {"platforms_with_digest": ["slack"], "platforms_without_digest": ["gmail"]}}
    should_act, reason = should_composer_act(gap)
    assert_eq(r, "Coverage gap → True", should_act, True)
    assert_true(r, "Reason mentions coverage_gap", "coverage_gap" in reason, reason)

    # No platforms but has agents → still runs (substrate-wide heartbeat)
    no_platforms_with_agents = {**healthy, "connected_platforms": []}
    should_act, reason = should_composer_act(no_platforms_with_agents)
    # Has 3 active agents + no synthesize → cross_platform_opportunity fires
    # OR it falls through to HEARTBEAT_OK. Either way, not blocked by missing platforms.
    assert_true(r, "No platforms + active agents → not blocked",
                "no substrate" not in reason, f"Reason wrongly blocked: {reason}")

    # No platforms AND no agents → False (no substrate)
    no_substrate = {**healthy, "connected_platforms": [], "agents": {"active": 0, "roles_present": []}}
    should_act, reason = should_composer_act(no_substrate)
    assert_eq(r, "No substrate (no platforms, no agents) → False", should_act, False)
    assert_true(r, "Reason mentions no substrate", "no substrate" in reason, reason)

    # At tier limit → False (but no lifecycle triggers)
    at_limit = {**healthy, "tier": {"can_create": False, "limit_message": "limit"}}
    should_act, reason = should_composer_act(at_limit)
    assert_eq(r, "At tier limit → False", should_act, False)
    assert_true(r, "Reason mentions tier limit", "tier" in reason.lower(), reason)

    # Phase 5: Underperformer → True (even at tier limit)
    underperformer = {
        **healthy,
        "tier": {"can_create": False, "limit_message": "limit"},
        "maturity": {
            "signals": [],
            "mature_agents": [],
            "underperformers": [{"agent_id": "abc", "title": "Bad Agent", "approval_rate": 0.2}],
        },
    }
    should_act, reason = should_composer_act(underperformer)
    assert_eq(r, "Underperformer at tier limit → True", should_act, True)
    assert_true(r, "Reason mentions lifecycle_underperformer",
                "lifecycle_underperformer" in reason, reason)

    # Phase 5: Mature expansion → True
    expansion = {
        **healthy,
        "coverage": {"platforms_with_digest": ["slack", "gmail"], "platforms_without_digest": []},
        "maturity": {
            "signals": [],
            "mature_agents": [
                {"agent_id": "a1", "title": "Slack Recap", "scope": "platform",
                 "role": "digest", "total_runs": 15, "approval_rate": 0.9, "maturity": "mature"},
            ],
            "underperformers": [],
        },
        "agents": {"active": 2, "roles_present": ["digest"]},
    }
    should_act, reason = should_composer_act(expansion)
    assert_eq(r, "Mature expansion → True", should_act, True)
    assert_true(r, "Reason mentions lifecycle_expansion",
                "lifecycle_expansion" in reason, reason)

    # Phase 5: Cross-agent pattern → True (3+ digests, no synthesize)
    # Use 1 platform to avoid cross_platform_opportunity trigger (which fires first)
    cross_agent = {
        **healthy,
        "connected_platforms": ["slack"],
        "agents": {"active": 4, "roles_present": ["digest"]},
        "maturity": {
            "signals": [
                {"role": "digest", "total_runs": 5},
                {"role": "digest", "total_runs": 4},
                {"role": "digest", "total_runs": 6},
            ],
            "mature_agents": [],
            "underperformers": [],
        },
    }
    should_act, reason = should_composer_act(cross_agent)
    assert_eq(r, "Cross-agent pattern → True", should_act, True)
    assert_true(r, "Reason mentions cross_agent_pattern",
                "cross_agent_pattern" in reason, reason)

    # Cross-agent pattern suppressed when synthesize already exists
    cross_agent_with_synth = {
        **cross_agent,
        "agents": {"active": 4, "roles_present": ["digest", "synthesize"]},
    }
    should_act, reason = should_composer_act(cross_agent_with_synth)
    assert_eq(r, "Cross-agent with synthesize → False", should_act, False)

    return r


# =============================================================================
# Phase 3: run_lifecycle_assessment() — synthetic data + real DB
# =============================================================================

async def phase3_lifecycle(supabase, ids: dict) -> PhaseResult:
    """Test lifecycle assessment with a real underperformer agent."""
    logger.info("\n[Phase 3] run_lifecycle_assessment()")
    r = PhaseResult("Lifecycle Assessment")

    from services.composer import run_lifecycle_assessment
    from services.agent_creation import create_agent_record

    # Create a test agent to be paused as underperformer
    agent_result = await create_agent_record(
        client=supabase,
        user_id=TEST_USER_ID,
        title=f"{TEST_PREFIX}Underperformer",
        role="digest",
        origin="composer",
        frequency="daily",
    )
    assert_true(r, "Created test underperformer agent", agent_result.get("success") is True,
                agent_result.get("message", ""))
    if not agent_result.get("success"):
        return r

    agent_id = agent_result["agent_id"]
    ids["agent_ids"].append(agent_id)

    # Build synthetic assessment with this agent as underperformer
    assessment = {
        "connected_platforms": ["slack"],
        "platform_details": [{"platform": "slack", "selected_sources": []}],
        "agents": {"active": 1, "roles_present": ["digest"], "active_list": []},
        "coverage": {"platforms_with_digest": ["slack"], "platforms_without_digest": []},
        "health": {"stale_agents": []},
        "maturity": {
            "signals": [],
            "mature_agents": [],
            "underperformers": [{
                "agent_id": agent_id,
                "title": f"{TEST_PREFIX}Underperformer",
                "role": "digest",
                "scope": "platform",
                "origin": "composer",
                "total_runs": 10,
                "approval_rate": 0.2,
                "maturity": "nascent",
                "is_underperformer": True,
            }],
        },
        "feedback": {"recent_count": 0},
        "tier": {"can_create": True, "limit_message": None},
    }

    # Test underperformer lifecycle
    result = await run_lifecycle_assessment(
        supabase, TEST_USER_ID, assessment, "lifecycle_underperformer: test"
    )

    assert_true(r, "Lifecycle result has actions_taken",
                isinstance(result.get("actions_taken"), list))
    assert_true(r, "Lifecycle paused underperformer",
                len(result["actions_taken"]) == 1 and result["actions_taken"][0]["action"] == "paused",
                f"actions: {result.get('actions_taken', [])}")

    # Verify agent was actually paused in DB
    db_check = supabase.table("agents").select("status").eq("id", agent_id).single().execute()
    assert_eq(r, "Agent status is paused in DB", db_check.data.get("status"), "paused")

    # Test expansion lifecycle (no real agent creation — just verify routing)
    expansion_assessment = {
        **assessment,
        "connected_platforms": ["slack", "gmail"],
        "platform_details": [],
        "maturity": {
            **assessment["maturity"],
            "underperformers": [],
            "mature_agents": [{
                "agent_id": "x", "title": "Slack Recap", "scope": "platform",
                "role": "digest", "total_runs": 15,
            }],
        },
    }
    # No sources → no expansion (empty platform_details)
    result2 = await run_lifecycle_assessment(
        supabase, TEST_USER_ID, expansion_assessment, "lifecycle_expansion: test"
    )
    assert_true(r, "Expansion with no sources → observation only",
                len(result2.get("actions_taken", [])) == 0,
                f"Expected 0 actions, got {result2.get('actions_taken', [])}")

    # Test observe path (underperformer below threshold)
    mild_assessment = {
        **assessment,
        "maturity": {
            **assessment["maturity"],
            "underperformers": [{
                "agent_id": agent_id,
                "title": f"{TEST_PREFIX}Mild",
                "origin": "composer",
                "total_runs": 4,
                "approval_rate": 0.35,
            }],
        },
    }
    result3 = await run_lifecycle_assessment(
        supabase, TEST_USER_ID, mild_assessment, "lifecycle_underperformer: test"
    )
    assert_true(r, "Mild underperformer → observe (not paused)",
                len(result3.get("actions_taken", [])) == 0,
                f"actions: {result3.get('actions_taken', [])}")
    assert_true(r, "Mild underperformer → has observation",
                len(result3.get("observations", [])) > 0)

    return r


# =============================================================================
# Phase 4: run_composer_assessment() — routing verification
# =============================================================================

async def phase4_assessment_routing(supabase) -> PhaseResult:
    """Test that run_composer_assessment routes to correct handler."""
    logger.info("\n[Phase 4] run_composer_assessment() routing")
    r = PhaseResult("Assessment Routing")

    from services.composer import run_composer_assessment

    base_assessment = {
        "connected_platforms": ["slack"],
        "platform_details": [{"platform": "slack", "selected_sources": []}],
        "agents": {"active": 1, "roles_present": ["digest"], "active_list": []},
        "coverage": {"platforms_with_digest": ["slack"], "platforms_without_digest": []},
        "health": {"stale_agents": []},
        "maturity": {"signals": [], "mature_agents": [], "underperformers": []},
        "feedback": {"recent_count": 0},
        "tier": {"can_create": True, "limit_message": None},
    }

    # Lifecycle route: should set action="lifecycle"
    lifecycle_assessment = {
        **base_assessment,
        "maturity": {
            "signals": [],
            "mature_agents": [],
            "underperformers": [{
                "agent_id": "fake-id",
                "title": "Fake Agent",
                "origin": "composer",
                "total_runs": 3,  # Below pause threshold
                "approval_rate": 0.35,
            }],
        },
    }
    result = await run_composer_assessment(
        supabase, TEST_USER_ID, lifecycle_assessment, "lifecycle_underperformer: test"
    )
    assert_in(r, "Result has lifecycle_actions key", "lifecycle_actions", result)
    assert_in(r, "Result has agents_created key", "agents_created", result)
    assert_in(r, "Result has observations key", "observations", result)
    # Mild underperformer → no actions taken (below pause threshold), route still runs
    # but since no lifecycle_actions, action stays "observed"
    assert_true(r, "Lifecycle route processed",
                result["action"] in ("lifecycle", "observed"),
                f"got {result['action']}")

    # Coverage gap with no sources → should return created but empty
    gap_assessment = {
        **base_assessment,
        "coverage": {"platforms_with_digest": [], "platforms_without_digest": ["notion"]},
        "platform_details": [{"platform": "notion", "selected_sources": []}],
    }
    result2 = await run_composer_assessment(
        supabase, TEST_USER_ID, gap_assessment, "coverage_gap: platforms without digest: ['notion']"
    )
    assert_eq(r, "Gap with no sources → observed", result2["action"], "observed")
    assert_eq(r, "No agents created (no sources)", len(result2["agents_created"]), 0)

    return r


# =============================================================================
# Phase 5: Maturity signal calculation — unit tests
# =============================================================================

def phase5_maturity_signals() -> PhaseResult:
    """Test maturity classification logic."""
    logger.info("\n[Phase 5] Maturity signal classification")
    r = PhaseResult("Maturity Signals")

    # Test maturity classification thresholds
    # These match the logic in heartbeat_data_query()
    def classify(total_runs, approval_rate):
        if total_runs >= 10 and approval_rate >= 0.8:
            return "mature"
        elif total_runs >= 5 and approval_rate >= 0.6:
            return "developing"
        elif total_runs >= 1:
            return "nascent"
        return "nascent"

    assert_eq(r, "0 runs → nascent", classify(0, 0.0), "nascent")
    assert_eq(r, "3 runs, 100% → nascent", classify(3, 1.0), "nascent")
    assert_eq(r, "5 runs, 60% → developing", classify(5, 0.6), "developing")
    assert_eq(r, "5 runs, 50% → nascent", classify(5, 0.5), "nascent")
    assert_eq(r, "10 runs, 80% → mature", classify(10, 0.8), "mature")
    assert_eq(r, "10 runs, 70% → developing", classify(10, 0.7), "developing")
    assert_eq(r, "15 runs, 90% → mature", classify(15, 0.9), "mature")

    # Test underperformer detection
    def is_underperformer(total_runs, approval_rate):
        return total_runs >= 5 and approval_rate < 0.4

    assert_eq(r, "3 runs, 20% → not underperformer (too few)", is_underperformer(3, 0.2), False)
    assert_eq(r, "5 runs, 30% → underperformer", is_underperformer(5, 0.3), True)
    assert_eq(r, "5 runs, 40% → not underperformer (boundary)", is_underperformer(5, 0.4), False)
    assert_eq(r, "10 runs, 10% → underperformer", is_underperformer(10, 0.1), True)
    assert_eq(r, "8 runs, 50% → not underperformer", is_underperformer(8, 0.5), False)

    # Test edit trend calculation
    def calc_trend(distances):
        if len(distances) < 3:
            return None
        recent_avg = sum(distances[:3]) / 3
        older = distances[3:min(6, len(distances))]
        older_avg = sum(older) / max(1, len(older))
        if older_avg > 0:
            return (recent_avg - older_avg) / older_avg
        return None

    assert_eq(r, "Insufficient data → None", calc_trend([0.5, 0.3]), None)
    # Improving: recent edits smaller than older edits
    trend = calc_trend([0.1, 0.15, 0.12, 0.4, 0.5, 0.45])
    assert_true(r, "Improving trend is negative", trend is not None and trend < 0,
                f"got {trend}")
    # Degrading: recent edits larger than older
    trend2 = calc_trend([0.5, 0.45, 0.55, 0.1, 0.15, 0.12])
    assert_true(r, "Degrading trend is positive", trend2 is not None and trend2 > 0,
                f"got {trend2}")
    # Edge: older_avg = 0 → None
    trend3 = calc_trend([0.1, 0.2, 0.3, 0.0, 0.0, 0.0])
    assert_eq(r, "Zero older avg → None", trend3, None)

    return r


# =============================================================================
# Phase 6: Origin guard — user_configured agents never auto-paused
# =============================================================================

async def phase6_origin_guard(supabase, ids: dict) -> PhaseResult:
    """Test that lifecycle NEVER auto-pauses user_configured agents."""
    logger.info("\n[Phase 6] Origin Guard — user_configured protection")
    r = PhaseResult("Origin Guard")

    from services.composer import run_lifecycle_assessment
    from services.agent_creation import create_agent_record

    # Create a user-configured agent (simulating manual creation)
    agent_result = await create_agent_record(
        client=supabase,
        user_id=TEST_USER_ID,
        title=f"{TEST_PREFIX}UserCreated",
        role="digest",
        origin="user_configured",
        frequency="daily",
    )
    assert_true(r, "Created user_configured agent", agent_result.get("success") is True,
                agent_result.get("message", ""))
    if not agent_result.get("success"):
        return r

    user_agent_id = agent_result["agent_id"]
    ids["agent_ids"].append(user_agent_id)

    # Create a composer-created agent (should be pausable)
    composer_result = await create_agent_record(
        client=supabase,
        user_id=TEST_USER_ID,
        title=f"{TEST_PREFIX}ComposerCreated",
        role="digest",
        origin="composer",
        frequency="daily",
    )
    assert_true(r, "Created composer agent", composer_result.get("success") is True)
    if not composer_result.get("success"):
        return r

    composer_agent_id = composer_result["agent_id"]
    ids["agent_ids"].append(composer_agent_id)

    # Build assessment with BOTH as underperformers
    assessment = {
        "connected_platforms": ["slack"],
        "platform_details": [{"platform": "slack", "selected_sources": []}],
        "agents": {"active": 2, "roles_present": ["digest"], "active_list": []},
        "coverage": {"platforms_with_digest": ["slack"], "platforms_without_digest": []},
        "health": {"stale_agents": []},
        "maturity": {
            "signals": [],
            "mature_agents": [],
            "underperformers": [
                {
                    "agent_id": user_agent_id,
                    "title": f"{TEST_PREFIX}UserCreated",
                    "role": "digest",
                    "origin": "user_configured",
                    "total_runs": 10,
                    "approval_rate": 0.2,
                    "is_underperformer": True,
                },
                {
                    "agent_id": composer_agent_id,
                    "title": f"{TEST_PREFIX}ComposerCreated",
                    "role": "digest",
                    "origin": "composer",
                    "total_runs": 10,
                    "approval_rate": 0.2,
                    "is_underperformer": True,
                },
            ],
        },
        "feedback": {"recent_count": 0},
        "tier": {"can_create": True, "limit_message": None},
    }

    result = await run_lifecycle_assessment(
        supabase, TEST_USER_ID, assessment, "lifecycle_underperformer: test"
    )

    actions = result.get("actions_taken", [])
    observations = result.get("observations", [])

    # user_configured should NOT be paused — should appear in observations
    paused_ids = [a["agent_id"] for a in actions if a.get("action") == "paused"]
    assert_true(r, "user_configured agent NOT paused",
                user_agent_id not in paused_ids,
                f"user_configured was paused! actions: {actions}")
    assert_true(r, "user_configured appears in observations",
                any("user-configured" in obs.lower() or "UserCreated" in obs for obs in observations),
                f"Expected observation about skipping, got: {observations}")

    # composer-created SHOULD be paused
    assert_true(r, "composer agent WAS paused",
                composer_agent_id in paused_ids,
                f"composer agent not paused. actions: {actions}")

    # Verify DB state
    user_db = supabase.table("agents").select("status").eq("id", user_agent_id).single().execute()
    assert_eq(r, "user_configured agent still active in DB", user_db.data.get("status"), "active")

    composer_db = supabase.table("agents").select("status").eq("id", composer_agent_id).single().execute()
    assert_eq(r, "composer agent paused in DB", composer_db.data.get("status"), "paused")

    return r


# =============================================================================
# Phase 7: Weighted approval rate
# =============================================================================

def phase7_weighted_approval() -> PhaseResult:
    """Test weighted approval: explicit=1.0, auto-delivered=0.5."""
    logger.info("\n[Phase 7] Weighted Approval Rate")
    r = PhaseResult("Weighted Approval")

    def calc_weighted(approved, delivered, rejected):
        """Replicate the weighted logic from composer.py."""
        total = approved + delivered + rejected
        if total == 0:
            return 0.0
        return (approved + delivered * 0.5) / total

    # All approved → 100%
    assert_eq(r, "10 approved, 0 delivered → 1.0",
              round(calc_weighted(10, 0, 0), 2), 1.0)

    # All delivered (no explicit approval) → 50%
    assert_eq(r, "0 approved, 10 delivered → 0.5",
              round(calc_weighted(0, 10, 0), 2), 0.5)

    # Mix: 5 approved, 5 delivered → 75%
    assert_eq(r, "5 approved, 5 delivered → 0.75",
              round(calc_weighted(5, 5, 0), 2), 0.75)

    # With rejections: 3 approved, 4 delivered, 3 rejected → (3 + 2) / 10 = 0.5
    assert_eq(r, "3 approved, 4 delivered, 3 rejected → 0.5",
              round(calc_weighted(3, 4, 3), 2), 0.5)

    # Maturity implications: 10 auto-delivered runs should NOT be "mature"
    # because 50% approval < 80% threshold
    rate_all_delivered = calc_weighted(0, 10, 0)
    is_mature = rate_all_delivered >= 0.8
    assert_eq(r, "All auto-delivered → NOT mature (50% < 80%)", is_mature, False)

    # Maturity: 8 approved + 2 delivered → (8 + 1) / 10 = 90% → mature
    rate_mostly_approved = calc_weighted(8, 2, 0)
    is_mature2 = rate_mostly_approved >= 0.8
    assert_eq(r, "8 approved + 2 delivered → mature (90% >= 80%)", is_mature2, True)

    # Underperformer: 2 approved, 8 delivered → (2 + 4) / 10 = 60% → NOT underperformer
    rate_mixed = calc_weighted(2, 8, 0)
    is_under = rate_mixed < 0.4
    assert_eq(r, "2 approved + 8 delivered → NOT underperformer (60% >= 40%)", is_under, False)

    # Underperformer: 0 approved, 3 delivered, 7 rejected → (0 + 1.5) / 10 = 15% → underperformer
    rate_bad = calc_weighted(0, 3, 7)
    is_under2 = rate_bad < 0.4
    assert_eq(r, "0 approved, 3 delivered, 7 rejected → underperformer (15% < 40%)", is_under2, True)

    return r


# =============================================================================
# Phase 8: Substrate-wide heartbeat (no platforms)
# =============================================================================

def phase8_substrate_heartbeat() -> PhaseResult:
    """Test heartbeat works for users with agents but no platforms."""
    logger.info("\n[Phase 8] Substrate-Wide Heartbeat")
    r = PhaseResult("Substrate Heartbeat")

    from services.composer import should_composer_act

    # User with agents but no platforms — should NOT be blocked
    research_user = {
        "connected_platforms": [],
        "agents": {"active": 2, "roles_present": ["research", "custom"]},
        "coverage": {"platforms_with_digest": [], "platforms_without_digest": []},
        "health": {"stale_agents": []},
        "maturity": {"signals": [], "mature_agents": [], "underperformers": []},
        "feedback": {"recent_count": 3},
        "tier": {"can_create": True, "limit_message": None},
    }
    should_act, reason = should_composer_act(research_user)
    assert_true(r, "No platforms + active agents → NOT blocked by substrate check",
                "no substrate" not in reason,
                f"Blocked: {reason}")

    # User with underperforming agent, no platforms — lifecycle should still fire
    research_underperformer = {
        **research_user,
        "maturity": {
            "signals": [],
            "mature_agents": [],
            "underperformers": [{"agent_id": "x", "title": "Bad Research", "approval_rate": 0.2}],
        },
    }
    should_act2, reason2 = should_composer_act(research_underperformer)
    assert_eq(r, "Underperformer with no platforms → True", should_act2, True)
    assert_true(r, "Reason is lifecycle", "lifecycle_underperformer" in reason2, reason2)

    # Zero everything — blocked
    empty = {
        "connected_platforms": [],
        "agents": {"active": 0, "roles_present": []},
        "coverage": {"platforms_with_digest": [], "platforms_without_digest": []},
        "health": {"stale_agents": []},
        "maturity": {"signals": [], "mature_agents": [], "underperformers": []},
        "feedback": {"recent_count": 0},
        "tier": {"can_create": True, "limit_message": None},
    }
    should_act3, reason3 = should_composer_act(empty)
    assert_eq(r, "No substrate at all → False", should_act3, False)
    assert_true(r, "Reason mentions no substrate", "no substrate" in reason3, reason3)

    return r


# =============================================================================
# Cleanup
# =============================================================================

async def cleanup(supabase, ids: dict):
    """Remove all test artifacts."""
    logger.info("\n[Cleanup]")
    for agent_id in ids.get("agent_ids", []):
        try:
            supabase.table("agent_runs").delete().eq("agent_id", agent_id).execute()
            supabase.table("workspace_files").delete().eq(
                "user_id", TEST_USER_ID
            ).like("path", f"%{agent_id}%").execute()
            supabase.table("agents").delete().eq("id", agent_id).execute()
        except Exception as e:
            logger.warning(f"  Cleanup error for {agent_id}: {e}")

    # Also clean any TEST_ADR111_ agents that might be leftover
    try:
        leftovers = supabase.table("agents").select("id").eq(
            "user_id", TEST_USER_ID
        ).like("title", f"{TEST_PREFIX}%").execute()
        for a in (leftovers.data or []):
            supabase.table("agent_runs").delete().eq("agent_id", a["id"]).execute()
            supabase.table("workspace_files").delete().eq(
                "user_id", TEST_USER_ID
            ).like("path", f"%{a['id']}%").execute()
            supabase.table("agents").delete().eq("id", a["id"]).execute()
        if leftovers.data:
            logger.info(f"  Deleted {len(leftovers.data)} leftover test agent(s)")
    except Exception:
        pass

    logger.info("  Cleanup complete")


# =============================================================================
# Main
# =============================================================================

async def main():
    from supabase import create_client

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY required")
        sys.exit(1)

    supabase = create_client(supabase_url, supabase_key)
    results: list[PhaseResult] = []
    ids = {"agent_ids": []}

    try:
        # Phase 1: Real DB query
        results.append(await phase1_heartbeat_data_query(supabase))

        # Phase 2: Pure logic (no DB)
        results.append(phase2_should_composer_act())

        # Phase 3: Lifecycle with real DB
        results.append(await phase3_lifecycle(supabase, ids))

        # Phase 4: Assessment routing
        results.append(await phase4_assessment_routing(supabase))

        # Phase 5: Maturity math (pure logic)
        results.append(phase5_maturity_signals())

        # Phase 6: Origin guard (real DB — creates test agents)
        results.append(await phase6_origin_guard(supabase, ids))

        # Phase 7: Weighted approval (pure logic)
        results.append(phase7_weighted_approval())

        # Phase 8: Substrate-wide heartbeat (pure logic)
        results.append(phase8_substrate_heartbeat())

    except Exception as e:
        import traceback
        logger.error(f"\nFatal error: {e}")
        logger.error(traceback.format_exc())
    finally:
        if ids:
            await cleanup(supabase, ids)

    # Report
    logger.info("\n" + "=" * 60)
    logger.info("ADR-111 COMPOSER TEST RESULTS")
    logger.info("=" * 60)

    total_passed = 0
    total_failed = 0
    for phase in results:
        total_passed += phase.passed
        total_failed += phase.failed
        status = "PASS" if phase.success else "FAIL"
        line = f"  [{status}] {phase.phase}: {phase.passed} passed, {phase.failed} failed"
        if phase.success:
            logger.info(line)
        else:
            logger.info(line)
            for err in phase.errors:
                logger.info(f"         → {err}")

    logger.info("=" * 60)
    logger.info(f"  Total: {total_passed} passed, {total_failed} failed")
    logger.info("=" * 60)

    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
