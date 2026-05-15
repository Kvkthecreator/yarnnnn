"""Regression gate for ADR-280 Stream A (library hygiene — kernel-side cleanup).

Covers the load-bearing acceptance criteria for the Stream A commit:
- reviewer_envelope.py reads bundle MANIFEST via bundle_reader (not hardcoded)
- ENVELOPE_SUMMARIZERS registry exists with signal_files entry
- read_signal_files relocated from reviewer_agent.py to reviewer_envelope.py
- _summarize_signal_files accepts path_glob parameter (no alpha-trader default)
- review_proposal_dispatch.py uses {context_domain}-parametric reads (no trading hardcode)
- Final grep gate: kernel-perception files contain zero literal program-domain paths

Per ADR-280 §10 closure summary, Stream A closes 13 of 22 remaining catalog
sites at the kernel-perception layer. This gate enforces those closures
+ guards against regression.
"""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
API_ROOT = REPO_ROOT / "api"


# ---------------------------------------------------------------------------
# 1. reviewer_envelope.py — bundle-MANIFEST-driven envelope assembly
# ---------------------------------------------------------------------------

def test_envelope_summarizers_registry_exists():
    """Stream A: ENVELOPE_SUMMARIZERS registry lands in services/reviewer_envelope.py."""
    from services import reviewer_envelope
    assert hasattr(reviewer_envelope, "ENVELOPE_SUMMARIZERS")
    assert isinstance(reviewer_envelope.ENVELOPE_SUMMARIZERS, dict)
    assert "signal_files" in reviewer_envelope.ENVELOPE_SUMMARIZERS
    assert callable(reviewer_envelope.ENVELOPE_SUMMARIZERS["signal_files"])


def test_summarize_signal_files_relocated_to_envelope_module():
    """Stream A: _summarize_signal_files lives in services/reviewer_envelope.py
    (relocated from agents/reviewer_agent.py). The function is kernel-internal
    envelope-summarizer infrastructure, not a Reviewer-facing primitive."""
    from services.reviewer_envelope import _summarize_signal_files
    assert callable(_summarize_signal_files)
    # Signature accepts path_glob parameter (Stream A: glob is bundle-declared,
    # not hardcoded as alpha-trader-specific).
    import inspect
    sig = inspect.signature(_summarize_signal_files)
    params = list(sig.parameters.keys())
    assert params == ["client", "user_id", "path_glob"], \
        f"Expected (client, user_id, path_glob); got {params}"


def test_read_signal_files_deleted_from_reviewer_agent():
    """Stream A: agents/reviewer_agent.py no longer exports read_signal_files
    (relocated to envelope module per ADR-280 Stream A)."""
    from agents import reviewer_agent
    assert not hasattr(reviewer_agent, "read_signal_files"), \
        "read_signal_files must be deleted from reviewer_agent.py per Singular Implementation"


def test_reviewer_agent_no_orphan_dead_block():
    """Stream A: orphan dead block at lines 1300-1325 (unattached docstring +
    function body without def line) deleted in this commit."""
    src = (API_ROOT / "agents" / "reviewer_agent.py").read_text()
    # The orphan was: section divider + unattached docstring "Read all signal
    # state YAML files" + function body. After Stream A deletion, the only
    # remaining mention of read_signal_files should be a comment explaining
    # the relocation.
    occurrences = src.count("read_signal_files")
    assert occurrences <= 1, \
        f"Expected at most one read_signal_files mention (relocation comment); got {occurrences}"


def test_envelope_assembly_reads_bundle_manifest():
    """Stream A: load_reviewer_governance_envelope reads bundle MANIFEST via
    bundle_reader.get_substrate_abi_for_workspace (not hardcoded paths)."""
    src = (API_ROOT / "services" / "reviewer_envelope.py").read_text()
    # Must invoke bundle_reader for program-shaped declarations
    assert "bundle_reader.get_substrate_abi_for_workspace" in src, \
        "envelope helper must read bundle MANIFEST as authority"
    # Must NOT hardcode program-specific paths
    assert "context/trading/_operator_profile" not in src, \
        "no hardcoded alpha-trader paths in envelope helper"
    assert "context/trading/_risk" not in src, \
        "no hardcoded alpha-trader paths in envelope helper"
    assert "context/trading/_performance" not in src, \
        "no hardcoded alpha-trader paths in envelope helper"
    assert "context/trading/signals" not in src, \
        "no hardcoded alpha-trader signals glob in envelope helper"


def test_envelope_returns_universal_keys_for_no_program_workspace():
    """No-program workspace gets universal envelope inputs only (kernel-shipped)."""
    from services.reviewer_envelope import load_reviewer_governance_envelope

    class _MockClient:
        def __init__(self):
            self._table_name = None
        def table(self, name):
            self._table_name = name
            return self
        def select(self, *a, **kw): return self
        def eq(self, *a, **kw): return self
        def limit(self, n): return self
        def execute(self):
            # No platform_connections → no active bundles
            return SimpleNamespace(data=[])

    envelope, elapsed_ms = asyncio.run(
        load_reviewer_governance_envelope(_MockClient(), "test-no-program-user")
    )
    # Universal envelope keys should be present (with empty string when file absent)
    universal_keys = {
        "identity_md", "principles_md", "precedent_md",
        "mandate_md", "autonomy_md", "preferences_yaml",
    }
    assert universal_keys.issubset(envelope.keys()), \
        f"Universal envelope keys missing: {universal_keys - envelope.keys()}"
    # No program-shaped keys for workspace with no active bundle
    program_keys = {"operator_profile_md", "risk_md", "performance_md", "signal_files"}
    program_present = program_keys.intersection(envelope.keys())
    assert program_present == set(), \
        f"No-program workspace should not have program-shaped envelope keys: {program_present}"
    assert isinstance(elapsed_ms, int) and elapsed_ms >= 0


def test_envelope_returns_program_keys_for_alpha_trader_workspace():
    """alpha-trader workspace gets universal + program-shaped envelope keys
    composed from the bundle MANIFEST's substrate_abi.reviewer_wake_envelope."""
    from services.reviewer_envelope import load_reviewer_governance_envelope

    class _MockClient:
        def __init__(self):
            self._table_name = None
        def table(self, name):
            self._table_name = name
            return self
        def select(self, *a, **kw): return self
        def eq(self, *a, **kw): return self
        def like(self, *a, **kw): return self
        def limit(self, n): return self
        def execute(self):
            if self._table_name == "platform_connections":
                return SimpleNamespace(data=[{
                    "platform": "trading", "status": "active",
                    "created_at": "2026-04-01T00:00:00Z",
                }])
            # workspace_files / workspace_blobs reads return empty
            return SimpleNamespace(data=[])

    envelope, _ = asyncio.run(
        load_reviewer_governance_envelope(_MockClient(), "test-trading-user")
    )
    # alpha-trader bundle declares these in its MANIFEST.substrate_abi.reviewer_wake_envelope
    expected_program_keys = {
        "operator_profile_md", "risk_md", "performance_md", "signal_files",
    }
    assert expected_program_keys.issubset(envelope.keys()), \
        f"alpha-trader envelope missing program keys: {expected_program_keys - envelope.keys()}"


# ---------------------------------------------------------------------------
# 2. review_proposal_dispatch.py — context_domain-parametric reads
# ---------------------------------------------------------------------------

def test_review_proposal_dispatch_no_trading_hardcode():
    """Stream A: review_proposal_dispatch.py reads context_domain-parametric;
    no `if context_domain == 'trading':` branch with hardcoded path."""
    src = (API_ROOT / "services" / "review_proposal_dispatch.py").read_text()
    assert 'if context_domain == "trading":' not in src, \
        "trading-specific branch in review_proposal_dispatch.py must be removed"
    assert '"/workspace/context/trading/_risk.md"' not in src, \
        "no hardcoded alpha-trader paths in review_proposal_dispatch.py"


# ---------------------------------------------------------------------------
# 3. cockpit_awareness.py — already program-agnostic (uses {domain} placeholders)
# ---------------------------------------------------------------------------

def test_cockpit_awareness_uses_domain_placeholders():
    """Stream A audit: cockpit_awareness.py uses `{domain}` placeholder
    syntax in its convention-teaching prose; zero literal program paths."""
    src = (API_ROOT / "agents" / "cockpit_awareness.py").read_text()
    # No literal program-domain paths in cockpit_awareness.py
    for program in ("context/trading", "context/commerce", "context/defi"):
        assert program not in src, \
            f"Literal program path {program} leaked into cockpit_awareness.py"
    # Uses {domain} placeholder syntax (convention-teaching)
    assert "{domain}" in src, \
        "cockpit_awareness.py should teach convention via {domain} placeholder"


# ---------------------------------------------------------------------------
# 4. Final grep gate — kernel-perception files contain zero literal program paths
# ---------------------------------------------------------------------------

# Files where any literal program-domain path is a regression. Per ADR-280 §10
# closure summary: these files form the "kernel-perception" closure scope.
# Files OUT of scope (per ADR-280 §7 + §10):
#   - api/services/risk_gate.py (program-specific code; future bundle-relocation ADR)
#   - api/services/primitives/track_regime.py (alpha-trader-specific primitive)
#   - api/services/primitives/track_universe.py (alpha-trader-specific primitive)
#   - api/services/primitives/schedule.py (alpha-trader-specific bundle prompt example)
#   - api/routes/cockpit.py (ADR-225 compositor scope)
#   - api/scripts/oneshot/* (one-time bootstrap scripts; intended program-coupling)
#   - api/agents/prompts/* (illustrative examples in prose; bundle-relocation candidates per Stream B)
KERNEL_PERCEPTION_FILES = [
    API_ROOT / "services" / "workspace_paths.py",
    API_ROOT / "services" / "reviewer_envelope.py",
    API_ROOT / "services" / "primitives" / "workspace.py",
    API_ROOT / "services" / "review_proposal_dispatch.py",
    API_ROOT / "services" / "execution_router.py",
    API_ROOT / "agents" / "reviewer_agent.py",
    API_ROOT / "agents" / "cockpit_awareness.py",
]

BANNED_PATTERN = re.compile(r"context/(trading|commerce|defi|prediction)")


def test_grep_gate_kernel_perception_no_program_paths():
    """ADR-280 Stream A final grep gate: kernel-perception files contain zero
    literal program-domain paths. Each violation must either be (a) refactored
    to consume bundle MANIFEST via bundle_reader, or (b) genuinely belong in
    a bundle-shipped file (relocated out of kernel)."""
    violations: list[str] = []
    for f in KERNEL_PERCEPTION_FILES:
        if not f.exists():
            continue
        content = f.read_text()
        for lineno, line in enumerate(content.splitlines(), start=1):
            # Skip pure-comment lines (# ...) and docstring example lines
            # that use {domain} placeholder explicitly. The discipline is
            # "kernel code does not encode program-shaped paths"; comments
            # that reference paths in passing narration are allowed.
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if BANNED_PATTERN.search(line):
                # Allow the relocation-comment in reviewer_agent.py + envelope
                # module's docstring reference to the historical hardcoded glob
                if "Relocated from" in line or "relocated to" in line:
                    continue
                violations.append(f"{f.relative_to(API_ROOT)}:{lineno}: {line.strip()}")
    assert not violations, (
        "Kernel-perception files contain literal program-domain paths "
        "(per ADR-280 Stream A this is regression). Violations:\n  "
        + "\n  ".join(violations)
    )


# ---------------------------------------------------------------------------
# 5. Phase 1 work continues to pass post-Stream-A
# ---------------------------------------------------------------------------

def test_phase1_lock_policy_still_composes_4_layers():
    """Smoke: Phase 1's lock policy composition still works after Stream A."""
    from services.workspace_paths import DEFAULT_REVIEWER_WRITE_LOCKS
    # Kernel-universal locks present
    from services.workspace_paths import SHARED_MANDATE_PATH
    assert SHARED_MANDATE_PATH in DEFAULT_REVIEWER_WRITE_LOCKS
    # No program-specific paths in kernel constant
    leaks = [p for p in DEFAULT_REVIEWER_WRITE_LOCKS if "context/trading" in p or "context/commerce" in p]
    assert leaks == []


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
