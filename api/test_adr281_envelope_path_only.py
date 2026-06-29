"""Regression gate for ADR-281 (path-only envelope; no kernel-side prompt-computation).

Covers the load-bearing acceptance criteria post-dissolution of
ENVELOPE_SUMMARIZERS:
- freddie_envelope.py has NO ENVELOPE_SUMMARIZERS registry, NO
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
    from services import freddie_envelope
    assert not hasattr(freddie_envelope, "ENVELOPE_SUMMARIZERS"), \
        "ENVELOPE_SUMMARIZERS registry must be deleted per ADR-281 dissolution"


def test_summarize_signal_files_function_deleted():
    """ADR-281 §D2: _summarize_signal_files kernel function must not exist."""
    from services import freddie_envelope
    assert not hasattr(freddie_envelope, "_summarize_signal_files"), \
        "_summarize_signal_files must be deleted; replaced by MirrorSignalState mechanical primitive"


def test_envelope_module_no_summarizer_artifacts():
    """ADR-281 grep-level guard: envelope module source contains no summarizer machinery."""
    src = (API_ROOT / "services" / "freddie_envelope.py").read_text()
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
    src = (API_ROOT / "services" / "freddie_envelope.py").read_text()
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
    """ADR-281 §D3: mechanical-only primitive; not in CHAT_PRIMITIVES, HEADLESS_PRIMITIVES, or FREDDIE_PRIMITIVES."""
    from services.primitives.registry import (
        CHAT_PRIMITIVES, HEADLESS_PRIMITIVES, FREDDIE_PRIMITIVES,
    )
    for surface, name in (
        (CHAT_PRIMITIVES, "CHAT_PRIMITIVES"),
        (HEADLESS_PRIMITIVES, "HEADLESS_PRIMITIVES"),
        (FREDDIE_PRIMITIVES, "FREDDIE_PRIMITIVES"),
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
                    {"path": "/workspace/operation/trading/signals/IH-1.yaml",
                     "content": "state: armed\ntriggered_today: []\n"},
                    {"path": "/workspace/operation/trading/signals/IH-2.yaml",
                     "content": "state: triggered\ntriggered_today: [NVDA]\n"},
                ])
            return SimpleNamespace(data=[])

    auth = SimpleNamespace(client=_MockClient(), user_id="test-user-12345")
    with patch("services.authored_substrate.write_revision") as mock_write:
        result = asyncio.run(handle_mirror_signal_state(auth, {
            "source": "operation/trading/signals/*.yaml",
            "write_to": "operation/trading/_signals_summary.md",
            "diff_aware": False,
        }))
        assert result["success"] is True
        assert result["signals_processed"] == 2
        assert "/workspace/operation/trading/_signals_summary.md" in result["paths_written"]
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
    assert signal_decl["path"] == "operation/trading/_signals_summary.md"


def test_alpha_trader_workspace_guide_signal_files_is_path_only():
    """alpha-trader workspace guide frontmatter mirrors the MANIFEST path-only shape."""
    guide_path = BUNDLES_ROOT / "alpha-trader" / "reference-workspace" / "_workspace_guide.md"
    content = guide_path.read_text()
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    fm = yaml.safe_load(match.group(1))
    envelope = fm["reviewer_wake_envelope"]
    signal_decl = next((e for e in envelope if e.get("key") == "signal_files"), None)
    assert signal_decl is not None
    assert signal_decl.get("path") == "operation/trading/_signals_summary.md"
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
    assert 'source="operation/trading/signals/*.yaml"' in prompt
    assert 'write_to="operation/trading/_signals_summary.md"' in prompt


# ---------------------------------------------------------------------------
# 4. Envelope assembly composes universal + bundle path entries
# ---------------------------------------------------------------------------

def test_envelope_returns_universal_keys_for_no_program_workspace():
    """No-program workspace gets universal envelope inputs only (kernel-shipped)."""
    from services.freddie_envelope import load_freddie_governance_envelope

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
        load_freddie_governance_envelope(_MockClient(), "test-no-program-user")
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
    from services.freddie_envelope import load_freddie_governance_envelope

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
        load_freddie_governance_envelope(_MockClient(), "test-trading-user")
    )
    expected_program_keys = {
        "operator_profile_md", "risk_md", "ground_truth_md", "signal_files",
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

# test_default_reviewer_write_locks_still_kernel_universal_only DELETED (ADR-320):
# the flat DEFAULT_FREDDIE_WRITE_LOCKS list dissolved into the five-root
# permission topology (CALLER_WRITE_POLICY). The intent — "reviewer locks
# contain zero literal program-domain paths" — is now structurally guaranteed
# by the topology (the reviewer's locked set is the root tuple
# (GOVERNANCE_ROOT, SYSTEM_ROOT), never a filename or program path) and is
# subsumed by test_adr320_permission_topology.py per Singular Implementation.


def test_review_proposal_dispatch_no_trading_hardcode():
    """Stream A preserved closure: no `if context_domain == 'trading'` branch."""
    src = (API_ROOT / "services" / "review_proposal_dispatch.py").read_text()
    assert 'if context_domain == "trading":' not in src


# ---------------------------------------------------------------------------
# 7. Final grep gate — kernel-perception files contain zero literal program paths
# ---------------------------------------------------------------------------

KERNEL_PERCEPTION_FILES = [
    API_ROOT / "services" / "workspace_paths.py",
    API_ROOT / "services" / "freddie_envelope.py",
    API_ROOT / "services" / "primitives" / "workspace.py",
    API_ROOT / "services" / "review_proposal_dispatch.py",
    API_ROOT / "services" / "execution_router.py",
    API_ROOT / "agents" / "freddie_agent.py",
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


# ---------------------------------------------------------------------------
# 8. Stream B Piece 1: judgment_log substrate (ADR-281 §5)
# ---------------------------------------------------------------------------

def test_review_judgment_log_path_constant_renamed():
    """ADR-281 §5.D1: REVIEW_DECISIONS_PATH renamed to PERSONA_JUDGMENT_LOG_PATH."""
    from services import workspace_paths
    assert hasattr(workspace_paths, "PERSONA_JUDGMENT_LOG_PATH"), \
        "PERSONA_JUDGMENT_LOG_PATH must exist in workspace_paths"
    assert workspace_paths.PERSONA_JUDGMENT_LOG_PATH == "persona/judgment_log.md"
    assert not hasattr(workspace_paths, "REVIEW_DECISIONS_PATH"), \
        "REVIEW_DECISIONS_PATH must be deleted per Singular Implementation"


def test_judgment_log_path_in_freddie_audit():
    """freddie_audit.JUDGMENT_LOG_PATH is the full /workspace/-prefixed path."""
    from services.freddie_audit import JUDGMENT_LOG_PATH
    assert JUDGMENT_LOG_PATH == "/workspace/persona/judgment_log.md"
    # And the legacy DECISIONS_PATH is gone
    from services import freddie_audit
    assert not hasattr(freddie_audit, "DECISIONS_PATH")


def test_append_recurrence_fire_deleted():
    """ADR-281 §5.D4 + Singular Implementation: blanket-write function deleted."""
    from services import freddie_audit
    assert not hasattr(freddie_audit, "append_recurrence_fire"), \
        "append_recurrence_fire must be deleted; replaced by render_lineage_entry_if_material"


def test_render_lineage_entry_if_material_exists():
    """ADR-281 §5.D2 + §5.D3: single-writer contract via material-outcome gate."""
    from services.freddie_audit import render_lineage_entry_if_material
    assert callable(render_lineage_entry_if_material)


def test_material_outcome_gate_routine_stand_down_renders_no_entry():
    """§5.D3: a Reviewer wake with no material outcome produces no lineage entry."""
    from services.freddie_audit import _detect_outcome_kind
    # stand_down with no material actions → None
    assert _detect_outcome_kind({"verdict": "stand_down", "actions_taken": []}) is None
    # only ReadFile calls → None (read-only wake, no outcome)
    assert _detect_outcome_kind({
        "verdict": "stand_down",
        "actions_taken": [
            {"tool": "ReadFile", "input": {"path": "/workspace/persona/IDENTITY.md"}, "result": {"success": True}},
            {"tool": "ListFiles", "input": {"path": "/workspace/context/"}, "result": {"success": True}},
        ],
    }) is None


def test_material_outcome_gate_propose_action_renders_entry():
    """§5.D3 condition 1: ProposeAction call → propose_action outcome."""
    from services.freddie_audit import _detect_outcome_kind
    assert _detect_outcome_kind({
        "verdict": "approve",
        "actions_taken": [
            {"tool": "ProposeAction", "input": {"action_type": "trading.submit_order"}, "result": {"success": True}},
        ],
    }) == "propose_action"


def test_material_outcome_gate_schedule_create_renders_entry():
    """§5.D3 condition 2: Schedule with action=create → schedule_create outcome."""
    from services.freddie_audit import _detect_outcome_kind
    assert _detect_outcome_kind({
        "verdict": "stand_down",
        "actions_taken": [
            {"tool": "Schedule", "input": {"action": "create", "slug": "morning-brief"}, "result": {"success": True}},
        ],
    }) == "schedule_create"


def test_material_outcome_gate_meta_verdict_renders_entry():
    """§5.D3 condition 5: meta-level verdict → meta_verdict:<verdict> outcome."""
    from services.freddie_audit import _detect_outcome_kind
    for meta in ("pause_autonomy", "narrow", "relax", "character_note"):
        assert _detect_outcome_kind({"verdict": meta, "actions_taken": []}) == f"meta_verdict:{meta}"


def test_invocation_dispatcher_uses_render_lineage_entry():
    """ADR-281 §5.D4: the reactive dispatch path invokes
    render_lineage_entry_if_material, NOT the deleted append_recurrence_fire
    (call sites; doc-comments narrating the dissolution are allowed).

    2026-06-04: the dispatch path moved from the deleted
    services/invocation_dispatcher.py into services/wake.py (ADR-296 v2 →
    ADR-298 wake-architecture migration). The render-lineage invariant is
    unchanged; only the file moved."""
    src = (API_ROOT / "services" / "wake.py").read_text()
    # Walk lines: any executable Python referencing append_recurrence_fire is forbidden.
    # Comment lines (#) explaining the dissolution are allowed.
    for lineno, raw in enumerate(src.splitlines(), start=1):
        line = raw.strip()
        if line.startswith("#"):
            continue
        if "append_recurrence_fire" in raw:
            raise AssertionError(
                f"wake.py:{lineno}: live reference to "
                f"append_recurrence_fire (must be deleted): {raw.strip()!r}"
            )
    assert "render_lineage_entry_if_material" in src, \
        "wake.py must invoke render_lineage_entry_if_material"


def test_track_regime_does_not_write_judgment_log():
    """ADR-281 §5 / Derived Principle 19: track_regime.py writes substrate
    (`_regime_freshness.yaml`), not directly to the judgment log."""
    src = (API_ROOT / "services" / "primitives" / "track_regime.py").read_text()
    # Should not have a write_revision call targeting /workspace/persona/judgment_log.md
    # or /workspace/persona/judgment_log.md (post-rename or pre-rename).
    for path in ("/workspace/persona/judgment_log.md", "/workspace/persona/judgment_log.md"):
        # Path may appear in doc-comments explaining the refactor — that's OK.
        # What's forbidden: an active write call. Heuristic: check for `path=` argument
        # passing the path string.
        assert f'path="{path}"' not in src, f"track_regime.py must not write to {path}"
        assert f"path='{path}'" not in src, f"track_regime.py must not write to {path}"
    # And should write to _regime_freshness.yaml instead
    assert "_regime_freshness.yaml" in src, \
        "track_regime.py must write freshness state to _regime_freshness.yaml substrate"


def test_alpha_trader_workspace_guide_declares_judgment_log_role():
    """alpha-trader bundle workspace guide declares judgment_log.md as system-ledger.

    ADR-281 renamed decisions.md → judgment_log.md; ADR-320 relocated it from
    review/ to persona/. The guide must name the new path and carry no live
    reference to either legacy path.
    """
    guide = (BUNDLES_ROOT / "alpha-trader" / "reference-workspace" / "_workspace_guide.md").read_text()
    assert "persona/judgment_log.md" in guide
    assert "review/decisions.md" not in guide, "old (pre-ADR-281/320) path must be fully replaced"


def test_no_live_decisions_md_path_in_kernel_perception_files():
    """ADR-281 §5 grep gate: kernel-perception files reference judgment_log.md, not decisions.md.

    Doc-comment narration explaining the refactor IS allowed (e.g. "decisions.md was
    renamed to judgment_log.md per ADR-281 §5"). What's forbidden: live path strings.

    ADR-320: the canonical home moved from review/ to persona/, so the banned
    legacy path is the full pre-rename/pre-relocation `/workspace/review/decisions.md`.
    The current `/workspace/persona/judgment_log.md` is the correct live path and
    must NOT be flagged.
    """
    files_to_check = [
        API_ROOT / "services" / "workspace_paths.py",
        API_ROOT / "services" / "freddie_envelope.py",
        API_ROOT / "services" / "review_proposal_dispatch.py",
        API_ROOT / "agents" / "freddie_agent.py",
        API_ROOT / "agents" / "cockpit_awareness.py",
    ]
    for f in files_to_check:
        if not f.exists():
            continue
        content = f.read_text()
        for lineno, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            # Skip doc-comments that explain the refactor
            if stripped.startswith("#") or stripped.startswith("*"):
                continue
            # Skip lines that are obviously docstring narration about the rename
            if "renamed" in line.lower() or "ADR-281" in line or "deleted" in line.lower():
                continue
            # Live legacy path strings forbidden (pre-ADR-281 rename + pre-ADR-320 relocation).
            if "/workspace/review/decisions.md" in line:
                raise AssertionError(
                    f"{f.relative_to(API_ROOT)}:{lineno}: live legacy decisions.md path "
                    f"reference (must be persona/judgment_log.md): {line.strip()!r}"
                )


# ---------------------------------------------------------------------------
# 9. FOUNDATIONS + GLOSSARY canon updates
# ---------------------------------------------------------------------------

def test_foundations_axiom_1_fifth_subclause_added():
    """FOUNDATIONS Axiom 1 gains the substrate-organization-as-canon sub-clause."""
    fnd = (REPO_ROOT / "docs" / "architecture" / "FOUNDATIONS.md").read_text()
    assert "Substrate organization is operator-readable canon" in fnd, \
        "Axiom 1 must include the fifth sub-clause per ADR-281"


def test_glossary_substrate_pedagogy_section_added():
    """GLOSSARY gains the Substrate Pedagogy section with role taxonomy + judgment_log + ABI."""
    glossary = (REPO_ROOT / "docs" / "architecture" / "GLOSSARY.md").read_text()
    assert "Substrate Pedagogy (ADR-281" in glossary, \
        "GLOSSARY must include the Substrate Pedagogy section"
    # Role taxonomy entries
    for role in ("operator-canon", "reviewer-workbench", "system-ledger",
                 "world-mirror", "running-narrative", "kernel-index"):
        assert f"`{role}`" in glossary, f"GLOSSARY missing role taxonomy entry for {role}"
    # Judgment log + Substrate ABI
    assert "Judgment log" in glossary
    assert "Substrate ABI" in glossary
    assert "Material-outcome gate" in glossary
    assert "The kernel does not compute for the prompt" in glossary


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
