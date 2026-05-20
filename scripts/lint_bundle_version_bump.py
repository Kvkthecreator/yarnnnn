#!/usr/bin/env python3
"""ADR-292 v3 D11 — CI lint enforcing bundle version bump on content changes.

Rule: any change under `docs/programs/{slug}/reference-workspace/` or
`docs/programs/{slug}/specs/` requires a bump in the corresponding
`docs/programs/{slug}/MANIFEST.yaml::version` in the same commit (or in a
commit ahead of the change in the same PR / push).

The drift class this catches: ADR-296 v2 Checkpoint 2 (commit `37426c5`)
modified bundle reference-workspace files for both alpha-trader and
alpha-author without bumping `version:` in either `MANIFEST.yaml`. Live
workspaces had no path to detect the update because `bundle_update_available()`
compares version strings and both matched. Code shipped at deploy; bundles
did not propagate.

This lint makes that mistake impossible — running it before commit (or in CI
on the PR head vs main) surfaces the missing bump as a hard failure.

Usage:
    # Check against main (CI mode):
    python scripts/lint_bundle_version_bump.py

    # Check against a specific ref:
    python scripts/lint_bundle_version_bump.py --base-ref origin/main

    # Check working-tree (uncommitted + staged):
    python scripts/lint_bundle_version_bump.py --working-tree

Exit codes:
    0 — clean (no bundle content changes, or all content changes have version bumps)
    1 — at least one bundle has content changes without a version bump
    2 — invocation error (bad ref, etc.)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLES_DIR = REPO_ROOT / "docs" / "programs"


def _run_git(args: list[str]) -> str:
    """Run a git command from REPO_ROOT; return stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )
    return result.stdout


def _changed_files(base_ref: Optional[str], working_tree: bool) -> set[str]:
    """Return repo-relative paths changed in the relevant range."""
    if working_tree:
        # Uncommitted + staged changes (covers `git status` shape).
        # `git diff HEAD` includes both staged and unstaged.
        out = _run_git(["diff", "--name-only", "HEAD"])
    else:
        ref = base_ref or "origin/main"
        # Compare HEAD against the merge-base of HEAD and base_ref. This
        # captures the diff introduced by the current branch / PR, not
        # unrelated changes pulled in from upstream.
        try:
            merge_base = _run_git(["merge-base", "HEAD", ref]).strip()
        except RuntimeError as exc:
            # If base_ref doesn't exist (e.g., fresh clone without origin),
            # fall back to HEAD~1.
            print(
                f"warning: could not resolve merge-base with {ref!r}; "
                f"falling back to HEAD~1 ({exc})",
                file=sys.stderr,
            )
            merge_base = "HEAD~1"
        out = _run_git(["diff", "--name-only", f"{merge_base}...HEAD"])
    return {line.strip() for line in out.splitlines() if line.strip()}


def _bundle_slugs() -> list[str]:
    """Return list of bundle slugs that have a reference-workspace/ dir."""
    if not BUNDLES_DIR.is_dir():
        return []
    slugs = []
    for child in sorted(BUNDLES_DIR.iterdir()):
        if not child.is_dir():
            continue
        if (child / "reference-workspace").is_dir():
            slugs.append(child.name)
    return slugs


def _bundle_content_paths_prefixes(slug: str) -> list[str]:
    """Repo-relative path prefixes whose change requires version bump."""
    return [
        f"docs/programs/{slug}/reference-workspace/",
        f"docs/programs/{slug}/specs/",
    ]


def _manifest_path(slug: str) -> str:
    return f"docs/programs/{slug}/MANIFEST.yaml"


def _bundle_content_changed(slug: str, changed: set[str]) -> list[str]:
    prefixes = _bundle_content_paths_prefixes(slug)
    return sorted([
        p for p in changed if any(p.startswith(prefix) for prefix in prefixes)
    ])


def _manifest_version_bumped(slug: str, base_ref: Optional[str], working_tree: bool) -> bool:
    """Return True if MANIFEST.yaml's `version:` line differs in the range."""
    manifest_rel = _manifest_path(slug)
    try:
        if working_tree:
            out = _run_git(["diff", "HEAD", "--", manifest_rel])
        else:
            ref = base_ref or "origin/main"
            try:
                merge_base = _run_git(["merge-base", "HEAD", ref]).strip()
            except RuntimeError:
                merge_base = "HEAD~1"
            out = _run_git(["diff", f"{merge_base}...HEAD", "--", manifest_rel])
    except RuntimeError as exc:
        print(f"error: could not diff {manifest_rel}: {exc}", file=sys.stderr)
        return False
    if not out.strip():
        return False
    # Look for a +version: line that has a corresponding -version: line.
    # Both must be present for a bump (added without removal would be a new
    # MANIFEST creation, which is its own case).
    has_plus = any(
        line.startswith("+version:") and not line.startswith("+++")
        for line in out.splitlines()
    )
    has_minus = any(
        line.startswith("-version:") and not line.startswith("---")
        for line in out.splitlines()
    )
    return has_plus and has_minus


def _new_manifest(slug: str, changed: set[str]) -> bool:
    """True if MANIFEST.yaml was newly added (no version-bump check needed)."""
    return _manifest_path(slug) in changed and not (BUNDLES_DIR / slug / "MANIFEST.yaml").exists()
    # Note: in a freshly-added bundle scenario the MANIFEST exists in the
    # working tree but didn't exist on the base ref; we treat this as
    # "no bump required" implicitly because the lint's job is to catch
    # content changes without version bumps, not to gate new bundle adds.


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Enforce ADR-292 v3 D11: bundle reference-workspace + specs "
            "content changes require a MANIFEST.yaml::version bump in the "
            "same range."
        )
    )
    parser.add_argument(
        "--base-ref",
        default=None,
        help="Git ref to compare against (default: origin/main).",
    )
    parser.add_argument(
        "--working-tree",
        action="store_true",
        help="Check working-tree (uncommitted + staged) instead of branch diff.",
    )
    args = parser.parse_args(argv)

    try:
        changed = _changed_files(args.base_ref, args.working_tree)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    slugs = _bundle_slugs()
    if not slugs:
        print("no bundles found under docs/programs/; nothing to lint")
        return 0

    failures: list[str] = []
    for slug in slugs:
        bundle_changes = _bundle_content_changed(slug, changed)
        if not bundle_changes:
            continue
        # Allow new-MANIFEST adds to bypass version-bump check (rare:
        # bundle creation commits).
        manifest_added = (
            _manifest_path(slug) in changed
            and (BUNDLES_DIR / slug / "MANIFEST.yaml").exists()
        )
        bumped = _manifest_version_bumped(slug, args.base_ref, args.working_tree)
        if bumped:
            print(
                f"✓ {slug}: {len(bundle_changes)} content file(s) changed, "
                f"MANIFEST.yaml version bumped"
            )
            continue
        if manifest_added:
            # Only acceptable if this is the first commit introducing the
            # bundle — see header note. Conservative: treat as failure
            # to surface the case for review.
            failures.append(
                f"{slug}: MANIFEST.yaml present but version line did not "
                f"change in range, and content files were modified. If this "
                f"is a new bundle, the first commit should establish "
                f"version:. If this is an existing bundle, bump version: to "
                f"trigger propagation."
            )
            continue
        failures.append(
            f"{slug}: {len(bundle_changes)} bundle content file(s) changed "
            f"but MANIFEST.yaml::version did not bump.\n    "
            + "\n    ".join(bundle_changes[:8])
            + (f"\n    ... and {len(bundle_changes) - 8} more" if len(bundle_changes) > 8 else "")
        )

    if not failures:
        print("\nADR-292 v3 D11 lint: clean")
        return 0

    print("\nADR-292 v3 D11 lint: FAILURES", file=sys.stderr)
    print(
        "\nBundle content changes require a MANIFEST.yaml::version bump per "
        "ADR-292 v3 D11. Without it, `bundle_update_available()` cannot "
        "detect the change, and live operator workspaces will not be "
        "offered the update via Settings → Workspace.\n",
        file=sys.stderr,
    )
    for f in failures:
        print(f"  ✗ {f}", file=sys.stderr)
    print(
        "\nFix: edit the affected MANIFEST.yaml's `version:` field to a new "
        "date-stamp (e.g., 2026-05-20.1). Same discipline as bumping "
        "api/prompts/CHANGELOG.md for prompt changes.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
