"""ADR-286 regression gate: kernel/program substrate boundary — single writer per path.

Asserts the structural invariants from ADR-286:
  - D1: Every path that any active bundle ships is NOT in workspace_init's
    `workspace_files` kernel-scaffold dict (with the ADR-383 steward-default
    carve — see below)
  - D2: Kernel-universal paths (the survivor set) ARE in workspace_files
  - D6: is_skeleton_content has been simplified — kernel-default rescue
    patches deleted, bundle-template-detection patches survive
  - D7: workspace_init no longer has the bundle_owned_paths skip block

The ADR-383 steward-default carve this gate once also pinned (MANDATE / IDENTITY /
principles seeded in the `if not program_slug:` branch, marked so a fork overwrites
them) is DELETED: ADR-414 D2 made genesis pure, ADR-632 retired the steward, and the
2026-09-12 residue sweep removed the constants and the four tests that named them.
What remains is the single-writer discipline itself — D1/D2/D6/D7 above.

Per discipline: AST + source-string assertions only. No live LLM call.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent


def _read_api(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _read_repo(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


# -----------------------------------------------------------------------------
# Bundle inventory — derived from active bundle reference-workspace directories.
# Future bundles inherit the rule by walking their directories the same way.
# -----------------------------------------------------------------------------

def _bundle_owned_paths() -> set[str]:
    """Walk every active bundle's reference-workspace/; return the set of
    workspace-relative paths each bundle ships."""
    paths: set[str] = set()
    programs_dir = REPO_ROOT / "docs" / "programs"
    if not programs_dir.is_dir():
        return paths
    for bundle_dir in programs_dir.iterdir():
        if not bundle_dir.is_dir():
            continue
        ref = bundle_dir / "reference-workspace"
        if not ref.is_dir():
            continue
        for f in list(ref.rglob("*.md")) + list(ref.rglob("*.yaml")):
            if f.name == "README.md" and f.parent == ref:
                # Bundle's top-level README is bundle-doc, not workspace substrate
                continue
            rel = f.relative_to(ref).as_posix()
            paths.add(f"/workspace/{rel}")
    return paths


# -----------------------------------------------------------------------------
# D1 — Kernel scaffold does NOT write bundle-owned paths
# -----------------------------------------------------------------------------

def test_workspace_init_does_not_scaffold_bundle_owned_paths() -> None:
    """The workspace_init `workspace_files` dict must NOT contain any
    workspace-relative path that any active bundle ships. If this fails,
    the dual-write pathology has been reintroduced."""
    src = _read_api("services/workspace_init.py")

    bundle_paths = _bundle_owned_paths()
    assert bundle_paths, "Expected at least one bundle to ship reference-workspace/ paths"

    # Find the workspace_files dict literal in workspace_init.py — pre-ADR-286
    # it included MANDATE/IDENTITY/BRAND/AUTONOMY etc. as keys. Post-ADR-286
    # only kernel-universal paths are keys. ADR-383 carves the steward paths
    # back in (conditionally) — they are NOT in this ban list (the conditional-
    # seeding discipline is asserted separately below).
    #
    # ADR-383 amendment (2026-07-02): GOVERNANCE_AUTONOMY_YAML_PATH moved OUT of
    # this ban list — it is now a steward-seed (like MANDATE/IDENTITY/principles).
    # The prose GOVERNANCE_AUTONOMY_PATH (AUTONOMY.md) stays bundle-owned/banned.
    # ADR-432 D1c: OPERATION_BRAND_PATH removed from this set — Brand retired.
    bundle_owned_constants = {
        "GOVERNANCE_AUTONOMY_PATH",
        "SYSTEM_AWARENESS_PATH",
    }

    # Locate the workspace_files dict — and include the conditional
    # `if not program_slug:` block that follows it (the steward seeds + the
    # workspace-guide default land there). The base dict literal closes at the
    # first `}\n`; the steward seeds are appended after via
    # `workspace_files[...] = (...)` assignments inside the conditional.
    dict_start = src.find("workspace_files = {")
    assert dict_start != -1, "workspace_files dict must exist in workspace_init.py"
    # Scan to the end of Phase 2's file-writing loop (`for path, (content`)
    # so both the dict literal AND the conditional steward-seed assignments
    # are in scope for the ban check.
    scan_end = src.find("for path, (content", dict_start)
    assert scan_end != -1, "Phase-2 file-write loop must follow workspace_files"
    scaffold_block = src[dict_start:scan_end]

    leaked = [c for c in bundle_owned_constants if c in scaffold_block]
    assert not leaked, (
        f"workspace_files scaffold leaks bundle-owned paths (ADR-286 D1 violation): "
        f"{leaked}. Move these to bundle-fork ownership."
    )


def test_workspace_init_drops_bundle_owned_imports() -> None:
    """The bundle-owned constants (DEFAULT_MANDATE_MD, DEFAULT_IDENTITY_MD,
    etc.) must no longer be imported in workspace_init.py — they're dead
    imports if the dict no longer uses them."""
    src = _read_api("services/workspace_init.py")
    # ADR-383: CONSTITUTION_MANDATE_PATH / PERSONA_IDENTITY_PATH /
    # PERSONA_PRINCIPLES_PATH + the DEFAULT_STEWARD_* constants are now
    # legitimately imported (the steward seeds). The bundle-OWNED constants
    # (the program's own MANDATE/IDENTITY/principles content + BRAND/AUTONOMY/
    # AWARENESS) stay banned — those are bundle-fork-only.
    # ADR-432 D1c: DEFAULT_BRAND_MD + OPERATION_BRAND_PATH removed from the ban
    # list — those constants no longer exist (Brand retired).
    banned_imports = {
        "DEFAULT_IDENTITY_MD",
        "DEFAULT_AUTONOMY_MD",
        "DEFAULT_AWARENESS_MD",
        "DEFAULT_REVIEW_IDENTITY_MD",
        "DEFAULT_REVIEW_PRINCIPLES_MD",
        "GOVERNANCE_AUTONOMY_PATH",
        "GOVERNANCE_AUTONOMY_YAML_PATH",
        "SYSTEM_AWARENESS_PATH",
    }
    # Find the import block from `from services.orchestration import (`
    # and `from services.workspace_paths import (` — assert none of the
    # banned names appear.
    for module in ("services.orchestration", "services.workspace_paths"):
        idx = src.find(f"from {module} import (")
        if idx == -1:
            continue
        close = src.find(")", idx)
        block = src[idx:close]
        leaked = [n for n in banned_imports if n in block]
        assert not leaked, (
            f"workspace_init still imports bundle-owned constants from {module} "
            f"(ADR-286 D7 dead-import violation): {leaked}"
        )


# -----------------------------------------------------------------------------
# D2 — Kernel-universal paths survive in the scaffold
# -----------------------------------------------------------------------------

def test_is_skeleton_content_kernel_default_patches_deleted() -> None:
    """Pre-ADR-286 kernel-default rescue patches must be deleted from
    is_skeleton_content. They existed solely to detect kernel defaults
    masquerading as authored content — a problem ADR-286 eliminates."""
    src = _read_api("services/workspace_utils.py")
    banned_patches = [
        "not yet declared",
        "not yet provided",
        "<!-- identity not yet",
        "<!-- brand not yet",
        "<!-- mandate not yet",
        "this is the declared review framework for this workspace",
        "this workspace runs no program",
    ]
    # These strings should no longer appear in the function body as content
    # checks (they may appear in docstring/comments referencing the deletion).
    # We check the function body specifically.
    fn_start = src.find("def is_skeleton_content")
    fn_end = src.find("\ndef ", fn_start + 1)
    body = src[fn_start:fn_end]
    # Strip docstring (between """..."""). The docstring may legitimately
    # mention the deleted patches as part of the "Deleted post-ADR-286" list.
    if '"""' in body:
        first_quote = body.find('"""')
        second_quote = body.find('"""', first_quote + 3)
        body_no_doc = body[:first_quote] + body[second_quote + 3:]
    else:
        body_no_doc = body
    for pattern in banned_patches:
        assert pattern.lower() not in body_no_doc.lower(), (
            f"is_skeleton_content body still contains deleted kernel-default "
            f"rescue patch: '{pattern}' (ADR-286 D6 violation)"
        )


def test_is_skeleton_content_template_detection_survives() -> None:
    """Bundle-template detection (used for surface display + activation gate)
    must survive — operator-hasn't-overwritten-yet detection."""
    from services.workspace_utils import is_skeleton_content
    assert is_skeleton_content(""), "empty must classify as skeleton"
    assert is_skeleton_content("# Heading (template)"), "(template) marker must classify as skeleton"
    assert is_skeleton_content("# Short\n\n**Operator**: author this here"), (
        "short bundle template prompt must classify as skeleton"
    )
    # Bundle-body exact match
    body = "# Some bundle content\n## Section\nstuff"
    assert is_skeleton_content(body, bundle_body=body), (
        "exact match to bundle_body must classify as skeleton"
    )
    # Operator-authored content
    assert not is_skeleton_content(
        "# My mandate\n\nWe make money trading momentum signals on liquid US equities.\n\n## Success criteria\n- Net Sharpe > 1.0"
    ), "substantive operator content must NOT classify as skeleton"


# -----------------------------------------------------------------------------
# D7 — bundle_owned_paths skip block deleted
# -----------------------------------------------------------------------------

def test_bundle_owned_paths_skip_block_deleted() -> None:
    """The ADR-269 iter-4 bundle_owned_paths skip block is unnecessary
    under ADR-286 (there's no kernel write to skip). Deletion required
    per ADR-286 D7."""
    src = _read_api("services/workspace_init.py")
    # The original block was named `bundle_owned_paths: set[str] = set()`
    # and iterated bundle reference-workspace at runtime. Post-ADR-286 it's gone.
    assert "bundle_owned_paths: set[str] = set()" not in src, (
        "bundle_owned_paths skip block must be deleted per ADR-286 D7 — "
        "no kernel write to skip when kernel doesn't write bundle-owned paths"
    )


# -----------------------------------------------------------------------------
# Signature cleanup
# -----------------------------------------------------------------------------