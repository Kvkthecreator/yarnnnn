"""
The capture lane executor (ADR-393).

Runs one capture declaration deterministically: parse its ``@primitive: ...``
directive, look up the handler, execute it with a system-attributed auth
shape, write the per-declaration health signal, and record one
``execution_events`` row (``funnel_decision="capture"``). Zero LLM. No wake,
no balance gate, no funnel — a capture runs on cadence to make substrate fresh
and wakes no one (ADR-393 D1).

This is a clean rebuild of the deleted ``wake.py::_dispatch_mechanical`` body —
the directive parser, the platform-capability gate, and the transition-guarded
"capability missing" narration all move here, where they belong. The `wake.py`
carve-out (the "theatre" bypass) is deleted, not carried as a fallback
(Singular Implementation).

Attribution (ADR-209 / ADR-288): the executing actor is the mechanism, not a
principal. Auth carries ``caller_identity = "system:<slug>"`` as the default;
a primitive that asserts its own specific actor name (e.g. SyncPlatformState →
``system:sync-platform-state``) still wins per ADR-288 D2.
"""

from __future__ import annotations

import logging
import re as _re
from datetime import datetime, timezone
from typing import Any, Optional

import yaml as _yaml

from services.capture.declarations import CaptureDeclaration, write_capture_signal
from services.telemetry import record_execution_event

try:
    import sentry_sdk as _sentry
    _SENTRY_AVAILABLE = True
except ImportError:
    _SENTRY_AVAILABLE = False

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Directive parsing — @primitive: <Name>(<args>)
#
# Moved verbatim (behavior-preserving) from the deleted wake.py mechanical
# dispatcher. The capture declaration's `primitive:` body names a primitive
# call; we parse it into (name, kwargs) and run the registered handler.
# ---------------------------------------------------------------------------

_PRIMITIVE_DIRECTIVE_RE = _re.compile(
    r"@primitive:\s*(\w+)\s*\((.*?)\)\s*$",
    _re.DOTALL,
)


def parse_primitive_directive(directive: str) -> Optional[tuple[str, dict]]:
    """Parse a ``@primitive: <Name>(<args>)`` directive body.

    Returns ``(primitive_name, kwargs_dict)`` or None if unparseable. Args are
    coerced from Python-flavored kwargs (``tool="x", write_to="y"``) to a YAML
    flow-mapping by replacing top-level ``=`` with ``:`` — same conservative
    transform the pre-ADR-393 dispatcher used, so bundle directives move
    byte-for-byte.
    """
    if not directive:
        return None
    text = directive.strip()
    m = _PRIMITIVE_DIRECTIVE_RE.search(text)
    if not m:
        return None
    primitive_name = m.group(1)
    args_body = m.group(2).strip()
    if not args_body:
        return (primitive_name, {})

    yaml_body = _re.sub(r"(\b\w+)\s*=\s*", r"\1: ", args_body)
    try:
        parsed = _yaml.safe_load("{" + yaml_body + "}")
    except Exception as e:
        logger.warning(
            "[CAPTURE] failed to parse @primitive args: %s | body=%r", e, args_body,
        )
        return None
    if not isinstance(parsed, dict):
        logger.warning(
            "[CAPTURE] @primitive args did not parse to a dict: %r", parsed,
        )
        return None
    return (primitive_name, parsed)


# ---------------------------------------------------------------------------
# Platform-capability gate (moved from wake.py)
#
# A capture primitive that wraps a platform API (SyncPlatformState) can be
# derived to a required platform_connections.platform from its args; skip
# without firing when the connection is absent, so a per-minute capture on a
# disconnected platform doesn't spam credential failures.
# ---------------------------------------------------------------------------


def _required_platform_for_primitive(
    primitive_name: str, primitive_args: dict
) -> Optional[str]:
    """Derive the required platform (e.g. 'trading', 'slack') from a capture
    primitive's args, or None if it doesn't depend on a platform connection.

    Two shapes:
      - SyncPlatformState: convention ``tool="platform_<name>_<verb>"`` →
        ``<name>`` == platform_connections.platform.
      - CaptureConnector (ADR-394): the ``platform=`` arg names it directly.

    A capture on a disconnected platform skips (health-signals) rather than
    fires-and-fails."""
    args = primitive_args or {}
    if primitive_name == "CaptureConnector":
        platform = args.get("platform")
        return platform if isinstance(platform, str) and platform else None
    if primitive_name != "SyncPlatformState":
        return None
    tool = args.get("tool")
    if not isinstance(tool, str) or not tool.startswith("platform_"):
        return None
    parts = tool.split("_", 2)
    if len(parts) < 3:
        return None
    return parts[1]


def _platform_connection_active(client, user_id: str, platform: str) -> bool:
    """True iff the user has an active platform_connections row for `platform`.
    Fail-closed: any DB error returns False (skip rather than fire-and-fail)."""
    try:
        result = (
            client.table("platform_connections")
            .select("id")
            .eq("user_id", user_id)
            .eq("platform", platform)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        return bool(result.data)
    except Exception as e:
        logger.warning(
            "[CAPTURE:cap-gate] platform_connections lookup failed for %s/%s: %s",
            user_id[:8], platform, e,
        )
        return False


class _CaptureAuth:
    """Auth shape for primitive handlers running in the capture lane. Mirrors
    the pre-ADR-393 `_MechanicalAuth` + the `kernel_mirrors._MirrorAuth`
    precedent: `caller_identity` carries the ADR-288 attribution default; the
    primitive overrides with its own actor name where it asserts one."""

    def __init__(self, user_id: str, client: Any, caller_identity: str):
        self.user_id = user_id
        self.client = client
        self.caller_identity = caller_identity


async def run_capture_declaration(
    client,
    user_id: str,
    declaration: CaptureDeclaration,
) -> dict:
    """Execute one capture declaration deterministically (ADR-393 D1).

    Parses the ``@primitive:`` directive, gates on platform connection where
    applicable, runs the registered handler, writes the per-declaration health
    signal, and records one ``execution_events`` row (funnel_decision=capture,
    wake_source=None — there was no wake). Zero LLM. Never wakes the Reviewer.

    Returns ``{success, slug, primitive?, items?, error_reason?, duration_ms}``.
    Best-effort on the health signal + telemetry — a capture's substrate write
    is the work; signal/telemetry failures are logged, not propagated.
    """
    if declaration.paused:
        return {"success": True, "slug": declaration.slug, "skipped": "paused"}

    started_at = datetime.now(timezone.utc)
    observed_at = started_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    slug = declaration.slug

    if _SENTRY_AVAILABLE:
        with _sentry.configure_scope() as scope:
            scope.set_user({"id": user_id})
            scope.set_tag("capture_slug", slug)

    parsed = parse_primitive_directive(declaration.primitive)
    if parsed is None:
        msg = f"capture {slug!r} has no parseable @primitive: directive"
        logger.warning("[CAPTURE] %s", msg)
        record_execution_event(
            client, user_id=user_id, slug=slug,
            mode="mechanical", trigger_type="capture",
            status="failed", error_reason="no_primitive_directive",
            error_detail=msg, funnel_decision="capture",
        )
        await write_capture_signal(
            client, user_id, slug=slug, status="error",
            observed_at=observed_at, last_error="no_primitive_directive",
        )
        return {"success": False, "slug": slug, "error_reason": "no_primitive_directive"}

    primitive_name, primitive_args = parsed

    # Platform-capability gate: skip (don't fire) when a required connection is
    # absent. Records a skipped row + a health-signal block; no narration spam
    # (the health signal IS the operator surface for a dead peripheral, ADR-389).
    required_platform = _required_platform_for_primitive(primitive_name, primitive_args)
    if required_platform and not _platform_connection_active(client, user_id, required_platform):
        record_execution_event(
            client, user_id=user_id, slug=slug,
            mode="mechanical", trigger_type="capture",
            status="skipped", error_reason="capability_missing",
            error_detail=f"required platform {required_platform!r} not connected",
            funnel_decision="capture",
        )
        await write_capture_signal(
            client, user_id, slug=slug, status="skipped",
            observed_at=observed_at,
            last_error=f"capability_missing:{required_platform}",
        )
        return {
            "success": False, "slug": slug,
            "error_reason": "capability_missing",
        }

    try:
        from services.primitives.registry import HANDLERS
    except ImportError as e:
        logger.exception("[CAPTURE] HANDLERS import failed: %s", e)
        return {"success": False, "slug": slug, "error_reason": "registry_import_failed"}

    handler = HANDLERS.get(primitive_name)
    if handler is None:
        msg = f"capture {slug!r} names unknown primitive {primitive_name!r}"
        logger.warning("[CAPTURE] %s", msg)
        record_execution_event(
            client, user_id=user_id, slug=slug,
            mode="mechanical", trigger_type="capture",
            status="failed", error_reason="unknown_primitive",
            error_detail=msg, funnel_decision="capture",
        )
        await write_capture_signal(
            client, user_id, slug=slug, status="error",
            observed_at=observed_at, last_error=f"unknown_primitive:{primitive_name}",
        )
        return {"success": False, "slug": slug, "error_reason": "unknown_primitive"}

    auth = _CaptureAuth(
        user_id=user_id,
        client=client,
        caller_identity=f"system:{slug}",
    )

    try:
        result = await handler(auth, primitive_args)
    except Exception as e:
        logger.exception(
            "[CAPTURE] %s/%s primitive %s raised: %s",
            user_id[:8], slug, primitive_name, e,
        )
        if _SENTRY_AVAILABLE:
            _sentry.capture_exception(e)
        duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        record_execution_event(
            client, user_id=user_id, slug=slug,
            mode="mechanical", trigger_type="capture",
            status="failed", error_reason="primitive_raised",
            error_detail=str(e), duration_ms=duration_ms,
            funnel_decision="capture",
        )
        await write_capture_signal(
            client, user_id, slug=slug, status="error",
            observed_at=observed_at, last_error=f"primitive_raised:{e}"[:500],
        )
        return {"success": False, "slug": slug, "error_reason": "primitive_raised",
                "duration_ms": duration_ms}

    duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
    success = bool(result.get("success", False)) if isinstance(result, dict) else False
    status = "success" if success else "failed"
    inner_error = None
    if not success and isinstance(result, dict):
        inner_error = result.get("error")

    # items processed: prefer the primitive's own count; fall back to paths written.
    items: Optional[int] = None
    target: Optional[str] = None
    if isinstance(result, dict):
        if isinstance(result.get("items_processed"), int):
            items = result["items_processed"]
        elif isinstance(result.get("paths_written"), list):
            items = len(result["paths_written"])
        pw = result.get("paths_written")
        if isinstance(pw, list) and pw:
            target = pw[0]

    record_execution_event(
        client, user_id=user_id, slug=slug,
        mode="mechanical", trigger_type="capture",
        status=status, duration_ms=duration_ms,
        error_reason=None if success else inner_error,
        funnel_decision="capture",
    )
    await write_capture_signal(
        client, user_id, slug=slug,
        status="ok" if success else "error",
        observed_at=observed_at, items=items, target=target,
        last_error=None if success else (str(inner_error)[:500] if inner_error else "failed"),
    )

    logger.info(
        "[CAPTURE] %s/%s done (status=%s duration_ms=%d primitive=%s items=%s)",
        user_id[:8], slug, status, duration_ms, primitive_name, items,
    )
    return {
        "success": success,
        "slug": slug,
        "primitive": primitive_name,
        "items": items,
        "result": result,
        "duration_ms": duration_ms,
        "error_reason": inner_error,
    }


__all__ = ["run_capture_declaration", "parse_primitive_directive"]
