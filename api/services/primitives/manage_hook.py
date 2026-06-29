"""
ManageHook Primitive — ADR-296 v2 D2.

The canonical way to author / modify / pause / resume / archive a hook
in /workspace/_hooks.yaml. Available in both chat and headless modes;
present in CHAT_PRIMITIVES + FREDDIE_PRIMITIVES.

Per ADR-296 v2 D2, hooks are the sibling declarative shape to recurrences:
  - Recurrences are the cron-tick wake source's configuration (time-driven)
  - Hooks are the substrate-event wake source's configuration (event-driven)
Both compose into the singular evaluation gate identically.

A hook is a record with five load-bearing fields ({slug, event,
path_match, field_change, prompt}) living in the single canonical file
``/workspace/_hooks.yaml``. The substrate-event wake source walks
workspace_file_versions at every scheduler tick, matches revisions
against declared hooks, and submits a wake proposal per match.

Five actions (mirror Schedule):
  - "create"   append a new entry (slug must be unique)
  - "update"   merge fields into an existing entry
  - "pause"    set paused: true
  - "resume"   set paused: false
  - "archive"  remove the entry (revision log preserves prior state per ADR-209)

Authorship per ADR-209:
  - Operator-via-chat:   authored_by="operator"
  - Reviewer-mid-loop:   authored_by="freddie:{occupant}"
  - System (bundle fork):authored_by="system:bundle-fork"
All three paths produce the same substrate writes through the same
primitive. Per Singular Implementation, no separate paths exist.

Reviewer hook authoring is part of its cadence + standing-intent
authority per ADR-296 v2 D3 — declaring interest in a substrate
transition is the substrate-event analog of authoring cadence.
"""

from __future__ import annotations

import logging
from typing import Any

import yaml

from services.wake_sources.substrate_event import HOOKS_PATH, parse_hooks

logger = logging.getLogger(__name__)


MANAGE_HOOK_TOOL = {
    "name": "ManageHook",
    "description": """Manage a substrate-event hook in /workspace/_hooks.yaml (ADR-296 v2 D2).

A hook is a record with five load-bearing fields:
  slug:         stable identifier
  event:        "substrate_change" (today's only event type)
  path_match:   workspace-absolute glob pattern (e.g., "/workspace/operation/authored/*/profile.md")
  field_change: dict of frontmatter key → expected new value (e.g., {status: "ready_for_review"})
  prompt:       what the Reviewer reads when the hook fires

ONE primitive, FIVE actions:
  - "create"   append a new entry. Requires slug, path_match, field_change, prompt.
  - "update"   merge fields into existing entry. Requires slug.
  - "pause"    set paused: true.
  - "resume"   set paused: false.
  - "archive"  remove the entry. Slug must exist.

Per ADR-296 v2 D2, hooks are the substrate-event wake source's
configuration. The substrate-event wake source walks workspace_file_versions
at every scheduler tick, matches against declared hooks, and submits a
wake proposal per match. The transition guard ensures the hook fires
ONLY on the transition into the matched state (not on every write that
preserves it).

Example: author a pre-ship-audit hook for an authoring program

  ManageHook(action="create",
      slug="pre-ship-audit",
      path_match="/workspace/operation/authored/*/profile.md",
      field_change={"status": "ready_for_review"},
      prompt="A draft was just marked ready_for_review. Read the draft at /workspace/operation/authored/{piece-slug}/content.md and audit per voice + continuity + anti-slop + editorial criteria. ...")

Example: pause + resume

  ManageHook(action="pause", slug="pre-ship-audit")
  ManageHook(action="resume", slug="pre-ship-audit")
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "update", "pause", "resume", "archive"],
                "description": "The lifecycle action to perform.",
            },
            "slug": {
                "type": "string",
                "description": "Hook slug — stable identifier within /workspace/_hooks.yaml.",
            },
            "event": {
                "type": "string",
                "description": "Event type — today's only value is 'substrate_change'.",
            },
            "path_match": {
                "type": "string",
                "description": (
                    "Workspace-absolute glob pattern (fnmatch syntax) for the "
                    "path(s) this hook listens on. E.g., "
                    "'/workspace/operation/authored/*/profile.md'."
                ),
            },
            "field_change": {
                "type": "object",
                "description": (
                    "Dict of frontmatter key → expected new value. The hook "
                    "fires only on the transition into this state (not on "
                    "every write that preserves it). Multi-field hooks are "
                    "conjunctive."
                ),
            },
            "prompt": {
                "type": "string",
                "description": (
                    "What the Reviewer reads when the hook fires. The "
                    "addressed-equivalent envelope; tells the Reviewer what "
                    "to do with the substrate transition."
                ),
            },
            "changes": {
                "type": "object",
                "description": "Dict of field → new-value for action='update'.",
            },
            "authored_by": {
                "type": "string",
                "description": (
                    "Required attribution per ADR-209 / ADR-296 v2 D3. "
                    "'operator' for chat, 'freddie:{occupant}' for the "
                    "Reviewer's own writes, 'system:bundle-fork' for "
                    "bundle activation. Auth.caller_identity is the default."
                ),
            },
        },
        "required": ["action", "slug"],
    },
}


async def handle_manage_hook(auth: Any, input: dict) -> dict:
    """Execute a ManageHook action against /workspace/_hooks.yaml.

    Returns a dict with `success` plus action-specific fields.

    Per ADR-209 + ADR-296 v2: every write goes through UserMemory.write
    (which routes to write_revision with the supplied authored_by and
    a descriptive message).
    """
    from services.workspace import UserMemory  # local import: avoid cycle

    user_id = getattr(auth, "user_id", None)
    db_client = getattr(auth, "client", None)
    if not user_id:
        return {"success": False, "error": "auth_required", "message": "user_id required"}

    input = input or {}
    action = input.get("action") or ""
    slug = input.get("slug") or ""
    changes = input.get("changes") or {}

    authored_by_raw = input.get("authored_by") or getattr(auth, "caller_identity", None)
    if not authored_by_raw or not isinstance(authored_by_raw, str) or not authored_by_raw.strip():
        return {
            "success": False,
            "error": "missing_authored_by",
            "message": (
                "ManageHook requires authored_by per ADR-209. Pass "
                "'operator', 'freddie:{occupant}', 'agent:{slug}', or "
                "'system:bundle-fork'. Silent attribution would break the "
                "ADR-209 revision-chain audit trail."
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
    # HOOKS_PATH is "/workspace/_hooks.yaml"; strip /workspace/ for UserMemory.
    rel_path = HOOKS_PATH[len("/workspace/"):]
    current = await um.read(rel_path)

    hooks = parse_hooks(current or "")
    idx = next((i for i, h in enumerate(hooks) if h.get("slug") == slug), -1)

    if action == "create":
        if idx >= 0:
            return {
                "success": False,
                "error": "already_exists",
                "message": f"hook slug={slug!r} already exists (use action='update')",
            }
        path_match = input.get("path_match") or ""
        field_change = input.get("field_change") or {}
        prompt = input.get("prompt") or ""
        event = input.get("event") or "substrate_change"

        if not path_match:
            return {
                "success": False,
                "error": "missing_path_match",
                "message": "path_match is required for create",
            }
        if not isinstance(field_change, dict) or not field_change:
            return {
                "success": False,
                "error": "missing_field_change",
                "message": "field_change must be a non-empty dict for create",
            }
        if not prompt or not str(prompt).strip():
            return {
                "success": False,
                "error": "missing_prompt",
                "message": "prompt is required for create",
            }
        if event != "substrate_change":
            return {
                "success": False,
                "error": "invalid_event",
                "message": f"event={event!r} must be 'substrate_change' (today's only event type)",
            }

        new_hook = {
            "slug": slug,
            "event": event,
            "path_match": path_match,
            "field_change": dict(field_change),
            "prompt": str(prompt).strip(),
            "paused": False,
        }
        hooks.append(new_hook)
        msg = f"created hook {slug}"

    elif action == "archive":
        if idx < 0:
            return {
                "success": False,
                "error": "not_found",
                "message": f"hook slug={slug!r} not found",
            }
        hooks.pop(idx)
        msg = f"archived hook {slug}"

    else:
        if idx < 0:
            return {
                "success": False,
                "error": "not_found",
                "message": f"hook slug={slug!r} not found",
            }
        hook = hooks[idx]

        if action == "pause":
            hook["paused"] = True
            msg = f"paused hook {slug}"
        elif action == "resume":
            hook["paused"] = False
            msg = f"resumed hook {slug}"
        elif action == "update":
            applied = []
            for k, v in (changes or {}).items():
                if k == "slug":
                    continue  # immutable
                if k in ("event", "path_match", "prompt"):
                    if v and str(v).strip():
                        hook[k] = str(v).strip()
                        applied.append(k)
                elif k == "field_change":
                    if isinstance(v, dict) and v:
                        hook[k] = dict(v)
                        applied.append(k)
                elif k == "paused":
                    hook[k] = bool(v)
                    applied.append(k)
            msg = f"updated hook {slug}: {sorted(applied)}"
        hooks[idx] = hook

    # Serialize back to YAML
    yaml_body = {"hooks": hooks} if hooks else {"hooks": []}
    yaml_text = yaml.safe_dump(yaml_body, sort_keys=False, default_flow_style=False)

    ok = await um.write(
        rel_path,
        yaml_text,
        summary=f"hook:{action} {slug}",
        authored_by=authored_by,
        message=msg,
    )
    if not ok:
        return {
            "success": False,
            "error": "write_failed",
            "message": f"failed to write {HOOKS_PATH}",
        }

    return {
        "success": True,
        "action": action,
        "slug": slug,
        "path": HOOKS_PATH,
        "message": msg,
        "hook_count": len(hooks),
    }


__all__ = ["MANAGE_HOOK_TOOL", "handle_manage_hook"]
