"""Regression gate for ADR-292 — Operator-Initiated Versioned Substrate Update.

ADR-292 closes the kernel/bundle → live-workspace propagation gap via the
Claude Code `claude --update` model: platform versions substrate, operator
opts in on demand. NOT a daily cron, NOT a mechanical primitive.

This gate enforces the structural shape:

  1. substrate_reapply module exports the right public surface
     (apply_substrate_update + two detection helpers + dataclasses +
     constants); no longer exports the wrong-shape names.
  2. Attribution actor system:substrate-update is valid per ADR-209 taxonomy.
  3. ReapplyPlatformSubstrate is NOT in HANDLERS (wrong shape — reverted).
  4. back-office-substrate-reapply recurrence is NOT in any bundle's
     _recurrences.yaml (wrong shape — reverted).
  5. KERNEL_VERSION constant exists in orchestration.py and is non-empty.
  6. Both active bundles (alpha-trader + alpha-author) declare `version:`
     in MANIFEST.yaml.
  7. bundle_reader.get_bundle_version() helper resolves the version.
  8. MANDATE.md frontmatter parse/render round-trip is idempotent.
  9. MANDATE.md frontmatter version-stamp write preserves heading + body.
  10. ADR-292 doc + propagation-discipline.md exist + reference each other.

Run:
    .venv/bin/python -m api.test_adr292_continuous_reapply
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_PASS: list[str] = []
_FAIL: list[tuple[str, str]] = []


def _ok(name: str) -> None:
    _PASS.append(name)
    print(f"  ✓ {name}")


def _bad(name: str, reason: str) -> None:
    _FAIL.append((name, reason))
    print(f"  ✗ {name}\n      {reason}")


# ---------------------------------------------------------------------------
# 1. substrate_reapply module exports — operator-initiated shape
# ---------------------------------------------------------------------------

def test_module_exports_correct_shape() -> None:
    try:
        from services import substrate_reapply
    except Exception as e:
        _bad("substrate_reapply module imports", f"import failed: {e}")
        return

    needed = [
        "apply_substrate_update",
        "bundle_update_available",
        "kernel_update_available",
        "BundleUpdateInfo",
        "KernelUpdateInfo",
        "UpdateReport",
        "UpdateAction",
        "ConflictedFile",  # ADR-292 v3 D10
        "UPDATE_AUDIT_LOG_PATH",
        "UPDATE_AUTHORED_BY",
        "CONFIG_PATHS",  # ADR-292 v3 D9
        "CONFLICT_BACKUP_PREFIX",  # ADR-292 v3 D10
    ]
    missing = [s for s in needed if not hasattr(substrate_reapply, s)]
    if not missing:
        _ok(f"substrate_reapply exports operator-initiated public surface ({len(needed)} symbols incl. v3)")
    else:
        _bad("substrate_reapply exports", f"missing: {missing}")


def test_wrong_shape_exports_absent() -> None:
    """Sanity: the reverted names (mechanical-primitive surface) are gone."""
    try:
        from services import substrate_reapply
    except Exception as e:
        _bad("substrate_reapply module imports for negative check", f"{e}")
        return

    forbidden = [
        "REAPPLY_PLATFORM_SUBSTRATE_TOOL",       # mechanical-primitive tool def
        "handle_reapply_platform_substrate",     # mechanical-primitive handler
        "reapply_platform_substrate",            # old daily-cron entry point
        "REAPPLY_AUTHORED_BY",                   # renamed to UPDATE_AUTHORED_BY
        "REAPPLY_AUDIT_LOG_PATH",                # renamed to UPDATE_AUDIT_LOG_PATH
        "ReapplyReport",                         # renamed to UpdateReport
        "ReapplyAction",                         # renamed to UpdateAction
    ]
    leaked = [s for s in forbidden if hasattr(substrate_reapply, s)]
    if not leaked:
        _ok("wrong-shape exports absent (Singular Implementation honored)")
    else:
        _bad(
            "wrong-shape exports present",
            f"leaked symbols from reverted shape: {leaked}. "
            f"Singular Implementation requires deletion, not co-existence.",
        )


def test_audit_log_path_constant() -> None:
    from services.substrate_reapply import UPDATE_AUDIT_LOG_PATH

    expected = "_shared/substrate-update-log.md"
    if UPDATE_AUDIT_LOG_PATH == expected:
        _ok(f"UPDATE_AUDIT_LOG_PATH == {expected!r}")
    else:
        _bad("UPDATE_AUDIT_LOG_PATH value", f"expected {expected!r}, got {UPDATE_AUDIT_LOG_PATH!r}")


def test_attribution_actor() -> None:
    from services.substrate_reapply import UPDATE_AUTHORED_BY
    from services.authored_substrate import is_valid_author

    expected = "system:substrate-update"
    if UPDATE_AUTHORED_BY != expected:
        _bad("UPDATE_AUTHORED_BY value", f"expected {expected!r}, got {UPDATE_AUTHORED_BY!r}")
        return

    if is_valid_author(UPDATE_AUTHORED_BY):
        _ok(f"UPDATE_AUTHORED_BY == {expected!r} (passes ADR-209 taxonomy)")
    else:
        _bad("UPDATE_AUTHORED_BY taxonomy", f"{UPDATE_AUTHORED_BY!r} rejected by is_valid_author")


# ---------------------------------------------------------------------------
# 2. Wrong-shape mechanical surface is reverted
# ---------------------------------------------------------------------------

def test_mechanical_primitive_not_registered() -> None:
    """ReapplyPlatformSubstrate must NOT be in HANDLERS — wrong-shape revert."""
    from services.primitives.registry import HANDLERS

    if "ReapplyPlatformSubstrate" in HANDLERS:
        _bad(
            "ReapplyPlatformSubstrate absent from HANDLERS",
            "primitive should NOT be registered — operator-initiated update "
            "is not a mechanical dispatcher primitive. Wrong shape from the "
            "reverted commit.",
        )
    else:
        _ok("ReapplyPlatformSubstrate absent from HANDLERS (wrong shape reverted)")


def test_daily_recurrence_not_shipped() -> None:
    """back-office-substrate-reapply must NOT be in any bundle — wrong-shape revert."""
    bundle_root = REPO_ROOT / "docs" / "programs"
    leaks: list[str] = []
    for slug_dir in bundle_root.iterdir():
        if not slug_dir.is_dir():
            continue
        recurrences_path = slug_dir / "reference-workspace" / "_recurrences.yaml"
        if not recurrences_path.is_file():
            continue
        try:
            data = yaml.safe_load(recurrences_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            _bad(f"parse {recurrences_path}", str(e))
            continue
        for rec in data.get("recurrences", []) or []:
            if rec.get("slug") == "back-office-substrate-reapply":
                leaks.append(slug_dir.name)

    if not leaks:
        _ok("back-office-substrate-reapply absent from all bundles (wrong shape reverted)")
    else:
        _bad(
            "daily recurrence absent",
            f"recurrence leaked in bundle(s): {leaks}. Operator-initiated "
            f"update is not a cron — daily recurrence must not exist.",
        )


# ---------------------------------------------------------------------------
# 3. Version stamps
# ---------------------------------------------------------------------------

def test_kernel_version_constant() -> None:
    try:
        from services.orchestration import KERNEL_VERSION
    except Exception as e:
        _bad("KERNEL_VERSION import", f"{e}")
        return

    if isinstance(KERNEL_VERSION, str) and KERNEL_VERSION.strip():
        _ok(f"KERNEL_VERSION = {KERNEL_VERSION!r}")
    else:
        _bad("KERNEL_VERSION shape", f"expected non-empty string, got {KERNEL_VERSION!r}")


def test_alpha_trader_bundle_has_version() -> None:
    manifest_path = REPO_ROOT / "docs" / "programs" / "alpha-trader" / "MANIFEST.yaml"
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    version = data.get("version")
    if isinstance(version, str) and version.strip():
        _ok(f"alpha-trader MANIFEST.yaml declares version={version!r}")
    else:
        _bad("alpha-trader version", f"missing or empty `version:` field; got {version!r}")


def test_alpha_author_bundle_has_version() -> None:
    manifest_path = REPO_ROOT / "docs" / "programs" / "alpha-author" / "MANIFEST.yaml"
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    version = data.get("version")
    if isinstance(version, str) and version.strip():
        _ok(f"alpha-author MANIFEST.yaml declares version={version!r}")
    else:
        _bad("alpha-author version", f"missing or empty `version:` field; got {version!r}")


def test_get_bundle_version_helper() -> None:
    from services.bundle_reader import get_bundle_version

    trader_v = get_bundle_version("alpha-trader")
    author_v = get_bundle_version("alpha-author")
    if not trader_v:
        _bad("get_bundle_version('alpha-trader')", f"got {trader_v!r}")
        return
    if not author_v:
        _bad("get_bundle_version('alpha-author')", f"got {author_v!r}")
        return

    # Non-existent bundle returns None
    none_v = get_bundle_version("does-not-exist")
    if none_v is not None:
        _bad("get_bundle_version unknown slug", f"expected None, got {none_v!r}")
        return

    _ok("get_bundle_version() resolves declared versions + returns None for unknown")


# ---------------------------------------------------------------------------
# 4. MANDATE.md frontmatter round-trip
# ---------------------------------------------------------------------------

def test_frontmatter_empty_roundtrip() -> None:
    """No frontmatter present → parse returns empty dict + content unchanged."""
    from services.substrate_reapply import _parse_frontmatter, _render_frontmatter

    body = "# Mandate — alpha-trader (template)\n\nDeclare your standing intent here.\n"
    fm, rest = _parse_frontmatter(body)
    if fm != {} or rest != body:
        _bad(
            "frontmatter empty parse",
            f"expected ({{}} body unchanged), got ({fm!r}, {rest!r})",
        )
        return

    rendered = _render_frontmatter(fm, rest)
    if rendered == body:
        _ok("empty-frontmatter parse + render is idempotent")
    else:
        _bad("frontmatter empty render", f"expected body unchanged, got {rendered!r}")


def test_frontmatter_write_preserves_body() -> None:
    """Adding version stamps to a no-frontmatter MANDATE.md preserves heading + body."""
    from services.substrate_reapply import _write_workspace_versions, _read_workspace_versions

    original = "# Mandate — alpha-trader (template)\n\nDeclare your standing intent here.\n"
    updated = _write_workspace_versions(
        original,
        bundle_version="2026-05-18.1",
        kernel_version="2026-05-18.1",
    )
    # Verify frontmatter present
    if not updated.startswith("---\n"):
        _bad(
            "frontmatter write preserves body",
            f"expected updated content to start with '---\\n', got: {updated[:50]!r}",
        )
        return
    # Verify body preserved verbatim AFTER the frontmatter block
    if "# Mandate — alpha-trader (template)" not in updated or "Declare your standing intent here." not in updated:
        _bad(
            "frontmatter write preserves body",
            f"heading or body lost after frontmatter write: {updated!r}",
        )
        return
    # Verify round-trip read
    b, k = _read_workspace_versions(updated)
    if b != "2026-05-18.1" or k != "2026-05-18.1":
        _bad(
            "frontmatter read after write",
            f"expected ('2026-05-18.1', '2026-05-18.1'), got ({b!r}, {k!r})",
        )
        return

    _ok("frontmatter write preserves body + read round-trips")


def test_frontmatter_idempotent_second_write() -> None:
    """Writing the same version stamps twice produces identical content."""
    from services.substrate_reapply import _write_workspace_versions

    original = "# Mandate\n\nBody.\n"
    first = _write_workspace_versions(original, bundle_version="v1", kernel_version="v1")
    second = _write_workspace_versions(first, bundle_version="v1", kernel_version="v1")
    if first == second:
        _ok("frontmatter write is idempotent (same version stamps → same content)")
    else:
        _bad(
            "frontmatter idempotency",
            f"second write differs from first:\nfirst:\n{first}\nsecond:\n{second}",
        )


# ---------------------------------------------------------------------------
# 5. UpdateReport shape
# ---------------------------------------------------------------------------

def test_update_report_shape() -> None:
    import dataclasses
    from services.substrate_reapply import UpdateReport, UpdateAction

    required_report = {
        "user_id", "source", "ran_at", "scope", "program_slug",
        "kernel_from", "kernel_to", "bundle_from", "bundle_to",
        "actions", "skipped_operator_authored", "skipped_aligned",
        "config_conflicts",  # ADR-292 v3 D10
        "error",
    }
    actual_report = {f.name for f in dataclasses.fields(UpdateReport)}
    missing = required_report - actual_report
    if missing:
        _bad("UpdateReport fields", f"missing: {missing}")
        return

    required_action = {"path", "layer", "change_summary"}
    actual_action = {f.name for f in dataclasses.fields(UpdateAction)}
    missing_action = required_action - actual_action
    if missing_action:
        _bad("UpdateAction fields", f"missing: {missing_action}")
        return

    # Smoke render
    report = UpdateReport(
        user_id="test-user",
        source="test",
        ran_at="2026-05-18T00:00:00+00:00",
        scope="both",
        program_slug="alpha-trader",
        kernel_from="2026-05-17",
        kernel_to="2026-05-18.1",
        bundle_from="2026-05-17",
        bundle_to="2026-05-18.1",
        actions=[
            UpdateAction(path="system/_playbook.md", layer="kernel", change_summary="canon updated"),
        ],
        skipped_operator_authored=2,
        skipped_aligned=10,
    )
    md = report.to_log_markdown()
    if "Substrate update" in md and "alpha-trader" in md and "system/_playbook.md" in md and "2026-05-18.1" in md:
        _ok("UpdateReport.to_log_markdown produces structured audit-log block")
    else:
        _bad("to_log_markdown output", f"missing expected markers: {md[:300]}...")


# ---------------------------------------------------------------------------
# 5b. v3 — ConflictedFile + config-conflict rendering (ADR-292 v3 D9+D10)
# ---------------------------------------------------------------------------

def test_conflicted_file_dataclass_shape() -> None:
    """ConflictedFile carries path + backup_path + bundle_version (D10)."""
    import dataclasses
    from services.substrate_reapply import ConflictedFile

    required = {"path", "backup_path", "bundle_version"}
    actual = {f.name for f in dataclasses.fields(ConflictedFile)}
    missing = required - actual
    if missing:
        _bad("ConflictedFile fields", f"missing: {missing}")
        return
    _ok(f"ConflictedFile carries required fields {sorted(required)}")


def test_config_paths_closed_set() -> None:
    """CONFIG_PATHS is a frozenset containing exactly _recurrences.yaml + _hooks.yaml.

    Per ADR-292 v3 D9 this is the closed-set policy declaration. Adding a third
    file is an ADR amendment, not a code change in isolation.
    """
    from services.substrate_reapply import CONFIG_PATHS

    if not isinstance(CONFIG_PATHS, frozenset):
        _bad("CONFIG_PATHS type", f"expected frozenset, got {type(CONFIG_PATHS).__name__}")
        return

    expected = frozenset({"_recurrences.yaml", "_hooks.yaml"})
    if CONFIG_PATHS != expected:
        _bad(
            "CONFIG_PATHS value",
            f"expected {expected}, got {CONFIG_PATHS}. Adding/removing entries "
            f"requires an ADR amendment per D9.",
        )
        return
    _ok(f"CONFIG_PATHS == {sorted(CONFIG_PATHS)} (ADR-292 v3 D9 closed-set)")


def test_conflict_backup_prefix_value() -> None:
    from services.substrate_reapply import CONFLICT_BACKUP_PREFIX

    expected = "_shared/conflict-backups"
    if CONFLICT_BACKUP_PREFIX == expected:
        _ok(f"CONFLICT_BACKUP_PREFIX == {expected!r}")
    else:
        _bad(
            "CONFLICT_BACKUP_PREFIX value",
            f"expected {expected!r}, got {CONFLICT_BACKUP_PREFIX!r}",
        )


def test_update_report_renders_config_conflicts() -> None:
    """to_log_markdown surfaces config_conflicts with backup paths."""
    from services.substrate_reapply import UpdateReport, ConflictedFile

    report = UpdateReport(
        user_id="test-user",
        source="test",
        ran_at="2026-05-20T11:00:00+00:00",
        scope="bundle",
        program_slug="alpha-trader",
        kernel_from=None,
        kernel_to=None,
        bundle_from="2026-05-18.1",
        bundle_to="2026-05-20.1",
        config_conflicts=[
            ConflictedFile(
                path="_recurrences.yaml",
                backup_path="_shared/conflict-backups/2026-05-20T11-00-00Z/_recurrences.yaml",
                bundle_version="2026-05-20.1",
            ),
        ],
    )
    md = report.to_log_markdown()

    required_markers = [
        "Config conflicts auto-resolved",
        "_recurrences.yaml",
        "_shared/conflict-backups/2026-05-20T11-00-00Z/_recurrences.yaml",
        "2026-05-20.1",
        "operator may inspect the backup",  # case-insensitive substring
    ]
    md_lower = md.lower()
    missing = [m for m in required_markers if m.lower() not in md_lower]
    if missing:
        _bad(
            "config_conflicts rendering",
            f"missing markers: {missing}\nRendered:\n{md}",
        )
        return
    _ok("UpdateReport renders config_conflicts with backup-path discoverability")


def test_fork_return_shape_includes_v3_fields() -> None:
    """fork_reference_workspace return dict includes config_conflicts + bundle_version (D10)."""
    import inspect
    from services.programs import fork_reference_workspace

    # We can't run the async fork in this synchronous test gate, but we can
    # check the docstring + source as a structural smoke test.
    src = inspect.getsource(fork_reference_workspace)
    needed_returns = [
        '"config_conflicts": config_conflicts',
        '"bundle_version": bundle_version',
    ]
    missing = [m for m in needed_returns if m not in src]
    if missing:
        _bad(
            "fork_reference_workspace return shape",
            f"v3 return-dict keys not found in source: {missing}",
        )
        return
    _ok("fork_reference_workspace returns config_conflicts + bundle_version (v3)")


def test_fork_decision_tree_branches_present() -> None:
    """fork_reference_workspace source contains all 5 v3 decision-tree branches."""
    import inspect
    from services.programs import fork_reference_workspace

    src = inspect.getsource(fork_reference_workspace)
    branches = [
        "write_new",
        "skip_aligned",
        "write_refresh_skeleton",
        "config_conflict_auto_resolve",
        "skip_operator_authored_prose",
    ]
    missing = [b for b in branches if b not in src]
    if missing:
        _bad(
            "fork_reference_workspace decision tree (D10)",
            f"missing branches: {missing}",
        )
        return
    _ok(f"fork_reference_workspace decision tree has all 5 branches per D10")


# ---------------------------------------------------------------------------
# 6. Detection-helper shape (sync — checks they exist + are coroutines)
# ---------------------------------------------------------------------------

def test_detection_helpers_are_coroutines() -> None:
    import inspect
    from services.substrate_reapply import bundle_update_available, kernel_update_available

    if not inspect.iscoroutinefunction(bundle_update_available):
        _bad("bundle_update_available", "not a coroutine function")
        return
    if not inspect.iscoroutinefunction(kernel_update_available):
        _bad("kernel_update_available", "not a coroutine function")
        return
    _ok("detection helpers are async coroutine functions")


def test_apply_substrate_update_signature() -> None:
    """apply_substrate_update must accept (client, user_id, *, scope, source)."""
    import inspect
    from services.substrate_reapply import apply_substrate_update

    if not inspect.iscoroutinefunction(apply_substrate_update):
        _bad("apply_substrate_update", "not a coroutine function")
        return

    sig = inspect.signature(apply_substrate_update)
    params = list(sig.parameters)
    if params[:2] != ["client", "user_id"]:
        _bad(
            "apply_substrate_update signature",
            f"expected first two positional params (client, user_id), got {params[:2]}",
        )
        return
    if "scope" not in sig.parameters or "source" not in sig.parameters:
        _bad(
            "apply_substrate_update signature",
            f"missing keyword params (scope, source); got: {params}",
        )
        return
    _ok("apply_substrate_update(client, user_id, *, scope, source) signature correct")


# ---------------------------------------------------------------------------
# 7. ADR + planning doc cross-references
# ---------------------------------------------------------------------------

def test_adr292_doc_exists() -> None:
    adr_path = REPO_ROOT / "docs" / "adr" / "ADR-292-continuous-substrate-reapply.md"
    if adr_path.is_file():
        _ok(f"ADR-292 doc exists at {adr_path.relative_to(REPO_ROOT)}")
    else:
        _bad("ADR-292 doc", f"missing: {adr_path}")


def test_planning_doc_references_adr292() -> None:
    planning = REPO_ROOT / "docs" / "architecture" / "propagation-discipline.md"
    if not planning.is_file():
        _bad("planning doc exists", f"missing: {planning}")
        return
    content = planning.read_text(encoding="utf-8")
    if "ADR-292" in content:
        _ok("propagation-discipline.md references ADR-292")
    else:
        _bad("planning doc references ADR-292", "ADR-292 not cited")


def test_adr292_doc_reflects_operator_initiated_shape() -> None:
    """The ADR text must reflect the corrected shape — not the reverted daily-cron shape."""
    adr_path = REPO_ROOT / "docs" / "adr" / "ADR-292-continuous-substrate-reapply.md"
    if not adr_path.is_file():
        _bad("ADR-292 shape check", "ADR file missing")
        return
    content = adr_path.read_text(encoding="utf-8")

    # Positive markers — must be present
    positive = ["Operator-Initiated", "claude --update", "apply_substrate_update", "KERNEL_VERSION", "MANDATE.md frontmatter"]
    missing = [m for m in positive if m not in content]
    if missing:
        _bad(
            "ADR-292 positive markers",
            f"missing markers indicating operator-initiated shape: {missing}",
        )
        return

    # Negative markers — must NOT be present as live design. The ADR is
    # allowed to NAME the reverted shape in the "Drafting history" + "Explicit
    # non-goals" sections (that's the historical-context and the
    # singular-implementation discipline-record); the test verifies the
    # corrected shape is the *operative* design, not that historical phrases
    # are scrubbed.
    #
    # Heuristic: count occurrences of each negative phrase. ≤2 = legitimate
    # historical/non-goal mention. ≥3 = leaked as live design.
    negative_phrases = ["back-office-substrate-reapply", "daily cron"]
    overused = []
    lower = content.lower()
    for phrase in negative_phrases:
        if lower.count(phrase.lower()) >= 3:
            overused.append(f"{phrase} (count={lower.count(phrase.lower())})")
    if overused:
        _bad(
            "ADR-292 negative-marker overuse",
            f"reverted-shape language appears too often to be just historical: {overused}",
        )
        return

    _ok("ADR-292 text reflects operator-initiated shape (corrected from reverted v1)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    print("ADR-292 — Operator-Initiated Versioned Substrate Update regression gate\n")

    test_module_exports_correct_shape()
    test_wrong_shape_exports_absent()
    test_audit_log_path_constant()
    test_attribution_actor()
    test_mechanical_primitive_not_registered()
    test_daily_recurrence_not_shipped()
    test_kernel_version_constant()
    test_alpha_trader_bundle_has_version()
    test_alpha_author_bundle_has_version()
    test_get_bundle_version_helper()
    test_frontmatter_empty_roundtrip()
    test_frontmatter_write_preserves_body()
    test_frontmatter_idempotent_second_write()
    test_update_report_shape()
    test_conflicted_file_dataclass_shape()
    test_config_paths_closed_set()
    test_conflict_backup_prefix_value()
    test_update_report_renders_config_conflicts()
    test_fork_return_shape_includes_v3_fields()
    test_fork_decision_tree_branches_present()
    test_detection_helpers_are_coroutines()
    test_apply_substrate_update_signature()
    test_adr292_doc_exists()
    test_planning_doc_references_adr292()
    test_adr292_doc_reflects_operator_initiated_shape()

    total = len(_PASS) + len(_FAIL)
    print(f"\n{len(_PASS)}/{total} pass")
    if _FAIL:
        print("\nFAILURES:")
        for name, reason in _FAIL:
            print(f"  • {name}: {reason}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
