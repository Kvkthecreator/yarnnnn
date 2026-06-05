"""Shared boilerplate for canary scripts at api/scripts/operator/canary_*.py.

Extracted 2026-05-27 per docs/analysis/evaluation-infrastructure-audit-
2026-05-27.md. The 5 historical canary_phase4_*.py scripts each
re-implemented the same path-convention constants + status-flip regex
+ receipt-print formatting; this module centralizes those so new
canaries can import instead of duplicate.

Existing canary_phase4_v1 through v5 scripts are NOT migrated to use
this module — they remain as historical-trace artifacts of the ADR-299
investigation arc (their inline implementations are part of the
substrate-receipt). New canaries (post-2026-05-27) import here.

Conventions:
- A "piece" is an authored draft under /workspace/operation/authored/{slug}/
  with two canonical files: profile.md (frontmatter + title) and content.md
  (the prose). Status transitions on profile.md fire the substrate-event
  hook bound in alpha-author's _hooks.yaml.
- Status field uses YAML frontmatter `status:` line (not block-scoped).
  Canary tests typically transition draft → ready_for_review to fire
  the pre-ship-audit reactive wake.
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Path conventions for authored-piece probes
# ---------------------------------------------------------------------------


def piece_paths(slug: str) -> dict[str, str]:
    """Return canonical paths for an authored piece by slug.

    A piece is a draft under /workspace/operation/authored/{slug}/ with
    two files: profile.md (frontmatter + title) and content.md (prose).

    Returns:
        {"dir": str, "profile": str, "content": str}
    """
    base = f"/workspace/operation/authored/{slug}"
    return {
        "dir": base,
        "profile": f"{base}/profile.md",
        "content": f"{base}/content.md",
    }


# ---------------------------------------------------------------------------
# Frontmatter mutation
# ---------------------------------------------------------------------------


_STATUS_PATTERN = re.compile(r"^status:\s*\S+", re.MULTILINE)


def flip_status(content: str, new_value: str) -> str:
    """Replace the YAML-frontmatter `status:` line with `status: {new_value}`.

    Single-line replacement; assumes status: appears on its own line
    (standard YAML frontmatter shape). Raises ValueError if no status:
    line is found, which indicates the profile.md is malformed.
    """
    if not _STATUS_PATTERN.search(content):
        raise ValueError("No `status:` line found in profile.md frontmatter")
    return _STATUS_PATTERN.sub(f"status: {new_value}", content, count=1)


def extract_status(content: str) -> str | None:
    """Return current status: field value from profile.md content, or None if absent."""
    m = re.search(r"^status:\s*(\S+)", content, flags=re.MULTILINE)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Receipt-print formatting
# ---------------------------------------------------------------------------


def print_canary_receipt(
    canary_name: str,
    fired_at_iso: str,
    final_revision_id: str,
    *,
    watch_targets: list[str] | None = None,
) -> None:
    """Print the standard canary-fired receipt block.

    Replaces the per-canary inline print sequence: "=== Canary vN fired ===",
    expected-wake-window, wake_queue dedup_key target, substrate-write
    targets to watch.

    Args:
        canary_name: human label, e.g. "v6-mandate-coherence-test"
        fired_at_iso: ISO 8601 UTC timestamp of the canary-triggering write
        final_revision_id: revision_id of the canary-triggering write
        watch_targets: extra lines to print under "Watch:" section
    """
    print()
    print(f"=== Canary {canary_name} fired ===")
    print(f"Expected Reviewer wake within ~1-5 min of {fired_at_iso}.")
    print("Watch:")
    print(f"  wake_queue WHERE dedup_key = '{final_revision_id}'")
    print(
        f"  execution_events WHERE wake_source='substrate_event' AND created_at > '{fired_at_iso}'"
    )
    print("  reviewer substrate writes (judgment_log.md + standing_intent.md)")
    for line in watch_targets or []:
        print(f"  {line}")
