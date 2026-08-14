"""Radar hub routes — ADR-486 R1/R2, re-cut by ADR-564/565.

R1 — the authoring path. A member declares a hub on a meaning-folder (any
depth under ``operation/`` — ADR-565 D3): topic + sources + cadence + the
CRITERION (what matters here). Two files through the one door: the machine
config ``{folder}/_radar.yaml`` (schedule · paused · sources — the retired
``prompt:`` steer key never re-enters) and the prose ``{folder}/CRITERION.md``
(ADR-564 D2 — operator/lane-authored, never machine-parsed). The kind='radar'
index materializes immediately so a ``fire_on_activation`` hub sweeps on the
next scheduler tick (~5 min — declare a radar, the first report arrives while
you watch).

R2 — ``GET /api/radar/hubs/{topic}`` is a LAZY PROJECTION over the hub
folder + the ledgers (ADR-486 D5, derived-never-stored): declaration +
criterion + the LIVING REPORT head (ADR-565 D1) + the legacy briefs shelf +
sweep health from execution_events, composed at read time. Nothing here
stores dashboard state; the substrate and the ledger are the only sources.

Auth boundary (ADR-501): everything scopes to the ACTING WORKSPACE'S OWNER
user_id — the radar stack's end-to-end key (discovery grouping, the
kind='radar' index, the sweep contract "user_id = workspace owner UUID").
Resolved once per handler via ``_acting_owner``; byte-identical for owners,
and a member bound to a granted workspace reads/authors the WORKSPACE's hubs
(previously their own user_id: an empty surface + orphaned creates). Writes
attribute ``operator`` (the ADR-209 route-side taxonomy).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

import yaml as _yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()

_SEGMENT_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,58}[a-z0-9]$|^[a-z0-9]$")
_MAX_TOPIC_DEPTH = 4  # a meaning-path, not a filing cabinet — reject silly nesting
_MAX_SOURCES = 12  # the TrackWebSources cap — reject loudly at the door


def _validate_topic(topic: str) -> str:
    """A topic is a meaning-folder path under operation/ (ADR-565 D3): one or
    more kebab-case segments. Returns the normalized topic or raises 422."""
    t = (topic or "").strip().strip("/").lower()
    segments = t.split("/") if t else []
    if not segments or len(segments) > _MAX_TOPIC_DEPTH or not all(
        _SEGMENT_RE.match(s) for s in segments
    ):
        raise HTTPException(
            status_code=422,
            detail="topic must be 1..4 kebab-case path segments (a-z, 0-9, hyphens)",
        )
    return "/".join(segments)


# ---------------------------------------------------------------------------
# Shapes
# ---------------------------------------------------------------------------


class HubSource(BaseModel):
    id: str
    url: str
    max_entries: int = Field(default=8, ge=1, le=20)
    # ADR-564 D5 / ADR-565 D5 — the earn-their-keep reading, derived at read
    # time on the composed view only (get_hub), never stored, absent on the
    # cheap list projection.
    fed_count: Optional[int] = None    # sweeps in the window that fetched this source
    cited_count: Optional[int] = None  # report derivations in the window citing it


class CreateHubRequest(BaseModel):
    topic: str
    sources: list[HubSource]
    schedule: str = "0 21 * * *"  # daily 21:00 UTC default
    criterion: Optional[str] = None  # what matters here → CRITERION.md (ADR-564 D2)
    fire_on_activation: bool = True  # first report within one tick


class UpdateHubRequest(BaseModel):
    """Partial update — absent fields keep their declared values."""

    paused: Optional[bool] = None
    schedule: Optional[str] = None
    criterion: Optional[str] = None  # revises CRITERION.md, never the yaml
    sources: Optional[list[HubSource]] = None


class HubSummary(BaseModel):
    topic: str
    declaration_path: str
    schedule: Optional[Any] = None
    paused: bool = False
    criterion: Optional[str] = None
    sources: list[HubSource] = []
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    report_path: Optional[str] = None
    report_title: Optional[str] = None
    # The pre-ADR-565 shelf — legacy reads only; new sweeps never add to it.
    # (latest_brief_path/title were served-and-never-consumed after the desk
    # re-cut; deleted 2026-08-13 — the count gates the shelf section, the
    # composed view lists the entries.)
    brief_count: int = 0


class BriefEntry(BaseModel):
    path: str
    title: str
    date: Optional[str] = None


class SweepEvent(BaseModel):
    slug: str
    status: str
    created_at: Optional[str] = None
    error_reason: Optional[str] = None


class HubView(HubSummary):
    """The R2 composed view — summary + the living report head + the legacy
    briefs shelf + sweep health, projected at read time from substrate +
    ledger."""

    report: Optional[str] = None  # the living report head (ADR-565 D1)
    briefs: list[BriefEntry] = []
    recent_sweeps: list[SweepEvent] = []
    # ADR-564 D5 — the denominators behind each source's fed/cited counts:
    # how many sweeps (signal revisions) and report derivations the trailing
    # window actually held, so the FE can say "fetched in 12 of 14 sweeps".
    window_sweeps: Optional[int] = None
    window_changes: Optional[int] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hub_path(topic: str) -> str:
    return f"/workspace/operation/{topic}/_radar.yaml"


def _acting_workspace(auth) -> Optional[str]:
    """The workspace this request is bound to (ADR-501) — scopes the hub scan.

    The explicit `auth.workspace_id` is the strongest signal (get_user_client
    already resolved it fail-closed from X-Workspace-Id); omitting it falls
    through to the contextvar/owner path and resolves a member's OWN workspace.
    """
    from services.workspace_context import effective_workspace_id
    return effective_workspace_id(auth.user_id, getattr(auth, "workspace_id", None))


def _acting_owner(auth) -> str:
    """The acting workspace's OWNER user id — the radar stack's key (ADR-501).

    Same seam as the addressed wake (routes/feed.py): resolve at the boundary,
    key the stack by the owner. Owner sessions resolve to themselves."""
    from services.workspace_context import acting_workspace_owner
    return acting_workspace_owner(
        auth.client, auth.user_id, getattr(auth, "workspace_id", None)
    )


def _read_declaration(client, user_id: str, topic: str) -> Optional[str]:
    rows = (
        client.table("workspace_files")
        .select("content")
        .eq("user_id", user_id)
        .eq("path", _hub_path(topic))
        .limit(1)
        .execute()
    ).data or []
    return rows[0].get("content") if rows else None


def _title_of(content: str) -> str:
    # The brief's own leading `# Title` — the same reader the writer used, so
    # the shelf shows what the file says. (Was `services.settle`'s until
    # ADR-507 deleted that module; re-homed to the writer, `services/radar.py`.)
    from services.radar import extract_title
    return extract_title(content or "")


def _date_prefix(path: str) -> Optional[str]:
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", path.rsplit("/", 1)[-1])
    return m.group(1) if m else None


def compose_declaration_yaml(
    *,
    schedule: Any,
    paused: bool,
    sources: list[dict],
    fire_on_activation: bool = False,
) -> str:
    """Compose the ``_radar.yaml`` body — PURE machine config (ADR-565 D2:
    the ``prompt:`` steer key is retired; judgment prose lives in
    ``CRITERION.md``, which no machine writer ever touches). Deterministic,
    machine-class (ADR-254 underscore-yaml): comment header + safe_dump."""
    payload: dict[str, Any] = {"schedule": schedule}
    if fire_on_activation:
        payload["fire_on_activation"] = True
    payload["paused"] = paused
    payload["sources"] = sources
    header = (
        "# _radar.yaml — radar hub declaration (ADR-486, re-cut ADR-565)\n"
        "# Standing sweep: schedule fires → sources fetched → the folder's\n"
        "# living report.md is revised under CRITERION.md. Machine config\n"
        "# only — what matters here belongs in CRITERION.md, not this file.\n"
    )
    return header + _yaml.safe_dump(payload, sort_keys=False, allow_unicode=True,
                                    default_flow_style=False)


def _summarize(client, user_id: str, hub, index_row: Optional[dict],
               sources: list[dict]) -> HubSummary:
    from services.radar import _read_criterion, _read_file

    briefs = (
        client.table("workspace_files")
        .select("path")
        .eq("user_id", user_id)
        .like("path", f"{hub.root}/briefs/%")
        .execute()
    ).data or []
    report_head = _read_file(client, user_id, hub.report_path)
    return HubSummary(
        topic=hub.topic,
        declaration_path=hub.declaration_path,
        schedule=hub.schedule,
        paused=hub.paused,
        criterion=_read_criterion(client, user_id, hub),
        sources=[HubSource(**{k: v for k, v in s.items()
                              if k in {"id", "url", "max_entries"}})
                 for s in sources if isinstance(s, dict) and s.get("id") and s.get("url")],
        last_run_at=(index_row or {}).get("last_run_at"),
        next_run_at=(index_row or {}).get("next_run_at"),
        report_path=hub.report_path if report_head else None,
        report_title=_title_of(report_head) if report_head else None,
        brief_count=len(briefs),
    )


_STATS_WINDOW = 40  # revisions per chain considered — a trailing window, not an archive scan


def _source_stats(
    client, user_id: str, hub, sources: list[HubSource]
) -> tuple[list[HubSource], int, int]:
    """The earn-their-keep instrument (ADR-564 D5, surfaced per ADR-565 D5) —
    derived at read time from the ledger's reference edges, never stored.

    The window is the hub's OWN signal revision chain — hub-scoped by
    construction: every sweep revises the signal citing that sweep's raw
    observations, whose paths carry the source slug (inbound/web/{slug}/…).
    Per declared source:
      fed   = sweeps in the window whose signal revision cites the source's raw
              (i.e. the fetch succeeded and fed entries into the sweep)
      cited = report revisions of kind 'derivation' in the window citing the
              source's raw (the derivation used a sweep this source fed)

    Honest limitation, stated rather than implied: the v1 derive cites ALL of
    a changed sweep's raws (ADR-564 D3's single-turn shape), so `cited` reads
    "was fetched in a sweep that produced change", not per-claim selectivity.
    The instrument sharpens when the mechanical selection pass ships under
    scattered-source pressure. "fed N, cited 0 in K sweeps" is already the
    pruning affordance D5 names — a source that only ever feeds NO_CHANGE
    sweeps, or fails to fetch, reads at a glance.
    """
    from services.primitives.track_web_sources import _slug as _source_slug

    def _edges(path: str, *, kind: Optional[str] = None) -> list[list]:
        q = (
            client.table("workspace_file_versions")
            .select("derived_from, revision_kind")
            .eq("user_id", user_id)
            .eq("path", path)
        )
        rows = (
            q.order("created_at", desc=True).limit(_STATS_WINDOW).execute()
        ).data or []
        return [
            r.get("derived_from") or []
            for r in rows
            if (kind is None or r.get("revision_kind") == kind)
        ]

    try:
        sweep_edges = _edges(hub.signal_path)
        change_edges = _edges(hub.report_path, kind="derivation")
    except Exception as e:  # the instrument must never take down the view
        logger.warning("[RADAR] source stats failed for %s: %s", hub.topic, e)
        return sources, 0, 0

    def _counts(needle: str, edge_lists: list[list]) -> int:
        return sum(
            1
            for edges in edge_lists
            if any(isinstance(p, str) and needle in p for p in edges)
        )

    enriched: list[HubSource] = []
    for s in sources:
        needle = f"/inbound/web/{_source_slug(s.id)}/"
        enriched.append(
            s.model_copy(
                update={
                    "fed_count": _counts(needle, sweep_edges),
                    "cited_count": _counts(needle, change_edges),
                }
            )
        )
    return enriched, len(sweep_edges), len(change_edges)


def _declared_sources(content: str) -> list[dict]:
    try:
        parsed = _yaml.safe_load(content) or {}
        src = parsed.get("sources")
        return [s for s in src if isinstance(s, dict)] if isinstance(src, list) else []
    except _yaml.YAMLError:
        return []


async def _materialize(client, user_id: str) -> None:
    """Immediate index sync post-write — a fire_on_activation hub arms now,
    not at the next global discovery."""
    from services.radar import discover_radar_hubs, materialize_radar_index
    from services.workspace_context import effective_workspace_id
    hubs = discover_radar_hubs(
        client, workspace_id=effective_workspace_id(user_id)
    ).get(user_id, [])
    await materialize_radar_index(client, user_id, hubs)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/radar/hubs")
async def list_hubs(auth: UserClient) -> list[HubSummary]:
    from services.radar import discover_radar_hubs
    actor = _acting_owner(auth)
    hubs = [
        h for h in discover_radar_hubs(
            auth.client, workspace_id=_acting_workspace(auth)
        ).get(actor, [])
    ]

    index_rows = (
        auth.client.table("tasks")
        .select("slug, last_run_at, next_run_at")
        .eq("user_id", actor)
        .eq("kind", "radar")
        .execute()
    ).data or []
    by_slug = {r["slug"]: r for r in index_rows}

    out: list[HubSummary] = []
    for hub in sorted(hubs, key=lambda h: h.topic):
        content = _read_declaration(auth.client, actor, hub.topic) or ""
        out.append(_summarize(auth.client, actor, hub,
                              by_slug.get(hub.slug), _declared_sources(content)))
    return out


def _write_criterion(auth, actor: str, topic: str, text: str, *, message: str) -> None:
    """The criterion lands as its own attributed revision of CRITERION.md —
    never inside the machine yaml (ADR-564 D2)."""
    from services.authored_substrate import write_revision
    write_revision(
        auth.client,
        user_id=actor,
        path=f"/workspace/operation/{topic}/CRITERION.md",
        content=text.strip() + "\n",
        authored_by="operator",
        message=message,
        workspace_id=getattr(auth, "workspace_id", None),
    )


@router.post("/radar/hubs", status_code=201)
async def create_hub(request: CreateHubRequest, auth: UserClient) -> HubSummary:
    actor = _acting_owner(auth)
    topic = _validate_topic(request.topic)
    if not request.sources:
        raise HTTPException(status_code=422, detail="a hub needs at least one source")
    if len(request.sources) > _MAX_SOURCES:
        raise HTTPException(status_code=422, detail=f"at most {_MAX_SOURCES} sources per hub")
    for s in request.sources:
        if not s.url.startswith(("http://", "https://")):
            raise HTTPException(status_code=422, detail=f"source {s.id!r}: url must be http(s)")

    if _read_declaration(auth.client, actor, topic) is not None:
        raise HTTPException(status_code=409, detail=f"hub '{topic}' already exists")

    content = compose_declaration_yaml(
        schedule=request.schedule,
        paused=False,
        sources=[s.model_dump() for s in request.sources],
        fire_on_activation=request.fire_on_activation,
    )

    from services.authored_substrate import write_revision
    write_revision(
        auth.client,
        user_id=actor,
        path=_hub_path(topic),
        content=content,
        authored_by="operator",
        message=f"declare radar hub '{topic}' ({len(request.sources)} sources, {request.schedule})",
        workspace_id=getattr(auth, "workspace_id", None),
    )
    if request.criterion and request.criterion.strip():
        _write_criterion(auth, actor, topic, request.criterion,
                         message=f"declare the criterion for '{topic}'")
    await _materialize(auth.client, actor)

    from services.radar import parse_radar_yaml
    hub = parse_radar_yaml(content, topic=topic, declaration_path=_hub_path(topic),
                           user_id=actor)
    row = (
        auth.client.table("tasks").select("slug, last_run_at, next_run_at")
        .eq("user_id", actor).eq("kind", "radar")
        .eq("slug", f"radar:{topic}").limit(1).execute()
    ).data or []
    return _summarize(auth.client, actor, hub, row[0] if row else None,
                      [s.model_dump() for s in request.sources])


@router.patch("/radar/hubs/{topic:path}")
async def update_hub(topic: str, request: UpdateHubRequest, auth: UserClient) -> HubSummary:
    actor = _acting_owner(auth)
    topic = _validate_topic(topic)
    content = _read_declaration(auth.client, actor, topic)
    if content is None:
        raise HTTPException(status_code=404, detail=f"no hub '{topic}'")

    try:
        parsed = _yaml.safe_load(_strip_frontmatter(content)) or {}
    except _yaml.YAMLError:
        raise HTTPException(status_code=422, detail="existing declaration unparseable — edit the file directly")
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail="existing declaration unparseable — edit the file directly")

    if request.paused is not None:
        parsed["paused"] = request.paused
    if request.schedule is not None:
        parsed["schedule"] = request.schedule
    if request.sources is not None:
        if not request.sources or len(request.sources) > _MAX_SOURCES:
            raise HTTPException(status_code=422, detail=f"1..{_MAX_SOURCES} sources per hub")
        parsed["sources"] = [s.model_dump() for s in request.sources]

    # The criterion never rides the yaml. An explicit update revises
    # CRITERION.md; a legacy declaration still carrying the retired `prompt:`
    # key migrates it into CRITERION.md at first touch (ADR-565 D2 — the
    # recompose below drops the key either way, so migrate-before-drop).
    legacy_steer = parsed.pop("prompt", None)
    if request.criterion is not None and request.criterion.strip():
        _write_criterion(auth, actor, topic, request.criterion,
                         message=f"revise the criterion for '{topic}'")
    elif isinstance(legacy_steer, str) and legacy_steer.strip():
        from services.radar import _read_file as _radar_read
        if not _radar_read(auth.client, actor,
                           f"/workspace/operation/{topic}/CRITERION.md"):
            _write_criterion(auth, actor, topic, legacy_steer,
                             message=f"migrate the legacy steer into the criterion for '{topic}' (ADR-565 D2)")

    # fire_on_activation is consume-on-first-update: it is a CREATE-time fact
    # (arm the first sweep), not a standing declaration fact. Re-emitting it
    # here kept a never-run hub permanently armed — every pause/resume PATCH
    # re-composed the flag, and compute_next_run_at (scheduling.py) returns
    # `now` whenever the flag is set with last_run_at NULL, so each update
    # re-triggered an immediate fire. Any update after creation drops it.
    new_content = compose_declaration_yaml(
        schedule=parsed.get("schedule"),
        paused=bool(parsed.get("paused", False)),
        sources=[s for s in (parsed.get("sources") or []) if isinstance(s, dict)],
    )

    from services.authored_substrate import write_revision
    write_revision(
        auth.client,
        user_id=actor,
        path=_hub_path(topic),
        content=new_content,
        authored_by="operator",
        message=f"update radar hub '{topic}'",
        workspace_id=getattr(auth, "workspace_id", None),
    )
    await _materialize(auth.client, actor)

    from services.radar import parse_radar_yaml
    hub = parse_radar_yaml(new_content, topic=topic, declaration_path=_hub_path(topic),
                           user_id=actor)
    row = (
        auth.client.table("tasks").select("slug, last_run_at, next_run_at")
        .eq("user_id", actor).eq("kind", "radar")
        .eq("slug", f"radar:{topic}").limit(1).execute()
    ).data or []
    return _summarize(auth.client, actor, hub, row[0] if row else None,
                      [s for s in (parsed.get("sources") or []) if isinstance(s, dict)])


@router.get("/radar/hubs/{topic:path}")
async def get_hub(topic: str, auth: UserClient) -> HubView:
    """R2 — the composed hub view, projected at read time (never stored)."""
    actor = _acting_owner(auth)
    topic = _validate_topic(topic)
    content = _read_declaration(auth.client, actor, topic)
    if content is None:
        raise HTTPException(status_code=404, detail=f"no hub '{topic}'")

    from services.radar import parse_radar_yaml
    hub = parse_radar_yaml(content, topic=topic, declaration_path=_hub_path(topic),
                           user_id=actor)
    if hub is None:
        raise HTTPException(status_code=422, detail="declaration unparseable")

    row = (
        auth.client.table("tasks").select("slug, last_run_at, next_run_at")
        .eq("user_id", actor).eq("kind", "radar")
        .eq("slug", hub.slug).limit(1).execute()
    ).data or []
    summary = _summarize(auth.client, actor, hub, row[0] if row else None,
                         _declared_sources(content))

    briefs_rows = (
        auth.client.table("workspace_files")
        .select("path, content")
        .eq("user_id", actor)
        .like("path", f"{hub.root}/briefs/%")
        .order("path", desc=True)
        .limit(50)
        .execute()
    ).data or []
    briefs = [BriefEntry(path=b["path"], title=_title_of(b.get("content", "")),
                         date=_date_prefix(b["path"])) for b in briefs_rows]

    # Sweep health — the ledger is the source (falsifiers 3+4 read the same rows).
    events = (
        auth.client.table("execution_events")
        .select("slug, status, created_at, error_reason")
        .eq("user_id", actor)
        .in_("slug", [f"radar-sweep:{topic}", f"radar-brief:{topic}"])
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    ).data or []
    sweeps = [SweepEvent(**{k: e.get(k) for k in
                            ("slug", "status", "created_at", "error_reason")})
              for e in events]

    from services.radar import _read_file as _radar_read_file
    report_head = _radar_read_file(auth.client, actor, hub.report_path)

    # The earn-their-keep reading rides the composed view only (ADR-564 D5).
    enriched_sources, window_sweeps, window_changes = _source_stats(
        auth.client, actor, hub, summary.sources
    )
    view = HubView(**summary.model_dump(), report=report_head, briefs=briefs,
                   recent_sweeps=sweeps,
                   window_sweeps=window_sweeps, window_changes=window_changes)
    view.sources = enriched_sources
    return view


@router.post("/radar/hubs/{topic:path}/run")
async def run_hub_now(topic: str, auth: UserClient) -> dict:
    """Sweep now — the manual fire (the ADR-569 D7 direct-switch slot, owed
    to radar since the desk rebuild). Runs one sweep inline and records,
    exactly one scheduled sweep's body; the ledger meters it identically."""
    from datetime import datetime, timezone as _tz
    from services.radar import parse_radar_yaml, record_radar_run, run_radar_sweep

    actor = _acting_owner(auth)
    topic = _validate_topic(topic)
    content = _read_declaration(auth.client, actor, topic)
    if content is None:
        raise HTTPException(status_code=404, detail=f"no hub '{topic}'")
    hub = parse_radar_yaml(content, topic=topic, declaration_path=_hub_path(topic),
                           user_id=actor)
    if hub is None:
        raise HTTPException(status_code=422, detail="declaration unparseable — repair it first")

    result = await run_radar_sweep(auth.client, actor, hub)
    try:
        record_radar_run(auth.client, actor, hub,
                         last_run_at=datetime.now(_tz.utc))
    except Exception as e:
        logger.warning("[RADAR] manual-run record failed for %s: %s", topic, e)
    return result


def _strip_frontmatter(content: str) -> str:
    m = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    return content[m.end():] if m else content
