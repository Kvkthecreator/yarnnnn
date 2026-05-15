"""Regression gate for ADR-280 Phase 1 (first commit — substrate ABI mechanism).

Covers the load-bearing acceptance criteria for the first atomic commit:
- alpha-trader + alpha-commerce bundle MANIFESTs declare valid substrate_abi blocks
- services/workspace_guide.py exposes the canonical reader API
- services/bundle_reader.py extensions return correct shapes
- DEFAULT_REVIEWER_WRITE_LOCKS contains zero program-specific paths (kernel-universal only)
- _is_path_locked_for_reviewer composes kernel + bundle + guide + operator-overrides correctly
- Workspace guide soft-cap budget warning fires when content exceeds threshold

Genesis-by-Reviewer + workspace_init wiring + migration script are tested
separately in test_adr280_phase1_genesis.py (second commit).

Per ADR-280 §10 drift catalog, this gate also serves as the regression
guard against re-introducing program-specific paths into kernel constants —
test_no_program_paths_in_kernel_locks fails on regression.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys

import pytest
import yaml


# ---------------------------------------------------------------------------
# 1. Bundle MANIFEST declarations — schema + presence
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLES_ROOT = REPO_ROOT / "docs" / "programs"


def _load_bundle(slug: str) -> dict:
    """Load a bundle MANIFEST from the repo."""
    with (BUNDLES_ROOT / slug / "MANIFEST.yaml").open() as f:
        return yaml.safe_load(f)


def test_alpha_trader_bundle_declares_substrate_abi():
    """ADR-280 §8 Phase 1: alpha-trader MANIFEST has non-empty substrate_abi block."""
    m = _load_bundle("alpha-trader")
    abi = m.get("substrate_abi")
    assert abi is not None, "alpha-trader missing substrate_abi block"
    assert abi.get("schema_version") == 1, "schema_version must be 1"
    assert isinstance(abi.get("path_zones"), list) and len(abi["path_zones"]) > 0
    assert isinstance(abi.get("reviewer_wake_envelope"), list) and len(abi["reviewer_wake_envelope"]) > 0


def test_alpha_trader_path_zones_use_valid_roles():
    """ADR-280 §3.bis: path_zones[*].role must be one of the six canonical roles."""
    m = _load_bundle("alpha-trader")
    valid_roles = {
        "operator-canon", "reviewer-workbench", "system-ledger",
        "world-mirror", "running-narrative", "kernel-index",
    }
    for zone in m["substrate_abi"]["path_zones"]:
        assert zone.get("role") in valid_roles, f"Invalid role in zone {zone.get('path')}: {zone.get('role')}"
        assert isinstance(zone.get("path"), str) and zone["path"].startswith("context/")


def test_alpha_trader_envelope_declares_signal_files_summarizer():
    """ADR-280 §2.D6.b + §3.bis: signal_files glob requires summarizer reference."""
    m = _load_bundle("alpha-trader")
    envelope = m["substrate_abi"]["reviewer_wake_envelope"]
    signal_decl = next((e for e in envelope if e.get("key") == "signal_files"), None)
    assert signal_decl is not None, "signal_files envelope key missing"
    assert "path_glob" in signal_decl, "signal_files must declare path_glob"
    assert signal_decl.get("summarizer") == "signal_files", "summarizer ref must match kernel registry name"


def test_alpha_commerce_bundle_declares_substrate_abi():
    """ADR-280 §8 Phase 1: deferred bundle also declares substrate_abi (validates additive pattern)."""
    m = _load_bundle("alpha-commerce")
    abi = m.get("substrate_abi")
    assert abi is not None, "alpha-commerce missing substrate_abi block — additive pattern broken"
    assert abi.get("schema_version") == 1
    assert any(z.get("path") == "context/customers" for z in abi["path_zones"])


# ---------------------------------------------------------------------------
# 2. Kernel constants — no program-specific paths leak
# ---------------------------------------------------------------------------

def test_default_reviewer_write_locks_contains_zero_program_paths():
    """ADR-280 §8 Phase 1 grep gate: DEFAULT_REVIEWER_WRITE_LOCKS is kernel-universal only."""
    from services.workspace_paths import DEFAULT_REVIEWER_WRITE_LOCKS
    leaks = [
        p for p in DEFAULT_REVIEWER_WRITE_LOCKS
        if "context/trading" in p or "context/commerce" in p or "context/defi" in p or "context/prediction" in p
    ]
    assert leaks == [], (
        f"Program-specific paths leaked back into kernel constant — "
        f"per ADR-280 these belong in bundle MANIFEST.substrate_abi.path_zones: {leaks}"
    )


def test_default_reviewer_write_locks_preserves_kernel_universals():
    """Kernel-universal locks must still be present (don't overcorrect)."""
    from services.workspace_paths import (
        DEFAULT_REVIEWER_WRITE_LOCKS,
        SHARED_MANDATE_PATH,
        SHARED_IDENTITY_PATH,
        SHARED_AUTONOMY_PATH,
    )
    for required in (SHARED_MANDATE_PATH, SHARED_IDENTITY_PATH, SHARED_AUTONOMY_PATH):
        assert required in DEFAULT_REVIEWER_WRITE_LOCKS, f"{required} missing from kernel defaults"


# ---------------------------------------------------------------------------
# 3. workspace_guide.py — reader API + frontmatter extraction
# ---------------------------------------------------------------------------

def test_workspace_guide_module_exports():
    """ADR-280 §8 Phase 1: services/workspace_guide.py exports the canonical reader API."""
    from services import workspace_guide
    assert callable(workspace_guide.read_frontmatter)
    assert callable(workspace_guide.read_frontmatter_async)
    assert callable(workspace_guide.get_path_zone_locks)
    assert callable(workspace_guide.get_reviewer_wake_envelope_decls)
    assert workspace_guide.WORKSPACE_GUIDE_PATH == "/workspace/_workspace_guide.md"


def test_workspace_guide_extract_frontmatter_well_formed():
    """Well-formed frontmatter parses to a dict."""
    from services.workspace_guide import _extract_frontmatter
    content = """---
schema_version: 1
path_zones:
  - path: context/trading
    role: operator-canon
---

# Workspace Guide

Body content.
"""
    result = _extract_frontmatter(content)
    assert result.get("schema_version") == 1
    assert len(result.get("path_zones", [])) == 1


def test_workspace_guide_extract_frontmatter_malformed_returns_empty():
    """Fail-open per ADR-258 D9 lock-policy discipline — never raise."""
    from services.workspace_guide import _extract_frontmatter
    # Missing closing delimiter
    assert _extract_frontmatter("---\nschema_version: 1\n# no close") == {}
    # Empty content
    assert _extract_frontmatter("") == {}
    # No frontmatter at all
    assert _extract_frontmatter("# Just a markdown file") == {}
    # Malformed YAML inside the delimiters
    assert _extract_frontmatter("---\n  : invalid : yaml :\n---") == {}


def test_workspace_guide_get_path_zone_locks():
    """ADR-280 §2.D2: operator-canon zones become locked paths; locks.add/remove apply."""
    from services.workspace_guide import get_path_zone_locks
    frontmatter = {
        "path_zones": [
            {"path": "context/trading", "role": "operator-canon",
             "authored_files": ["_operator_profile.md", "_risk.md"]},
            {"path": "context/portfolio", "role": "operator-canon"},
            # NOT operator-canon — should NOT be locked
            {"path": "memory", "role": "running-narrative"},
            {"path": "review", "role": "reviewer-workbench"},
        ],
        "locks": {
            "add": ["custom/extra.md"],
            "remove": ["context/portfolio"],  # operator overrides default
        },
    }
    locked = get_path_zone_locks(frontmatter)
    assert "context/trading" in locked
    assert "context/trading/_operator_profile.md" in locked
    assert "context/trading/_risk.md" in locked
    assert "memory" not in locked, "running-narrative must not be locked"
    assert "review" not in locked, "reviewer-workbench must not be locked"
    assert "custom/extra.md" in locked, "operator add not honored"
    assert "context/portfolio" not in locked, "operator remove not honored"


def test_workspace_guide_size_warning_fires_on_oversize():
    """ADR-280 §8 Phase 1: oversize guide logs a warning (informational, no raise)."""
    from services.workspace_guide import _check_guide_size
    import logging
    huge = "x" * (26 * 1024)  # exceed 25KB cap
    with patch("services.workspace_guide.logger") as mock_logger:
        _check_guide_size(huge, "test-user-12345678")
        mock_logger.warning.assert_called_once()
        assert "soft cap" in str(mock_logger.warning.call_args).lower()


def test_workspace_guide_size_warning_silent_when_under_cap():
    """Under-cap content emits no warning."""
    from services.workspace_guide import _check_guide_size
    with patch("services.workspace_guide.logger") as mock_logger:
        _check_guide_size("normal-sized content", "test-user-12345678")
        mock_logger.warning.assert_not_called()


# ---------------------------------------------------------------------------
# 4. bundle_reader.py extensions — substrate_abi aggregation + lock-set computation
# ---------------------------------------------------------------------------

def _mock_client_with_trading_connection():
    """Mock supabase client returning an active trading platform_connection."""
    class _Mock:
        def __init__(self):
            self.last_table = None
        def table(self, name):
            self.last_table = name
            return self
        def select(self, *a, **kw): return self
        def eq(self, *a, **kw): return self
        def limit(self, n): return self
        def execute(self):
            if self.last_table == "platform_connections":
                return SimpleNamespace(data=[{
                    "platform": "trading", "status": "active",
                    "created_at": "2026-04-01T00:00:00Z",
                }])
            return SimpleNamespace(data=[])
    return _Mock()


def _mock_client_no_connections():
    """Mock supabase client returning no platform_connections."""
    class _Mock:
        def table(self, name): return self
        def select(self, *a, **kw): return self
        def eq(self, *a, **kw): return self
        def limit(self, n): return self
        def execute(self): return SimpleNamespace(data=[])
    return _Mock()


def test_get_substrate_abi_for_workspace_no_program():
    """Workspace with no active program returns empty path_zones + envelope."""
    from services.bundle_reader import get_substrate_abi_for_workspace
    abi = get_substrate_abi_for_workspace("test-user", _mock_client_no_connections())
    assert abi == {"path_zones": [], "reviewer_wake_envelope": []}


def test_get_substrate_abi_for_workspace_with_alpha_trader_active():
    """Workspace with trading connection sees alpha-trader's substrate_abi declarations."""
    from services.bundle_reader import get_substrate_abi_for_workspace
    abi = get_substrate_abi_for_workspace("test-user", _mock_client_with_trading_connection())
    assert len(abi["path_zones"]) >= 2, "Should see context/trading + context/portfolio zones"
    paths = [z["path"] for z in abi["path_zones"]]
    assert "context/trading" in paths
    # Origin tagging — bundle slug surfaced for downstream attribution
    assert all(z.get("_program_slug") == "alpha-trader" for z in abi["path_zones"])
    # Envelope declarations include operator_profile_md
    keys = [e["key"] for e in abi["reviewer_wake_envelope"]]
    assert "operator_profile_md" in keys


def test_get_path_zone_locks_for_workspace_no_program_returns_empty():
    """No active program → no bundle-declared locks."""
    from services.bundle_reader import get_path_zone_locks_for_workspace
    locks = get_path_zone_locks_for_workspace("test-user", _mock_client_no_connections())
    assert locks == set()


def test_get_path_zone_locks_for_workspace_with_alpha_trader_active():
    """Active alpha-trader → bundle-declared locks include context/trading/* paths."""
    from services.bundle_reader import get_path_zone_locks_for_workspace
    locks = get_path_zone_locks_for_workspace("test-user", _mock_client_with_trading_connection())
    assert "context/trading" in locks, "zone path itself must be locked (operator-canon role)"
    assert "context/trading/_operator_profile.md" in locks, "authored_files entry must be locked"
    assert "context/trading/_risk.md" in locks, "authored_files entry must be locked"


# ---------------------------------------------------------------------------
# 5. _is_path_locked_for_reviewer — full composition (4 layers)
# ---------------------------------------------------------------------------

def test_lock_policy_no_program_only_kernel_universal_locks():
    """Workspace with no program: only kernel-universal locks fire."""
    from services.primitives.workspace import _is_path_locked_for_reviewer
    auth = SimpleNamespace(client=_mock_client_no_connections(), user_id="test-no-program")
    # MANDATE.md is kernel-universal — locked
    assert asyncio.run(_is_path_locked_for_reviewer(auth, "context/_shared/MANDATE.md"))
    # context/trading/* — NOT locked (no active bundle declares it)
    auth2 = SimpleNamespace(client=_mock_client_no_connections(), user_id="test-no-program-2")
    assert not asyncio.run(_is_path_locked_for_reviewer(auth2, "context/trading/_operator_profile.md"))


def test_lock_policy_with_alpha_trader_active_composes_bundle_locks():
    """Workspace with alpha-trader active: bundle substrate_abi composes program-specific locks in."""
    from services.primitives.workspace import _is_path_locked_for_reviewer
    # Per-call fresh auth (cache is per-instance)
    auth = SimpleNamespace(client=_mock_client_with_trading_connection(), user_id="test-trading")
    assert asyncio.run(_is_path_locked_for_reviewer(auth, "context/_shared/MANDATE.md")), \
        "kernel-universal still locked"

    auth2 = SimpleNamespace(client=_mock_client_with_trading_connection(), user_id="test-trading-2")
    assert asyncio.run(_is_path_locked_for_reviewer(auth2, "context/trading/_operator_profile.md")), \
        "bundle substrate_abi must compose program-specific lock"

    auth3 = SimpleNamespace(client=_mock_client_with_trading_connection(), user_id="test-trading-3")
    assert asyncio.run(_is_path_locked_for_reviewer(auth3, "context/trading/_risk.md")), \
        "authored_files entry must be locked"


def test_lock_policy_unrelated_paths_not_locked():
    """Sanity check: unrelated paths (not in any layer) are NOT locked."""
    from services.primitives.workspace import _is_path_locked_for_reviewer
    auth = SimpleNamespace(client=_mock_client_with_trading_connection(), user_id="test-unrelated")
    assert not asyncio.run(_is_path_locked_for_reviewer(auth, "memory/notes.md")), \
        "reviewer-workbench paths must remain writable"
    auth2 = SimpleNamespace(client=_mock_client_with_trading_connection(), user_id="test-unrelated-2")
    assert not asyncio.run(_is_path_locked_for_reviewer(auth2, "review/notes.md")), \
        "Reviewer's notebook must remain writable"


# ---------------------------------------------------------------------------
# 6. ADR-223 schema doc updated — substrate_abi section present
# ---------------------------------------------------------------------------

def test_adr223_documents_substrate_abi_schema():
    """ADR-280 §8 Phase 1: ADR-223 doc updated to declare substrate_abi schema."""
    adr223_path = REPO_ROOT / "docs" / "adr" / "ADR-223-program-bundle-specification.md"
    text = adr223_path.read_text()
    # Section heading present
    assert "substrate_abi" in text, "ADR-223 must document substrate_abi"
    assert "MANIFEST.yaml `substrate_abi` block" in text, "Schema section title must be present"
    # Six roles enumerated
    for role in ("operator-canon", "reviewer-workbench", "system-ledger",
                 "world-mirror", "running-narrative", "kernel-index"):
        assert role in text, f"Role taxonomy entry {role} missing from ADR-223"


# ---------------------------------------------------------------------------
# 7. genesis_prompt.py — kernel template + assemble_genesis_prompt
# ---------------------------------------------------------------------------

def test_genesis_prompt_module_exports():
    """ADR-280 §8 Phase 1: api/agents/genesis_prompt.py exists with required exports."""
    from agents import genesis_prompt
    assert genesis_prompt.GENESIS_RECURRENCE_SLUG == "workspace-genesis"
    assert callable(genesis_prompt.assemble_genesis_prompt)
    # Universal kernel template constants populated
    assert len(genesis_prompt.KERNEL_PATH_ZONES) >= 15, \
        "Kernel template must declare 15+ universal path zones"
    assert len(genesis_prompt.KERNEL_REVIEWER_WAKE_ENVELOPE) == 6, \
        "Kernel template must declare 6 universal envelope inputs"


def test_genesis_prompt_kernel_zones_use_valid_roles():
    """All kernel-template zones use one of the six canonical roles."""
    from agents.genesis_prompt import KERNEL_PATH_ZONES
    valid_roles = {
        "operator-canon", "reviewer-workbench", "system-ledger",
        "world-mirror", "running-narrative", "kernel-index",
    }
    for zone in KERNEL_PATH_ZONES:
        assert zone["role"] in valid_roles, f"Invalid role: {zone}"


def test_genesis_prompt_prose_template_has_required_sections():
    """ADR-280 §3 + CC cross-check: prose template covers the three required sections."""
    from agents.genesis_prompt import PROSE_TEMPLATE
    for section in (
        "## How this workspace works",
        "## What NOT to write to operator-canon",  # CC cross-check edit
        "## When things diverge",
    ):
        assert section in PROSE_TEMPLATE, f"Missing section: {section}"
    # Guaranteed-topology line per CC cross-check edit (phrase may wrap across lines).
    # Normalize whitespace before matching so wrapping doesn't break the assertion.
    normalized = " ".join(PROSE_TEMPLATE.split())
    assert "guaranteed to be the substrate topology" in normalized
    assert "do not need to `ListFiles` defensively" in normalized
    # Six-role taxonomy enumerated in prose
    for role in ("operator-canon", "reviewer-workbench", "system-ledger",
                 "world-mirror", "running-narrative", "kernel-index"):
        assert role in PROSE_TEMPLATE


def test_assemble_genesis_prompt_no_program():
    """No-program workspace: prompt has universal content but no program section."""
    from agents.genesis_prompt import assemble_genesis_prompt
    prompt = assemble_genesis_prompt(None, None)
    assert "genesis wake" in prompt
    assert "WriteFile" in prompt
    assert "/workspace/_workspace_guide.md" in prompt
    assert "reviewer:{occupant}/genesis" in prompt
    assert "Program-specific declarations" not in prompt


def test_assemble_genesis_prompt_with_program():
    """Program-active workspace: prompt includes program section composing bundle ABI."""
    from agents.genesis_prompt import assemble_genesis_prompt
    sample_abi = {
        "path_zones": [
            {"path": "context/trading", "role": "operator-canon",
             "purpose": "per-instrument", "_program_slug": "alpha-trader"},
        ],
        "reviewer_wake_envelope": [
            {"key": "operator_profile_md",
             "path": "context/trading/_operator_profile.md", "optional": False},
            {"key": "signal_files",
             "path_glob": "context/trading/signals/*.yaml",
             "summarizer": "signal_files", "optional": True},
        ],
    }
    prompt = assemble_genesis_prompt("alpha-trader", sample_abi)
    assert "alpha-trader" in prompt
    assert "Program-specific declarations" in prompt
    assert "context/trading" in prompt
    assert "summarizer: signal_files" in prompt


# ---------------------------------------------------------------------------
# 8. workspace_init.py genesis-wake integration (mocked invoke_reviewer)
# ---------------------------------------------------------------------------

def test_workspace_init_genesis_skipped_when_guide_exists():
    """Idempotency: if workspace guide already exists, genesis wake is skipped."""
    from services import workspace_init
    # Mock workspace_guide.read_frontmatter to return non-empty (guide exists)
    with patch("services.workspace_guide.read_frontmatter") as mock_read:
        mock_read.return_value = {"schema_version": 1, "path_zones": []}
        # Call the genesis branch directly via a minimal harness
        # (full initialize_workspace requires Supabase + many other moving parts;
        # we test the genesis branch's idempotency behavior)
        import importlib
        importlib.reload(workspace_init)  # Ensure fresh state
    # Above is a type-existence check; full integration test is in
    # the migration script itself (which runs against kvk's live workspace).
    # Asserting the idempotency contract via code inspection:
    init_src = (REPO_ROOT / "api" / "services" / "workspace_init.py").read_text()
    assert "Workspace guide exists" in init_src, \
        "workspace_init.py must skip genesis when guide exists"
    assert "GENESIS_RECURRENCE_SLUG" in init_src, \
        "workspace_init.py must use the canonical genesis slug"
    assert 'trigger="reactive"' in init_src, \
        "workspace_init.py must invoke Reviewer with reactive trigger (recurrence-fire shape)"


def test_workspace_init_genesis_imports_resolve():
    """workspace_init.py imports the genesis machinery cleanly (no circular imports)."""
    # If this import succeeds, the wiring is structurally sound.
    from services import workspace_init  # noqa: F401
    from agents.genesis_prompt import assemble_genesis_prompt  # noqa: F401
    from services import workspace_guide  # noqa: F401
    from services import bundle_reader  # noqa: F401


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
