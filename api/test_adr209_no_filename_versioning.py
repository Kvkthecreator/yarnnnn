"""
Regression-guard — ADR-209 Phase 5.

Runs as a standalone script (pytest-compatible shape retained for future
CI integration). Asserts that live code does NOT reintroduce any of the
filename-versioning or /history/-subfolder patterns that the Authored
Substrate's revision chain replaces.

This is the permanent enforcement of the ADR-209 deprecation manifest.
If someone in the future adds (say) a `/runs/v{N}.md` write pattern back
to workspace.py, this test will fail and they'll have to either route
through write_revision (which lands a revision automatically — no need
for filename versioning) or explicitly justify the exception in the
banned-patterns allowlist below.

Scope: api/ + web/ live code only. Excludes:
  - venv / node_modules / __pycache__ / .next
  - api/prompts/CHANGELOG.md (historical record)
  - api/test_* (test files that deliberately reference the patterns to
    assert their absence, including this file)
  - docs/adr/ADR-119-*, docs/adr/ADR-209-*, docs/architecture/authored-substrate.md,
    docs/architecture/GLOSSARY.md (explicitly-scoped deprecation records)

Usage:
    cd api && python test_adr209_no_filename_versioning.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# =============================================================================
# Banned patterns — each must return ZERO live-code hits
# =============================================================================
#
# Each entry: (pattern, description). Patterns are POSIX extended regex for
# `grep -E`. Keep patterns specific enough to avoid false positives (e.g.,
# don't just grep `version` — too broad).

BANNED_PATTERNS = [
    # /history/ subfolder archival (ADR-119 Phase 3, superseded by ADR-209)
    (r"_archive_to_history", "ADR-119 Phase 3 archival helper — replaced by write_revision()"),
    (r"_cap_history", "ADR-119 Phase 3 version cap helper — revisions are uncapped"),
    (r"_is_evolving_file", "ADR-119 Phase 3 evolving-file gate — every file versions automatically now"),
    # `list_history` is a method name we deleted; guard against reintroduction.
    # Match boundary-delimited to avoid false positives like `list_history_sql`.
    (r"\blist_history\b", "ADR-119 Phase 3 history list method — replaced by ListRevisions primitive"),
    # Filename-versioning (ADR-209 §2: "versioning lives in a separate metadata plane, never in the namespace")
    (r"thesis-v[0-9]+\.md", "Filename-encoded versioning — use revision chain"),
    (r"-archive\.md\b", "Filename-encoded archive suffix — use revision chain"),
    # /history/{filename}/v{N}.md literal write patterns
    (r'/history/[^"\']*/v[0-9]+\.md', "Literal /history/v{N}.md path — use revision chain"),
    # ADR-176 Phase 4 entity-profile archive pattern constants
    (r"_MAX_PROFILE_VERSIONS", "ADR-176 Phase 4 entity-profile cap — archive pattern deleted by Phase 2"),
    (r"_ENTITY_PROFILE_FILENAMES", "ADR-176 Phase 4 entity-profile gate — archive pattern deleted by Phase 2"),
    (r"_MAX_HISTORY_VERSIONS", "ADR-119 Phase 3 cap constant — deleted"),
    (r"_EVOLVING_PATTERNS", "ADR-119 Phase 3 file pattern set — deleted"),
    (r"_EVOLVING_DIRS", "ADR-119 Phase 3 dir pattern set — deleted"),
]

# =============================================================================
# Search roots + exclusions
# =============================================================================

SEARCH_ROOTS = [
    REPO_ROOT / "api",
    REPO_ROOT / "web",
    REPO_ROOT / "docs",
]

EXCLUDED_DIRS = {
    "venv",
    "node_modules",
    "__pycache__",
    ".next",
    "previous_versions",
}

# Specific file paths that are permitted to mention banned patterns (historical
# records / test files / migration SQL). Everything else must be clean.
ALLOWED_FILES = {
    # Historical ADRs / doc records
    "docs/adr/ADR-119-workspace-filesystem-architecture.md",
    "docs/adr/ADR-209-authored-substrate.md",
    "docs/architecture/authored-substrate.md",
    "docs/architecture/GLOSSARY.md",
    # FOUNDATIONS v6.1 Axiom 1 second clause explicitly names the retired
    # filename-versioning patterns as part of the deprecation record — the
    # mention IS the axiomatic commitment that they are banned.
    "docs/architecture/FOUNDATIONS.md",
    # Prompt changelog — historical record of past prompt changes
    "api/prompts/CHANGELOG.md",
    # Test files — including this one — reference banned patterns deliberately
    "api/test_adr209_phase2.py",
    "api/test_adr209_phase3.py",
    "api/test_adr209_phase4.py",
    "api/test_adr209_phase5.py",
    "api/test_adr209_no_filename_versioning.py",
    # Migration 158 / 159 — migration SQL mentions /history/ in comments explaining the cleanup
    "supabase/migrations/158_adr209_authored_substrate.sql",
    "supabase/migrations/159_adr209_phase5_cleanup.sql",
}


def _is_allowed(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    if rel in ALLOWED_FILES:
        return True
    # Exclude paths under any excluded dir
    parts = set(rel.split("/"))
    if parts & EXCLUDED_DIRS:
        return True
    return False


def _search_pattern(pattern: str) -> list[tuple[str, str]]:
    """Run a scoped grep for `pattern`. Return [(relative_path, line), ...]."""
    hits: list[tuple[str, str]] = []
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        # -r recursive; -n line numbers; -E extended regex; -I skip binary.
        # Include Python / TypeScript / Markdown / SQL. Exclude dirs via
        # post-filter (shell --exclude-dir is inconsistent across platforms).
        result = subprocess.run(
            [
                "grep", "-rnEI",
                "--include=*.py",
                "--include=*.ts",
                "--include=*.tsx",
                "--include=*.md",
                "--include=*.sql",
                pattern,
                str(root),
            ],
            capture_output=True, text=True,
        )
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            # Line shape: /abs/path:line_num:content
            try:
                abs_path_str, _lineno, _ = line.split(":", 2)
            except ValueError:
                continue
            abs_path = Path(abs_path_str)
            if _is_allowed(abs_path):
                continue
            hits.append((abs_path.relative_to(REPO_ROOT).as_posix(), line))
    return hits


def main() -> int:
    all_violations: list[str] = []
    print("=== ADR-209 Phase 5 regression guard ===")
    for pattern, description in BANNED_PATTERNS:
        hits = _search_pattern(pattern)
        status = "✓" if not hits else "✗"
        print(f"{status} {pattern!r:<45s} ({len(hits)} hits) — {description}")
        for rel, line in hits[:5]:
            print(f"    {line.strip()}")
            all_violations.append(f"{pattern}: {line.strip()}")
        if len(hits) > 5:
            print(f"    …and {len(hits) - 5} more")

    print()
    if all_violations:
        print(f"✗ FAIL — {len(all_violations)} banned-pattern references in live code.")
        print("  If the reference is intentional (e.g., new test or migration), add the")
        print("  file path to ALLOWED_FILES in this script with a comment explaining why.")
        return 1

    print("✓ PASS — zero banned-pattern references in live code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
