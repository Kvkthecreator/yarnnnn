"""
ManageRecurrence Primitive — ADR-235 D1.c

Recurrence-declaration lifecycle manager. Spun out of UpdateContext as part
of the UpdateContext dissolution (ADR-235). Mirrors the shape of ManageAgent
and ManageDomains: one verb, several actions, one substrate-write target.

Cognitive shape: lifecycle action over a YAML declaration at the
natural-home substrate location (per ADR-231 D2):

  /workspace/reports/{slug}/_spec.yaml         — DELIVERABLE shape
  /workspace/operations/{slug}/_action.yaml    — ACTION shape
  /workspace/context/{domain}/_recurring.yaml  — ACCUMULATION shape (multi-decl)
  /workspace/_shared/back-office.yaml          — MAINTENANCE shape (multi-decl)

Five actions: create, update, pause, resume, archive.

Available in BOTH chat and headless modes (mirrors ADR-231 D5 intent — chat
authors recurrences via operator conversation; headless agents may pause
or resume their own declarations on outcome signals).
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


MANAGE_RECURRENCE_TOOL = {
    "name": "ManageRecurrence",
    "description": """Manage a recurrence declaration (ADR-231 D5).

A recurrence declaration is a YAML file at the natural-home substrate
location. ONE primitive, FIVE actions:

  - "create"  — write a new declaration (single-decl shapes) or append an
                 entry to a multi-decl file (accumulation, maintenance)
  - "update"  — merge `changes` into an existing declaration's body
  - "pause"   — set paused: true (optional paused_until ISO timestamp)
  - "resume"  — set paused: false
  - "archive" — remove the declaration (delete file or remove entry)

Path is derived from shape + slug (+ domain for accumulation):

  shape='deliverable':   /workspace/reports/{slug}/_spec.yaml
  shape='action':        /workspace/operations/{slug}/_action.yaml
  shape='accumulation':  /workspace/context/{domain}/_recurring.yaml  (multi-decl, requires domain)
  shape='maintenance':   /workspace/_shared/back-office.yaml          (multi-decl)

Examples:
  ManageRecurrence(action="create", shape="deliverable", slug="market-weekly",
      body={schedule: "0 9 * * 1", display_name: "Weekly Market Report",
            output_path: "/workspace/reports/market-weekly/{date}/output.md",
            agents: ["analyst", "writer"]})

  ManageRecurrence(action="create", shape="accumulation",
      slug="competitors-weekly-scan", domain="competitors",
      body={schedule: "0 9 * * 1", agent: "researcher",
            objective: "Weekly competitive moves"})

  ManageRecurrence(action="pause", shape="deliverable", slug="market-weekly")
  ManageRecurrence(action="resume", shape="deliverable", slug="market-weekly")
  ManageRecurrence(action="update", shape="deliverable", slug="market-weekly",
      changes={schedule: "0 9 * * *"})  # change cadence to daily
  ManageRecurrence(action="archive", shape="deliverable", slug="market-weekly")""",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "update", "pause", "resume", "archive"],
                "description": "Lifecycle action to perform.",
            },
            "shape": {
                "type": "string",
                "enum": ["deliverable", "accumulation", "action", "maintenance"],
                "description": "Recurrence shape — drives natural-home path. Required for all actions.",
            },
            "slug": {
                "type": "string",
                "description": "Operator-legible nameplate. Required for all actions.",
            },
            "domain": {
                "type": "string",
                "description": "For shape='accumulation': context domain slug (e.g., 'competitors'). Required because accumulation declarations live at /workspace/context/{domain}/_recurring.yaml as multi-entry files.",
            },
            "body": {
                "type": "object",
                "description": "For action='create': declaration body. Keys depend on shape: deliverable expects {schedule, output_path, agents, ...}; accumulation expects {schedule, agent, objective, context_writes, ...}; action expects {schedule, target_capability, target_channel, ...}; maintenance expects {executor, schedule, ...}. The slug is added automatically.",
            },
            "changes": {
                "type": "object",
                "description": "For action='update': partial dict of fields to merge into the existing declaration. e.g., {schedule: '0 9 * * *'} to change cadence.",
            },
            "paused_until": {
                "type": "string",
                "description": "For action='pause': optional ISO-8601 timestamp. If provided, declaration auto-resumes after this date.",
            },
        },
        "required": ["action", "shape", "slug"],
    },
}


_SHAPE_TO_FILENAME = {
    "deliverable": "_spec.yaml",
    "accumulation": "_recurring.yaml",
    "action": "_action.yaml",
    "maintenance": "back-office.yaml",
}

_SINGLE_DECL_SHAPES = {"deliverable", "action"}
_MULTI_DECL_SHAPES = {"accumulation", "maintenance"}


def _resolve_recurrence_path(shape: str, slug: str, domain: Optional[str]) -> str:
    """Compute the workspace-relative path for a recurrence file.

    UserMemory.write expects paths relative to /workspace/, so we return
    the relative form.
    """
    if shape == "deliverable":
        return f"reports/{slug}/_spec.yaml"
    if shape == "action":
        return f"operations/{slug}/_action.yaml"
    if shape == "accumulation":
        if not domain:
            raise ValueError("domain required for shape='accumulation'")
        return f"context/{domain}/_recurring.yaml"
    if shape == "maintenance":
        return "_shared/back-office.yaml"
    raise ValueError(f"unknown shape: {shape}")


async def handle_manage_recurrence(auth: Any, input: dict) -> dict:
    """Recurrence declaration lifecycle (extracted from UpdateContext._handle_recurrence).

    Routes by shape to single-decl or multi-decl handler. Each successful
    write also kicks off scheduling-index materialization (best-effort,
    non-fatal — the index is fully reconstructable from filesystem state).

    All writes are attributed `authored_by="yarnnn:adr-231"` (preserves the
    pre-ADR-235 author marker for backward compatibility with revision
    history).
    """
    from services.workspace import UserMemory

    action = input.get("action")
    shape = input.get("shape")
    slug = input.get("slug")
    domain = input.get("domain")
    body = input.get("body") or {}
    changes = input.get("changes") or {}
    paused_until = input.get("paused_until")

    if action not in {"create", "update", "pause", "resume", "archive"}:
        return {
            "success": False,
            "error": "invalid_action",
            "message": "action must be one of: create, update, pause, resume, archive",
        }
    if not slug:
        return {"success": False, "error": "missing_slug", "message": "slug is required"}
    if shape not in _SHAPE_TO_FILENAME:
        return {
            "success": False,
            "error": "invalid_shape",
            "message": "shape must be one of: deliverable, accumulation, action, maintenance",
        }
    if shape == "accumulation" and not domain:
        return {
            "success": False,
            "error": "missing_domain",
            "message": "domain is required when shape='accumulation'",
        }

    try:
        rel_path = _resolve_recurrence_path(shape, slug, domain)
    except ValueError as e:
        return {"success": False, "error": "invalid_path", "message": str(e)}

    abs_path = f"/workspace/{rel_path}"
    um = UserMemory(auth.client, auth.user_id)
    authored_by = "yarnnn:adr-231"

    current = await um.read(rel_path)

    try:
        if shape in _SINGLE_DECL_SHAPES:
            result = await _handle_recurrence_single(
                um=um,
                rel_path=rel_path,
                abs_path=abs_path,
                shape=shape,
                slug=slug,
                action=action,
                body=body,
                changes=changes,
                paused_until=paused_until,
                current=current,
                authored_by=authored_by,
            )
        else:
            result = await _handle_recurrence_multi(
                um=um,
                rel_path=rel_path,
                abs_path=abs_path,
                shape=shape,
                slug=slug,
                action=action,
                body=body,
                changes=changes,
                paused_until=paused_until,
                current=current,
                authored_by=authored_by,
            )
    except Exception as e:
        logger.warning(f"[MANAGE_RECURRENCE] {action} failed: {e}")
        return {"success": False, "error": "execution_error", "message": str(e)}

    # ADR-231 Phase 3.3: materialize scheduling index after successful YAML
    # write so the scheduler sees the change on its next tick. Best-effort —
    # the index is fully reconstructable from filesystem state.
    if result.get("success"):
        try:
            from services.scheduling import materialize_scheduling_index
            await materialize_scheduling_index(auth.client, auth.user_id)
        except Exception as e:
            logger.warning(
                f"[MANAGE_RECURRENCE] scheduling index materialization failed (non-fatal): {e}"
            )

    return result


async def _handle_recurrence_single(
    *,
    um,
    rel_path: str,
    abs_path: str,
    shape: str,
    slug: str,
    action: str,
    body: dict,
    changes: dict,
    paused_until: Optional[str],
    current: Optional[str],
    authored_by: str,
) -> dict:
    """Handle DELIVERABLE / ACTION shapes — one declaration per file."""
    from services.recurrence import (
        parse_recurrence_yaml,
        serialize_declaration_yaml,
        RecurrenceDeclaration,
        RecurrenceShape,
    )

    if action == "create":
        if current:
            return {
                "success": False,
                "error": "already_exists",
                "message": f"declaration already exists at {abs_path} (use action='update' to modify)",
            }
        body_with_slug = dict(body)
        body_with_slug.setdefault("slug", slug)
        decl = RecurrenceDeclaration.from_yaml_block(
            shape=RecurrenceShape(shape),
            slug=slug,
            declaration_path=abs_path,
            data=body_with_slug,
        )
        yaml_text = serialize_declaration_yaml(decl)
        ok = await um.write(
            rel_path,
            yaml_text,
            summary=f"recurrence:create {shape}/{slug}",
            authored_by=authored_by,
            message=f"create {shape} recurrence {slug}",
        )
        if not ok:
            return {"success": False, "error": "write_failed", "message": f"failed to write {abs_path}"}
        return {
            "success": True,
            "action": "create",
            "shape": shape,
            "slug": slug,
            "path": abs_path,
            "message": f"created {shape} recurrence at {abs_path}",
        }

    if action == "archive":
        if not current:
            return {"success": False, "error": "not_found", "message": f"no declaration at {abs_path}"}
        ok = await um.write(
            rel_path,
            "",
            summary=f"recurrence:archive {shape}/{slug}",
            authored_by=authored_by,
            message=f"archive {shape} recurrence {slug}",
        )
        if not ok:
            return {"success": False, "error": "write_failed", "message": f"failed to write {abs_path}"}
        return {
            "success": True,
            "action": "archive",
            "shape": shape,
            "slug": slug,
            "path": abs_path,
            "message": f"archived {shape} recurrence {slug}",
        }

    if not current:
        return {"success": False, "error": "not_found", "message": f"no declaration at {abs_path}"}

    decls = parse_recurrence_yaml(current, abs_path)
    if not decls:
        return {
            "success": False,
            "error": "parse_failed",
            "message": f"could not parse existing declaration at {abs_path}",
        }
    decl = decls[0]
    new_data = dict(decl.data)

    if action == "pause":
        new_data["paused"] = True
        if paused_until:
            new_data["paused_until"] = paused_until
        msg = f"paused {shape} recurrence {slug}"
    elif action == "resume":
        new_data["paused"] = False
        new_data.pop("paused_until", None)
        msg = f"resumed {shape} recurrence {slug}"
    elif action == "update":
        for k, v in changes.items():
            new_data[k] = v
        msg = f"updated {shape} recurrence {slug}: {sorted(changes.keys())}"
    else:
        return {"success": False, "error": "unhandled_action", "message": action}

    decl.data = new_data
    yaml_text = serialize_declaration_yaml(decl)
    ok = await um.write(
        rel_path,
        yaml_text,
        summary=f"recurrence:{action} {shape}/{slug}",
        authored_by=authored_by,
        message=msg,
    )
    if not ok:
        return {"success": False, "error": "write_failed", "message": f"failed to write {abs_path}"}
    return {
        "success": True,
        "action": action,
        "shape": shape,
        "slug": slug,
        "path": abs_path,
        "message": msg,
    }


async def _handle_recurrence_multi(
    *,
    um,
    rel_path: str,
    abs_path: str,
    shape: str,
    slug: str,
    action: str,
    body: dict,
    changes: dict,
    paused_until: Optional[str],
    current: Optional[str],
    authored_by: str,
) -> dict:
    """Handle ACCUMULATION / MAINTENANCE shapes — list-of-declarations file."""
    import yaml as _yaml

    list_key = "recurrences" if shape == "accumulation" else "back_office_jobs"

    parsed = {}
    if current:
        try:
            loaded = _yaml.safe_load(current)
            if isinstance(loaded, dict):
                parsed = loaded
        except _yaml.YAMLError as e:
            return {
                "success": False,
                "error": "parse_failed",
                "message": f"could not parse existing {abs_path}: {e}",
            }

    entries = parsed.get(list_key)
    if not isinstance(entries, list):
        entries = []

    def _entry_slug(entry: dict) -> Optional[str]:
        if not isinstance(entry, dict):
            return None
        s = entry.get("slug")
        if s:
            return str(s)
        if shape == "maintenance":
            from services.recurrence import _slug_from_executor

            ex = entry.get("executor")
            if ex:
                return _slug_from_executor(str(ex))
        return None

    idx = next((i for i, e in enumerate(entries) if _entry_slug(e) == slug), -1)

    if action == "create":
        if idx >= 0:
            return {
                "success": False,
                "error": "already_exists",
                "message": f"entry slug='{slug}' already exists in {abs_path} (use action='update')",
            }
        new_entry = dict(body)
        new_entry.setdefault("slug", slug)
        if shape == "maintenance" and not new_entry.get("executor"):
            return {
                "success": False,
                "error": "missing_executor",
                "message": "back-office entries require body.executor (dotted Python path)",
            }
        entries.append(new_entry)
        msg = f"created {shape} recurrence {slug}"
    elif action == "archive":
        if idx < 0:
            return {"success": False, "error": "not_found", "message": f"no entry slug='{slug}' in {abs_path}"}
        entries.pop(idx)
        msg = f"archived {shape} recurrence {slug}"
    else:
        if idx < 0:
            return {"success": False, "error": "not_found", "message": f"no entry slug='{slug}' in {abs_path}"}
        entry = dict(entries[idx])
        if action == "pause":
            entry["paused"] = True
            if paused_until:
                entry["paused_until"] = paused_until
            msg = f"paused {shape} recurrence {slug}"
        elif action == "resume":
            entry["paused"] = False
            entry.pop("paused_until", None)
            msg = f"resumed {shape} recurrence {slug}"
        elif action == "update":
            for k, v in changes.items():
                entry[k] = v
            msg = f"updated {shape} recurrence {slug}: {sorted(changes.keys())}"
        else:
            return {"success": False, "error": "unhandled_action", "message": action}
        entries[idx] = entry

    parsed[list_key] = entries
    yaml_text = _yaml.safe_dump(parsed, sort_keys=False, default_flow_style=False)
    ok = await um.write(
        rel_path,
        yaml_text,
        summary=f"recurrence:{action} {shape}/{slug}",
        authored_by=authored_by,
        message=msg,
    )
    if not ok:
        return {"success": False, "error": "write_failed", "message": f"failed to write {abs_path}"}
    return {
        "success": True,
        "action": action,
        "shape": shape,
        "slug": slug,
        "path": abs_path,
        "message": msg,
    }
