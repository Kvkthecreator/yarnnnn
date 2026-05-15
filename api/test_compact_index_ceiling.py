#!/usr/bin/env python3
"""Regression gate — compact-index ceiling enforcement, both profiles
(post-ADR-174 + ADR-186 hardening, 2026-05-15).

Validates:
- `_enforce_compact_index_ceiling` is the singular enforcement path.
- Workspace profile output that exceeds 2400 chars (≈600 tokens) is truncated.
- Entity profile output that exceeds 2400 chars is also truncated.
- Both render under the ceiling for realistic inputs.
- Truncation suffix is the canonical operator-grep-able string.

Singular Implementation: one helper, two profile callers. Test asserts both
paths go through the helper.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


_passes = 0
_fails: list[str] = []


def _ok(msg: str) -> None:
    global _passes
    _passes += 1
    print(f"  ✓ {msg}")


def _bad(label: str, detail: str) -> None:
    _fails.append(f"{label}: {detail}")
    print(f"  ✗ {label}: {detail}")


# ---------------------------------------------------------------------------
# 1. Helper exists and is wired into both profiles
# ---------------------------------------------------------------------------

def test_helper_wired_into_both_profiles() -> None:
    src = (ROOT / "services" / "working_memory.py").read_text()

    if "def _enforce_compact_index_ceiling(" in src:
        _ok("_enforce_compact_index_ceiling helper exists")
    else:
        _bad(
            "helper definition",
            "expected `def _enforce_compact_index_ceiling(` in services/working_memory.py",
        )

    # workspace profile call site
    if "_enforce_compact_index_ceiling(\"\\n\".join(lines), \"format_compact_index\")" in src:
        _ok("format_compact_index returns via _enforce_compact_index_ceiling")
    else:
        _bad(
            "workspace profile wiring",
            "expected format_compact_index to return via _enforce_compact_index_ceiling",
        )

    # entity profile call site
    if "_enforce_compact_index_ceiling(\"\\n\".join(lines), \"_format_entity_index\")" in src:
        _ok("_format_entity_index returns via _enforce_compact_index_ceiling")
    else:
        _bad(
            "entity profile wiring",
            "expected _format_entity_index to return via _enforce_compact_index_ceiling",
        )

    # No inline truncation block left in format_compact_index (Singular Implementation)
    if "exceeded {_TOKEN_CEILING}-token ceiling" not in src:
        _ok("inline truncation block removed (singular impl)")
    else:
        _bad(
            "inline block removal",
            "old inline _TOKEN_CEILING block still present — should be deleted",
        )


# ---------------------------------------------------------------------------
# 2. Behavior: under-ceiling output passes through unchanged
# ---------------------------------------------------------------------------

def test_under_ceiling_passes_through() -> None:
    # Ensure we're not in development mode (which would assert)
    prior_env = os.environ.get("ENV")
    os.environ["ENV"] = "production"
    try:
        from services.working_memory import _enforce_compact_index_ceiling

        small = "## tiny index\n- one line\n"
        out = _enforce_compact_index_ceiling(small, "test_under_ceiling")
        if out == small:
            _ok("under-ceiling output passes through unchanged")
        else:
            _bad("passthrough", f"expected unchanged, got mutation (len {len(out)})")
    finally:
        if prior_env is None:
            os.environ.pop("ENV", None)
        else:
            os.environ["ENV"] = prior_env


# ---------------------------------------------------------------------------
# 3. Behavior: over-ceiling output is truncated with canonical suffix
# ---------------------------------------------------------------------------

def test_over_ceiling_truncates_with_suffix() -> None:
    prior_env = os.environ.get("ENV")
    os.environ["ENV"] = "production"
    try:
        from services.working_memory import _enforce_compact_index_ceiling

        bloat = "x" * 3000  # well over 2400-char ceiling
        out = _enforce_compact_index_ceiling(bloat, "test_over_ceiling")

        # Truncated to <= ceiling + suffix length
        if len(out) < len(bloat):
            _ok(f"over-ceiling output truncated (3000 → {len(out)})")
        else:
            _bad("truncation length", f"expected truncated, got len {len(out)}")

        if "... (truncated — compact index too large)" in out:
            _ok("canonical truncation suffix present")
        else:
            _bad(
                "truncation suffix",
                "expected `... (truncated — compact index too large)` in output",
            )
    finally:
        if prior_env is None:
            os.environ.pop("ENV", None)
        else:
            os.environ["ENV"] = prior_env


# ---------------------------------------------------------------------------
# 4. Behavior: development env raises AssertionError on overflow
# ---------------------------------------------------------------------------

def test_dev_env_raises_on_overflow() -> None:
    prior_env = os.environ.get("ENV")
    os.environ["ENV"] = "development"
    try:
        from services.working_memory import _enforce_compact_index_ceiling

        try:
            _enforce_compact_index_ceiling("y" * 3000, "test_dev_overflow")
        except AssertionError as exc:
            if "test_dev_overflow" in str(exc) and "600-token ceiling" in str(exc):
                _ok("dev env raises AssertionError with label + ceiling cited")
            else:
                _bad(
                    "dev assertion message",
                    f"expected label + ceiling in message, got: {exc}",
                )
            return
        _bad(
            "dev assertion",
            "expected AssertionError in development env on overflow, got silent pass",
        )
    finally:
        if prior_env is None:
            os.environ.pop("ENV", None)
        else:
            os.environ["ENV"] = prior_env


# ---------------------------------------------------------------------------
# 5. Realistic entity-profile render stays under ceiling
# ---------------------------------------------------------------------------

def test_realistic_entity_render_under_ceiling() -> None:
    prior_env = os.environ.get("ENV")
    os.environ["ENV"] = "production"
    try:
        from services.working_memory import _format_entity_index

        # Plausibly-populated working memory; nothing pathological.
        wm = {
            "workspace_state": {
                "tasks_active": 5,
                "context_domains": 4,
                "balance_exhausted": False,
            },
            "context_domains": [
                {"domain": "trading", "file_count": 12, "temporal": False},
                {"domain": "portfolio", "file_count": 4, "temporal": False},
            ],
            "active_tasks": [
                {"slug": "morning-brief", "mode": "judgment",
                 "schedule": "0 9 * * 1-5", "status": "active",
                 "last_run": "2026-05-14T13:00Z", "next_run": "2026-05-15T13:00Z"},
            ],
        }
        out = _format_entity_index(
            wm, surface_context={"taskSlug": "morning-brief"}
        )
        # ≤ 2400 chars = ≤ ceiling
        if len(out) <= 2400:
            _ok(f"realistic entity render fits ceiling ({len(out)} chars)")
        else:
            _bad(
                "entity render size",
                f"realistic render at {len(out)} chars exceeds ceiling — "
                f"either inputs were unrealistic or the renderer bloated",
            )
    finally:
        if prior_env is None:
            os.environ.pop("ENV", None)
        else:
            os.environ["ENV"] = prior_env


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 72)
    print("compact-index ceiling enforcement gate (ADR-174 + ADR-186, 2026-05-15)")
    print("=" * 72)

    test_helper_wired_into_both_profiles()
    test_under_ceiling_passes_through()
    test_over_ceiling_truncates_with_suffix()
    test_dev_env_raises_on_overflow()
    test_realistic_entity_render_under_ceiling()

    print()
    print("=" * 72)
    if _fails:
        print(f"FAIL: {len(_fails)} assertion(s) failed, {_passes} passed")
        for f in _fails:
            print(f"  - {f}")
        return 1
    print(f"PASS: {_passes}/{_passes} assertions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
