"""Sources endpoint — the standing-watch "drivers" view (ADR-338 D4.1).

`GET /api/sources` returns the operator's declared web/RSS watch sources
(`_sources.yaml`) paired with the last-observed per-source health from the
distilled signal substrate (`_watch_signal.yaml`) — the Check-7
declared-vs-observed shape. The FE `/sources` atomic surface (register:
os-config — a transport "driver" binding per ADR-338 D2) consumes this for
the watch editor + health column.

Kernel-agnostic (ADR-224 boundary): the watch declaration path is NOT
hardcoded. It is discovered from the active bundle's
`substrate_abi.watches[].declaration` via `bundle_reader.get_watches_for_workspace`.
A workspace with no active bundle watch returns an empty watches list — the
surface degrades to the honest "no standing watch declared" empty state
(perception is a flow, never a gate — ADR-332 §2).

The declaration is operator-owned + operator-edited (the FE writes it via
`writeShape('sources', <declaration_path>, ...)` → WriteFile per ADR-235
D1.b). The signal is system-written (TrackWebSources, `system:track-web-sources`)
and read-only here — the operator never edits observed health.

Auth boundary: derives user from `auth.user_id`. No cross-user reads.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

import yaml as _yaml
from fastapi import APIRouter
from pydantic import BaseModel

from services.supabase import UserClient
from services.workspace_context import substrate_scope_filter

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response shapes
# ---------------------------------------------------------------------------


class DeclaredSource(BaseModel):
    """One operator-declared watch source (the `sources[]` entry shape)."""

    id: str
    url: str
    attestation: str = "platform"
    max_entries: int = 8


class ObservedSourceHealth(BaseModel):
    """Last-observed health for a declared source (from `_watch_signal.yaml`).

    Pairs to a DeclaredSource by id. Absent when the watch has never fired
    or the signal file does not yet exist — the FE renders that as "not yet
    observed" rather than a freshness error.
    """

    id: str
    status: str  # 'ok' | 'error'
    observed_at: Optional[str] = None
    entry_count: int = 0
    error: Optional[str] = None


class WatchView(BaseModel):
    """One standing watch: its declared sources + observed health, paired.

    `declaration_path` is the workspace-relative path the FE writes to when
    the operator edits the source list (kernel-agnostic — comes from the
    bundle, not a kernel constant).
    """

    watch_id: str
    program_slug: Optional[str] = None
    shape: Optional[str] = None
    recurrence: Optional[str] = None
    declaration_path: str
    signal_path: Optional[str] = None
    declared: list[DeclaredSource]
    observed: list[ObservedSourceHealth]
    observed_at: Optional[str] = None
    source_cap: int = 12


class SourcesResponse(BaseModel):
    """All standing watches for the workspace. Empty when no active bundle
    declares a watch (honest empty state — not an error)."""

    watches: list[WatchView]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TIER_FM_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)


def _read_workspace_file(client: Any, user_id: str, rel_path: str) -> str:
    """Read one workspace file's content. '' on miss/error."""
    path = rel_path if rel_path.startswith("/workspace/") else f"/workspace/{rel_path.lstrip('/')}"
    try:
        res = (
            client.table("workspace_files")
            .select("content")
            .eq(*substrate_scope_filter(user_id))
            .eq("path", path)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning("[SOURCES] read failed for %s: %s", path, exc)
        return ""
    return (res.data or [{}])[0].get("content") or ""


def _strip_tier_frontmatter(content: str) -> str:
    m = _TIER_FM_RE.match(content)
    return content[m.end():] if m else content


def _parse_declared(content: str) -> list[DeclaredSource]:
    """Parse `_sources.yaml` → DeclaredSource[]. Tolerant: bad rows skipped."""
    if not content.strip():
        return []
    try:
        parsed = _yaml.safe_load(_strip_tier_frontmatter(content)) or {}
    except _yaml.YAMLError:
        return []
    raw = parsed.get("sources") if isinstance(parsed, dict) else None
    if not isinstance(raw, list):
        return []
    out: list[DeclaredSource] = []
    for s in raw:
        if not isinstance(s, dict):
            continue
        url = s.get("url")
        if not url or not isinstance(url, str):
            continue
        sid = str(s.get("id") or url)
        attestation = s.get("attestation") or "platform"
        if attestation not in ("platform", "operator", "agent"):
            attestation = "platform"
        try:
            max_entries = max(1, min(int(s.get("max_entries") or 8), 20))
        except (TypeError, ValueError):
            max_entries = 8
        out.append(DeclaredSource(id=sid, url=url, attestation=attestation, max_entries=max_entries))
    return out


def _parse_observed(content: str) -> tuple[list[ObservedSourceHealth], Optional[str]]:
    """Parse `_watch_signal.yaml` → (ObservedSourceHealth[], observed_at).

    The signal file is system-written by TrackWebSources with per-source
    blocks {id, source_ref, attestation, observed_at, status, entries[],
    error?}. Returns ([], None) when the file does not exist yet (watch
    never fired).
    """
    if not content.strip():
        return [], None
    try:
        parsed = _yaml.safe_load(_strip_tier_frontmatter(content)) or {}
    except _yaml.YAMLError:
        return [], None
    if not isinstance(parsed, dict):
        return [], None
    top_observed_at = parsed.get("observed_at")
    blocks = parsed.get("sources")
    if not isinstance(blocks, list):
        return [], (top_observed_at if isinstance(top_observed_at, str) else None)
    out: list[ObservedSourceHealth] = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        sid = str(b.get("id") or b.get("source_ref") or "unnamed")
        status = b.get("status") or "ok"
        entries = b.get("entries")
        entry_count = len(entries) if isinstance(entries, list) else 0
        out.append(
            ObservedSourceHealth(
                id=sid,
                status=str(status),
                observed_at=b.get("observed_at") if isinstance(b.get("observed_at"), str) else None,
                entry_count=entry_count,
                error=b.get("error") if isinstance(b.get("error"), str) else None,
            )
        )
    return out, (top_observed_at if isinstance(top_observed_at, str) else None)


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.get("", response_model=SourcesResponse)
async def get_sources(auth: UserClient) -> SourcesResponse:
    """Return the workspace's standing watches: declared sources + observed
    health, paired. Empty list when no active bundle declares a watch."""
    from services.bundle_reader import get_watches_for_workspace

    try:
        watches = get_watches_for_workspace(auth.user_id, auth.client)
    except Exception as exc:
        logger.warning("[SOURCES] get_watches failed for %s: %s", auth.user_id[:8], exc)
        watches = []

    views: list[WatchView] = []
    for w in watches:
        declaration = w.get("declaration") or ""
        if not declaration:
            continue
        signal = w.get("distills_to") or ""
        declared = _parse_declared(_read_workspace_file(auth.client, auth.user_id, declaration))
        observed: list[ObservedSourceHealth] = []
        observed_at: Optional[str] = None
        if signal:
            observed, observed_at = _parse_observed(
                _read_workspace_file(auth.client, auth.user_id, signal)
            )
        views.append(
            WatchView(
                watch_id=str(w.get("id") or "watch"),
                program_slug=w.get("_program_slug"),
                shape=w.get("shape"),
                recurrence=w.get("recurrence"),
                declaration_path=declaration,
                signal_path=signal or None,
                declared=declared,
                observed=observed,
                observed_at=observed_at,
            )
        )

    return SourcesResponse(watches=views)
