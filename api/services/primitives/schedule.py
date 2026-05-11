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
    "description": """Manage a recurrence in /workspace/_recurrences.yaml (ADR-261 §3, extended by ADR-263).

A recurrence is a record with four load-bearing fields:
  slug:     stable identifier
  schedule: cron expression (or null for reactive)
  mode:     judgment | mechanical (ADR-263 — declares wake intent at authoring time)
  prompt:   what the Reviewer reads at fire time (judgment) OR a `@primitive: ...` directive (mechanical)

ONE primitive, FIVE actions:
  - "create"   append a new entry. Requires slug, schedule, prompt; mode optional (default 'judgment').
  - "update"   merge fields into existing entry. Requires slug.
  - "pause"    set paused: true. Optional paused_until ISO timestamp.
  - "resume"   set paused: false, clear paused_until.
  - "archive"  remove the entry from _recurrences.yaml. Slug must exist.

Mode discipline (ADR-263):
  - 'judgment' (default) — recurrence's prompt invokes the Reviewer. Today's behavior for all existing recurrences.
  - 'mechanical' — recurrence's prompt names a primitive invocation (`@primitive: SyncPlatformState(...)`).
                   Dispatcher parses and executes deterministically; no Reviewer wake; no LLM cost.
                   Use for substrate-mirroring work (per ADR-264 SyncPlatformState).

Examples:
  Schedule(action="create",
      slug="signal-evaluation",
      schedule="0 * 9-16 * 1-5",
      mode="judgment",
      prompt="Evaluate the universe against signals IH-1 through IH-5 on fresh 1Hour bars. Write findings to /workspace/context/trading/signals/.")

  Schedule(action="create",
      slug="track-positions",
      schedule="* * 9-16 * 1-5",
      mode="mechanical",
      prompt='@primitive: SyncPlatformState(tool="platform_trading_get_positions", write_to="context/portfolio/positions/{symbol}.yaml", iterate_field="positions", item_key="symbol")')

  Schedule(action="update", slug="signal-evaluation", changes={"schedule": "*/30 9-16 * * 1-5"})
  Schedule(action="update", slug="track-positions", changes={"mode": "judgment"})  # flip mode

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
            "mode": {
                "type": "string",
                "enum": ["judgment", "mechanical"],
                "description": "For action='create': wake intent (ADR-263). 'judgment' (default) wakes the Reviewer with the prompt; 'mechanical' executes the prompt's @primitive: directive deterministically (no Reviewer wake, no LLM cost).",
            },
            "prompt": {
                "type": "string",
                "description": "For action='create': the message the Reviewer reads at fire time (mode=judgment) OR a @primitive: directive (mode=mechanical).",
            },
            "changes": {
                "type": "object",
                "description": "For action='update': partial dict of fields to merge. e.g. {schedule: '0 9 * * *', prompt: 'updated wording', mode: 'mechanical'}.",
            },
            "paused_until": {
                "type": "string",
                "description": "For action='pause': optional ISO-8601 timestamp; recurrence auto-resumes after this date.",
            },
        },
        "required": ["action", "slug"],
    },
}


async def handle_schedule(auth: Any, input: dict) -> dict:
    """Execute a Schedule action against ``/workspace/_recurrences.yaml``.

    Returns a dict with ``success`` plus action-specific fields.

    Per ADR-209 + ADR-235: every write goes through ``UserMemory.write``
    (which routes to ``write_revision`` with the supplied ``authored_by``
    and a descriptive message).
    """
    from services.workspace import UserMemory  # local import: avoid cycle at module load

    user_id = getattr(auth, "user_id", None)
    db_client = getattr(auth, "client", None)
    if not user_id:
        return {"success": False, "error": "auth_required", "message": "user_id required"}

    input = input or {}
    action = input.get("action") or ""
    slug = input.get("slug") or ""
    schedule = input.get("schedule")
    prompt = input.get("prompt")
    mode = input.get("mode")  # ADR-263: judgment | mechanical
    changes = input.get("changes") or {}
    paused_until = input.get("paused_until")
    authored_by = input.get("authored_by") or "operator"

    if not slug or not isinstance(slug, str):
        return {"success": False, "error": "missing_slug", "message": "slug is required"}

    if action not in {"create", "update", "pause", "resume", "archive"}:
        return {
            "success": False,
            "error": "invalid_action",
            "message": f"unknown action {action!r}",
        }

    um = UserMemory(db_client, user_id)
    # RECURRENCES_PATH is "/workspace/_recurrences.yaml"; UserMemory._base
    # is "/workspace" and prepends it via _full_path, so we strip the
    # "/workspace/" prefix to give it the bare workspace-relative path.
    rel_path = RECURRENCES_PATH[len("/workspace/"):]
    current = await um.read(rel_path)
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
        # ADR-263: validate mode at create-time. Default to judgment when absent.
        from services.recurrence import (
            DEFAULT_RECURRENCE_MODE, RECURRENCE_MODES,
        )
        resolved_mode = (
            str(mode).strip().lower() if isinstance(mode, str) and mode.strip()
            else DEFAULT_RECURRENCE_MODE
        )
        if resolved_mode not in RECURRENCE_MODES:
            return {
                "success": False,
                "error": "invalid_mode",
                "message": f"mode={mode!r} must be one of {list(RECURRENCE_MODES)}",
            }
        new_rec = Recurrence(
            slug=slug,
            schedule=(schedule.strip() if isinstance(schedule, str) and schedule.strip() else None),
            prompt=str(prompt).strip(),
            mode=resolved_mode,
        )
        recurrences.append(new_rec)
        msg = f"created recurrence {slug} (mode={resolved_mode})"

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
                elif k == "mode":
                    # ADR-263: mode is mutable post-create. Validate.
                    from services.recurrence import RECURRENCE_MODES, is_valid_mode
                    new_mode = str(v).strip().lower() if isinstance(v, str) else ""
                    if not is_valid_mode(new_mode):
                        return {
                            "success": False,
                            "error": "invalid_mode",
                            "message": f"mode={v!r} must be one of {list(RECURRENCE_MODES)}",
                        }
                    rec.mode = new_mode
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

    # Sync the thin `tasks` scheduling index with the just-mutated YAML
    # (ADR-261 D3 — YAML is truth, table is the index). Idempotent; drops
    # rows whose recurrence was archived, upserts schedule changes. Failure
    # is non-fatal — the next scheduler tick will reconcile — but log so
    # the gap is visible.
    from services.scheduling import materialize_scheduling_index
    scheduling_index_rows = 0
    try:
        scheduling_index_rows = await materialize_scheduling_index(db_client, user_id)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            f"[SCHEDULE] materialize_scheduling_index failed for {user_id[:8]}: {exc}"
        )

    return {
        "success": True,
        "action": action,
        "slug": slug,
        "path": RECURRENCES_PATH,
        "message": msg,
        "scheduling_index_rows": scheduling_index_rows,
    }


__all__ = ["SCHEDULE_TOOL", "handle_schedule"]
