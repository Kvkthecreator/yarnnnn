"""
Foreign-read observability — ADR-335 Crawl-B, Increment A step 3.

A foreign MCP read is a zero-LLM HTTP call (no tokens, ~no dollar cost). The
real concern the amendment named (§E.B) is not dollars but *call volume* — an
unbounded mechanical executor hammering a flaky/adversarial server on a tight
recurrence. Per the 2026-06-19 decision: **observability first, enforcement
later** (the empirical-gate discipline — don't pick a rate cap on a guess;
record real volume, then bound it on evidence).

This module is the **metered mechanical executor** (ADR-335 B3): the one place
a foreign tool is invoked, bounded, with every fire recorded to the cost ledger.
It keeps `mcp_client.py` transport-pure — the client fetches; this records.

Singular Implementation: foreign calls reuse the ONE cost ledger
(`execution_events`, ADR-291) via `record_execution_event`. No new table — a
foreign read is a `mode='mechanical'` row (ADR-263: "runs deterministic Python")
with token fields omitted and `duration_ms` set. Foreign-call volume is then
visible in the existing ledger + calibration mirror with zero new infra.

Enforcement (per-binding rate caps) is a deliberate fast-follow, gated on the
volume data this recording produces — NOT built here.
"""

import logging
import time
from typing import Any, Optional

from integrations.core.mcp_client import MCPToolResult, get_mcp_client

logger = logging.getLogger(__name__)


async def read_foreign_tool(
    client: Any,
    *,
    user_id: str,
    watch_slug: str,
    server_url: str,
    access_token: str,
    tool_name: str,
    arguments: Optional[dict[str, Any]] = None,
) -> MCPToolResult:
    """Invoke one foreign MCP tool and record the call to the cost ledger.

    The ONE metered call site for foreign reads (ADR-335 B3). Bounded: one tool
    call, one ledger row, every fire observable. Never raises on a telemetry
    failure (recording is best-effort; the read result is what matters).

    Args:
        client:       Supabase service client (for the ledger write)
        user_id:      workspace owner
        watch_slug:   the declared watch this read serves (the ledger `slug`)
        server_url:   the bound MCP server
        access_token: decrypted token for the binding (TokenManager path)
        tool_name:    the foreign tool to call
        arguments:    tool arguments

    Returns the raw MCPToolResult (caller distills + attributes per D3).
    """
    mcp = get_mcp_client()
    started = time.monotonic()
    status = "success"
    error_detail: Optional[str] = None
    result: Optional[MCPToolResult] = None
    try:
        result = await mcp.call_tool(server_url, access_token, tool_name, arguments)
        if result.is_error:
            status = "failed"
            error_detail = (result.text or "foreign tool reported isError")[:2000]
    except Exception as exc:  # transport / auth / protocol failure
        status = "failed"
        error_detail = str(exc)[:2000]
        raise
    finally:
        duration_ms = int((time.monotonic() - started) * 1000)
        _record_foreign_read(
            client,
            user_id=user_id,
            watch_slug=watch_slug,
            server_url=server_url,
            tool_name=tool_name,
            status=status,
            duration_ms=duration_ms,
            error_detail=error_detail,
        )
    return result  # type: ignore[return-value]


def _record_foreign_read(
    client: Any,
    *,
    user_id: str,
    watch_slug: str,
    server_url: str,
    tool_name: str,
    status: str,
    duration_ms: int,
    error_detail: Optional[str],
) -> None:
    """Write one foreign-read row to execution_events (mode='mechanical',
    zero tokens). Best-effort — never raises into the read path."""
    try:
        from services.telemetry import record_execution_event

        record_execution_event(
            client,
            user_id=user_id,
            # slug carries watch + transport identity so volume is groupable
            # per-watch and per-server in the existing ledger.
            slug=f"foreign-read:{watch_slug}",
            mode="mechanical",
            trigger_type="scheduled",
            status=status,
            duration_ms=duration_ms,
            error_reason="foreign_read_failed" if status == "failed" else None,
            error_detail=error_detail,
            # No token fields — a foreign read is zero-LLM. The mechanical mode +
            # the foreign-read slug prefix are how this row is identified as a
            # foreign call in the ledger / calibration mirror.
        )
    except Exception as exc:  # telemetry is best-effort
        logger.info(
            "[FOREIGN-READ] ledger write failed for watch=%s tool=%s: %s",
            watch_slug, tool_name, exc,
        )
