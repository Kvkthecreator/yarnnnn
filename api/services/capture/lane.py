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
    wake_source=None — there was no wake). Zero LLM. Never wakes the Reviewer
    directly — a connector capture that landed new raw CONTRIBUTES one derive
    PROPOSAL to the wake funnel (ADR-401 D5, `_propose_derive_wake`); the
    funnel + pace decide whether the seat actually wakes.

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

    # The lane stamps the run's observed_at into the capture primitive's args
    # (Axiom 1 — the primitive never reads the clock; the raw-lane filename is
    # {observed_at}.{ext}). Observed live 2026-07-03: without this, raw landed
    # as `unknown.md` — un-ageable by the retention GC (the window reads the
    # filename stamp) and one-file-per-selector instead of a snapshot series.
    if primitive_name == "CaptureConnector":
        primitive_args = {**primitive_args, "observed_at": observed_at}

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

    # ADR-401 D5 — derive attention-routing. A connector capture that landed
    # NEW raw proposes ONE derive wake for the whole run (the run is the
    # natural batch: one fan-out over the aperture). The capture itself stays
    # mechanical — this contributes a PROPOSAL to the funnel (which still
    # decides), exactly as the MCP `remember` path does for its raw lane
    # (mcp_composition's wake adapter — the derive route connector raw was
    # missing). Diff-aware skips mean paths_written is only ACTUAL new
    # content: an unchanged world proposes nothing.
    if success and primitive_name == "CaptureConnector" and isinstance(result, dict):
        paths_written = result.get("paths_written")
        if isinstance(paths_written, list) and paths_written:
            await _propose_derive_wake(
                client, user_id,
                slug=slug,
                primitive_args=primitive_args,
                paths_written=[str(p) for p in paths_written],
                observed_at=observed_at,
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


async def _propose_derive_wake(
    client,
    user_id: str,
    *,
    slug: str,
    primitive_args: dict,
    paths_written: list,
    observed_at: str,
) -> None:
    """Propose the seat derive freshly-captured connector raw (ADR-401 D5).

    The SINGLE site in the capture lane that touches the wake contract
    (services.wake.submit_wake_proposal) — deliberately isolated in one
    best-effort adapter, mirroring mcp_composition's foreign-write adapter
    (the same derive-and-cite seam, ADR-376/DP32). Everything else in the
    lane stays wake-agnostic.

    One proposal per capture RUN (not per file): dedup key is the run stamp
    (`{slug}:{observed_at}`), so a re-enqueue of the same run dedups at the
    queue's UNIQUE constraint (ADR-298 D6). The funnel + pace still decide
    whether/when the seat actually wakes; derive stays a judgment act
    (ADR-394 D3) — deriving nothing is a valid outcome for a noisy batch.
    A proposal failure never fails the capture.
    """
    platform = str(primitive_args.get("platform") or "").strip().lower() or "connector"
    n = len(paths_written)
    shown = paths_written[:20]
    listing = "\n".join(f"- {p}" for p in shown)
    if n > len(shown):
        listing += f"\n… and {n - len(shown)} more"

    prompt = (
        f"The {platform} capture just landed {n} new raw file(s) in the inbound lane "
        f"(attributed system:{slug} — the peripheral is the mechanism, not a contributor). "
        f"This raw is retained but is not yet part of the workspace's understanding, and "
        f"recall cannot see it until you derive it.\n\n"
        f"As the seat, engage the new raw and derive what is worth keeping: distill the "
        f"operation-relevant understanding into the operation's substrate as a SEPARATE "
        f"citing act — the derived file carries `derived_from:` naming the raw path(s) it "
        f"distills — and never rewrite or move the raw itself (it is the source of record). "
        f"Connector raw is a firehose, mostly noise: deriving nothing is a valid judgment; "
        f"say so briefly if the batch carries nothing the mandate cares about. Un-cited raw "
        f"ages out mechanically under the retention window; whatever you cite is kept as "
        f"evidence.\n\n"
        f"New raw files:\n{listing}"
    )

    try:
        from services.wake import submit_wake_proposal

        outcome = await submit_wake_proposal(
            client, user_id,
            source="substrate_event",
            payload={
                "hook": {
                    "slug": f"derive-{slug}",
                    "event": "substrate_change",
                    "prompt": prompt,
                },
                "path": str(paths_written[0]),
                "field_change": {"source": "connector-capture", "platform": platform},
                # Run-stable dedup stamp (consumed as the queue dedup key;
                # telemetry-only downstream — never dereferenced as a
                # workspace_file_versions id).
                "revision_id": f"{slug}:{observed_at}",
            },
        )
        logger.info(
            "[CAPTURE] %s/%s derive wake proposed (%d new file(s), dedup=%s)",
            user_id[:8], slug, n, bool(outcome.get("dedup")) if isinstance(outcome, dict) else "?",
        )
    except Exception as exc:  # noqa: BLE001 — the capture's substrate write is the work
        logger.warning(
            "[CAPTURE] %s/%s derive-wake proposal failed (capture unaffected): %s",
            user_id[:8], slug, exc,
        )


__all__ = ["run_capture_declaration", "parse_primitive_directive"]
