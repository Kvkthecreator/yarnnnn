"""
Recurrence Declarations — ADR-231 Phase 2 infrastructure.

YAML-based recurrence declarations replace TASK.md as the canonical descriptor
for recurring or goal-bounded work. One declaration = one nameplate + pulse +
contract per FOUNDATIONS Axiom 9. Files live at natural-home substrate
locations (per ADR-231 D2):

    /workspace/context/{domain}/_recurring.yaml   # domain accumulation
    /workspace/reports/{slug}/_spec.yaml          # recurring deliverables
    /workspace/operations/{slug}/_action.yaml     # external actions
    /workspace/_shared/back-office.yaml           # back-office cron index

This module provides:
  - `RecurrenceShape` enum (the four work shapes)
  - `RecurrenceDeclaration` dataclass (parsed YAML wrapped with provenance)
  - `parse_recurrence_yaml(content, path)` — single declaration parsing
  - `parse_back_office_index(content, path)` — multi-entry parsing for back-office
  - `walk_workspace_recurrences(client, user_id)` — filesystem scanner
  - `compute_next_run_at(decl, now)` — scheduler-facing timing helper
  - YAML schema constants + validation helpers

The dispatcher (`api/services/invocation_dispatcher.py`, forthcoming) consumes
RecurrenceDeclaration objects and routes by shape. The scheduler queries the
walker for due declarations.

ADR-231 §D3 ratifies format-by-shape:
  - `.yaml` for machine config (this module's domain)
  - `.md` for operator prose (e.g., adjacent `_intent.md` for narrative intent)
  - `.json` for structured machine state (manifests)
  - audit logs in `.md` (append-only)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Recurrence shapes
# ---------------------------------------------------------------------------


class RecurrenceShape(str, Enum):
    """The four work shapes per ADR-166 (preserved as operator vocabulary
    per ADR-231 D8) — but here serving as the dispatcher's routing key,
    not a classification enum on the `tasks` table.

    Implied by substrate location:
      - `deliverable`     ← /workspace/reports/{slug}/_spec.yaml
      - `accumulation`    ← /workspace/context/{domain}/_recurring.yaml
      - `action`          ← /workspace/operations/{slug}/_action.yaml
      - `maintenance`     ← /workspace/_shared/back-office.yaml
    """

    DELIVERABLE = "deliverable"
    ACCUMULATION = "accumulation"
    ACTION = "action"
    MAINTENANCE = "maintenance"


# ---------------------------------------------------------------------------
# Path conventions
# ---------------------------------------------------------------------------


_DOMAIN_RECURRING_PATTERN = re.compile(
    r"^/workspace/context/(?P<domain>[a-z0-9_-]+)/_recurring\.yaml$"
)
_REPORT_SPEC_PATTERN = re.compile(
    r"^/workspace/reports/(?P<slug>[a-z0-9_-]+)/_spec\.yaml$"
)
_OPERATION_ACTION_PATTERN = re.compile(
    r"^/workspace/operations/(?P<slug>[a-z0-9_-]+)/_action\.yaml$"
)
_BACK_OFFICE_PATH = "/workspace/_shared/back-office.yaml"


def shape_for_path(path: str) -> Optional[RecurrenceShape]:
    """Identify the recurrence shape from a workspace file path.

    Returns None if the path doesn't match any recurrence-declaration convention.
    """
    if path == _BACK_OFFICE_PATH:
        return RecurrenceShape.MAINTENANCE
    if _DOMAIN_RECURRING_PATTERN.match(path):
        return RecurrenceShape.ACCUMULATION
    if _REPORT_SPEC_PATTERN.match(path):
        return RecurrenceShape.DELIVERABLE
    if _OPERATION_ACTION_PATTERN.match(path):
        return RecurrenceShape.ACTION
    return None


# ---------------------------------------------------------------------------
# RecurrenceDeclaration
# ---------------------------------------------------------------------------


@dataclass
class RecurrenceDeclaration:
    """One parsed recurrence declaration with provenance.

    Shape determines the dispatcher route. `slug` is the operator-legible
    nameplate (Axiom 9). `schedule` is the cron expression that becomes the
    pulse. `paused` allows operator-level pause/resume without schema changes.

    Shape-specific fields live in `data` (the raw YAML content) — the
    dispatcher reads them per-shape. Common fields are surfaced as
    properties for convenience.
    """

    shape: RecurrenceShape
    slug: str  # operator-legible nameplate
    declaration_path: str  # absolute workspace path of the source YAML
    data: dict  # the parsed YAML body for this declaration

    # Provenance (set by walker)
    user_id: Optional[str] = None
    last_modified: Optional[datetime] = None

    # ---- common fields surfaced as properties ----

    @property
    def schedule(self) -> Optional[str]:
        """Cron expression or named cadence ('daily', 'weekly', etc.)."""
        return _coerce_str(self.data.get("schedule"))

    @property
    def paused(self) -> bool:
        return bool(self.data.get("paused", False))

    @property
    def paused_until(self) -> Optional[datetime]:
        v = self.data.get("paused_until")
        if not v:
            return None
        if isinstance(v, datetime):
            return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        if isinstance(v, str):
            try:
                # accept ISO-8601 with or without timezone
                d = datetime.fromisoformat(v.replace("Z", "+00:00"))
                return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
            except ValueError:
                logger.warning("[RECURRENCE] invalid paused_until value: %r", v)
                return None
        return None

    @property
    def objective(self) -> Optional[str]:
        return _coerce_str(self.data.get("objective"))

    @property
    def display_name(self) -> Optional[str]:
        return _coerce_str(self.data.get("display_name"))

    @property
    def agents(self) -> list[str]:
        """List of agent slugs (production roles or user-authored Agent slugs)."""
        v = self.data.get("agents")
        if isinstance(v, list):
            return [str(x) for x in v if x]
        v = self.data.get("agent")
        if isinstance(v, str):
            return [v]
        return []

    @property
    def context_reads(self) -> list[str]:
        v = self.data.get("context_reads") or self.data.get("context_read") or []
        return [str(x) for x in v if x] if isinstance(v, list) else []

    @property
    def context_writes(self) -> list[str]:
        v = self.data.get("context_writes") or self.data.get("context_write") or []
        return [str(x) for x in v if x] if isinstance(v, list) else []

    @property
    def required_capabilities(self) -> list[str]:
        v = self.data.get("required_capabilities") or []
        return [str(x) for x in v if x] if isinstance(v, list) else []

    @property
    def output_path(self) -> Optional[str]:
        """For DELIVERABLE shape — natural-home path with optional `{date}` placeholder."""
        return _coerce_str(self.data.get("output_path"))

    @property
    def executor(self) -> Optional[str]:
        """For MAINTENANCE shape — dotted Python path of the executor function."""
        return _coerce_str(self.data.get("executor"))

    @property
    def domain(self) -> Optional[str]:
        """For ACCUMULATION shape — the context domain slug. Derived from the path."""
        match = _DOMAIN_RECURRING_PATTERN.match(self.declaration_path)
        return match.group("domain") if match else None

    def is_due(self, now: datetime, last_run_at: Optional[datetime] = None) -> bool:
        """Cheap deterministic gate. Returns True if this declaration should
        fire at `now`. Honors paused / paused_until. Does NOT parse the cron
        expression — that's the scheduler's job; this is a coarse filter.

        For exact next-run computation, the scheduler uses `croniter` against
        `self.schedule`. This method is for invocation-side gating only.
        """
        if self.paused:
            return False
        until = self.paused_until
        if until and now < until:
            return False
        # Coarse: if no schedule, never auto-due
        if not self.schedule:
            return False
        return True

    @classmethod
    def from_yaml_block(
        cls,
        shape: RecurrenceShape,
        slug: str,
        declaration_path: str,
        data: dict,
        user_id: Optional[str] = None,
        last_modified: Optional[datetime] = None,
    ) -> "RecurrenceDeclaration":
        return cls(
            shape=shape,
            slug=slug,
            declaration_path=declaration_path,
            data=dict(data) if data else {},
            user_id=user_id,
            last_modified=last_modified,
        )


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_recurrence_yaml(
    content: str,
    declaration_path: str,
    user_id: Optional[str] = None,
    last_modified: Optional[datetime] = None,
) -> list[RecurrenceDeclaration]:
    """Parse a single recurrence YAML file into one or more declarations.

    Supports two file shapes:

    1. Single-declaration files (`_spec.yaml`, `_action.yaml`) — one
       top-level dict with shape-specific keys plus optional `recurring:`
       sub-block. Slug derived from the path.

    2. Multi-declaration files (`_recurring.yaml`, `back-office.yaml`) —
       a list of declarations under a top-level key (`recurrences:` for
       domain-recurring, `back_office_jobs:` for the back-office index).
       Each entry has its own slug.

    Returns an empty list if the file is malformed or unrecognized.
    """
    shape = shape_for_path(declaration_path)
    if shape is None:
        logger.warning(
            "[RECURRENCE] unrecognized declaration path: %s", declaration_path
        )
        return []

    try:
        parsed = yaml.safe_load(content) if content else None
    except yaml.YAMLError as e:
        logger.error("[RECURRENCE] YAML parse error in %s: %s", declaration_path, e)
        return []

    if not isinstance(parsed, dict):
        logger.warning(
            "[RECURRENCE] expected dict at top level of %s, got %s",
            declaration_path,
            type(parsed).__name__,
        )
        return []

    # Multi-declaration files
    if shape == RecurrenceShape.MAINTENANCE:
        return _parse_back_office_block(parsed, declaration_path, user_id, last_modified)
    if shape == RecurrenceShape.ACCUMULATION:
        return _parse_domain_recurring_block(
            parsed, declaration_path, user_id, last_modified
        )

    # Single-declaration files (DELIVERABLE, ACTION)
    return _parse_single_declaration(
        parsed, shape, declaration_path, user_id, last_modified
    )


def _parse_single_declaration(
    parsed: dict,
    shape: RecurrenceShape,
    declaration_path: str,
    user_id: Optional[str],
    last_modified: Optional[datetime],
) -> list[RecurrenceDeclaration]:
    # DELIVERABLE: top-level may be {"report": {...}} or flat
    # ACTION: top-level may be {"action": {...}} or flat
    wrapper_keys = {
        RecurrenceShape.DELIVERABLE: "report",
        RecurrenceShape.ACTION: "action",
    }
    wrapper_key = wrapper_keys.get(shape)
    body = parsed.get(wrapper_key) if wrapper_key and wrapper_key in parsed else parsed
    if not isinstance(body, dict):
        return []

    # Slug priority: explicit `slug:` field, then derive from path
    slug = body.get("slug")
    if not slug:
        if shape == RecurrenceShape.DELIVERABLE:
            m = _REPORT_SPEC_PATTERN.match(declaration_path)
            slug = m.group("slug") if m else None
        elif shape == RecurrenceShape.ACTION:
            m = _OPERATION_ACTION_PATTERN.match(declaration_path)
            slug = m.group("slug") if m else None
    if not slug:
        logger.warning("[RECURRENCE] could not resolve slug for %s", declaration_path)
        return []

    # Flatten nested `recurring:` block onto the body so common properties
    # (schedule, paused) can be accessed uniformly via RecurrenceDeclaration props.
    flat = dict(body)
    nested = flat.pop("recurring", None)
    if isinstance(nested, dict):
        for k, v in nested.items():
            flat.setdefault(k, v)

    return [
        RecurrenceDeclaration.from_yaml_block(
            shape=shape,
            slug=str(slug),
            declaration_path=declaration_path,
            data=flat,
            user_id=user_id,
            last_modified=last_modified,
        )
    ]


def _parse_domain_recurring_block(
    parsed: dict,
    declaration_path: str,
    user_id: Optional[str],
    last_modified: Optional[datetime],
) -> list[RecurrenceDeclaration]:
    entries = parsed.get("recurrences")
    if not isinstance(entries, list):
        logger.warning(
            "[RECURRENCE] expected list under 'recurrences:' in %s",
            declaration_path,
        )
        return []
    out: list[RecurrenceDeclaration] = []
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        slug = raw.get("slug")
        if not slug:
            logger.warning(
                "[RECURRENCE] missing slug in domain entry under %s",
                declaration_path,
            )
            continue
        out.append(
            RecurrenceDeclaration.from_yaml_block(
                shape=RecurrenceShape.ACCUMULATION,
                slug=str(slug),
                declaration_path=declaration_path,
                data=dict(raw),
                user_id=user_id,
                last_modified=last_modified,
            )
        )
    return out


def _parse_back_office_block(
    parsed: dict,
    declaration_path: str,
    user_id: Optional[str],
    last_modified: Optional[datetime],
) -> list[RecurrenceDeclaration]:
    entries = parsed.get("back_office_jobs")
    if not isinstance(entries, list):
        logger.warning(
            "[RECURRENCE] expected list under 'back_office_jobs:' in %s",
            declaration_path,
        )
        return []
    out: list[RecurrenceDeclaration] = []
    for idx, raw in enumerate(entries):
        if not isinstance(raw, dict):
            continue
        executor = raw.get("executor")
        if not executor:
            logger.warning(
                "[RECURRENCE] back-office entry #%d missing executor in %s",
                idx,
                declaration_path,
            )
            continue
        # Slug priority: explicit slug, else derive from executor dotted-path
        slug = raw.get("slug") or _slug_from_executor(str(executor))
        out.append(
            RecurrenceDeclaration.from_yaml_block(
                shape=RecurrenceShape.MAINTENANCE,
                slug=slug,
                declaration_path=declaration_path,
                data=dict(raw),
                user_id=user_id,
                last_modified=last_modified,
            )
        )
    return out


def _slug_from_executor(executor: str) -> str:
    """Derive a slug from a dotted executor path.

    `services.back_office.narrative_digest` → `back-office-narrative-digest`
    """
    last = executor.rsplit(".", 1)[-1]
    last = last.replace("_", "-")
    if "back-office" not in last:
        last = f"back-office-{last}"
    return last


# ---------------------------------------------------------------------------
# Workspace walker
# ---------------------------------------------------------------------------


_RECURRENCE_FILE_NAMES = {
    "_recurring.yaml",
    "_spec.yaml",
    "_action.yaml",
    "back-office.yaml",
}


def walk_workspace_recurrences(
    client, user_id: str
) -> list[RecurrenceDeclaration]:
    """Scan the workspace_files table for recurrence declarations and parse them.

    Performs ONE Postgres query against `workspace_files` filtering on path
    suffix (LIKE patterns). Each matching row is parsed; any single bad file
    yields a logged warning but doesn't abort the scan.

    Returns a flat list of declarations, ordered by declaration_path then slug.
    """
    if client is None:
        return []

    try:
        # Pull all candidate files in one query. The path patterns map to the
        # four shapes defined in shape_for_path; we filter precisely after.
        result = (
            client.table("workspace_files")
            .select("path,content,updated_at")
            .eq("user_id", user_id)
            .or_(
                "path.like./workspace/context/%/_recurring.yaml,"
                "path.like./workspace/reports/%/_spec.yaml,"
                "path.like./workspace/operations/%/_action.yaml,"
                "path.eq./workspace/_shared/back-office.yaml"
            )
            .execute()
        )
    except Exception as e:
        logger.error("[RECURRENCE] workspace scan failed: %s", e)
        return []

    rows = result.data or []
    out: list[RecurrenceDeclaration] = []
    for row in rows:
        path = row.get("path")
        content = row.get("content") or ""
        updated_at_raw = row.get("updated_at")
        last_modified = None
        if isinstance(updated_at_raw, str):
            try:
                last_modified = datetime.fromisoformat(
                    updated_at_raw.replace("Z", "+00:00")
                )
            except ValueError:
                pass
        if not path:
            continue
        decls = parse_recurrence_yaml(
            content=content,
            declaration_path=path,
            user_id=user_id,
            last_modified=last_modified,
        )
        out.extend(decls)

    out.sort(key=lambda d: (d.declaration_path, d.slug))
    return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coerce_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, str):
        return v.strip() or None
    return str(v).strip() or None


def derive_declaration_path(shape: RecurrenceShape, slug: str, *, domain: Optional[str] = None) -> str:
    """Compute the canonical declaration path for a (shape, slug) pair.

    For ACCUMULATION, requires a `domain` argument (the path is per-domain
    and shared by multiple recurrence entries).
    """
    if shape == RecurrenceShape.MAINTENANCE:
        return _BACK_OFFICE_PATH
    if shape == RecurrenceShape.ACCUMULATION:
        if not domain:
            raise ValueError("domain required for ACCUMULATION declaration path")
        return f"/workspace/context/{domain}/_recurring.yaml"
    if shape == RecurrenceShape.DELIVERABLE:
        return f"/workspace/reports/{slug}/_spec.yaml"
    if shape == RecurrenceShape.ACTION:
        return f"/workspace/operations/{slug}/_action.yaml"
    raise ValueError(f"unknown shape: {shape}")


def serialize_declaration_yaml(decl: RecurrenceDeclaration) -> str:
    """Serialize a single declaration back to YAML.

    For multi-declaration files (ACCUMULATION, MAINTENANCE), this is the
    UNDERLYING entry shape — the caller is responsible for wrapping it in
    `recurrences:` / `back_office_jobs:` when writing.

    For single-declaration files (DELIVERABLE, ACTION), this returns a
    full file body wrapped in `report:` / `action:` accordingly.
    """
    body = dict(decl.data)
    if decl.shape == RecurrenceShape.DELIVERABLE:
        return yaml.safe_dump({"report": body}, sort_keys=False, default_flow_style=False)
    if decl.shape == RecurrenceShape.ACTION:
        return yaml.safe_dump({"action": body}, sort_keys=False, default_flow_style=False)
    # Multi-declaration entries: return entry body only
    return yaml.safe_dump(body, sort_keys=False, default_flow_style=False)


__all__ = [
    "RecurrenceShape",
    "RecurrenceDeclaration",
    "shape_for_path",
    "parse_recurrence_yaml",
    "walk_workspace_recurrences",
    "derive_declaration_path",
    "serialize_declaration_yaml",
]
