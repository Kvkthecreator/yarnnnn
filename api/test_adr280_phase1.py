"""Regression gate for ADR-280 Phase 1 (first commit — substrate ABI mechanism).

Covers the load-bearing acceptance criteria for the first atomic commit:
- alpha-trader + alpha-commerce bundle MANIFESTs declare valid substrate_abi blocks
- services/workspace_guide.py exposes the canonical reader API
- services/bundle_reader.py extensions return correct shapes
- DEFAULT_FREDDIE_WRITE_LOCKS contains zero program-specific paths (kernel-universal only)
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
        assert isinstance(zone.get("path"), str) and zone["path"].startswith("operation/")


def test_alpha_trader_envelope_declares_signal_files_path():
    """ADR-281 §D1: signal_files envelope entry uses path-only shape (post-dissolution
    of path_glob+summarizer per Derived Principle 19). Compaction is written by
    the mirror-signal-state mechanical recurrence; envelope reads the substrate."""
    m = _load_bundle("alpha-trader")
    envelope = m["substrate_abi"]["reviewer_wake_envelope"]
    signal_decl = next((e for e in envelope if e.get("key") == "signal_files"), None)
    assert signal_decl is not None, "signal_files envelope key missing"
    assert signal_decl.get("path") == "operation/trading/_signals_summary.md", \
        "signal_files must point at the mirror substrate file per ADR-281 §D1"
    assert "path_glob" not in signal_decl, "path_glob shape forbidden per ADR-281"
    assert "summarizer" not in signal_decl, "summarizer field forbidden per ADR-281"


def test_alpha_commerce_bundle_declares_substrate_abi():
    """ADR-280 §8 Phase 1: deferred bundle also declares substrate_abi (validates additive pattern)."""
    m = _load_bundle("alpha-commerce")
    abi = m.get("substrate_abi")
    assert abi is not None, "alpha-commerce missing substrate_abi block — additive pattern broken"
    assert abi.get("schema_version") == 1
    assert any(z.get("path") == "operation/customers" for z in abi["path_zones"])


# ---------------------------------------------------------------------------
# 2. Kernel constants — no program-specific paths leak
# ---------------------------------------------------------------------------

# NOTE (ADR-320): test_default_reviewer_write_locks_{contains_zero_program_paths,
# preserves_kernel_universals} DELETED. The DEFAULT_FREDDIE_WRITE_LOCKS flat-list
# collapsed into the five-root CALLER_WRITE_POLICY; per-program path-zone locks
# dissolved with the workspace_guide 4-layer composition. Governance-locked-from-seat
# coverage moved to test_adr320_permission_topology.py.


# ---------------------------------------------------------------------------
# 3. workspace_guide.py — reader API + frontmatter extraction
# ---------------------------------------------------------------------------

# NOTE (ADR-320): test_workspace_guide_module_exports DELETED.
# The workspace_guide get_path_zone_locks export dissolved with the 4-layer lock
# composition (collapsed into CALLER_WRITE_POLICY). Remaining workspace_guide
# frontmatter-reader coverage stays below.


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


# NOTE (ADR-320): test_workspace_guide_get_path_zone_locks DELETED.
# get_path_zone_locks (operator-canon-zone → locked-path composition) dissolved
# into the five-root CALLER_WRITE_POLICY prefix model. Permission coverage moved to
# test_adr320_permission_topology.py.


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
    assert len(abi["path_zones"]) >= 2, "Should see operation/trading + operation/portfolio zones"
    paths = [z["path"] for z in abi["path_zones"]]
    assert "operation/trading" in paths
    # Origin tagging — bundle slug surfaced for downstream attribution
    assert all(z.get("_program_slug") == "alpha-trader" for z in abi["path_zones"])
    # Envelope declarations include operator_profile_md
    keys = [e["key"] for e in abi["reviewer_wake_envelope"]]
    assert "operator_profile_md" in keys


# NOTE (ADR-320): test_get_path_zone_locks_for_workspace_{no_program_returns_empty,
# with_alpha_trader_active} DELETED. bundle_reader.get_path_zone_locks_for_workspace
# (per-program lock composition) dissolved into the static five-root
# CALLER_WRITE_POLICY. The get_substrate_abi_for_workspace coverage above is unaffected.


# ---------------------------------------------------------------------------
# 5. Permission gate — collapsed five-root model (ADR-320)
# ---------------------------------------------------------------------------
# NOTE (ADR-320): the four lock-composition tests that exercised the OLD
# _is_path_locked_for_reviewer (kernel + bundle + guide + operator-overrides) were
# DELETED — that function no longer exists. The collapsed _is_path_locked(caller_class,
# path) is a pure prefix check over CALLER_WRITE_POLICY; its behavior (governance/
# locked from the seat, operation/ writable, persona/notes writable) is covered by
# test_adr320_permission_topology.py.


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
# 7. Bundle-shipped workspace guides (revised §D4 — bundles ship the guide)
# ---------------------------------------------------------------------------

def test_alpha_trader_bundle_ships_workspace_guide():
    """ADR-280 revised §D4: alpha-trader bundle ships the workspace guide as
    operator-canon at reference-workspace/_workspace_guide.md."""
    guide_path = BUNDLES_ROOT / "alpha-trader" / "reference-workspace" / "_workspace_guide.md"
    assert guide_path.exists(), \
        "alpha-trader bundle must ship _workspace_guide.md at reference-workspace/ root"
    content = guide_path.read_text()
    # Must have YAML frontmatter
    assert content.startswith("---\n"), "Guide must start with YAML frontmatter"
    # Frontmatter must declare schema_version + path_zones + reviewer_wake_envelope
    import yaml as _yaml
    import re as _re
    match = _re.match(r"^---\s*\n(.*?)\n---", content, _re.DOTALL)
    assert match, "Guide frontmatter must be parseable"
    fm = _yaml.safe_load(match.group(1))
    assert fm.get("schema_version") == 1
    assert isinstance(fm.get("path_zones"), list) and len(fm["path_zones"]) > 0
    assert isinstance(fm.get("reviewer_wake_envelope"), list) and len(fm["reviewer_wake_envelope"]) > 0
    # alpha-trader-specific zones present
    paths = [z["path"] for z in fm["path_zones"]]
    assert "operation/trading" in paths
    # Universal kernel zones also present (bundle composes both)
    assert "constitution" in paths
    assert "persona/IDENTITY.md" in paths


def test_alpha_commerce_bundle_ships_workspace_guide():
    """Validates additive pattern: deferred bundle also ships its guide."""
    guide_path = BUNDLES_ROOT / "alpha-commerce" / "reference-workspace" / "_workspace_guide.md"
    assert guide_path.exists(), \
        "alpha-commerce bundle must ship _workspace_guide.md (validates additive pattern)"
    import yaml as _yaml
    import re as _re
    content = guide_path.read_text()
    match = _re.match(r"^---\s*\n(.*?)\n---", content, _re.DOTALL)
    fm = _yaml.safe_load(match.group(1))
    assert fm.get("schema_version") == 1
    paths = [z["path"] for z in fm["path_zones"]]
    assert "operation/customers" in paths


def test_bundle_guides_use_only_valid_roles():
    """Both bundle guides use the six canonical roles per ADR-280 §2.D2."""
    valid_roles = {
        "operator-canon", "reviewer-workbench", "system-ledger",
        "world-mirror", "running-narrative", "kernel-index",
    }
    import yaml as _yaml
    import re as _re
    for slug in ("alpha-trader", "alpha-commerce"):
        guide_path = BUNDLES_ROOT / slug / "reference-workspace" / "_workspace_guide.md"
        content = guide_path.read_text()
        match = _re.match(r"^---\s*\n(.*?)\n---", content, _re.DOTALL)
        fm = _yaml.safe_load(match.group(1))
        for zone in fm["path_zones"]:
            assert zone["role"] in valid_roles, f"{slug} invalid role: {zone}"


def test_bundle_guide_prose_has_required_sections():
    """Both bundle guides include the three required prose sections per ADR-280 §3."""
    for slug in ("alpha-trader", "alpha-commerce"):
        guide_path = BUNDLES_ROOT / slug / "reference-workspace" / "_workspace_guide.md"
        content = guide_path.read_text()
        for section in (
            "## How this workspace works",
            "## What NOT to write to operator-canon",
            "## When things diverge",
        ):
            assert section in content, f"{slug} guide missing section: {section}"
        # Guaranteed-topology phrase (may wrap across lines).
        normalized = " ".join(content.split())
        assert "guaranteed to be the substrate topology" in normalized, \
            f"{slug} guide missing guaranteed-topology line"


# ---------------------------------------------------------------------------
# 8. Kernel-default workspace guide for no-program workspaces
# ---------------------------------------------------------------------------

# NOTE (ADR-320): test_orchestration_exports_default_workspace_guide_md DELETED.
# It asserted the kernel-default guide enumerates the legacy `context/_shared` path
# zone; ADR-320 relocated the substrate into the five semantic roots
# (governance/ constitution/ persona/ operation/ system/), so the legacy-root
# assertion no longer holds. The kernel-default guide's structural integrity is still
# covered by test_kernel_default_guide_frontmatter_parses below.


def test_kernel_default_guide_frontmatter_parses():
    """Kernel-default guide's frontmatter is well-formed YAML."""
    from services.orchestration import DEFAULT_WORKSPACE_GUIDE_MD
    from services.workspace_guide import _extract_frontmatter
    fm = _extract_frontmatter(DEFAULT_WORKSPACE_GUIDE_MD)
    assert fm.get("schema_version") == 1
    assert isinstance(fm.get("path_zones"), list) and len(fm["path_zones"]) > 0
    assert isinstance(fm.get("reviewer_wake_envelope"), list) and len(fm["reviewer_wake_envelope"]) == 6
    # All universal envelope keys
    keys = [e["key"] for e in fm["reviewer_wake_envelope"]]
    for required in ("identity_md", "principles_md", "mandate_md", "autonomy_md"):
        assert required in keys, f"Universal envelope key {required} missing"


def test_workspace_init_writes_kernel_default_guide():
    """workspace_init.py Phase 2 writes the kernel-default guide alongside other skeletons."""
    init_src = (REPO_ROOT / "api" / "services" / "workspace_init.py").read_text()
    assert "DEFAULT_WORKSPACE_GUIDE_MD" in init_src, \
        "workspace_init.py must import + write DEFAULT_WORKSPACE_GUIDE_MD"
    assert "_workspace_guide.md" in init_src, \
        "workspace_init.py must reference _workspace_guide.md path"


def test_workspace_init_no_genesis_machinery():
    """ADR-280 §D4 dissolution: no genesis-by-Reviewer machinery in workspace_init.py."""
    init_src = (REPO_ROOT / "api" / "services" / "workspace_init.py").read_text()
    # Genesis-related symbols MUST be absent
    assert "GENESIS_RECURRENCE_SLUG" not in init_src, \
        "GENESIS_RECURRENCE_SLUG must be deleted (no genesis wake)"
    assert "assemble_genesis_prompt" not in init_src, \
        "assemble_genesis_prompt import must be deleted"
    assert "Genesis wake" not in init_src or "genesis-by-Reviewer wake was deleted" in init_src, \
        "Active genesis-wake invocation must be deleted (deletion-note allowed)"


def test_genesis_prompt_module_deleted():
    """ADR-280 §D4 dissolution: api/agents/genesis_prompt.py must not exist."""
    genesis_path = REPO_ROOT / "api" / "agents" / "genesis_prompt.py"
    assert not genesis_path.exists(), \
        "api/agents/genesis_prompt.py must be deleted per Singular Implementation"


def test_old_migration_script_deleted():
    """ADR-280 §D4 dissolution: old genesis migration script must not exist."""
    old_script = REPO_ROOT / "api" / "scripts" / "oneshot" / "adr280_genesis_for_existing_workspaces.py"
    assert not old_script.exists(), \
        "Old genesis migration script must be deleted per Singular Implementation"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
