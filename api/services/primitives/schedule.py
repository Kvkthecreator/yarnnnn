"""
Schedule Primitive — ADR-261 §3 (renamed from ManageRecurrence per A.3,
collapsed to single-file shape per Phase B).

The canonical way to author / modify / pause / resume / archive a
recurrence. Available in both chat and headless modes.

Per ADR-261 D1 + D2 + D4: a recurrence is a record with three
load-bearing fields ({slug, schedule, prompt}) living in the single
canonical file ``/workspace/_recurrences.yaml``. There is no per-shape
declaration file, no shape parameter, no path-derivation step.

Five actions:
  - "create"   append a new entry (slug must be unique)
  - "update"   merge fields into an existing entry
  - "pause"    set paused: true (optional paused_until)
  - "resume"   set paused: false, clear paused_until
  - "archive"  remove the entry (revision log preserves prior state per ADR-209)

Authorship per ADR-261 §3:
  - Operator-via-chat:   authored_by="operator"
  - Reviewer-mid-loop:   authored_by="reviewer:{occupant}"
  - System (bundle fork):authored_by="system:bundle-fork"
All three paths produce the same substrate writes through the same
primitive. Per singular-implementation, no separate paths exist.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from services.conventions import RECURRENCES_PATH
from services.recurrence import (
    Recurrence,
    parse_recurrences_yaml,
    serialize_recurrences_yaml,
)

logger = logging.getLogger(__name__)


SCHEDULE_TOOL = {
    "name": "Schedule",
    "description": """Manage a recurrence in /workspace/_recurrences.yaml (ADR-261 §3).

A recurrence is a record with three load-bearing fields:
  slug:     stable identifier
  schedule: cron expression (or null for reactive)
  prompt:   what the Reviewer reads at fire time

ONE primitive, FIVE actions:
  - "create"   append a new entry. Requires slug, schedule, prompt.
  - "update"   merge fields into existing entry. Requires slug.
  - "pause"    set paused: true. Optional paused_until ISO timestamp.
  - "resume"   set paused: false, clear paused_until.
  - "archive"  remove the entry from _recurrences.yaml. Slug must exist.

Examples:
  Schedule(action="create",
      slug="signal-evaluation",
      schedule="0 * 9-16 * 1-5",
      prompt="Evaluate the universe against signals IH-1 through IH-5 on fresh 1Hour bars. Write findings to /workspace/context/trading/signals/.")

  Schedule(action="update", slug="signal-evaluation", changes={"schedule": "*/30 9-16 * * 1-5"})

  Schedule(action="pause", slug="signal-evaluation", paused_until="2026-05-15T00:00:00Z")
  Schedule(action="resume", slug="signal-evaluation")
  Schedule(action="archive", slug="signal-evaluation")""",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "update", "pause", "resume", "archive"],
                "description": "Lifecycle action.",
            },
            "slug": {
                "type": "string",
                "description": "Operator-legible identifier. Required for all actions.",
            },
            "schedule": {
                "type": "string",
                "description": "For action='create': cron expression (e.g. '0 7 * * *') or null for reactive recurrences.",
            },
            "prompt": {
                "type": "string",
                "description": "For action='create': the message the Reviewer reads at fire time.",
            },
            "changes": {
                "type": "object",
                "description": "For action='update': partial dict of fields to merge. e.g. {schedule: '0 9 * * *', prompt: 'updated wording'}.",
            },
            "paused_until": {
                "type": "string",
                "description": "For action='pause': optional ISO-8601 timestamp; recurrence auto-resumes after this date.",
            },
        },
        "required": ["action", "slug"],
    },
}


async def handle_schedule(
    user_id: str,
    *,
    action: str,
    slug: str,
    schedule: Optional[str] = None,
    prompt: Optional[str] = None,
    changes: Optional[dict] = None,
    paused_until: Optional[str] = None,
    authored_by: str = "operator",
    db_client: Any = None,
    **_extra: Any,
) -> dict:
    """Execute a Schedule action against ``/workspace/_recurrences.yaml``.

    Returns a dict with ``success`` plus action-specific fields.

    Per ADR-209 + ADR-235: every write goes through ``UserMemory.write``
    (which routes to ``write_revision`` with the supplied ``authored_by``
    and a descriptive message).
    """
    from services.memory import UserMemory  # local import: avoid cycle at module load

    if not slug or not isinstance(slug, str):
        return {"success": False, "error": "missing_slug", "message": "slug is required"}

    if action not in {"create", "update", "pause", "resume", "archive"}:
        return {
            "success": False,
            "error": "invalid_action",
            "message": f"unknown action {action!r}",
        }

    um = UserMemory(user_id, db_client=db_client)
    rel_path = RECURRENCES_PATH.lstrip("/")  # UserMemory writes are relative
    current = await um.read(rel_path)

    recurrences = parse_recurrences_yaml(current or "", user_id=user_id)
    idx = next((i for i, r in enumerate(recurrences) if r.slug == slug), -1)

    if action == "create":
        if idx >= 0:
            return {
                "success": False,
                "error": "already_exists",
                "message": f"recurrence slug={slug!r} already exists (use action='update')",
            }
        if not prompt or not str(prompt).strip():
            return {
                "success": False,
                "error": "missing_prompt",
                "message": "prompt is required for create",
            }
        new_rec = Recurrence(
            slug=slug,
            schedule=(schedule.strip() if isinstance(schedule, str) and schedule.strip() else None),
            prompt=str(prompt).strip(),
        )
        recurrences.append(new_rec)
        msg = f"created recurrence {slug}"

    elif action == "archive":
        if idx < 0:
            return {
                "success": False,
                "error": "not_found",
                "message": f"recurrence slug={slug!r} not found",
            }
        recurrences.pop(idx)
        msg = f"archived recurrence {slug}"

    else:
        if idx < 0:
            return {
                "success": False,
                "error": "not_found",
                "message": f"recurrence slug={slug!r} not found",
            }
        rec = recurrences[idx]

        if action == "pause":
            rec.paused = True
            if paused_until:
                from services.recurrence import _coerce_datetime  # type: ignore[attr-defined]

                rec.paused_until = _coerce_datetime(paused_until)
            msg = f"paused recurrence {slug}"
        elif action == "resume":
            rec.paused = False
            rec.paused_until = None
            msg = f"resumed recurrence {slug}"
        elif action == "update":
            applied = []
            for k, v in (changes or {}).items():
                if k == "slug":
                    continue  # immutable
                if k == "schedule":
                    rec.schedule = (
                        str(v).strip() if isinstance(v, str) and str(v).strip() else None
                    )
                    applied.append(k)
                elif k == "prompt":
                    if v and str(v).strip():
                        rec.prompt = str(v).strip()
                        applied.append(k)
                elif k == "paused":
                    rec.paused = bool(v)
                    applied.append(k)
                elif k == "paused_until":
                    from services.recurrence import _coerce_datetime  # type: ignore[attr-defined]

                    rec.paused_until = _coerce_datetime(v)
                    applied.append(k)
                else:
                    rec.options[k] = v
                    applied.append(k)
            msg = f"updated recurrence {slug}: {sorted(applied)}"
        recurrences[idx] = rec

    yaml_text = serialize_recurrences_yaml(recurrences)
    ok = await um.write(
        rel_path,
        yaml_text,
        summary=f"recurrence:{action} {slug}",
        authored_by=authored_by,
        message=msg,
    )
    if not ok:
        return {
            "success": False,
            "error": "write_failed",
            "message": f"failed to write {RECURRENCES_PATH}",
        }

    return {
        "success": True,
        "action": action,
        "slug": slug,
        "path": RECURRENCES_PATH,
        "message": msg,
    }


__all__ = ["SCHEDULE_TOOL", "handle_schedule"]
