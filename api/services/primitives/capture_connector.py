"""
CaptureConnector Primitive — ADR-394

The connector *fan-out* capture primitive. Where SyncPlatformState (ADR-264)
mirrors ONE tool result into substrate (a state mirror, or a single-shot
capture), CaptureConnector loops a per-selector read tool over a *declared
watch* — the operator's `_watch.yaml` selection (ADR-392 D7) — and lands each
selected slice's raw observation in the capture lane.

This is the primitive the four-phase connector lane's **Phase 3 (Capture)**
needed and lacked (ADR-392 §5 step 4; ADR-394 D1):

    1 Connect — OAuth
    2 Select  — operator watch declaration (operation/_connectors/{platform}/_watch.yaml)
    3 Capture — THIS: loop the selected ids, mirror each raw into inbound/
    4 Derive  — the seat's derive-and-cite act (ADR-376; NOT here, NOT a cadence)

Why a NEW primitive, not a SyncPlatformState extension (ADR-394 D1):
SyncPlatformState iterates ``result[iterate_field]`` — items in ONE tool
result. Slack's ``platform_slack_get_channel_history`` takes a single
``channel_id``; capturing N selected channels means looping N *tool calls*,
which SyncPlatformState structurally can't do. Fan-out over a declaration is a
different job from mirroring one result, so it is its own primitive.
SyncPlatformState stays free of the connector-watch dependency; the raw-lane
path convention (``resolve_capture_path``) is REUSED, not duplicated.

Surface:
  CaptureConnector(
      platform: str,              # e.g. "slack" — the platform_connections.platform
      read_tool: str,             # e.g. "platform_slack_get_channel_history"
      selector_arg: str,          # the tool arg each selected id fills, e.g. "channel_id"
      tool_args: dict = {},       # static args merged into every per-selector call
      ext: str = "md",            # raw-lane file extension
      diff_aware: bool = True,    # skip a selector whose snapshot is unchanged
  )

Behavior (deterministic, zero LLM):
  1. Read the watch declaration's selected ids (connector_watch.read_selected_ids).
  2. For each selected id: handle_platform_tool(auth, read_tool,
     {**tool_args, selector_arg: id}).
  3. Write each raw result to inbound/{platform}/{id}/{observed_at}.{ext} via
     resolve_capture_path (reused from sync_platform_state) through the single
     write path, attributed system:sync-platform-state (the peripheral is the
     mechanism, not a principal — ADR-288).
  4. Diff-aware: an unchanged selector snapshot is skipped (no revision noise).
  5. observed_at is caller-stamped by the capture lane (Axiom 1 / resume
     safety — the primitive never reads the clock).

Return shape mirrors SyncPlatformState so the capture lane's health-signal
reader is unchanged: {success, paths_written, paths_skipped, items_processed}.

Dispatch surfaces (same policy as SyncPlatformState, ADR-264 D3):
  - HEADLESS_PRIMITIVES + FREDDIE_PRIMITIVES; NOT CHAT_PRIMITIVES (operators
    don't invoke capture directly).
  - Primary use: dispatched by a capture declaration in _captures.yaml, seeded
    at select-time (ADR-394 D2).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

# Reuse the raw-lane path convention + serialization + diff-aware write from
# the sibling primitive — Singular Implementation (ADR-394 D1: the path
# convention is not duplicated).
from services.primitives.sync_platform_state import (
    resolve_capture_path,
    _serialize_for_substrate,
    _write_if_changed,
    _full_path_for_logging,
)

logger = logging.getLogger(__name__)


CAPTURE_CONNECTOR_TOOL = {
    "name": "CaptureConnector",
    "description": """Fan-out connector capture: loop a per-selector read tool over the operator's watch declaration and land each selected slice's raw observation in the capture lane (ADR-394).

The connector Phase-3 (Capture) primitive. Reads the platform's watch
declaration (operation/_connectors/{platform}/_watch.yaml — the operator's
selected channels/pages/labels, ADR-392 D7), then calls the per-selector read
tool once per selected id and writes each raw result to
inbound/{platform}/{selector}/{observed_at}.{ext} (retain + attribute; ADR-376).
A SEPARATE derive act (the seat's derive-and-cite, ADR-376) distills
understanding into operation/ citing the raw — NOT this primitive, NOT a cadence.

Distinct from SyncPlatformState: that primitive mirrors ONE tool result (a
state mirror); this one loops a read tool over a DECLARATION of read targets.

Typical usage — inside a _captures.yaml declaration (seeded at select-time):
  @primitive: CaptureConnector(
    platform="slack",
    read_tool="platform_slack_get_channel_history",
    selector_arg="channel_id",
    tool_args={"limit": 50}
  )

Zero LLM. observed_at is stamped by the capture lane (the primitive never reads
the clock — Axiom 1 / resume safety). Diff-aware: an unchanged selector snapshot
is skipped (no revision noise).""",
    "input_schema": {
        "type": "object",
        "properties": {
            "platform": {
                "type": "string",
                "description": "The platform (e.g. 'slack') — matches platform_connections.platform and names the inbound/{platform}/ sub-lane.",
            },
            "read_tool": {
                "type": "string",
                "description": "The per-selector read tool (e.g. 'platform_slack_get_channel_history'). Routed through handle_platform_tool once per selected id.",
            },
            "selector_arg": {
                "type": "string",
                "description": "The read_tool argument each selected id fills (e.g. 'channel_id').",
            },
            "tool_args": {
                "type": "object",
                "description": "Static args merged into every per-selector call (e.g. {'limit': 50}). The selector_arg is set per-id and overrides any value here.",
            },
            "observed_at": {
                "type": "string",
                "description": "Intake timestamp for the raw-lane path — caller-stamped by the capture lane; the primitive never reads the clock (Axiom 1).",
            },
            "ext": {
                "type": "string",
                "description": "Raw-lane file extension (default 'md').",
            },
            "diff_aware": {
                "type": "boolean",
                "description": "Default True. Skip a selector whose snapshot matches the prior revision (no new revision row).",
            },
        },
        "required": ["platform", "read_tool", "selector_arg"],
    },
}


async def handle_capture_connector(auth: Any, input: dict) -> dict:
    """Execute CaptureConnector (ADR-394 D1).

    Returns:
      {
        "success": bool,
        "paths_written": list[str],
        "paths_skipped": list[str],   # diff-aware skips
        "items_processed": int,       # selected ids actually captured
        "error": str | None,
      }
    """
    from services.platform_tools import handle_platform_tool
    from services.connector_watch import read_selected_ids
    from services.workspace import UserMemory

    user_id = getattr(auth, "user_id", None)
    db_client = getattr(auth, "client", None)
    if not user_id or not db_client:
        return {
            "success": False, "error": "auth_required",
            "paths_written": [], "paths_skipped": [], "items_processed": 0,
        }

    input = input or {}
    platform = input.get("platform")
    read_tool = input.get("read_tool")
    selector_arg = input.get("selector_arg")
    tool_args = input.get("tool_args") or {}
    ext = input.get("ext") or "md"
    diff_aware = bool(input.get("diff_aware", True))
    # observed_at is caller-stamped by the capture lane (Axiom 1 — no clock read
    # in the primitive). Absent → "unknown" (resolve_capture_path tolerates it),
    # which only happens on a direct call outside the lane.
    observed_at = input.get("observed_at") or "unknown"

    if not platform or not isinstance(platform, str):
        return {
            "success": False, "error": "missing_platform",
            "paths_written": [], "paths_skipped": [], "items_processed": 0,
        }
    if not read_tool or not isinstance(read_tool, str):
        return {
            "success": False, "error": "missing_read_tool",
            "paths_written": [], "paths_skipped": [], "items_processed": 0,
        }
    if not selector_arg or not isinstance(selector_arg, str):
        return {
            "success": False, "error": "missing_selector_arg",
            "paths_written": [], "paths_skipped": [], "items_processed": 0,
        }

    # Phase 2 → Phase 3 bridge (ADR-394 D1, closes the watch-consumer gap):
    # the selected ids ARE what we capture. No selection → nothing to capture
    # (not an error — the platform is watched but nothing is in scope).
    selected_ids = await read_selected_ids(db_client, user_id, platform)
    if not selected_ids:
        logger.info(
            "[CAPTURE_CONNECTOR] %s/%s no selected ids — nothing to capture",
            user_id[:8], platform,
        )
        return {
            "success": True,
            "paths_written": [], "paths_skipped": [], "items_processed": 0,
        }

    um = UserMemory(db_client, user_id)
    paths_written: list[str] = []
    paths_skipped: list[str] = []
    items_processed = 0
    errors: list[str] = []

    for sel_id in selected_ids:
        call_args = {**tool_args, selector_arg: sel_id}
        try:
            tool_result = await handle_platform_tool(auth, read_tool, call_args)
        except Exception as e:
            logger.warning(
                "[CAPTURE_CONNECTOR] %s read_tool %s(%s=%s) raised: %s",
                platform, read_tool, selector_arg, sel_id, e,
            )
            errors.append(f"{sel_id}:tool_raised")
            continue

        if not isinstance(tool_result, dict) or not tool_result.get("success", False):
            err = (tool_result or {}).get("error") if isinstance(tool_result, dict) else "tool_failed"
            logger.warning(
                "[CAPTURE_CONNECTOR] %s read_tool %s(%s=%s) failed: %s",
                platform, read_tool, selector_arg, sel_id, err,
            )
            errors.append(f"{sel_id}:{err}")
            continue

        result = tool_result.get("result", {})
        # Each selector's raw lands in its own sub-lane:
        # inbound/{platform}/{selector}/{observed_at}.{ext}
        path = resolve_capture_path(platform, str(sel_id), observed_at, ext)
        new_content = _serialize_for_substrate(path, result)
        wrote = await _write_if_changed(
            um, path, new_content, diff_aware=diff_aware, tool=read_tool,
        )
        if wrote:
            paths_written.append(_full_path_for_logging(path))
        else:
            paths_skipped.append(_full_path_for_logging(path))
        items_processed += 1

    # Success iff at least one selector was processed without a hard tool error,
    # OR every selector was diff-skipped (nothing changed — a healthy quiet feed).
    # If every selected id errored, surface it as a failure so the health signal
    # reflects a dead peripheral.
    all_errored = bool(errors) and items_processed == 0
    return {
        "success": not all_errored,
        "paths_written": paths_written,
        "paths_skipped": paths_skipped,
        "items_processed": items_processed,
        "error": ("; ".join(errors[:5]) if all_errored else None),
    }


__all__ = ["CAPTURE_CONNECTOR_TOOL", "handle_capture_connector"]
