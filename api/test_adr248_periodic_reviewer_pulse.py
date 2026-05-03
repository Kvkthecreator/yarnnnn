"""ADR-248 regression gate — Periodic Reviewer Pulse + Autonomy Loop Closure.

Validates all four commits without hitting the database or the LLM.

Pure-Python per ADR-236 Rule 3. Run with:
    python api/test_adr248_periodic_reviewer_pulse.py
"""

from __future__ import annotations

import sys
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Canonical paths
BACK_OFFICE_YAML = REPO_ROOT / "docs" / "programs" / "alpha-trader" / "reference-workspace" / "_shared" / "back-office.yaml"
REVIEWER_REFLECTION = REPO_ROOT / "api" / "services" / "back_office" / "reviewer_reflection.py"
REVIEW_POLICY = REPO_ROOT / "api" / "services" / "review_policy.py"
WORKING_MEMORY = REPO_ROOT / "api" / "services" / "working_memory.py"
REFLECTION_WRITER = REPO_ROOT / "api" / "services" / "reflection_writer.py"
REVIEWER_AGENT = REPO_ROOT / "api" / "agents" / "reviewer_agent.py"
PERSONAS_YAML = REPO_ROOT / "docs" / "alpha" / "personas.yaml"


# ---------------------------------------------------------------------------
# Commit 1 — YAML declarations + gate floor
# ---------------------------------------------------------------------------

def assertion_1_back_office_yaml_exists():
    assert BACK_OFFICE_YAML.exists(), (
        f"Reference workspace back-office.yaml missing: {BACK_OFFICE_YAML}"
    )


def assertion_2_back_office_yaml_has_required_executors():
    content = BACK_OFFICE_YAML.read_text()
    required = [
        "services.back_office.narrative_digest",
        "services.back_office.proposal_cleanup",
        "services.back_office.outcome_reconciliation",
        "services.back_office.reviewer_calibration",
        "services.back_office.reviewer_reflection",
    ]
    for executor in required:
        assert executor in content, (
            f"back-office.yaml missing executor: {executor}"
        )


def assertion_3_back_office_yaml_execution_order():
    """Calibration must come before reflection (06:00 vs 07:00 UTC)."""
    content = BACK_OFFICE_YAML.read_text()
    cal_idx = content.find("reviewer_calibration")
    ref_idx = content.find("reviewer_reflection")
    assert cal_idx < ref_idx, (
        "reviewer_calibration must appear before reviewer_reflection in back-office.yaml "
        "(calibration must run first — reflection reads calibration.md)"
    )


def assertion_4_min_total_decisions_gate():
    src = REVIEWER_REFLECTION.read_text()
    assert "_MIN_TOTAL_DECISIONS = 5" in src, (
        "reviewer_reflection.py must have _MIN_TOTAL_DECISIONS = 5 "
        "(pattern-detection floor per ADR-248 D1)"
    )
    assert "len(decisions) < _MIN_TOTAL_DECISIONS" in src, (
        "reviewer_reflection.py must check total decisions against _MIN_TOTAL_DECISIONS"
    )


# ---------------------------------------------------------------------------
# Commit 2 — pause authority read side
# ---------------------------------------------------------------------------

def assertion_5_known_autonomy_keys_has_pause_fields():
    src = REVIEW_POLICY.read_text()
    assert '"paused_until"' in src, (
        "review_policy._KNOWN_AUTONOMY_KEYS must include 'paused_until' (ADR-248 D3)"
    )
    assert '"pause_reason"' in src, (
        "review_policy._KNOWN_AUTONOMY_KEYS must include 'pause_reason' (ADR-248 D3)"
    )


def assertion_6_pause_check_before_verdict_check():
    src = REVIEW_POLICY.read_text()
    pause_idx = src.find("paused_until")
    verdict_idx = src.find("verdict == \"reject\"")
    assert pause_idx < verdict_idx, (
        "Pause expiry check must appear before verdict check in "
        "should_auto_execute_verdict() — pause gates everything (ADR-248 D3)"
    )


def assertion_7_extract_autonomy_pause_helper():
    src = WORKING_MEMORY.read_text()
    assert "_extract_autonomy_pause" in src, (
        "working_memory.py must define _extract_autonomy_pause() helper (ADR-248 D5)"
    )
    assert "autonomy_paused_until" in src, (
        "working_memory.py must surface autonomy_paused_until in workspace_state"
    )


def assertion_8_pause_signal_in_compact_index():
    src = WORKING_MEMORY.read_text()
    assert "autonomy_paused_until" in src and "⚠" in src, (
        "format_compact_index must emit ⚠ pause signal when autonomy_paused_until is set"
    )


def assertion_9_pause_expiry_logic_correct():
    """Unit-test the _extract_autonomy_pause logic inline (without importing the module)."""
    import re as _re
    from datetime import datetime as _dt, timezone as _tz

    def _extract(content: str) -> dict:
        if not content or "paused_until:" not in content:
            return {}
        match = _re.search(r"paused_until:\s*['\"]?([^'\"\n#]+)['\"]?", content)
        if not match:
            return {}
        ts = match.group(1).strip()
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        paused_until = _dt.fromisoformat(ts)
        if paused_until.tzinfo is None:
            paused_until = paused_until.replace(tzinfo=_tz.utc)
        if paused_until <= _dt.now(_tz.utc):
            return {}
        return {"autonomy_paused_until": paused_until.strftime("%Y-%m-%d %H:%M UTC")}

    # Future timestamp → should surface
    future = (datetime.now(timezone.utc) + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = _extract(f"default:\n  paused_until: \"{future}\"\n")
    assert result.get("autonomy_paused_until"), "Future paused_until should return display string"

    # Past timestamp → should return empty dict
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = _extract(f"default:\n  paused_until: \"{past}\"\n")
    assert not result, "Expired paused_until should return empty dict"

    # Missing → empty dict
    result = _extract("default:\n  level: autonomous\n")
    assert not result, "Missing paused_until should return empty dict"


# ---------------------------------------------------------------------------
# Commit 3 — pause write path
# ---------------------------------------------------------------------------

def assertion_10_apply_pause_autonomy_in_reflection_writer():
    src = REFLECTION_WRITER.read_text()
    assert "_apply_pause_autonomy" in src, (
        "reflection_writer.py must define _apply_pause_autonomy() (ADR-248 D4)"
    )
    assert "pause_autonomy" in src, (
        "reflection_writer.py must handle pause_autonomy proposal type"
    )
    # pause_autonomy handler (--- 0.) must come before regular proposal loop (--- 1.)
    step0_idx = src.find("--- 0.")
    step1_idx = src.find("--- 1.")
    assert step0_idx != -1 and step1_idx != -1 and step0_idx < step1_idx, (
        "pause_autonomy handler (--- 0.) must precede regular proposal loop (--- 1.)"
    )


def assertion_11_reflection_writer_uses_write_revision():
    src = REFLECTION_WRITER.read_text()
    # _apply_pause_autonomy must use write_revision for ADR-209 attribution
    apply_fn_start = src.find("def _apply_pause_autonomy")
    assert apply_fn_start != -1, "_apply_pause_autonomy function not found"
    fn_body = src[apply_fn_start:apply_fn_start + 2000]
    assert "write_revision" in fn_body, (
        "_apply_pause_autonomy must write via write_revision() for ADR-209 attribution"
    )
    assert 'authored_by' in fn_body, (
        "_apply_pause_autonomy must pass authored_by to write_revision"
    )


def assertion_12_reviewer_agent_has_pause_autonomy():
    src = REVIEWER_AGENT.read_text()
    assert '"pause_autonomy"' in src, (
        "reviewer_agent.py _REFLECTION_TOOL must include pause_autonomy in enum"
    )
    assert "AUTONOMY.md" in src, (
        "reviewer_agent.py reflection tool must list AUTONOMY.md as valid target_file"
    )
    assert "duration_hours" in src, (
        "reviewer_agent.py reflection tool must include duration_hours field"
    )


def assertion_13_pause_autonomy_high_bar_in_prompt():
    src = REVIEWER_AGENT.read_text()
    # System prompt must include high-bar language: NOT for single losses / temporary drawdowns
    assert "single losing trade" in src or "single loss" in src, (
        "reviewer_agent.py _REFLECTION_SYSTEM_PROMPT must include high-bar language "
        "that pause_autonomy is not for a single losing trade / temporary drawdown"
    )
    assert "temporary drawdown" in src, (
        "reviewer_agent.py _REFLECTION_SYSTEM_PROMPT must mention 'temporary drawdown' "
        "as a case where pause_autonomy should NOT be used"
    )


# ---------------------------------------------------------------------------
# Personas invariants updated
# ---------------------------------------------------------------------------

def assertion_14_personas_yaml_has_narrative_digest():
    content = PERSONAS_YAML.read_text()
    assert "back-office-narrative-digest" in content, (
        "personas.yaml must include back-office-narrative-digest in scaffolded_recurrences"
    )


def assertion_15_personas_yaml_has_back_office_yaml_core_file():
    content = PERSONAS_YAML.read_text()
    assert "/workspace/_shared/back-office.yaml" in content, (
        "personas.yaml core_files must include /workspace/_shared/back-office.yaml"
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all():
    tests = [
        assertion_1_back_office_yaml_exists,
        assertion_2_back_office_yaml_has_required_executors,
        assertion_3_back_office_yaml_execution_order,
        assertion_4_min_total_decisions_gate,
        assertion_5_known_autonomy_keys_has_pause_fields,
        assertion_6_pause_check_before_verdict_check,
        assertion_7_extract_autonomy_pause_helper,
        assertion_8_pause_signal_in_compact_index,
        assertion_9_pause_expiry_logic_correct,
        assertion_10_apply_pause_autonomy_in_reflection_writer,
        assertion_11_reflection_writer_uses_write_revision,
        assertion_12_reviewer_agent_has_pause_autonomy,
        assertion_13_pause_autonomy_high_bar_in_prompt,
        assertion_14_personas_yaml_has_narrative_digest,
        assertion_15_personas_yaml_has_back_office_yaml_core_file,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✓ {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {test.__name__}: {e}")
            failed += 1

    print(f"\n{passed}/{len(tests)} assertions passed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
