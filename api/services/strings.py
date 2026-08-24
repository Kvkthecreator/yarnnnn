"""Strings — the maintained file, kept by Keeper (ADR-569).

The second member-facing manifestation of the ADR-564 frame (radar shipped
first as its specialization — ADR-569 D1 re-reads `report.md` as a maintained
file the APP designates). A STRING is the member's designation of ONE file in
a folder as kept current: a declared contract (what it must stay true to),
declared sources (where currency comes from), a cadence, and a standing
writer that revises its head — while the member corrects it like any file,
and every correction compounds (single-head-many-authors, ADR-384 D4).

THE LAW (ADR-569 D1): un-designated files are NEVER a standing writer's
target. Designation is the member's explicit act; authored artifacts stay
current through reference (data-ref), never standing writes.

One folder holds ONE string (v1 — the radar single-declaration posture),
declared by two files split on the ADR-564 D2 bright line:

    _string.yaml    — pure machine config (ADR-254 underscore-yaml):
                        target: metrics.csv      # the designated leaf,
                                                 # folder-relative, ONE segment
                        schedule: "0 13 * * *"   # UTC cron | @-semantic | list
                        paused: false
                        sources:                 # HTTP pull (D4), or a
                          - id: main             # connector slice (ADR-582
                            url: https://…       # D6): {connector, selector}
                                                 # reading LANDED snapshots
                        shape:                   # structured formats only —
                          columns: [date, mrr]   # csv: required column set
                          # keys: [mrr, churn]   # json: required top-level keys
    CONTRACT.md     — what this file means and must stay true to (prose,
                      operator/lane-authored, NEVER machine-parsed)

v1 designation scope (D1): ``md · csv · json · txt`` — formats whose
unattended revision does not fight an authoring surface's editing model.
Designating an authoring-app artifact (Studio html, Docs) is NAMED-DEFERRED,
never silently allowed: a standing writer revising inside Studio's medium
collides with its document model; if demand proves real, that collision gets
its own discourse. The refusal here is the ``unsupported_format`` problem.

One run = fetch → parse → map → validate → write, at the depth the format
demands (D4):

    fetch    — HTTP pull of the declared sources (httpx, honest UA); each raw
               body retained as an immutable observation under inbound/web/
               (the ADR-376/DP32 raw lane — the evidence the write CITES)
    map      — csv: parse + project to the declared columns; json: parse +
               require the declared keys; txt: passthrough; md: ONE bounded
               judgment turn governed by CONTRACT.md (exactly radar's
               criterion posture — the contract IS the criterion), returning
               the full revised document or the exact token NO_CHANGE
    validate — the machine-checkable half of the contract (``shape``). A
               violating write is REFUSED into a LOUD repair state (D3 — the
               ADR-567 D6 shape): no silent bad numbers, the desk says so,
               the lane repairs. Metered ``status='failed',
               error_reason='shape_violation'`` — the desk reads the ledger.
    write    — CONFINED to the declared leaf ONLY (stricter than radar's
               subtree rule — the ``_assert_hub_write`` shape, D3), via
               write_revision(revision_kind='derivation',
               derived_from=[raws]). History is the revision chain, never
               the namespace (ADR-209). An unchanged pull is an honest
               no-op: skipped/no_change, no manufactured revision.
    meter    — two execution_events rows per run:
               ``string-sweep:{topic}``  (mechanical fetch)
               ``string-write:{topic}``  (the write step — mechanical for
               structured formats, judgment for prose)

Scheduling rides the thin ``tasks`` index with ``kind='string'`` (the ADR-393
precedent, disjoint from 'radar'/'judgment'/'capture'): the tick discovers
declarations, materializes the slice (``preserve_due_commitment`` applies by
construction — b8ac1c7), claims via CAS, runs, records.

The topic is the folder path relative to ``/workspace/`` (any meaning-folder
— the designated file lives where it lives; the desk's identity param and the
Files association both carry it).

Attribution: raws as ``system:strings`` observations; the leaf write as
``system:strings`` with the face being Keeper (ADR-460 D2 — the member reads
"Keeper"; authored_by stays the mechanism). This module deliberately carries
no module-level ``services.*`` imports (the radar cycle-free property);
Keeper's registration lives in ``services/apps/__init__.py`` with the other
app residencies (ADR-562).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Union

import yaml as _yaml

logger = logging.getLogger(__name__)

STRING_KIND = "string"

#: String declarations live at {folder}/_string.yaml, any meaning-folder under
#: /workspace/ — the designated file's own folder (ADR-569 D2).
_WORKSPACE_PREFIX = "/workspace/"
STRING_DECLARATION_LEAF = "_string.yaml"
CONTRACT_LEAF = "CONTRACT.md"

#: The v1 designation scope (ADR-569 D1) — formats whose unattended revision
#: does not fight an authoring surface. Extending this set is a canon change
#: (the named-deferred authoring-artifact collision), never a convenience.
SUPPORTED_FORMATS = ("md", "csv", "json", "txt")

#: Structured formats map ONE endpoint to the leaf; prose folds several.
_MAX_SOURCES_PROSE = 12
_FETCH_TIMEOUT_S = 15.0
_MAX_FETCH_CHARS = 500_000
_USER_AGENT = "yarnnn-strings/1.0 (+https://yarnnn.com)"

#: One bounded judgment turn for a prose string (the radar report ceiling).
_STRING_MAX_TOKENS = 4096
_DERIVE_TIMEOUT_S = 120.0

#: The empty-run sentinel the posture contracts (radar's, verbatim).
NO_CHANGE_SENTINEL = "NO_CHANGE"

Schedule = Optional[Union[str, list[str]]]


# ---------------------------------------------------------------------------
# Declaration — parse + walk
# ---------------------------------------------------------------------------


@dataclass
class StringDecl:
    """One parsed string declaration. Structurally compatible with
    ``services.scheduling.compute_next_run_at`` (slug/schedule/paused/
    paused_until/options — the RadarHub precedent)."""

    topic: str  # folder path relative to /workspace/
    slug: str  # "string:{topic}" — disjoint from radar/recurrence/capture slugs
    target: str = ""  # the designated leaf, folder-relative (one segment)
    schedule: Schedule = None
    paused: bool = False
    paused_until: Optional[datetime] = None
    sources: list[dict] = field(default_factory=list)
    shape: dict = field(default_factory=dict)
    options: dict = field(default_factory=dict)
    declaration_path: str = ""
    user_id: Optional[str] = None
    #: A declaration that parses but cannot run — the LOUD half of D3. None
    #: when healthy. Values: missing_target | invalid_target |
    #: unsupported_format | sources_invalid.
    problem: Optional[str] = None

    @property
    def root(self) -> str:
        return f"{_WORKSPACE_PREFIX}{self.topic}"

    @property
    def target_path(self) -> str:
        return f"{self.root}/{self.target}"

    @property
    def contract_path(self) -> str:
        return f"{self.root}/{CONTRACT_LEAF}"

    @property
    def format(self) -> Optional[str]:
        ext = self.target.rsplit(".", 1)[-1].lower() if "." in self.target else ""
        return ext if ext in SUPPORTED_FORMATS else None


def topic_from_declaration_path(path: str) -> Optional[str]:
    """``/workspace/{folder...}/_string.yaml`` → the folder path relative to
    ``/workspace/`` (the string's topic identifier). Pure. None for paths
    outside the convention (including a declaration at the workspace root —
    a string lives in a meaning-folder, not the root)."""
    p = (path or "").strip()
    if not p.startswith(_WORKSPACE_PREFIX) or not p.endswith(f"/{STRING_DECLARATION_LEAF}"):
        return None
    middle = p[len(_WORKSPACE_PREFIX):-(len(STRING_DECLARATION_LEAF) + 1)]
    parts = [s for s in middle.split("/") if s]
    return "/".join(parts) if parts else None


def _classify_target(target: str) -> Optional[str]:
    """The designation boundary, machine-checked. None = healthy; else the
    problem token (ADR-569 D1: designation, not file-type, is the boundary —
    but the v1 SCOPE is format-bounded, and the refusal is loud)."""
    if not target:
        return "missing_target"
    if "/" in target or target.startswith("_") or target in (CONTRACT_LEAF,):
        # One segment, in the string's own folder; never the machinery files.
        return "invalid_target"
    ext = target.rsplit(".", 1)[-1].lower() if "." in target else ""
    if ext not in SUPPORTED_FORMATS:
        return "unsupported_format"
    return None


def _is_http_source(s: dict) -> bool:
    return str(s.get("url", "")).startswith(("http://", "https://"))


def _is_connector_source(s: dict) -> bool:
    """A connector source (ADR-582 D6): {connector: slack, selector: C123} —
    the app consumes LANDED snapshots at the connection's destination;
    never a platform API, never a credential."""
    return bool(str(s.get("connector", "")).strip()) and bool(
        str(s.get("selector", "")).strip()
    )


def _classify_sources(sources: list[dict], fmt: Optional[str]) -> Optional[str]:
    """Source rules (D4, amended by ADR-582 D6): HTTP pull OR a connector
    slice; structured formats map exactly ONE source to the leaf; prose folds
    up to the radar cap."""
    clean = [
        s for s in sources
        if isinstance(s, dict) and s.get("id")
        and (_is_http_source(s) or _is_connector_source(s))
    ]
    if len(clean) != len(sources) or not clean:
        return "sources_invalid"
    if fmt in ("csv", "json", "txt") and len(clean) != 1:
        return "sources_invalid"
    if fmt == "md" and len(clean) > _MAX_SOURCES_PROSE:
        return "sources_invalid"
    return None


def parse_string_yaml(
    content: str, *, topic: str, declaration_path: str, user_id: Optional[str] = None
) -> Optional[StringDecl]:
    """Parse one ``_string.yaml`` body. None on unparseable (the caller's 422
    repair state); a PARSEABLE declaration that cannot run comes back with
    ``problem`` set — visible, never silently dark (D3)."""
    if not content or not content.strip():
        return None
    try:
        parsed = _yaml.safe_load(_strip_tier_frontmatter(content))
    except _yaml.YAMLError as e:
        logger.warning("[STRINGS] %s unparseable: %s", declaration_path, e)
        return None
    if not isinstance(parsed, dict):
        return None

    schedule_raw = parsed.get("schedule")
    schedule: Schedule
    if schedule_raw is None:
        schedule = None
    elif isinstance(schedule_raw, list):
        cleaned = [str(s).strip() for s in schedule_raw if s and str(s).strip()]
        schedule = (cleaned[0] if len(cleaned) == 1 else cleaned) if cleaned else None
    elif str(schedule_raw).strip():
        schedule = str(schedule_raw).strip()
    else:
        schedule = None

    target = str(parsed.get("target") or "").strip()
    sources_raw = parsed.get("sources")
    sources = [s for s in sources_raw if isinstance(s, dict)] if isinstance(sources_raw, list) else []
    shape_raw = parsed.get("shape")
    shape = shape_raw if isinstance(shape_raw, dict) else {}

    options = {
        k: v for k, v in parsed.items()
        if k not in {"target", "schedule", "paused", "paused_until", "sources", "shape"}
    }

    decl = StringDecl(
        topic=topic,
        slug=f"string:{topic}",
        target=target,
        schedule=schedule,
        paused=bool(parsed.get("paused", False)),
        paused_until=_coerce_datetime(parsed.get("paused_until")),
        sources=sources,
        shape=shape,
        options=options,
        declaration_path=declaration_path,
        user_id=user_id,
    )
    decl.problem = _classify_target(target) or _classify_sources(sources, decl.format)
    return decl


def _strip_tier_frontmatter(content: str) -> str:
    """Strip ADR-226 tier frontmatter if present (the TrackWebSources rule)."""
    import re
    m = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    return content[m.end():] if m else content


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
            return None
    return None


def discover_strings(client, *, workspace_id: Optional[str] = None) -> dict[str, list[StringDecl]]:
    """All string declarations, grouped by the OWNER user_id of their
    workspace — the discover_radar_hubs shape verbatim (ADR-501 keying: the
    grouping key is the workspace's owner, resolved through the service
    client, never the file's author)."""
    try:
        q = (
            client.table("workspace_files")
            .select("user_id, workspace_id, path, content")
            .like("path", f"{_WORKSPACE_PREFIX}%/{STRING_DECLARATION_LEAF}")
        )
        if workspace_id:
            q = q.eq("workspace_id", workspace_id)
        rows = q.execute().data or []
    except Exception as e:
        logger.warning("[STRINGS] discovery scan failed: %s", e)
        return {}

    from services.workspace_context import acting_workspace_owner  # noqa: F401 (parity: the owner resolver below)

    owner_of: dict[str, str] = {}

    def _owner(row: dict) -> Optional[str]:
        ws = row.get("workspace_id")
        if not ws:
            return row.get("user_id")
        if ws not in owner_of:
            try:
                # SERVICE client, deliberately — the discover_radar_hubs
                # rationale holds unchanged: `workspaces` RLS is owner-only,
                # so a member's client cannot resolve its granted workspace's
                # owner; the authorization already happened on the scan.
                from services.supabase import get_service_client

                res = (
                    get_service_client()
                    .table("workspaces").select("owner_id").eq("id", ws).limit(1).execute()
                ).data or []
                owner_of[ws] = (res[0].get("owner_id") if res else None) or row.get("user_id")
            except Exception:  # noqa: BLE001 — fall back to the author
                owner_of[ws] = row.get("user_id")
        return owner_of[ws]

    by_user: dict[str, list[StringDecl]] = {}
    for row in rows:
        path = row.get("path") or ""
        topic = topic_from_declaration_path(path)
        if topic is None:
            logger.warning("[STRINGS] %s is not a string declaration path; skipping", path)
            continue
        key = _owner(row)
        if not key:
            continue
        decl = parse_string_yaml(
            row.get("content") or "",
            topic=topic,
            declaration_path=path,
            user_id=key,
        )
        if decl is None:
            continue
        by_user.setdefault(key, []).append(decl)
    return by_user


# ---------------------------------------------------------------------------
# The confinement law (ADR-569 D3) — asserted at the write site
# ---------------------------------------------------------------------------


def _assert_string_write(decl: StringDecl, path: str) -> None:
    """The standing writer revises ONLY the designated leaf — stricter than
    radar's subtree confinement, because designation is per-FILE (D1). A
    capability constraint asserted at the write site; raises rather than
    writes — a confined actor aiming anywhere else is a bug, not a judgment
    call."""
    if path != decl.target_path:
        raise ValueError(
            f"string write-confinement: {path!r} is not the designated leaf "
            f"{decl.target_path!r} (un-designated files are never a standing "
            "writer's target — ADR-569 D1)"
        )


# ---------------------------------------------------------------------------
# Scheduling — the kind='string' slice of the tasks index (ADR-393 precedent)
# ---------------------------------------------------------------------------


async def materialize_string_index(
    client, user_id: str, decls: list[StringDecl], *, now: Optional[datetime] = None
) -> int:
    """Sync the tasks index (kind='string' rows) against this user's strings.
    Idempotent; touches only its own kind. A declaration with a ``problem``
    gets NO row — it cannot run, and scheduling it would turn the loud repair
    state into a silent failure loop. Returns rows touched."""
    from services.scheduling import (
        compute_next_run_at, preserve_due_commitment, _parse_iso,
    )
    from services.schedule_utils import get_workspace_timezone

    if now is None:
        now = datetime.now(timezone.utc)
    by_slug = {d.slug: d for d in decls if d.problem is None}

    try:
        existing = (
            client.table("tasks")
            .select("id, slug, last_run_at, next_run_at, kind")
            .eq("user_id", user_id)
            .eq("kind", STRING_KIND)
            .execute()
        )
        existing_by_slug = {r["slug"]: r for r in (existing.data or [])}
    except Exception as e:
        logger.warning("[STRINGS_SCHED] index read failed for %s: %s", user_id[:8], e)
        return 0

    user_tz = get_workspace_timezone(client, user_id)
    touched = 0

    for slug, decl in by_slug.items():
        existing_row = existing_by_slug.get(slug)
        last_run_at = _parse_iso(existing_row.get("last_run_at") if existing_row else None)
        try:
            next_run = compute_next_run_at(
                decl, last_run_at=last_run_at, now=now, user_timezone=user_tz,
            )
        except ValueError as e:
            logger.error("[STRINGS_SCHED] %s/%s schedule resolution failed: %s",
                         user_id[:8], slug, e)
            next_run = None

        # A due-but-unfired next_run_at is a COMMITMENT (b8ac1c7): this
        # materializer runs at the top of the drain tick, and the due scan
        # below must still find the stored time — without this, a never-run
        # string created conversationally could never fire.
        next_run = preserve_due_commitment(
            _parse_iso(existing_row.get("next_run_at") if existing_row else None),
            next_run, now=now, paused=decl.paused,
        )

        import json as _json
        row = {
            "user_id": user_id,
            "slug": slug,
            "status": "active",
            "kind": STRING_KIND,
            "schedule": _json.dumps(decl.schedule) if isinstance(decl.schedule, list) else decl.schedule,
            "next_run_at": next_run.isoformat() if next_run else None,
            "declaration_path": decl.declaration_path,
            "paused": decl.paused,
        }
        try:
            if existing_row:
                client.table("tasks").update(row).eq("id", existing_row["id"]).execute()
            else:
                client.table("tasks").insert(row).execute()
            touched += 1
        except Exception as e:
            logger.warning("[STRINGS_SCHED] upsert failed for %s/%s: %s", user_id[:8], slug, e)

    for slug, existing_row in existing_by_slug.items():
        if slug not in by_slug:
            try:
                client.table("tasks").delete().eq("id", existing_row["id"]).execute()
                touched += 1
                logger.info("[STRINGS_SCHED] dropped string row %s/%s (declaration gone or in repair)",
                            user_id[:8], slug)
            except Exception as e:
                logger.warning("[STRINGS_SCHED] delete failed for %s/%s: %s", user_id[:8], slug, e)

    return touched


def claim_string_run(client, user_id: str, slug: str, original_next_run: Optional[str],
                     *, sentinel_hours: int = 2) -> bool:
    """CAS atomic claim, kind-scoped (the radar/capture mechanism verbatim)."""
    if original_next_run is None:
        return False
    from datetime import timedelta
    sentinel = (datetime.now(timezone.utc) + timedelta(hours=sentinel_hours)).isoformat()
    try:
        result = (
            client.table("tasks")
            .update({"next_run_at": sentinel})
            .eq("user_id", user_id)
            .eq("slug", slug)
            .eq("kind", STRING_KIND)
            .eq("next_run_at", original_next_run)
            .execute()
        )
        return bool(result.data)
    except Exception as e:
        logger.warning("[STRINGS_SCHED] claim failed for %s/%s: %s", user_id[:8], slug, e)
        return False


def record_string_run(client, user_id: str, decl: StringDecl, *, last_run_at: datetime) -> None:
    """Advance last_run_at + next_run_at post-run (clears the CAS sentinel)."""
    from services.scheduling import compute_next_run_at
    from services.schedule_utils import get_workspace_timezone

    try:
        next_run = compute_next_run_at(
            decl, last_run_at=last_run_at, now=last_run_at,
            user_timezone=get_workspace_timezone(client, user_id),
        )
    except ValueError:
        next_run = None
    try:
        client.table("tasks").update({
            "last_run_at": last_run_at.isoformat(),
            "next_run_at": next_run.isoformat() if next_run else None,
        }).eq("user_id", user_id).eq("slug", decl.slug).eq("kind", STRING_KIND).execute()
    except Exception as e:
        logger.warning("[STRINGS_SCHED] record run failed for %s/%s: %s", user_id[:8], decl.slug, e)


# ---------------------------------------------------------------------------
# The resident — Keeper (ADR-562: declared in the app's registration)
# ---------------------------------------------------------------------------


def resolve_strings_resident() -> tuple[str, str]:
    """The standing writer's resident colleague — Keeper.

    The SLUG comes from the app's own registration (ADR-562 D3 — one
    declaration, read back); model + character come from the character row,
    where identity/engine/character live (ADR-460). Keeper is a POSTURE over
    Produce (the Critic shape — a stance, not a fourth addressed operation),
    so resolution goes through the one folded character namespace, exactly as
    a lane pinning it does. Returns ``(model, posture)``.
    """
    import services.apps  # noqa: F401  (registration side-effect — ADR-562)
    from services.agents_registry import get_agent
    from services.authoring import resident_for_app

    slug = resident_for_app("strings") or "keeper"
    row = get_agent(slug)
    if row is None:  # a registration naming a ghost is a bug, not a fallback
        raise KeyError(f"strings resident {slug!r} is not a kernel character")
    return row["model"], row["posture"]


# ---------------------------------------------------------------------------
# Fetch — v1 sources are HTTP pull only (D4)
# ---------------------------------------------------------------------------


async def _fetch_source(url: str) -> str:
    import httpx
    async with httpx.AsyncClient(
        timeout=_FETCH_TIMEOUT_S,
        headers={"User-Agent": _USER_AGENT},
        follow_redirects=True,
    ) as http:
        resp = await http.get(url)
        resp.raise_for_status()
        return resp.text


#: ADR-594 D2 — the freshness floor, THE spend guard for connector reach
#: (successor of the deleted digest's `is_due`): a selector whose newest
#: landed snapshot is younger than this is read, not re-reached, so two
#: strings sharing a selector cost one platform read per window.
_CONNECTOR_CAPTURE_MIN_INTERVAL_S = 600


async def _reach_connector_sources(
    client, user_id: str, conn_sources: list[dict], *, observed_at: str,
) -> None:
    """ADR-594 D2 — reach with a receipt: before reading, invoke the ONE
    capture writer for this run's declared selectors (grouped per platform),
    which lands attributed observations at the fixed intake lane. The
    effective set is the intersection with the connection's aperture — a
    string narrows the operator's consent, never widens it. Failure degrades
    to the newest landed snapshot (stale-but-honest; the desk states
    staleness); never raises."""
    from services.connectors import (
        connection_row,
        read_landed_snapshots,
        run_connector_capture,
    )
    from services.workspace import UserMemory

    by_plat: dict[str, list[str]] = {}
    for s in conn_sources:
        plat = str(s.get("connector", "")).strip().lower()
        sel = str(s.get("selector", "")).strip()
        if plat and sel:
            by_plat.setdefault(plat, []).append(sel)

    um = UserMemory(client, user_id)
    now = datetime.now(timezone.utc)
    for plat, sels in by_plat.items():
        row = connection_row(client, user_id, plat)
        if row is None:
            continue  # unconnected — the read step reports the honest empty
        stale: list[str] = []
        for sel in sels:
            try:
                snaps = await read_landed_snapshots(um, plat, sel, limit=1)
            except Exception:  # noqa: BLE001
                snaps = []
            if snaps and (now - snaps[-1][1]).total_seconds() < _CONNECTOR_CAPTURE_MIN_INTERVAL_S:
                continue  # the freshness floor — the receipt IS the guard
            stale.append(sel)
        if not stale:
            continue
        try:
            await run_connector_capture(
                client, user_id, row, observed_at=observed_at, selectors=stale,
            )
        except Exception as e:  # noqa: BLE001 — reach must not fail the run
            logger.warning("[STRINGS] connector reach failed %s/%s: %s",
                           user_id[:8], plat, e)


async def _read_connector_source(
    client, user_id: str, platform: str, selector: str,
) -> tuple[Optional[str], Optional[str]]:
    """Resolve a connector source (ADR-582 D6): the newest LANDED snapshot at
    the fixed intake lane. Returns (content, /workspace-absolute path) or
    (None, None) — an un-captured selector is the same honest empty as a dead
    feed. Substrate reads only — the reach half lives in
    `_reach_connector_sources`, which goes through the ONE capture writer;
    this read path never touches a platform API or HTTP."""
    from services.connectors import read_landed_snapshots
    from services.workspace import UserMemory

    um = UserMemory(client, user_id)
    snaps = await read_landed_snapshots(um, platform, selector, limit=1)
    if not snaps:
        return None, None
    rel = snaps[-1][0]
    try:
        body = await um.read(rel)
    except Exception as e:  # noqa: BLE001
        logger.warning("[STRINGS] connector source read failed %s: %s", rel, e)
        return None, None
    if body is None:
        return None, None
    return body, f"/workspace/{rel.lstrip('/')}"


def _retain_raw(client, user_id: str, *, source_id: str, url: str,
                observed_at: str, stamp: str, body: str, fmt: str) -> str:
    """Retain one fetched body as an immutable raw observation — the
    ADR-376/DP32 raw lane, sibling to track_web_sources' (same inbound/web/
    home, source-slugged). Returns the path the write CITES."""
    from services.authored_substrate import write_revision
    from services.primitives.track_web_sources import _slug as _source_slug

    ext = fmt if fmt in SUPPORTED_FORMATS else "txt"
    path = f"/workspace/inbound/web/{_source_slug(source_id)}/{stamp}.{ext}"
    truncated = body[:_MAX_FETCH_CHARS]
    write_revision(
        client,
        user_id=user_id,
        path=path,
        content=truncated,
        authored_by="system:strings",
        message=f"raw string observation: {url} @ {observed_at}",
        revision_kind="observation",
    )
    return path


# ---------------------------------------------------------------------------
# Map + validate — the machine-checkable half of the contract (D3)
# ---------------------------------------------------------------------------


class ShapeViolation(Exception):
    """The fetched material does not satisfy the declared shape. The run
    REFUSES the write and surfaces the reason — the loud repair state."""


def map_structured(raw: str, *, fmt: str, shape: dict) -> str:
    """csv/json/txt: parse → map → validate. Pure. Returns the leaf content
    to write, or raises ShapeViolation with an operator-readable reason."""
    if fmt == "txt":
        if not raw.strip():
            raise ShapeViolation("the source returned an empty body")
        return raw if raw.endswith("\n") else raw + "\n"

    if fmt == "csv":
        import csv as _csv
        import io as _io
        try:
            rows = list(_csv.reader(_io.StringIO(raw)))
        except _csv.Error as e:
            raise ShapeViolation(f"the source is not parseable CSV: {e}")
        rows = [r for r in rows if any((c or "").strip() for c in r)]
        if not rows:
            raise ShapeViolation("the source returned no CSV rows")
        declared = shape.get("columns")
        if isinstance(declared, list) and declared:
            declared = [str(c) for c in declared]
            header = [c.strip() for c in rows[0]]
            missing = [c for c in declared if c not in header]
            if missing:
                raise ShapeViolation(
                    f"declared column(s) missing from the source: {', '.join(missing)}"
                )
            # The MAP: project every row onto the declared columns, in the
            # declared order — the contract's shape is the file's shape.
            idx = [header.index(c) for c in declared]
            out = _io.StringIO()
            w = _csv.writer(out, lineterminator="\n")
            w.writerow(declared)
            for r in rows[1:]:
                w.writerow([(r[i] if i < len(r) else "") for i in idx])
            return out.getvalue()
        out = _io.StringIO()
        w = _csv.writer(out, lineterminator="\n")
        for r in rows:
            w.writerow(r)
        return out.getvalue()

    if fmt == "json":
        import json as _json
        try:
            parsed = _json.loads(raw)
        except ValueError as e:
            raise ShapeViolation(f"the source is not parseable JSON: {e}")
        declared = shape.get("keys")
        if isinstance(declared, list) and declared:
            if not isinstance(parsed, dict):
                raise ShapeViolation("shape declares keys but the source is not a JSON object")
            missing = [str(k) for k in declared if str(k) not in parsed]
            if missing:
                raise ShapeViolation(
                    f"declared key(s) missing from the source: {', '.join(missing)}"
                )
        return _json.dumps(parsed, indent=2, ensure_ascii=False) + "\n"

    raise ShapeViolation(f"unsupported structured format: {fmt}")


# ---------------------------------------------------------------------------
# The prose posture — the JOB overlay for an md string's judgment turn
# ---------------------------------------------------------------------------

#: Composed at run time UNDER Keeper's character (character first, job second
#: — the lane_runner order). The CONTRACT rides the user message, exactly as
#: radar's criterion does.
_KEEPER_RUN_POSTURE = """THE STANDING KEEPER JOB — the maintained file "{target}" in {root}.

A scheduled run fired in the member's workspace. Nobody is present; the file
you keep will be read later, and other artifacts cite it by reference. You are
handed THE CONTRACT (what this file means and must stay true to), THE CURRENT
FILE (it may carry the member's own corrections — preserve them; they compound
into every future run), and THE FRESH SOURCE MATERIAL (fetched just now from
the declared sources).

Return the FULL REVISED FILE: fold what the sources change into the current
content, under the contract. Keeping is the job — fidelity over novelty; what
the contract excludes stays out, however interesting.

THE BAR
- If the sources change nothing under the contract, reply with exactly:
  NO_CHANGE
  An unchanged file honestly reported beats a manufactured update — never pad.
- The file is the current state, not a log — fold, don't append; prune what
  has stopped being true.
- Preserve the member's corrections and voice where the sources don't
  contradict them; when they do, update the claim and cite why.
- Every new claim cites its source url inline as a markdown link. NEVER
  invent facts, numbers, or sources.

THE OUTPUT CONTRACT
Return the full file's markdown and NOTHING else — or the exact token
NO_CHANGE. No preamble, no code fence around the whole thing.
"""


def build_keeper_run_posture(decl: StringDecl) -> str:
    """The prose run's derive posture — pure."""
    return _KEEPER_RUN_POSTURE.format(target=decl.target, root=decl.root)


#: The DESK posture (ADR-569 D6, via ADR-567 D4's mechanism) — the job
#: overlay for a lane bound to a maintained file's target leaf. This is
#: Keeper-as-file-custodian: the member and the colleague run the string's
#: lifecycle in conversation, and the colleague works by writing the folder's
#: files. Composed fresh per turn (derived-never-stored); the state block
#: keeps the conversation honest against the substrate.
_KEEPER_DESK_FRAME = """KEEPER'S DESK — you keep the maintained file in {root} with the member.

A string runs a standing loop: on a schedule, its declared sources are pulled
and the DESIGNATED file is revised under its contract (mechanically for
csv/json/txt — fetch, map to the declared shape, validate, write; as a
bounded judgment turn for md, governed by CONTRACT.md). At this desk the
member talks to you about that loop — designating the file, declaring its
contract and sources, tuning it, and correcting the file. You act by WRITING
THE FOLDER'S FILES; the kernel reads them (the declaration is discovered
within ~5 minutes of landing; runs then fire on its schedule).

THE LAW (never bend it): only the DESIGNATED target is a standing writer's
target. One string per folder. v1 targets are md, csv, json or txt — an
authoring artifact (a deck's html, a Docs document) is NOT designatable;
it stays current by CITING a maintained file instead.

THE THREE FILES (all inside {root}/)
- CONTRACT.md — what the file means and must stay true to, in prose: for
  structured formats, what each column/field means; for prose, its
  conventions and voice. The member's declaration; you draft and revise it
  FROM what they tell you. Ordinary markdown, no frontmatter, never
  machine-parsed.
- _string.yaml — machine config, STRICT YAML, nothing but these keys:
    target: metrics.csv      # the designated leaf (md/csv/json/txt, this folder)
    schedule: "0 13 * * *"   # UTC cron (or a list of crons)
    paused: false
    sources:
      - id: short-slug       # kebab, unique
        url: https://…       # http(s) endpoint; csv/json/txt: EXACTLY ONE source
    shape:                   # structured formats only, optional but valuable
      columns: [date, mrr]   # csv: the required columns (file is projected to them)
      # keys: [mrr, churn]   # json: required top-level keys
  NO prose, NO other keys. After writing it, READ IT BACK to confirm it
  parses as clean YAML — a malformed declaration means the file silently
  stops being kept, and repairing it is YOUR job at this desk.
- the target file — the standing run is its author; revise it directly only
  when the member asks for a correction (their corrections compound — the
  next run inherits the head).

SETTING UP (when the state below shows no declaration yet)
Ask what the file must stay true to and where currency comes from, in plain
words. Then write CONTRACT.md first, then _string.yaml. Confirm what you set
up: the contract in one sentence, the source(s), the cadence, the shape (for
structured formats), and when the first run will fire. If the member names no
cadence, daily is the default. NEVER invent source URLs — only endpoints the
member names or that you know verifiably exist; when unsure, say so and ask.

MANAGING (ongoing)
Change the source, the cadence, the shape, pause/resume (`paused: true`),
tighten the contract — each is an edit to the file that owns the fact,
attributed to this conversation. Prefer EditFile for small changes. A run
refused with a shape violation means the SOURCE and the declared shape
disagree — read both, say which is wrong, and repair that one. When the
member asks why the file reads as it does, answer from the contract — and
offer to revise it if their intent has drifted from its text.

THE CURRENT STATE (read fresh this turn)
{state}"""


def build_keeper_desk_posture(client: Any, user_id: str, target_path: str) -> str:
    """The desk job overlay for a strings-bound lane (ADR-567 D4's mechanism,
    ADR-569's branch). ``target_path`` is the lane's binding
    (``{root}/{target-leaf}``); the root derives from it. Reads the folder's
    files fresh — the state block lets the colleague answer from substrate,
    not memory."""
    root = target_path.rsplit("/", 1)[0]
    leaf = target_path.rsplit("/", 1)[-1]
    topic = root[len(_WORKSPACE_PREFIX):] if root.startswith(_WORKSPACE_PREFIX) else root
    decl = _read_file(client, user_id, f"{root}/{STRING_DECLARATION_LEAF}")
    contract = _read_file(client, user_id, f"{root}/{CONTRACT_LEAF}")
    head = _read_file(client, user_id, target_path)

    lines: list[str] = []
    if decl and decl.strip():
        parsed = parse_string_yaml(
            decl, topic=topic,
            declaration_path=f"{root}/{STRING_DECLARATION_LEAF}",
        )
        if parsed is None:
            lines.append(
                "- _string.yaml EXISTS BUT DOES NOT PARSE — the standing loop "
                "is dark until it is repaired. Read it, fix the YAML, write it "
                "back."
            )
        elif parsed.problem is not None:
            lines.append(
                f"- _string.yaml parses but CANNOT RUN ({parsed.problem}) — "
                f"repair the declaration:\n{decl.strip()}"
            )
        else:
            lines.append(f"- _string.yaml (parses OK):\n{decl.strip()}")
    else:
        lines.append(
            "- NO DECLARATION YET — nothing is being kept. The member picked "
            f"the file '{leaf}'; set the string up with them (see SETTING UP)."
        )
    if contract and contract.strip():
        lines.append(f"- CONTRACT.md:\n{contract.strip()}")
    else:
        lines.append("- No CONTRACT.md yet.")
    if head and head.strip():
        lines.append(
            f"- {leaf} head: {len(head.splitlines())} lines, "
            f"{len(head)} chars."
        )
    else:
        lines.append(f"- {leaf} does not exist yet — the first run writes it.")

    return _KEEPER_DESK_FRAME.format(root=root, state="\n".join(lines))


def _read_file(client, user_id: str, path: str) -> Optional[str]:
    try:
        rows = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", path)
            .limit(1)
            .execute()
        ).data or []
        return rows[0].get("content") if rows else None
    except Exception as e:
        logger.warning("[STRINGS] read failed for %s: %s", path, e)
        return None


# ---------------------------------------------------------------------------
# The run — fetch → map/derive → validate → place → cite → embed → meter
# ---------------------------------------------------------------------------


async def run_string_sweep(client, user_id: str, decl: StringDecl) -> dict:
    """One run of one string. Returns {success, slug, target_path?,
    no_change?, error_reason?, detail?}. Never raises past its own boundary —
    the drainer records the run either way."""
    from services.telemetry import record_execution_event

    started = datetime.now(timezone.utc)
    topic = decl.topic

    # A declaration in a problem state never runs — the desk already says so.
    if decl.problem is not None or decl.format is None:
        return {"success": False, "slug": decl.slug,
                "error_reason": decl.problem or "unsupported_format"}

    # ── 1. fetch (mechanical, $0) — HTTP pull, raws retained; OR a connector
    #       source: REACH WITH A RECEIPT (ADR-594 D2) — invoke the one capture
    #       writer for this run's declared selectors (aperture-intersected,
    #       freshness-floored), then read the LANDED snapshot and cite it.
    #       Capture retained it, so there is no re-retain here. ──────────────
    observed_at = started.isoformat()
    stamp = started.strftime("%Y-%m-%dT%H-%M-%S")
    bodies: list[tuple[dict, str]] = []
    raw_paths: list[str] = []
    errors: list[str] = []
    conn_sources = [s for s in decl.sources if _is_connector_source(s)]
    if conn_sources:
        # The stamp must satisfy `connectors.parse_stamp` (it names the landed
        # file) — isoformat's microseconds/offset spelling would land
        # snapshots the shared reader then skips as unstamped.
        await _reach_connector_sources(
            client, user_id, conn_sources,
            observed_at=started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
    for s in decl.sources:
        try:
            if _is_connector_source(s):
                landed, landed_path = await _read_connector_source(
                    client, user_id, str(s["connector"]), str(s["selector"]),
                )
                if landed is None:
                    errors.append(f"{s.get('id')}: no landed snapshot")
                    continue
                bodies.append((s, landed[:_MAX_FETCH_CHARS]))
                raw_paths.append(landed_path)
                continue
            body = await _fetch_source(str(s["url"]))
            if len(body) > _MAX_FETCH_CHARS:
                body = body[:_MAX_FETCH_CHARS]
            bodies.append((s, body))
            raw_paths.append(_retain_raw(
                client, user_id, source_id=str(s["id"]), url=str(s["url"]),
                observed_at=observed_at, stamp=stamp, body=body, fmt=decl.format,
            ))
        except Exception as e:  # noqa: BLE001 — per-source isolation
            errors.append(f"{s.get('id')}: {e!r}")

    sweep_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
    sweep_ok = bool(bodies)
    record_execution_event(
        client, user_id=user_id, slug=f"string-sweep:{topic}",
        mode="mechanical", trigger_type="scheduled",
        status="success" if sweep_ok else "failed",
        error_reason=None if sweep_ok else "no_sources_fetched",
        error_detail=("; ".join(errors)[:500] or None) if errors else None,
        duration_ms=sweep_ms, funnel_decision="string",
        principal_id=user_id,
    )
    if not sweep_ok:
        return {"success": False, "slug": decl.slug, "error_reason": "no_sources_fetched"}

    current = _read_file(client, user_id, decl.target_path)

    # ── 2. map (mechanical) or derive (one bounded judgment turn) ─────────
    write_started = datetime.now(timezone.utc)
    if decl.format in ("csv", "json", "txt"):
        try:
            content = map_structured(bodies[0][1], fmt=decl.format, shape=decl.shape)
        except ShapeViolation as e:
            # D3 — the LOUD repair state: the write is REFUSED, the ledger
            # says why, the desk reads the ledger, the lane repairs. No
            # silent bad numbers.
            record_execution_event(
                client, user_id=user_id, slug=f"string-write:{topic}",
                mode="mechanical", trigger_type="scheduled", status="failed",
                error_reason="shape_violation", error_detail=str(e)[:500],
                funnel_decision="string", principal_id=user_id,
            )
            return {"success": False, "slug": decl.slug,
                    "error_reason": "shape_violation", "detail": str(e)}
        write_mode = "mechanical"
        ledger_model = None
        usage: dict = {}
    else:
        # md — the judgment derive, governed by CONTRACT.md (D4: a prose file
        # kept current IS a judgment derive; the contract is its criterion).
        # The turn's mechanics (router gate → completion → fence strip →
        # honest no-change) are the shared bounded derive turn (ADR-580 D6).
        from services.derive_turn import run_bounded_derive_turn

        contract = _read_file(client, user_id, decl.contract_path)
        def _source_label(s: dict) -> str:
            return s.get("url") or "{}:{}".format(s.get("connector"), s.get("selector"))

        material = "\n\n".join(
            f"SOURCE {s.get('id')} ({_source_label(s)}):\n{body[:40_000]}"
            for s, body in bodies
        )
        user_msg = (
            (f"THE CONTRACT (what this file must stay true to):\n\n{contract}\n\n"
             if contract and contract.strip() else
             "THERE IS NO CONTRACT DECLARED YET — hold a conservative bar: only "
             "clearly substantive updates on the file's own subject.\n\n")
            + (f"THE CURRENT FILE:\n\n{current}\n\n" if current
               else "THE FILE DOES NOT EXIST YET — this is the string's first "
                    "run. Write the baseline from the source material.\n\n")
            + f"THE FRESH SOURCE MATERIAL (just fetched):\n\n{material}\n"
        )
        resident_model, resident_character = resolve_strings_resident()
        turn = await run_bounded_derive_turn(
            model=resident_model,
            system=resident_character + "\n\n" + build_keeper_run_posture(decl),
            user_msg=user_msg,
            max_tokens=_STRING_MAX_TOKENS,
            timeout=_DERIVE_TIMEOUT_S,
            no_change_tokens=(NO_CHANGE_SENTINEL,),
        )
        if turn.status == "router_disabled":
            record_execution_event(
                client, user_id=user_id, slug=f"string-write:{topic}",
                mode="judgment", trigger_type="scheduled", status="skipped",
                error_reason="router_disabled",
                funnel_decision="string", principal_id=user_id,
            )
            return {"success": False, "slug": decl.slug, "error_reason": "router_disabled"}
        if turn.status == "raised":
            logger.error("[STRINGS] derive failed for %s/%s: %s", user_id[:8], decl.slug, turn.error)
            record_execution_event(
                client, user_id=user_id, slug=f"string-write:{topic}",
                mode="judgment", trigger_type="scheduled", status="failed",
                error_reason="derive_raised", error_detail=(turn.error or "")[:500],
                funnel_decision="string", principal_id=user_id,
            )
            return {"success": False, "slug": decl.slug, "error_reason": "derive_raised"}
        write_mode = "judgment"
        ledger_model = turn.ledger_model
        usage = turn.usage
        if turn.status == "no_change":
            record_execution_event(
                client, user_id=user_id, slug=f"string-write:{topic}",
                mode="judgment", trigger_type="scheduled", status="skipped",
                error_reason="no_change", model=ledger_model,
                funnel_decision="string", principal_id=user_id, **usage,
            )
            return {"success": True, "slug": decl.slug, "no_change": True}
        text = turn.text
        content = text + ("\n" if not text.endswith("\n") else "")

    write_ms = int((datetime.now(timezone.utc) - write_started).total_seconds() * 1000)

    # An unchanged pull is an honest no-op — no manufactured revision.
    if current is not None and content == current:
        record_execution_event(
            client, user_id=user_id, slug=f"string-write:{topic}",
            mode=write_mode, trigger_type="scheduled", status="skipped",
            error_reason="no_change", model=ledger_model,
            duration_ms=write_ms, funnel_decision="string",
            principal_id=user_id, **usage,
        )
        return {"success": True, "slug": decl.slug, "no_change": True}

    # ── 3. place + cite — CONFINED to the designated leaf ONLY (D3) ───────
    path = decl.target_path
    _assert_string_write(decl, path)

    from services.authored_substrate import write_revision
    revision_id = write_revision(
        client,
        user_id=user_id,
        path=path,
        content=content,
        # The face is Keeper, the fact is the ledger (ADR-460 D2).
        authored_by="system:strings",
        message=f"Keeper kept '{decl.target}' current "
                f"(standing pull, {len(bodies)} source{'s' if len(bodies) != 1 else ''})",
        revision_kind="derivation",
        derived_from=raw_paths,
    )

    # ── 4. embed (retrieval — a maintained file nobody can recall is dead) ─
    try:
        from services.primitives.workspace import _embed_workspace_file
        await _embed_workspace_file(client, user_id, path, content)
    except Exception as e:
        logger.warning("[STRINGS] embed failed for %s: %s", path, e)

    # ── 5. meter ──────────────────────────────────────────────────────────
    record_execution_event(
        client, user_id=user_id, slug=f"string-write:{topic}",
        mode=write_mode, trigger_type="scheduled", status="success",
        model=ledger_model, duration_ms=write_ms,
        funnel_decision="string", principal_id=user_id, **usage,
    )

    logger.info("[STRINGS] %s/%s → %s (rev %s)", user_id[:8], decl.slug, path, revision_id[:8])
    return {"success": True, "slug": decl.slug, "target_path": path,
            "revision_id": revision_id}


# ---------------------------------------------------------------------------
# Drainer — the scheduler-tick entry point
# ---------------------------------------------------------------------------


async def drain_due_string_runs(client) -> tuple[int, int, int]:
    """Discover strings, sync the kind='string' index, run due strings.
    Returns (found, succeeded, failed). Zero strings declared → one LIKE
    scan, nothing else."""
    now = datetime.now(timezone.utc)
    decls_by_user = discover_strings(client)

    for uid, decls in decls_by_user.items():
        try:
            await materialize_string_index(client, uid, decls, now=now)
        except Exception as e:
            logger.warning("[STRINGS] materialize failed for %s: %s", uid[:8], e)

    try:
        due_rows = (
            client.table("tasks")
            .select("id, user_id, slug, next_run_at")
            .eq("status", "active")
            .eq("kind", STRING_KIND)
            .lte("next_run_at", now.isoformat())
            .execute()
        ).data or []
    except Exception as e:
        logger.warning("[STRINGS] due query failed: %s", e)
        return 0, 0, 0

    found = succeeded = failed = 0
    for row in due_rows:
        uid = row["user_id"]
        decl = next(
            (d for d in decls_by_user.get(uid, []) if d.slug == row.get("slug")), None
        )
        if decl is None or decl.paused or decl.problem is not None:
            continue
        found += 1

        if not claim_string_run(client, uid, decl.slug, row.get("next_run_at")):
            continue
        try:
            result = await run_string_sweep(client, uid, decl)
            if result.get("success"):
                succeeded += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            logger.exception("[STRINGS] run raised for %s/%s: %s", uid[:8], decl.slug, e)
        finally:
            try:
                record_string_run(client, uid, decl, last_run_at=datetime.now(timezone.utc))
            except Exception as e:
                logger.warning("[STRINGS] record run failed for %s/%s: %s", uid[:8], decl.slug, e)

    return found, succeeded, failed


__all__ = [
    "STRING_KIND",
    "STRING_DECLARATION_LEAF",
    "CONTRACT_LEAF",
    "SUPPORTED_FORMATS",
    "NO_CHANGE_SENTINEL",
    "StringDecl",
    "ShapeViolation",
    "topic_from_declaration_path",
    "parse_string_yaml",
    "discover_strings",
    "materialize_string_index",
    "claim_string_run",
    "record_string_run",
    "resolve_strings_resident",
    "map_structured",
    "build_keeper_run_posture",
    "build_keeper_desk_posture",
    "run_string_sweep",
    "drain_due_string_runs",
]
