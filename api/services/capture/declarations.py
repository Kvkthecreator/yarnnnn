"""
Capture declarations — the _captures.yaml substrate + the health signal (ADR-393).

A CAPTURE is deterministic, upstream, intent-free perception: a platform pull,
a ground-truth state mirror, a standing web/repo watch, a substrate mirror. It
runs on cadence, writes substrate, and wakes no one (ADR-393 D1). This is the
substrate that replaced the `mode: mechanical` recurrence carve-out — the
"theatre" bypass (`wake.py::_dispatch_mechanical`) is deleted, and the work it
did lives here.

## Schema (mirrors _recurrences.yaml for operator legibility)

    captures:
      - slug: track-positions
        schedule: "@every 1min during regular_hours"   # cron | @-semantic | list
        primitive: |
          @primitive: SyncPlatformState(
            tool="platform_trading_get_positions",
            write_to="operation/portfolio/positions/{symbol}.yaml",
            iterate_field="positions", item_key="symbol", diff_aware=true
          )
        display_name: "Position State Mirror"     # → options (legibility only)

Load-bearing fields: ``slug`` + ``schedule`` + ``primitive`` (the
``@primitive: <Name>(<args>)`` directive the lane parses + runs). Everything
else is ``options`` (display_name, description, fire_on_activation, ...).

The `primitive` field is the capture analogue of a recurrence's `prompt`: for a
recurrence the prompt reaches the Reviewer; for a capture the directive names a
deterministic primitive the lane executes. There is NO `mode` field — being in
_captures.yaml IS the class (the pipeline a unit runs on is its class, ADR-393
D2). A capture never wakes the Reviewer.

`schedule` accepts the same grammar as a recurrence (plain UTC cron, ADR-268
`@`-semantic market-anchored, or a list of either) so the trader's
market-anchored mirrors move byte-for-byte. `fire_on_activation: true` (in
options) is honored by the shared `compute_next_run_at` (ADR-270).

## The health signal (_capture_signal.yaml)

Per ADR-389, the only judgment a peripheral invites is about its HEALTH: is the
feed live? current? A capture that fails is a health signal, not a judgment
miss. The lane writes a per-workspace `_capture_signal.yaml` — one thin block
per declaration: `{slug, last_run, status, last_error, items, target}`. This is
DELIBERATELY thin (liveness/freshness only) — NOT a content distillation. A
capture primitive that ALSO distills (e.g. TrackWebSources' `_watch_signal.yaml`
with per-source entries) writes its own richer signal; this file is the
uniform health surface the steward's peripheral-field fact reads (ADR-393 D3,
`freddie_envelope.py::_peripheral_field_fact`) and the data source for the
ADR-392 Phase B selection surface.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Union

import yaml

from services.conventions import CAPTURES_PATH

logger = logging.getLogger(__name__)


# Same schedule grammar as a recurrence (ADR-268): plain cron | @-semantic |
# list of either. None is NOT meaningful for a capture (a capture with no
# cadence never runs — declare it or delete it), but we tolerate it in the
# parser and let the scheduler skip it (next_run_at stays None).
Schedule = Optional[Union[str, list[str]]]


# The health signal lives one per workspace, a sibling of the captures file.
CAPTURE_SIGNAL_PATH = "/workspace/_capture_signal.yaml"


def captures_path() -> str:
    """The canonical captures declaration path (workspace-absolute)."""
    return CAPTURES_PATH


def capture_signal_path() -> str:
    """The canonical capture health-signal path (workspace-absolute)."""
    return CAPTURE_SIGNAL_PATH


@dataclass
class CaptureDeclaration:
    """One parsed _captures.yaml entry (ADR-393).

    Load-bearing: ``slug`` + ``schedule`` + ``primitive`` (the
    ``@primitive: <Name>(<args>)`` directive). ``options`` carries
    operator-legibility metadata (display_name, description, fire_on_activation)
    exactly like a Recurrence's options — same shape so the shared scheduling
    helpers (``compute_next_run_at``) work unchanged.
    """

    slug: str
    schedule: Schedule = None
    primitive: str = ""  # the @primitive: <Name>(<args>) directive
    paused: bool = False
    paused_until: Optional[datetime] = None
    options: dict = field(default_factory=dict)

    # Provenance (set by walker)
    user_id: Optional[str] = None
    last_modified: Optional[datetime] = None


def parse_captures_yaml(
    content: str,
    user_id: Optional[str] = None,
    last_modified: Optional[datetime] = None,
) -> list[CaptureDeclaration]:
    """Parse the canonical ``/workspace/_captures.yaml`` body.

    Accepts a top-level list OR a dict with a ``captures:`` (or ``entries:``)
    key holding a list — both shapes for operator legibility, mirroring the
    recurrence parser. Returns an empty list on parse error/empty content. One
    malformed entry is skipped with a warning; it never aborts the whole parse.
    """
    if not content or not content.strip():
        return []

    try:
        parsed = yaml.safe_load(content)
    except yaml.YAMLError as e:
        logger.error("[CAPTURE] YAML parse error: %s", e)
        return []

    if parsed is None:
        return []

    if isinstance(parsed, dict):
        entries = parsed.get("captures") or parsed.get("entries")
        if entries is None:
            logger.warning(
                "[CAPTURE] expected list at top-level or under 'captures:' key"
            )
            return []
    elif isinstance(parsed, list):
        entries = parsed
    else:
        logger.warning(
            "[CAPTURE] expected list or dict at top level, got %s",
            type(parsed).__name__,
        )
        return []

    if not isinstance(entries, list):
        logger.warning("[CAPTURE] entries must be a list, got %s", type(entries).__name__)
        return []

    out: list[CaptureDeclaration] = []
    for idx, raw in enumerate(entries):
        if not isinstance(raw, dict):
            logger.warning("[CAPTURE] entry #%d is not a dict, skipping", idx)
            continue

        slug = raw.get("slug")
        if not slug:
            logger.warning("[CAPTURE] entry #%d missing slug, skipping", idx)
            continue

        # The directive is the load-bearing field. Accept `primitive:` (the
        # canonical key) — a capture with no directive can never run.
        directive = raw.get("primitive")
        if not directive or not str(directive).strip():
            logger.warning(
                "[CAPTURE] entry '%s' missing 'primitive:' directive, skipping", slug
            )
            continue

        # schedule: null | str | list[str] — same normalization as recurrence.
        schedule_raw = raw.get("schedule")
        schedule: Schedule
        if schedule_raw is None:
            schedule = None
        elif isinstance(schedule_raw, list):
            cleaned = [str(s).strip() for s in schedule_raw if s and str(s).strip()]
            schedule = cleaned if cleaned else None
            if schedule and len(cleaned) == 1:
                schedule = cleaned[0]
        elif str(schedule_raw).strip():
            schedule = str(schedule_raw).strip()
        else:
            schedule = None

        paused_until = _coerce_datetime(raw.get("paused_until"))

        # options = everything else (display_name, description,
        # fire_on_activation, ...). Same convention as Recurrence.options.
        options = {
            k: v
            for k, v in raw.items()
            if k not in {"slug", "schedule", "primitive", "paused", "paused_until"}
        }

        out.append(
            CaptureDeclaration(
                slug=str(slug),
                schedule=schedule,
                primitive=str(directive).strip(),
                paused=bool(raw.get("paused", False)),
                paused_until=paused_until,
                options=options,
                user_id=user_id,
                last_modified=last_modified,
            )
        )

    return out


def _coerce_datetime(v: Any) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str):
        try:
            d = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning("[CAPTURE] invalid datetime value: %r", v)
            return None
    return None


# ---------------------------------------------------------------------------
# Workspace walker
# ---------------------------------------------------------------------------


def walk_workspace_captures(client, user_id: str) -> list[CaptureDeclaration]:
    """Read ``/workspace/_captures.yaml`` for a user and return parsed entries.

    One canonical file per workspace (mirrors the recurrence walker). Returns
    an empty list if the file doesn't exist or is empty.
    """
    if client is None:
        return []

    try:
        result = (
            client.table("workspace_files")
            .select("content,updated_at")
            .eq("user_id", user_id)
            .eq("path", CAPTURES_PATH)
            .limit(1)
            .execute()
        )
    except Exception as e:
        logger.error("[CAPTURE] read failed for user=%s: %s", user_id[:8], e)
        return []

    rows = result.data or []
    if not rows:
        return []

    content = rows[0].get("content") or ""
    last_modified = _coerce_datetime(rows[0].get("updated_at"))
    return parse_captures_yaml(content, user_id=user_id, last_modified=last_modified)


# ---------------------------------------------------------------------------
# Health signal (_capture_signal.yaml) — the peripheral-field freshness surface
# ---------------------------------------------------------------------------


async def read_capture_signal(client, user_id: str) -> dict:
    """Read the per-workspace capture health signal. Returns the parsed dict
    ({'captures': {slug: block}}) or an empty dict. Never raises."""
    from services.workspace import UserMemory

    um = UserMemory(client, user_id)
    rel = CAPTURE_SIGNAL_PATH.lstrip("/").removeprefix("workspace/")
    try:
        body = await um.read(rel)
    except Exception:
        body = None
    if not body:
        return {}
    try:
        parsed = yaml.safe_load(body) or {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("[CAPTURE_SIGNAL] parse failed user=%s: %s", user_id[:8], exc)
        return {}
    return parsed if isinstance(parsed, dict) else {}


async def write_capture_signal(
    client,
    user_id: str,
    *,
    slug: str,
    status: str,
    observed_at: str,
    items: Optional[int] = None,
    target: Optional[str] = None,
    last_error: Optional[str] = None,
) -> bool:
    """Upsert one declaration's health block into ``_capture_signal.yaml``.

    Read-merge-write: the file carries one block per capture slug so the steward
    reads the whole peripheral field in one file. THIN by design — liveness and
    freshness only (``status`` ∈ ok|error|skipped, ``observed_at``, item count,
    the write target, and a last-error string) — NOT a content distillation. A
    capture primitive that distills content writes its own richer signal (e.g.
    TrackWebSources' ``_watch_signal.yaml``); this uniform file is what the
    peripheral-field fact reads (ADR-393 D3) + the ADR-392 Phase B data source.

    Diff-aware via the substrate write path (a byte-identical re-write is
    skipped). Best-effort: a signal-write failure never fails the capture (the
    capture's substrate write already succeeded). ``observed_at`` is
    caller-stamped (Axiom 1 / resume safety — the lane never reads the clock).
    """
    from services.workspace import UserMemory

    um = UserMemory(client, user_id)
    rel = CAPTURE_SIGNAL_PATH.lstrip("/").removeprefix("workspace/")

    # Read-merge the existing signal so per-slug blocks accumulate.
    existing = await read_capture_signal(client, user_id)
    captures = existing.get("captures")
    if not isinstance(captures, dict):
        captures = {}

    block: dict[str, Any] = {
        "status": status,
        "observed_at": observed_at,
    }
    if items is not None:
        block["items"] = items
    if target:
        block["target"] = target
    if last_error:
        block["last_error"] = last_error
    captures[slug] = block

    payload = {"captures": captures}
    content = yaml.safe_dump(
        payload, sort_keys=True, default_flow_style=False, allow_unicode=True
    )
    try:
        await um.write(
            rel,
            content,
            summary=f"capture-signal:{slug}",
            authored_by="system:capture-lane",
            message=f"health signal {slug} → {status}",
        )
        return True
    except Exception as exc:  # noqa: BLE001 — signal write must never fail the capture
        logger.warning(
            "[CAPTURE_SIGNAL] write failed user=%s slug=%s: %s",
            user_id[:8], slug, exc,
        )
        return False


__all__ = [
    "CaptureDeclaration",
    "Schedule",
    "CAPTURE_SIGNAL_PATH",
    "captures_path",
    "capture_signal_path",
    "parse_captures_yaml",
    "walk_workspace_captures",
    "read_capture_signal",
    "write_capture_signal",
]
