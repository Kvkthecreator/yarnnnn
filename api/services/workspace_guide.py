"""Workspace guide reader (ADR-280).

The workspace guide is the singular canonical workspace doc — one file per
workspace at `/workspace/_workspace_guide.md`, containing YAML frontmatter
(machine-parsed by kernel) + prose body (read by Reviewer at every wake +
read by operator when they want to understand or revise).

This module is the kernel-side reader of the frontmatter. The prose body is
read by the Reviewer at every wake via the standard `ReadFile` primitive (no
special path) — only the frontmatter has machine consumers.

Per ADR-280 §2.D3 the guide uses the `_money_truth.md`-grandfathered
frontmatter+prose pattern (one file, two consumers, no sync problem). Per
ADR-254 file-format discipline this is acceptable: the file is primary-LLM-
readable prose with a structured machine-readable frontmatter section.

Genesis-by-Reviewer (per ADR-280 §2.D4) authors this file at first wake from
the kernel template (services/genesis_prompt.py) + active bundle's
`substrate_abi` declaration (services/bundle_reader.py). Operator and
Reviewer revise it through normal authoring channels thereafter.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


#: Canonical workspace path for the guide.
WORKSPACE_GUIDE_PATH = "/workspace/_workspace_guide.md"

#: Frontmatter delimiter regex — matches the YAML frontmatter block at the
#: top of a markdown file. Same shape used by other kernel readers (e.g.,
#: `_money_truth.md` reconciler reads frontmatter the same way).
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

#: Soft size cap on guide content per ADR-280 §8 Phase 1 acceptance.
#: Mirrors CC's `truncateEntrypointContent` discipline (see
#: `docs/analysis/src_claudeCC/memdir/memdir.ts:57`). Informational only —
#: oversize guides still parse and serve their frontmatter; the kernel
#: logs a warning so operators / observability surfaces know the guide
#: is bloating into the wake envelope (defends ADR-159's compact-index
#: token budget against silent over-time growth).
_GUIDE_SOFT_CAP_BYTES = 25 * 1024
_GUIDE_SOFT_CAP_LINES = 600


def _extract_frontmatter(content: str) -> dict[str, Any]:
    """Parse YAML frontmatter from a markdown file's content.

    Returns empty dict when:
      - content is empty
      - no frontmatter block present
      - frontmatter block is malformed YAML

    Never raises — fail-open per ADR-258 D9 lock-policy discipline (lock
    enforcement that breaks because frontmatter is malformed would be worse
    than lock enforcement that quietly degrades to "no bundle-declared
    locks beyond kernel defaults").
    """
    if not content:
        return {}
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}
    try:
        parsed = yaml.safe_load(match.group(1))
        if isinstance(parsed, dict):
            return parsed
        return {}
    except Exception as exc:
        logger.warning(
            f"[WORKSPACE_GUIDE] Malformed frontmatter — falling back to empty: {exc}"
        )
        return {}


def read_frontmatter(client: Any, user_id: str) -> dict[str, Any]:
    """Synchronous: read the workspace guide's YAML frontmatter.

    Returns empty dict when the guide doesn't exist yet (pre-genesis state)
    or when frontmatter is absent/malformed. Callers that compose multiple
    inputs (kernel + workspace-guide + operator overrides) treat empty as
    "no contribution from this layer" — a workspace with no guide gets only
    the kernel-universal defaults, which is correct fallback behavior.
    """
    if not user_id:
        return {}
    try:
        res = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", WORKSPACE_GUIDE_PATH)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning(
            f"[WORKSPACE_GUIDE] read failed for user={user_id[:8]}: {exc}"
        )
        return {}
    rows = res.data or []
    if not rows:
        return {}
    content = rows[0].get("content") or ""
    _check_guide_size(content, user_id)
    return _extract_frontmatter(content)


def _check_guide_size(content: str, user_id: str) -> None:
    """Soft cap warning per ADR-280 §8 Phase 1 acceptance.

    Logs a warning when the guide exceeds either the byte or line cap.
    Informational only — frontmatter parsing always proceeds. The warning
    surfaces over-time guide bloat to operators / observability without
    breaking Reviewer wakes.

    Defends ADR-159's compact-index token budget — every wake reads the
    whole guide; an oversize guide silently inflates wake envelope cost.
    """
    if not content:
        return
    byte_size = len(content.encode("utf-8"))
    line_count = content.count("\n") + 1
    if byte_size > _GUIDE_SOFT_CAP_BYTES or line_count > _GUIDE_SOFT_CAP_LINES:
        logger.warning(
            f"[WORKSPACE_GUIDE] Guide exceeds soft cap for user={user_id[:8]} "
            f"(bytes={byte_size}/{_GUIDE_SOFT_CAP_BYTES}, "
            f"lines={line_count}/{_GUIDE_SOFT_CAP_LINES}). "
            f"Consider refactoring — guide reads land in every Reviewer wake "
            f"and inflate compact-index token cost (ADR-159, ADR-280 §8)."
        )


async def read_frontmatter_async(client: Any, user_id: str) -> dict[str, Any]:
    """Async wrapper around `read_frontmatter`.

    The Supabase client's `execute()` is synchronous (per existing kernel
    pattern in `services/reviewer_audit.py`, `services/reviewer_envelope.py`),
    so the async variant just delegates. The async signature exists so
    callers in async contexts (chat.py, invocation_dispatcher.py, the future
    Phase 2 envelope refactor) can await this consistently with their other
    asyncio.gather() calls.
    """
    return read_frontmatter(client, user_id)


def get_path_zone_locks(frontmatter: dict[str, Any]) -> set[str]:
    """Extract the set of paths locked from Reviewer writes from frontmatter.

    Composes per ADR-280 §2.D6.a:
      - Every path_zone with role='operator-canon' is locked.
      - Plus operator additions from frontmatter `locks.add`.
      - Minus operator overrides from frontmatter `locks.remove`.

    Returns paths workspace-relative (no leading slash) to match the
    normalization used by the lock-check function.
    """
    locked: set[str] = set()
    for zone in frontmatter.get("path_zones", []) or []:
        if not isinstance(zone, dict):
            continue
        role = zone.get("role")
        path = zone.get("path")
        if role == "operator-canon" and isinstance(path, str):
            locked.add(path.lstrip("/"))
            # Also lock any explicitly-named authored_files under this zone
            for f in zone.get("authored_files", []) or []:
                if isinstance(f, str):
                    locked.add(f"{path.lstrip('/')}/{f}")

    locks_block = frontmatter.get("locks", {})
    if isinstance(locks_block, dict):
        for p in locks_block.get("add", []) or []:
            if isinstance(p, str):
                locked.add(p.lstrip("/"))
        for p in locks_block.get("remove", []) or []:
            if isinstance(p, str):
                locked.discard(p.lstrip("/"))

    return locked


def get_reviewer_wake_envelope_decls(frontmatter: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract the reviewer_wake_envelope declarations from frontmatter.

    Returns a list of dicts shaped like
      {key: str, path: str, optional: bool}     # for direct path reads
    or
      {key: str, path_glob: str, summarizer: str, optional: bool}  # for collections

    Used by `services/reviewer_envelope.py::load_reviewer_governance_envelope`
    in Phase 2 (today the envelope helper hardcodes alpha-trader paths;
    Phase 2 refactor reads this declaration instead).
    """
    decls = frontmatter.get("reviewer_wake_envelope", []) or []
    if not isinstance(decls, list):
        return []
    return [d for d in decls if isinstance(d, dict) and d.get("key")]
