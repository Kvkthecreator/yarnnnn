"""Regression gate for ADR-281 (path-only envelope; no kernel-side prompt-computation).

Covers the load-bearing acceptance criteria post-dissolution of
ENVELOPE_SUMMARIZERS:
- reviewer_envelope.py has NO ENVELOPE_SUMMARIZERS registry, NO
  _summarize_signal_files function, NO path_glob dispatch — path-only.
- MirrorSignalState primitive added + registered in HANDLERS (mechanical-only).
- alpha-trader bundle MANIFEST signal_files entry uses path-only shape.
- alpha-trader bundle _recurrences.yaml has mirror-signal-state mechanical recurrence.
- ADR-280 marked Superseded; ADR-281 is the canonical ADR.
- FOUNDATIONS Derived Principle 19 added.
- Final grep gate (preserved from Stream A): kernel-perception files
  contain zero literal program-domain paths.

Per ADR-281 Derived Principle 19: the kernel reads substrate; substrate
that needs compaction is written by mechanical primitives, not summarized
at LLM-prompt-assembly time.
"""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
API_ROOT = REPO_ROOT / "api"
BUNDLES_ROOT = REPO_ROOT / "docs" / "programs"


# ---------------------------------------------------------------------------
# 1. Summarizer machinery is fully dissolved
# ---------------------------------------------------------------------------

def test_envelope_summarizers_registry_deleted():
    """ADR-281 §D2: ENVELOPE_SUMMARIZERS registry must not exist."""
    from services import reviewer_envelope
    assert not hasattr(reviewer_envelope, "ENVELOPE_SUMMARIZERS"), \
        "ENVELOPE_SUMMARIZERS registry must be deleted per ADR-281 dissolution"


def test_summarize_signal_files_function_deleted():
    """ADR-281 §D2: _summarize_signal_files kernel function must not exist."""
    from services import reviewer_envelope
    assert not hasattr(reviewer_envelope, "_summarize_signal_files"), \
        "_summarize_signal_files must be deleted; replaced by MirrorSignalState mechanical primitive"


def test_envelope_module_no_summarizer_artifacts():
    """ADR-281 grep-level guard: envelope module source contains no summarizer machinery."""
    src = (API_ROOT / "services" / "reviewer_envelope.py").read_text()
    assert "ENVELOPE_SUMMARIZERS" not in src, \
        "ENVELOPE_SUMMARIZERS string must not appear in envelope module"
    assert "_summarize_signal_files" not in src, \
        "_summarize_signal_files reference must not appear in envelope module"
    assert "SummarizerFn" not in src, \
        "SummarizerFn type alias must not appear in envelope module"


def test_envelope_assembly_path_only():
    """ADR-281 §D2: envelope-assembly loop dispatches on `path` only, not path_glob/summarizer.

    Doc-comment mentions explaining why path_glob/summarizer DON'T exist
    (the dissolution rationale) are allowed; what's forbidden is the
    dispatch branch — any line of executable Python code referencing
    path_glob.
    """
    src = (API_ROOT / "services" / "reviewer_envelope.py").read_text()
    # Walk lines; skip comment + docstring lines; assert no executable code references path_glob.
    in_docstring = False
    for lineno, raw_line in enumerate(src.splitlines(), start=1):
        line = raw_line.strip()
        # Track triple-quoted module/function docstrings (simple heuristic
        # sufficient for a single-module gate). Each triple-quote toggles.
        if '"""' in line:
            count = line.count('"""')
            if count % 2 == 1:
                in_docstring = not in_docstring
            continue
        if in_docstring:
            continue
        if line.startswith("#"):
            continue
        assert 'path_glob' not in line, \
            f"envelope module line {lineno} references path_glob in executable code " \
            f"(forbidden per ADR-281 — path-only declaration shape): {line!r}"


# ---------------------------------------------------------------------------
# 2. MirrorSignalState primitive added + registered
# ---------------------------------------------------------------------------

def test_mirror_signal_state_primitive_module_exists():
    """ADR-281 §D3: MirrorSignalState primitive module exists."""
    from services.primitives import mirror_signal_state
    assert hasattr(mirror_signal_state, "handle_mirror_signal_state")
    assert callable(mirror_signal_state.handle_mirror_signal_state)


def test_mirror_signal_state_registered_in_handlers():
    """ADR-281 §D3: MirrorSignalState registered in HANDLERS for dispatcher routing."""
    from services.primitives.registry import HANDLERS
    assert "MirrorSignalState" in HANDLERS, \
        "MirrorSignalState must be registered in HANDLERS for mechanical-mode dispatch"
    from services.primitives.mirror_signal_state import handle_mirror_signal_state
    assert HANDLERS["MirrorSignalState"] is handle_mirror_signal_state


def test_mirror_signal_state_NOT_in_llm_surfaces():
    """ADR-281 §D3: mechanical-only primitive; not in CHAT_PRIMITIVES, HEADLESS_PRIMITIVES, or REVIEWER_PRIMITIVES."""
    from services.primitives.registry import (
        CHAT_PRIMITIVES, HEADLESS_PRIMITIVES, REVIEWER_PRIMITIVES,
    )
    for surface, name in (
        (CHAT_PRIMITIVES, "CHAT_PRIMITIVES"),
        (HEADLESS_PRIMITIVES, "HEADLESS_PRIMITIVES"),
        (REVIEWER_PRIMITIVES, "REVIEWER_PRIMITIVES"),
    ):
        names = [t.get("name") for t in surface if isinstance(t, dict)]
        assert "MirrorSignalState" not in names, \
            f"MirrorSignalState must NOT appear in {name} (mechanical-only per ADR-281)"


def test_mirror_signal_state_handler_writes_substrate():
    """Smoke: MirrorSignalState handler writes through write_revision when signals present."""
    from services.primitives.mirror_signal_state import handle_mirror_signal_state

    class _MockClient:
        def __init__(self):
            self.last_table = None
        def table(self, name):
            self.last_table = name
            return self
        def select(self, *a, **kw): return self
        def eq(self, *a, **kw): return self
        def like(self, *a, **kw): return self
        def limit(self, n): return self
        def execute(self):
            if self.last_table == "workspace_files":
                # Return signal yaml content for the glob query
                return SimpleNamespace(data=[
                    {"path": "/workspace/context/trading/signals/IH-1.yaml",
                     "content": "state: armed\ntriggered_today: []\n"},
                    {"path": "/workspace/context/trading/signals/IH-2.yaml",
                     "content": "state: triggered\ntriggered_today: [NVDA]\n"},
                ])
            return SimpleNamespace(data=[])

    auth = SimpleNamespace(client=_MockClient(), user_id="test-user-12345")
    with patch("services.authored_substrate.write_revision") as mock_write:
        result = asyncio.run(handle_mirror_signal_state(auth, {
            "source": "context/trading/signals/*.yaml",
            "write_to": "context/trading/_signals_summary.md",
            "diff_aware": False,
        }))
        assert result["success"] is True
        assert result["signals_processed"] == 2
        assert "/workspace/context/trading/_signals_summary.md" in result["paths_written"]
        assert mock_write.called
        call_kwargs = mock_write.call_args.kwargs
        assert call_kwargs["authored_by"] == "system:mirror-signal-state"
        assert "IH-1" in call_kwargs["content"]
        assert "IH-2" in call_kwargs["content"]


# ---------------------------------------------------------------------------
# 3. alpha-trader bundle uses path-only envelope shape + mirror recurrence
# ---------------------------------------------------------------------------

def test_alpha_trader_manifest_signal_files_is_path_only():
    """ADR-281 §D1: alpha-trader MANIFEST signal_files entry uses path, not path_glob+summarizer."""
    with (BUNDLES_ROOT / "alpha-trader" / "MANIFEST.yaml").open() as f:
        m = yaml.safe_load(f)
    envelope = m["substrate_abi"]["reviewer_wake_envelope"]
    signal_decl = next((e for e in envelope if e.get("key") == "signal_files"), None)
    assert signal_decl is not None, "alpha-trader MANIFEST must declare signal_files envelope entry"
    assert "path" in signal_decl, "signal_files must use path-only shape per ADR-281"
    assert "path_glob" not in signal_decl, "path_glob shape forbidden per ADR-281"
    assert "summarizer" not in signal_decl, "summarizer shape forbidden per ADR-281"
    assert signal_decl["path"] == "context/trading/_signals_summary.md"


def test_alpha_trader_workspace_guide_signal_files_is_path_only():
    """alpha-trader workspace guide frontmatter mirrors the MANIFEST path-only shape."""
    guide_path = BUNDLES_ROOT / "alpha-trader" / "reference-workspace" / "_workspace_guide.md"
    content = guide_path.read_text()
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    fm = yaml.safe_load(match.group(1))
    envelope = fm["reviewer_wake_envelope"]
    signal_decl = next((e for e in envelope if e.get("key") == "signal_files"), None)
    assert signal_decl is not None
    assert signal_decl.get("path") == "context/trading/_signals_summary.md"
    assert "path_glob" not in signal_decl
    assert "summarizer" not in signal_decl


def test_alpha_trader_has_mirror_signal_state_recurrence():
    """ADR-281 §D3: alpha-trader declares the mirror-signal-state mechanical recurrence."""
    rec_path = BUNDLES_ROOT / "alpha-trader" / "reference-workspace" / "_recurrences.yaml"
    with rec_path.open() as f:
        recs = yaml.safe_load(f)
    by_slug = {r.get("slug"): r for r in recs.get("recurrences", [])}
    mirror = by_slug.get("mirror-signal-state")
    assert mirror is not None, "alpha-trader bundle must declare mirror-signal-state recurrence"
    assert mirror.get("mode") == "mechanical"
    assert mirror.get("fire_on_activation") is True, \
        "mirror-signal-state must fire on activation to populate substrate before first Reviewer wake"
    prompt = mirror.get("prompt", "")
    assert "@primitive: MirrorSignalState" in prompt
    assert 'source="context/trading/signals/*.yaml"' in prompt
    assert 'write_to="context/trading/_signals_summary.md"' in prompt


# ---------------------------------------------------------------------------
# 4. Envelope assembly composes universal + bundle path entries
# ---------------------------------------------------------------------------

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
            return SimpleNamespace(data=[])

    envelope, elapsed_ms = asyncio.run(
        load_reviewer_governance_envelope(_MockClient(), "test-no-program-user")
    )
    universal_keys = {
        "identity_md", "principles_md", "precedent_md",
        "mandate_md", "autonomy_md", "preferences_yaml",
    }
    assert universal_keys.issubset(envelope.keys())
    # No program-shaped keys for workspace with no active bundle
    assert "signal_files" not in envelope
    assert isinstance(elapsed_ms, int) and elapsed_ms >= 0


def test_envelope_returns_program_keys_for_alpha_trader_workspace():
    """alpha-trader workspace gets universal + program-shaped envelope keys from bundle MANIFEST."""
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
            return SimpleNamespace(data=[])

    envelope, _ = asyncio.run(
        load_reviewer_governance_envelope(_MockClient(), "test-trading-user")
    )
    expected_program_keys = {
        "operator_profile_md", "risk_md", "performance_md", "signal_files",
    }
    assert expected_program_keys.issubset(envelope.keys())


# ---------------------------------------------------------------------------
# 5. ADR-280 superseded; ADR-281 canonical; FOUNDATIONS Principle 19 added
# ---------------------------------------------------------------------------

def test_adr_280_marked_superseded():
    """ADR-281 supersedes ADR-280; ADR-280 status flips to Superseded."""
    adr280_path = REPO_ROOT / "docs" / "adr" / "ADR-280-substrate-abi-workspace-guide.md"
    text = adr280_path.read_text()
    assert "Superseded by [ADR-281]" in text, "ADR-280 must declare Superseded status"


def test_adr_281_exists():
    """ADR-281 exists as the canonical ADR for substrate-pedagogy work."""
    adr281_path = REPO_ROOT / "docs" / "adr" / "ADR-281-substrate-canonical-substrate-only-prompts.md"
    assert adr281_path.exists()
    text = adr281_path.read_text()
    assert "The kernel does not compute for the prompt" in text


def test_foundations_principle_19_added():
    """FOUNDATIONS gains Derived Principle 19 per ADR-281."""
    fnd = (REPO_ROOT / "docs" / "architecture" / "FOUNDATIONS.md").read_text()
    assert "19. **The kernel does not compute for the prompt**" in fnd, \
        "FOUNDATIONS must include Derived Principle 19 per ADR-281"


def test_adr_223_drops_path_glob_summarizer():
    """ADR-223 §3.bis schema doc reflects ADR-281's path-only revision."""
    adr223 = (REPO_ROOT / "docs" / "adr" / "ADR-223-program-bundle-specification.md").read_text()
    assert "ADR-281" in adr223, "ADR-223 must reference ADR-281's schema revision"
    # The schema description forbids path_glob + summarizer
    assert "no `path_glob`" in adr223 or "no `path_glob` or `summarizer`" in adr223


# ---------------------------------------------------------------------------
# 6. Phase 1 + Stream A preserved work still passes
# ---------------------------------------------------------------------------

def test_default_reviewer_write_locks_still_kernel_universal_only():
    """Phase 1 closure preserved: DEFAULT_REVIEWER_WRITE_LOCKS contains zero program paths."""
    from services.workspace_paths import DEFAULT_REVIEWER_WRITE_LOCKS
    leaks = [p for p in DEFAULT_REVIEWER_WRITE_LOCKS
             if "context/trading" in p or "context/commerce" in p]
    assert leaks == []


def test_review_proposal_dispatch_no_trading_hardcode():
    """Stream A preserved closure: no `if context_domain == 'trading'` branch."""
    src = (API_ROOT / "services" / "review_proposal_dispatch.py").read_text()
    assert 'if context_domain == "trading":' not in src


# ---------------------------------------------------------------------------
# 7. Final grep gate — kernel-perception files contain zero literal program paths
# ---------------------------------------------------------------------------

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
    """ADR-281 final grep gate: kernel-perception files contain zero literal
    program-domain paths."""
    violations: list[str] = []
    for f in KERNEL_PERCEPTION_FILES:
        if not f.exists():
            continue
        content = f.read_text()
        for lineno, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if BANNED_PATTERN.search(line):
                if "Relocated from" in line or "relocated to" in line:
                    continue
                violations.append(f"{f.relative_to(API_ROOT)}:{lineno}: {line.strip()}")
    assert not violations, (
        "Kernel-perception files contain literal program-domain paths. "
        "Violations:\n  " + "\n  ".join(violations)
    )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
