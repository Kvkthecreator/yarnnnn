"""
services/wake_sources/substrate_event.py — Substrate-event wake source (ADR-296 v2 D1).

A substrate transition declared in `/workspace/_hooks.yaml` happened.
The operator or Reviewer authored a hook declaring interest in some
substrate change (e.g., draft profile.md frontmatter status →
ready_for_review); when the change lands in `workspace_file_versions`,
the hook fires a wake proposal to the funnel.

Per ADR-296 v2 D2 hooks substrate is the sibling declarative shape to
recurrences:
  - Recurrences are the cron-tick wake source's configuration (time-driven)
  - Hooks are the substrate-event wake source's configuration (event-driven)
Both compose into the singular evaluation gate identically.

Detection mechanism: at every scheduler tick (~5 minutes),
`walk_hooks(client, user_id)` queries `workspace_file_versions` rows
created since the last walk, matches each against the user's declared
hook entries by `path_match` (glob) + `field_change` (frontmatter key →
expected value), and submits one wake proposal per match.

The scheduler-tick cadence is the existing infrastructure — no new
process, no event listener, no webhook. Hooks fire on the next
scheduler tick after the substrate transition lands.

ADR-296 v2 §F5 — worldview-delta surface: the hook's payload carries
the `path` + `field_change` so the Reviewer can read which substrate
transition fired its wake. The Reviewer's user-message envelope
includes both as `substrate_event_path` + `substrate_event_field_change`.

Hook schema (in /workspace/_hooks.yaml):

```yaml
hooks:
  - slug: pre-ship-audit
    event: substrate_change
    path_match: /workspace/context/authored/*/profile.md
    field_change: { status: ready_for_review }
    prompt: |
      A draft was just marked ready_for_review. Read the draft at
      /workspace/context/authored/{piece-slug}/content.md and audit per
      voice + continuity + anti-slop + editorial criteria. ...
```

Per ADR-296 v2 D3 the Reviewer or operator both author hooks via the
`ManageHook` primitive (CHAT_PRIMITIVES + REVIEWER_PRIMITIVES). Reviewer
hook authoring is part of its cadence + standing-intent authority.
"""

from __future__ import annotations

import fnmatch
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import yaml

from services.wake import submit_wake_proposal

logger = logging.getLogger(__name__)


HOOKS_PATH = "/workspace/_hooks.yaml"


# ---------------------------------------------------------------------------
# Hook substrate parser
# ---------------------------------------------------------------------------


def parse_hooks(content: str) -> list[dict]:
    """Parse /workspace/_hooks.yaml content into a list of hook dicts.

    Returns an empty list when content is empty, malformed, or has
    no `hooks:` key. Never raises — bad substrate degrades gracefully
    (no hooks fire on bad parse).

    Each hook dict carries at minimum:
      - slug: str
      - event: str (today only "substrate_change")
      - path_match: str (glob)
      - field_change: dict (frontmatter key → expected value)
      - prompt: str
      - paused: bool (optional; defaults False)
    """
    if not content or not content.strip():
        return []
    try:
        parsed = yaml.safe_load(content)
    except Exception as exc:
        logger.warning("[WAKE:substrate] _hooks.yaml parse failed: %s", exc)
        return []
    if not isinstance(parsed, dict):
        return []
    hooks_raw = parsed.get("hooks") or []
    if not isinstance(hooks_raw, list):
        return []

    hooks: list[dict] = []
    for h in hooks_raw:
        if not isinstance(h, dict):
            continue
        slug = h.get("slug")
        if not slug or not isinstance(slug, str):
            continue
        hooks.append({
            "slug": slug,
            "event": h.get("event") or "substrate_change",
            "path_match": h.get("path_match") or "",
            "field_change": h.get("field_change") or {},
            "prompt": h.get("prompt") or "",
            "paused": bool(h.get("paused", False)),
        })
    return hooks


def read_hooks(client: Any, user_id: str) -> list[dict]:
    """Read the user's /workspace/_hooks.yaml + parse. Returns [] on absence."""
    try:
        from services.workspace import UserMemory
        memory = UserMemory(client, user_id)
        # UserMemory.read uses workspace-relative paths
        content = memory.read("_hooks.yaml") or ""
    except Exception as exc:
        logger.warning("[WAKE:substrate] _hooks.yaml read failed: %s", exc)
        return []
    return parse_hooks(content)


# ---------------------------------------------------------------------------
# Hook matcher — checks one revision against one hook
# ---------------------------------------------------------------------------


def _extract_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from a markdown file's content body.

    Returns an empty dict when no frontmatter block is present or parse
    fails. Frontmatter is the leading `---\\n...\\n---\\n` block per
    standard convention.
    """
    if not content or not content.startswith("---"):
        return {}
    # Find the closing `---` on its own line
    lines = content.splitlines()
    if len(lines) < 2 or lines[0].strip() != "---":
        return {}
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}
    fm_body = "\n".join(lines[1:end_idx])
    try:
        parsed = yaml.safe_load(fm_body)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _path_matches(path: str, glob_pattern: str) -> bool:
    """Match a workspace-absolute path against a glob pattern.

    Both are leading-slash workspace-absolute (e.g.,
    `/workspace/context/authored/foo/profile.md`).
    """
    if not glob_pattern:
        return False
    return fnmatch.fnmatch(path, glob_pattern)


def _field_change_matches(
    new_content: str,
    prev_content: Optional[str],
    expected: dict,
) -> bool:
    """Return True iff the file's frontmatter transitioned to match `expected`.

    A "transition" means: the field's current value matches the expected
    value AND either (a) there was no previous content, OR (b) the
    previous content's field value differed.

    This avoids re-firing the hook on every write that preserves the
    transitioned state — only the actual transition triggers a wake.

    `expected` is a dict like {"status": "ready_for_review"}; all keys
    must transition (multi-field hooks are conjunctive).
    """
    if not expected:
        return False
    new_fm = _extract_frontmatter(new_content)
    prev_fm = _extract_frontmatter(prev_content or "")
    for key, expected_value in expected.items():
        if new_fm.get(key) != expected_value:
            return False
        # Transition guard: previous value must have differed
        if prev_fm.get(key) == expected_value:
            return False
    return True


def _matches_hook(
    revision: dict,
    prev_content: Optional[str],
    hook: dict,
) -> bool:
    """Check whether a workspace_file_versions revision matches a hook declaration."""
    if hook.get("paused"):
        return False
    if hook.get("event") != "substrate_change":
        return False
    path = revision.get("path") or ""
    if not _path_matches(path, hook.get("path_match", "")):
        return False
    new_content = revision.get("content") or ""
    return _field_change_matches(new_content, prev_content, hook.get("field_change", {}))


# ---------------------------------------------------------------------------
# Walker — scheduler-tick entry point
# ---------------------------------------------------------------------------


async def walk_hooks(
    client: Any,
    user_id: str,
    *,
    since: Optional[datetime] = None,
) -> list[dict]:
    """Walk substrate revisions since `since`; submit a wake proposal per match.

    Called by the scheduler tick after the cron-tick recurrence dispatch
    completes. Quietly degrades on errors (logs + returns empty list);
    never raises.

    Args:
        client: Supabase service client
        user_id: Workspace owner UUID
        since: Only consider revisions created after this timestamp.
               When None, defaults to "last 30 minutes" so a missed
               scheduler tick doesn't lose hooks; over-firing within a
               single transition is prevented by the field_change
               transition guard.

    Returns:
        List of WakeOutcome dicts — one per hook that fired.
    """
    hooks = read_hooks(client, user_id)
    if not hooks:
        return []

    if since is None:
        # Default lookback: 30 minutes. Scheduler runs every 5 minutes;
        # 30min covers up to 6 missed ticks. The transition guard in
        # `_field_change_matches` prevents re-firing on the same change.
        from datetime import timedelta
        since = datetime.now(timezone.utc) - timedelta(minutes=30)

    since_iso = since.strftime("%Y-%m-%dT%H:%M:%S+00:00")

    # Query recent revisions across all paths the user owns. We then
    # filter in-memory against each hook's glob — cheaper than running
    # one DB query per hook when hook count is small.
    try:
        result = (
            client.table("workspace_file_versions")
            .select("id, path, content, parent_version_id, created_at")
            .eq("user_id", user_id)
            .gte("created_at", since_iso)
            .order("created_at", desc=False)
            .limit(200)
            .execute()
        )
    except Exception as exc:
        logger.warning("[WAKE:substrate] workspace_file_versions query failed: %s", exc)
        return []

    revisions = result.data or []
    if not revisions:
        return []

    outcomes: list[dict] = []
    for rev in revisions:
        # Resolve the previous revision's content for the transition guard.
        prev_content = await _get_parent_content(client, rev.get("parent_version_id"))

        for hook in hooks:
            if not _matches_hook(rev, prev_content, hook):
                continue
            try:
                outcome = await submit_wake_proposal(
                    client, user_id,
                    source="substrate_event",
                    payload={
                        "hook": hook,
                        "path": rev.get("path") or "",
                        "field_change": dict(hook.get("field_change") or {}),
                        "revision_id": rev.get("id"),
                    },
                )
                outcomes.append(outcome)
            except Exception as exc:
                logger.warning(
                    "[WAKE:substrate] submit_wake_proposal raised for hook=%s path=%s: %s",
                    hook.get("slug"), rev.get("path"), exc,
                )
            # One revision can fire at most one hook (the matched one);
            # if multiple hooks match the same revision, all fire.

    return outcomes


async def _get_parent_content(client: Any, parent_version_id: Optional[str]) -> Optional[str]:
    """Resolve the parent revision's content for the transition guard.

    Returns None when there is no parent (first revision for the path)
    or on lookup error (treat as no-prior-state — transition fires).
    """
    if not parent_version_id:
        return None
    try:
        result = (
            client.table("workspace_file_versions")
            .select("content")
            .eq("id", parent_version_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return None
        return rows[0].get("content")
    except Exception as exc:
        logger.warning(
            "[WAKE:substrate] parent revision lookup failed for %s: %s",
            parent_version_id, exc,
        )
        return None


__all__ = [
    "HOOKS_PATH",
    "parse_hooks",
    "read_hooks",
    "walk_hooks",
]
