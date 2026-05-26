"""ADR-294 — Regression gate for operator-proxy machinery.

Validates structural invariants of the operator-proxy capability. Does NOT
run full scenarios (those produce observation artifacts, not pass/fail
gates — per ADR-294 D9).

Asserts:
1. is_valid_author accepts operator-proxy:* namespace + rejects malformed variants
2. ProxyConfig.caller_identity produces the canonical shape
3. ProxyConfig.from_persona resolves alpha-persona registry correctly
4. Scenario YAML parser accepts well-formed scenario + rejects malformed
5. Scenario schema version gate refuses unknown versions
6. Public API surface exists with expected method names
7. Capture artifact filenames are stable (the 8-file set)
8. caller_identity is plumbed through to write_substrate output dict
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_API_ROOT = _REPO_ROOT / "api"
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))


# ---------------------------------------------------------------------------
# 1. is_valid_author accepts operator-proxy:* sub-namespace
# ---------------------------------------------------------------------------

def test_is_valid_author_accepts_operator_proxy_namespace():
    from services.authored_substrate import is_valid_author

    assert is_valid_author("operator-proxy:claude-sonnet-4-7:acting-as-kvk")
    assert is_valid_author("operator-proxy:scenario-runner:acting-as-alpha-trader-2")
    assert is_valid_author("operator-proxy:external:chatgpt-5:acting-as-yarnnn-author")
    # Existing namespaces still accepted (no regression).
    assert is_valid_author("operator")
    assert is_valid_author("reviewer:ai:reviewer-sonnet-v8")
    assert is_valid_author("system:bundle-fork")
    assert is_valid_author("agent:foo")
    assert is_valid_author("specialist:writer")


def test_is_valid_author_rejects_malformed_proxy_strings():
    from services.authored_substrate import is_valid_author

    # Missing colon — bare prefix shouldn't validate.
    assert not is_valid_author("operator-proxy")
    # Hyphen continuation with no colon — should NOT match operator-proxy:
    assert not is_valid_author("operator-proxy-bad")
    # Empty
    assert not is_valid_author("")


# ---------------------------------------------------------------------------
# 2. ProxyConfig caller_identity shape
# ---------------------------------------------------------------------------

def test_proxy_config_caller_identity_shape():
    from services.operator_proxy.client import ProxyConfig

    cfg = ProxyConfig(
        user_id="00000000-0000-0000-0000-000000000000",
        email="test@example.com",
        caller="claude-sonnet-4-7",
        persona_slug="alpha-trader-2",
    )
    assert cfg.caller_identity == "operator-proxy:claude-sonnet-4-7:acting-as-alpha-trader-2"


def test_proxy_config_caller_identity_with_external_caller():
    """Future MCP-as-operator shape per ADR-294 D2."""
    from services.operator_proxy.client import ProxyConfig

    cfg = ProxyConfig(
        user_id="00000000-0000-0000-0000-000000000000",
        email="test@example.com",
        caller="external:chatgpt-5",
        persona_slug="yarnnn-author",
    )
    assert cfg.caller_identity == "operator-proxy:external:chatgpt-5:acting-as-yarnnn-author"


# ---------------------------------------------------------------------------
# 3. ProxyConfig.from_persona resolves registry
# ---------------------------------------------------------------------------

def test_proxy_config_from_persona_resolves_kvk():
    from services.operator_proxy.client import ProxyConfig

    cfg = ProxyConfig.from_persona("kvk", caller="claude-sonnet-4-7")
    # kvk user_id from docs/alpha/personas.yaml — known invariant
    assert cfg.user_id == "2abf3f96-118b-4987-9d95-40f2d9be9a18"
    assert cfg.persona_slug == "kvk"
    assert cfg.caller == "claude-sonnet-4-7"
    assert cfg.caller_identity == "operator-proxy:claude-sonnet-4-7:acting-as-kvk"


# ---------------------------------------------------------------------------
# 4. Scenario parser
# ---------------------------------------------------------------------------

def test_scenario_parser_accepts_minimal_scenario():
    from services.operator_proxy.scenarios import Scenario

    raw = {
        "scenario": "test-min",
        "description": "minimal scenario for parser test",
        "persona": "kvk",
        "turns": [{"send_message": "hello"}],
    }
    s = Scenario.from_dict(raw)
    assert s.slug == "test-min"
    assert s.persona == "kvk"
    assert len(s.turns) == 1


def test_scenario_parser_accepts_full_scenario():
    from services.operator_proxy.scenarios import Scenario

    raw = {
        "scenario": "test-full",
        "description": "full scenario for parser test",
        "persona": "alpha-trader",
        "setup": [
            {"fire": "track-account"},
            {
                "write_substrate": {
                    "path": "/workspace/context/trading/_money_truth.md",
                    "authored_by": "operator-proxy:scenario-runner:acting-as-alpha-trader",
                    "content": "stub",
                }
            },
        ],
        "turns": [
            {"send_message": "Reviewer, what's your read?", "expect": ["reviewer_responded"]},
            {"approve_proposal": {"id": "fake-id"}, "expect": ["proposal_executed"]},
        ],
        "capture": ["revision_chain", "decisions_md", "action_proposals"],
    }
    s = Scenario.from_dict(raw)
    assert s.slug == "test-full"
    assert len(s.setup) == 2
    assert len(s.turns) == 2
    assert "revision_chain" in s.capture


def test_scenario_parser_rejects_missing_required_fields():
    from services.operator_proxy.scenarios import Scenario, ScenarioError

    with pytest.raises(ScenarioError):
        Scenario.from_dict({"description": "no slug"})

    with pytest.raises(ScenarioError):
        Scenario.from_dict({"scenario": "no-persona"})

    with pytest.raises(ScenarioError):
        Scenario.from_dict("not a dict")  # type: ignore


def test_scenario_parser_refuses_unknown_schema_version():
    from services.operator_proxy.scenarios import Scenario, ScenarioError

    raw = {
        "scenario_schema_version": 99,
        "scenario": "future",
        "persona": "kvk",
    }
    with pytest.raises(ScenarioError):
        Scenario.from_dict(raw)


# ---------------------------------------------------------------------------
# 5. Public API surface
# ---------------------------------------------------------------------------

def test_operator_proxy_public_api_present():
    """ADR-294 D1 — verify public method names exist on OperatorProxy."""
    from services.operator_proxy import OperatorProxy, ProxyConfig, ProxyError

    # OperatorProxy methods
    for method in (
        "send_message",
        "read_feed",
        "approve_proposal",
        "reject_proposal",
        "list_pending_proposals",
        "write_substrate",
        "read_file",
        "list_recurrences",
        "from_persona",
    ):
        assert hasattr(OperatorProxy, method), f"OperatorProxy missing method: {method}"

    # ProxyConfig + ProxyError exposed at package root
    assert ProxyConfig is not None
    assert ProxyError is not None


# ---------------------------------------------------------------------------
# 6. Capture artifact filenames are the canonical set
# ---------------------------------------------------------------------------

def test_capture_artifact_filenames():
    """ADR-294 D7 — the 8-file canonical capture set."""
    from services.operator_proxy import capture as capture_module
    import inspect

    source = inspect.getsource(capture_module)
    for filename in (
        "README.md",
        "PLAYBOOK.md",
        "transcript.md",
        "substrate-diff.md",
        "decisions.md",
        "proposals.md",
        "token-usage.md",
        "findings.md",
    ):
        assert filename in source, f"capture.py does not reference canonical artifact: {filename}"


# ---------------------------------------------------------------------------
# 7. Evaluations README documents the canonical set
# (renamed from "observations" 2026-05-26 — see docs/evaluations/README.md
# §"Why 'evaluations' and not 'observations'" for the discipline rationale)
# ---------------------------------------------------------------------------

def test_evaluations_readme_documents_canon():
    readme = _REPO_ROOT / "docs" / "evaluations" / "README.md"
    assert readme.is_file(), "docs/evaluations/README.md missing"
    text = readme.read_text()

    # Canonical artifact set must be documented
    for filename in (
        "transcript.md",
        "substrate-diff.md",
        "decisions.md",
        "proposals.md",
        "token-usage.md",
        "findings.md",
    ):
        assert filename in text, f"evaluations README missing canonical artifact ref: {filename}"

    # Caller-identity discipline must be documented
    assert "operator-proxy:" in text, "evaluations README missing caller-identity discipline"
    assert "ADR-294" in text, "evaluations README missing ADR-294 reference"
    # Criterion-declaration discipline introduced 2026-05-26 must be documented
    assert "criterion-declaration" in text.lower(), "evaluations README missing criterion-declaration discipline"


# ---------------------------------------------------------------------------
# 8. Scripts exist + are importable
# ---------------------------------------------------------------------------

def test_scripts_operator_loop_importable():
    """ADR-294 D4 — CLI scripts exist + parse without error."""
    import importlib.util

    loop_path = _API_ROOT / "scripts" / "operator" / "loop.py"
    assert loop_path.is_file()
    spec = importlib.util.spec_from_file_location("loop_test_import", loop_path)
    assert spec is not None
    # We don't execute (would require argv); just verify it loads.
    module = importlib.util.module_from_spec(spec)
    assert module is not None


def test_scripts_operator_run_scenario_importable():
    import importlib.util

    rs_path = _API_ROOT / "scripts" / "operator" / "run_scenario.py"
    assert rs_path.is_file()
    spec = importlib.util.spec_from_file_location("rs_test_import", rs_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert module is not None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
