"""
SyncPlatformState Primitive — ADR-264

The canonical mechanical-recurrence-friendly primitive that wraps
``(platform-tool call → substrate write → diff-awareness)`` as one atomic
deterministic operation. Established by ADR-264 to honor FOUNDATIONS
Axiom 1 third clause: external-system state lives in substrate too.

Surface:
  SyncPlatformState(
      tool: str,                          # platform tool name, e.g. "platform_trading_get_positions"
      tool_args: dict = {},               # input arguments to the tool
      write_to: str,                      # substrate path template, e.g. "operation/portfolio/positions/{symbol}.yaml"
      iterate_field: str | None = None,   # if set, iterate over result[iterate_field] and write per-item
      item_key: str | None = None,        # template-variable name for per-item iteration (e.g. "symbol")
      diff_aware: bool = True,            # only write substrate if content meaningfully changed since prior revision
  )

Behavior:
  1. Call the platform tool via ``handle_platform_tool(auth, tool, tool_args)``.
  2. Resolve write target(s):
     - If ``iterate_field`` is None: single write to ``write_to``.
     - If ``iterate_field`` is set: iterate over ``result[iterate_field]``,
       write one substrate file per item using ``{item_key}`` template var.
  3. Diff-aware: skip writes whose content hasn't changed (saves revision noise).
  4. Write via ``write_revision()`` with ``authored_by="system:sync-platform-state"``
     and ``message="synced {tool} → {path}"``.
  5. Return ``{success, paths_written, paths_skipped, items_processed, error?}``.

Dispatch surfaces:
  - LLM tool: registered in HEADLESS_PRIMITIVES + FREDDIE_PRIMITIVES (NOT
    in CHAT_PRIMITIVES per ADR-264 D3 — operators don't invoke directly).
  - Mechanical recurrence: dispatched by the invocation_dispatcher when a
    mechanical-mode recurrence's prompt names ``@primitive: SyncPlatformState(...)``
    per ADR-263 D5 + ADR-264 D2.

This primitive does ONE job: mirror external state into substrate. It does
not evaluate significance, emit canonical verbs, or invoke the Reviewer.
The recurrence's ``mode=mechanical`` declaration (per ADR-263) is what
keeps the Reviewer asleep on these substrate writes.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


# --- ADR-392 D2 — the connector raw capture lane (ledger-intake, ADR-376/DP32) ---
# Connectors are the third context-in transport; a platform sync is an attributed
# RAW observation that lands IMMUTABLY in the capture lane (retain + attribute),
# and a SEPARATE derive act distills understanding into operation/ (cite via
# derived_from). Sibling to the live inbound/mcp/ + inbound/web/ lanes; NOT
# operation/ (that fusion was the pre-ADR-376 conflation). Raw-lane mechanism =
# Option A (inbound/ namespace, ADR-392 §3, ratified 2026-07-01); connectors
# enrol in the re-founding flag-day A→B flip with the other two lanes.
INBOUND_CAPTURE_PREFIX = "inbound/"
_DEFAULT_SELECTOR = "inbox"


def _slugify_selector(value: str) -> str:
    """Turn a channel/page/label/id into a safe single path segment.

    Mirrors the mcp/web sublane convention (lowercase, hyphenated, no slashes)
    so the connector lane is byte-parallel to inbound/mcp/{client}/ +
    inbound/web/{source}/.
    """
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return s or _DEFAULT_SELECTOR


def resolve_capture_path(
    platform: str,
    selector: Optional[str],
    observed_at: str,
    ext: str = "md",
) -> str:
    """Resolve where a connector RAW observation lands (ADR-392 D2 / ADR-376).

    inbound/{platform}/{selector}/{observed_at}.{ext} — the per-platform,
    per-selector capture sub-lane. `selector` is the channel/page/label/repo;
    absent → the platform's `inbox` sub-lane. `observed_at` is the caller-supplied
    intake timestamp (the primitive does not read the clock — Axiom 1 / resume
    safety; the recurrence stamps it). Immutable, attributed
    `system:sync-platform-state`; never rewritten.
    """
    plat = _slugify_selector(platform)
    sel = _slugify_selector(selector) if selector else _DEFAULT_SELECTOR
    stamp = (observed_at or "").strip() or "unknown"
    ext = (ext or "md").lstrip(".")
    return f"{INBOUND_CAPTURE_PREFIX}{plat}/{sel}/{stamp}.{ext}"


SYNC_PLATFORM_STATE_TOOL = {
    "name": "SyncPlatformState",
    "description": """Mirror external-system state into substrate (ADR-264).

Wraps a platform-tool call + substrate write + diff-awareness as one atomic
deterministic operation. The primitive's role is to mediate between an
external system (broker, commerce platform, GitHub, Slack, Notion, etc.)
and the workspace's substrate. Judgment reads substrate, never APIs.

Typical usage:
  - Inside a `mechanical`-mode recurrence's prompt (ADR-263), e.g.:
      mode: mechanical
      prompt: |
        @primitive: SyncPlatformState(
          tool="platform_trading_get_positions",
          write_to="operation/portfolio/positions/{symbol}.yaml",
          iterate_field="positions",
          item_key="symbol"
        )
  - Direct invocation by the Reviewer mid-loop (rare) or by a headless
    specialist that needs to refresh substrate before reasoning.

Per-item iteration: when ``iterate_field`` is set, the primitive iterates
over ``result[iterate_field]`` and writes one substrate file per item.
The ``item_key`` names the template variable in ``write_to`` that resolves
to each item's value at that key.

Diff-aware: when content matches the prior revision, the write is skipped
(no new revision row, no noise in the revision chain).""",
    "input_schema": {
        "type": "object",
        "properties": {
            "tool": {
                "type": "string",
                "description": "Platform tool name (e.g. 'platform_trading_get_positions'). Routed through handle_platform_tool.",
            },
            "tool_args": {
                "type": "object",
                "description": "Input arguments for the platform tool. Optional; defaults to empty dict.",
            },
            "write_to": {
                "type": "string",
                "description": "Substrate path template, workspace-relative (e.g. 'operation/portfolio/positions/{symbol}.yaml'). Template variables: {item_key} for per-item, plus any operator context.",
            },
            "iterate_field": {
                "type": "string",
                "description": "Optional. If set, iterate over result[iterate_field] and write per-item. Without this, writes a single file with the full result.",
            },
            "item_key": {
                "type": "string",
                "description": "Optional. Template-variable name for per-item iteration. Required when iterate_field is set.",
            },
            "diff_aware": {
                "type": "boolean",
                "description": "Default True. If True, skip writes whose content matches the prior revision (no new revision row).",
            },
            "capture": {
                "type": "object",
                "description": (
                    "ADR-392 D2 — connector context-in capture mode. When present, the "
                    "primitive routes the raw observation to the capture lane "
                    "inbound/{platform}/{selector}/{observed_at}.{ext} (retain + attribute; "
                    "ADR-376) instead of writing `write_to` directly. A SEPARATE derive act "
                    "(a judgment recurrence or steward wake) distills understanding into "
                    "operation/ citing the raw. Fields: platform (required, e.g. 'slack'), "
                    "selector (channel/page/label/repo; per-item resolved from item_key when "
                    "iterating), observed_at (required intake timestamp — the caller stamps it; "
                    "the primitive never reads the clock), ext (default 'md'). When absent, "
                    "legacy write_to-direct behavior is preserved (the alpha-trader migration "
                    "window; ADR-392 §5 step 7)."
                ),
                "properties": {
                    "platform": {"type": "string"},
                    "selector": {"type": "string"},
                    "observed_at": {"type": "string"},
                    "ext": {"type": "string"},
                },
            },
        },
        "required": ["tool", "write_to"],
    },
}


async def handle_sync_platform_state(auth: Any, input: dict) -> dict:
    """Execute SyncPlatformState primitive (ADR-264).

    Returns:
      {
        "success": bool,
        "paths_written": list[str],
        "paths_skipped": list[str],     # diff-aware skips
        "items_processed": int,
        "error": str | None,
      }
    """
    from services.platform_tools import handle_platform_tool
    from services.workspace import UserMemory

    user_id = getattr(auth, "user_id", None)
    db_client = getattr(auth, "client", None)
    if not user_id or not db_client:
        return {
            "success": False,
            "error": "auth_required",
            "paths_written": [],
            "paths_skipped": [],
            "items_processed": 0,
        }

    input = input or {}
    tool = input.get("tool")
    tool_args = input.get("tool_args") or {}
    write_to = input.get("write_to")
    iterate_field = input.get("iterate_field")
    item_key = input.get("item_key")
    diff_aware = bool(input.get("diff_aware", True))

    # ADR-392 D2 — connector capture mode. When `capture` is present, the raw
    # observation routes to the inbound/ lane (retain + attribute) and the
    # primitive derives the path itself; `write_to` is then optional. When
    # absent, legacy write_to-direct behavior holds (trader-migration window).
    capture = input.get("capture")
    capture_platform: Optional[str] = None
    capture_observed_at: Optional[str] = None
    capture_ext: str = "md"
    capture_selector: Optional[str] = None
    if capture is not None:
        if not isinstance(capture, dict):
            return {
                "success": False, "error": "capture_must_be_object",
                "paths_written": [], "paths_skipped": [], "items_processed": 0,
            }
        capture_platform = capture.get("platform")
        capture_observed_at = capture.get("observed_at")
        capture_ext = capture.get("ext") or "md"
        capture_selector = capture.get("selector")
        if not capture_platform or not isinstance(capture_platform, str):
            return {
                "success": False, "error": "capture_missing_platform",
                "paths_written": [], "paths_skipped": [], "items_processed": 0,
            }
        if not capture_observed_at or not isinstance(capture_observed_at, str):
            return {
                "success": False, "error": "capture_missing_observed_at",
                "paths_written": [], "paths_skipped": [], "items_processed": 0,
            }

    # Validate inputs
    if not tool or not isinstance(tool, str):
        return {
            "success": False,
            "error": "missing_tool",
            "paths_written": [], "paths_skipped": [], "items_processed": 0,
        }
    # write_to is required ONLY in legacy (non-capture) mode; capture mode
    # derives the raw-lane path itself.
    if capture is None and (not write_to or not isinstance(write_to, str)):
        return {
            "success": False,
            "error": "missing_write_to",
            "paths_written": [], "paths_skipped": [], "items_processed": 0,
        }
    if iterate_field and not item_key:
        return {
            "success": False,
            "error": "missing_item_key",
            "paths_written": [], "paths_skipped": [], "items_processed": 0,
        }

    # Call the platform tool
    try:
        tool_result = await handle_platform_tool(auth, tool, tool_args)
    except Exception as e:
        logger.warning("[SYNC_PLATFORM_STATE] platform tool %s raised: %s", tool, e)
        return {
            "success": False,
            "error": f"tool_raised: {e}",
            "paths_written": [], "paths_skipped": [], "items_processed": 0,
        }

    if not tool_result.get("success", False):
        return {
            "success": False,
            "error": tool_result.get("error") or "tool_failed",
            "paths_written": [], "paths_skipped": [], "items_processed": 0,
        }

    result = tool_result.get("result", {})
    um = UserMemory(db_client, user_id)
    paths_written: list[str] = []
    paths_skipped: list[str] = []

    # Single-write path
    if not iterate_field:
        # Capture mode derives inbound/{platform}/{selector}/{observed_at}.{ext};
        # legacy mode uses the caller's write_to directly.
        if capture is not None:
            path = resolve_capture_path(
                capture_platform, capture_selector, capture_observed_at, capture_ext,
            )
        else:
            path = write_to
        new_content = _serialize_for_substrate(path, result)
        wrote = await _write_if_changed(
            um, path, new_content, diff_aware=diff_aware,
            tool=tool,
        )
        if wrote:
            paths_written.append(_full_path_for_logging(path))
        else:
            paths_skipped.append(_full_path_for_logging(path))
        return {
            "success": True,
            "paths_written": paths_written,
            "paths_skipped": paths_skipped,
            "items_processed": 1,
        }

    # Per-item iteration path
    items = result.get(iterate_field)
    if not isinstance(items, list):
        return {
            "success": False,
            "error": f"iterate_field {iterate_field!r} did not yield a list (got {type(items).__name__})",
            "paths_written": [], "paths_skipped": [], "items_processed": 0,
        }

    items_processed = 0
    for item in items:
        if not isinstance(item, dict):
            logger.warning(
                "[SYNC_PLATFORM_STATE] iterate item is not a dict, skipping: %r", item,
            )
            continue
        item_value = item.get(item_key)
        if item_value is None:
            logger.warning(
                "[SYNC_PLATFORM_STATE] item missing key %r, skipping: %r",
                item_key, item,
            )
            continue

        # Resolve path. Capture mode: the per-item selector is the item_key
        # value (each channel/page becomes its own inbound sub-lane); legacy
        # mode: interpolate the caller's write_to template.
        if capture is not None:
            path = resolve_capture_path(
                capture_platform, str(item_value), capture_observed_at, capture_ext,
            )
        else:
            try:
                path = write_to.format(**{item_key: str(item_value)})
            except KeyError as e:
                logger.warning(
                    "[SYNC_PLATFORM_STATE] template resolution failed for write_to=%r missing %s",
                    write_to, e,
                )
                continue

        new_content = _serialize_for_substrate(path, item)
        wrote = await _write_if_changed(
            um, path, new_content, diff_aware=diff_aware,
            tool=tool,
        )
        if wrote:
            paths_written.append(_full_path_for_logging(path))
        else:
            paths_skipped.append(_full_path_for_logging(path))
        items_processed += 1

    return {
        "success": True,
        "paths_written": paths_written,
        "paths_skipped": paths_skipped,
        "items_processed": items_processed,
    }


def _serialize_for_substrate(path: str, payload: Any) -> str:
    """Serialize a payload to substrate-appropriate text by file extension.

    .yaml/.yml → YAML dump (operator-readable, machine-parseable)
    .json      → JSON dump
    .md        → markdown body if payload is a string, else YAML frontmatter wrap
    other      → JSON dump (safe default)
    """
    if path.endswith((".yaml", ".yml")):
        return yaml.safe_dump(payload, sort_keys=False, default_flow_style=False, allow_unicode=True)
    if path.endswith(".json"):
        return json.dumps(payload, indent=2, sort_keys=False, default=str)
    if path.endswith(".md"):
        if isinstance(payload, str):
            return payload
        # Wrap structured data in YAML frontmatter for markdown files
        frontmatter = yaml.safe_dump(payload, sort_keys=False, default_flow_style=False, allow_unicode=True)
        return f"---\n{frontmatter}---\n"
    # Safe default
    return json.dumps(payload, indent=2, sort_keys=False, default=str)


async def _write_if_changed(
    um: Any,
    rel_path: str,
    new_content: str,
    *,
    diff_aware: bool,
    tool: str,
) -> bool:
    """Write substrate, optionally skipping when content unchanged.

    Returns True if a write happened, False if skipped due to diff-awareness.
    """
    if diff_aware:
        try:
            existing = await um.read(rel_path)
        except Exception:
            existing = None
        if existing is not None and existing == new_content:
            return False

    full_abs = _full_path_for_logging(rel_path)
    await um.write(
        rel_path,
        new_content,
        summary=f"sync:{tool}",
        authored_by="system:sync-platform-state",
        message=f"synced {tool} → /workspace/{rel_path.lstrip('/')}",
    )
    logger.debug("[SYNC_PLATFORM_STATE] wrote %s via %s", full_abs, tool)
    return True


def _full_path_for_logging(rel_path: str) -> str:
    """Render a workspace-relative path as the operator-facing absolute path."""
    return f"/workspace/{rel_path.lstrip('/')}"


__all__ = [
    "SYNC_PLATFORM_STATE_TOOL",
    "handle_sync_platform_state",
    "resolve_capture_path",
    "INBOUND_CAPTURE_PREFIX",
]
