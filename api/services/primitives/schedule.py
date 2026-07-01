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
  - Reviewer-mid-loop:   authored_by="freddie:{occupant}"
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

A recurrence is a JUDGMENT prompt on a cadence — a record with three load-bearing fields:
  slug:     stable identifier
  schedule: cron expression (or null for reactive)
  prompt:   what the Reviewer reads at fire time

ADR-393: a recurrence is judgment-only. Deterministic intake (mirroring platform
state, running a `@primitive:` directive, standing web/repo watches) is NOT a
recurrence — it is a CAPTURE, declared in /workspace/_captures.yaml and run by
the capture lane outside the wake funnel. Do not put a `@primitive:` directive
in a recurrence prompt; it will not run.

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
      prompt="Evaluate the universe against signals IH-1 through IH-5 on fresh 1Hour bars. Write findings to /workspace/operation/trading/signals/.")

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
    changes = input.get("changes") or {}
    paused_until = input.get("paused_until")

    # ADR-274 / FOUNDATIONS v8.5 Axiom 4 amendment: authored_by is load-bearing.
    # Every Trigger-authoring write must assert which Identity is authoring.
    # Silent attribution drift would break the Trigger-dimension audit trail.
    #
    # ADR-288 D2: default authored_by from auth.caller_identity when not
    # explicitly supplied. Every auth-construction site sets caller_identity
    # per the ADR-209 taxonomy (yarnnn.py operator-chat, freddie_agent wake,
    # HeadlessAuth specialist dispatch, _MechanicalAuth recurrence, MCP
    # boundary). Per-dispatch-loop injection at the agent layer (pre-ADR-288)
    # is superseded. Fail-fast on missing remains as the safety net for direct
    # callers (routes, scripts) that bypass the auth-construction sites.
    authored_by_raw = input.get("authored_by") or getattr(auth, "caller_identity", None)
    if not authored_by_raw or not isinstance(authored_by_raw, str) or not authored_by_raw.strip():
        return {
            "success": False,
            "error": "missing_authored_by",
            "message": (
                "Schedule requires authored_by per FOUNDATIONS v8.5 Axiom 4 "
                "(Trigger authoring is an Identity-layer responsibility). "
                "Pre-ADR-288 callers injected at dispatch; ADR-288 D1 sets "
                "auth.caller_identity at construction time. Direct callers "
                "(routes, scripts) must pass authored_by explicitly "
                "(e.g., 'operator', 'reviewer:simons', 'agent:portfolio-tracker', "
                "'system:bundle-fork'). Silent attribution would break the "
                "Trigger-dimension audit trail."
            ),
        }
    authored_by = authored_by_raw.strip()

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
        # ADR-393: recurrences are judgment-only — no `mode`. Deterministic
        # intake lives in _captures.yaml (the capture lane), not authored here.
        new_schedule = (
            schedule.strip() if isinstance(schedule, str) and schedule.strip() else None
        )

        # ADR-327: the pace-population constraint at declaration time is
        # DELETED. "How often" is no longer an operator dial — it is the
        # Reviewer's allocation problem within the dollar budget (_budget.yaml).
        # Recurrence creation is no longer frequency-gated; cost is governed
        # downstream at the wake funnel (window budget, ADR-327 D3/D4). The
        # per-slug min-interval floor still applies at fire time (ADR-313 Gate 3).

        new_rec = Recurrence(
            slug=slug,
            schedule=new_schedule,
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
            # ADR-327: the pace-population gate on schedule updates is DELETED
            # (see the create-action note above). Frequency is the Reviewer's
            # allocation problem within _budget.yaml, not a declaration-time
            # gate. Cost is governed at the wake funnel; the per-slug
            # min-interval floor still applies at fire time (ADR-313 Gate 3).

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
                    # ADR-393: `mode` is retired from recurrences. Ignore it on
                    # update rather than erroring (a stale client sending mode
                    # shouldn't fail the whole update); it simply does nothing.
                    logger.info(
                        "[SCHEDULE] ignoring retired 'mode' field on update of %s "
                        "(ADR-393: recurrences are judgment-only)", slug,
                    )
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
