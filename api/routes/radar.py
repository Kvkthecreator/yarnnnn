"""Radar hub routes — ADR-486 R1 (watch authoring) + R2 (the composed view).

R1 — the first in-product writer of hub declarations (before this, watches
were bundle-shipped only; the R0 eval hub was declared by a one-shot).
A member declares a hub: topic + sources + cadence (+ optional steer). The
declaration lands at ``operation/{topic}/_radar.yaml`` through write_revision
(the one door), and the kind='radar' index materializes immediately so a
``fire_on_activation`` hub sweeps on the next scheduler tick (~5 min — the
felt moment: declare a radar, the first brief arrives while you watch).

R2 — ``GET /api/radar/hubs/{topic}`` is a LAZY PROJECTION over the hub
folder + the ledgers (ADR-486 D5, derived-never-stored): declaration +
briefs shelf + sweep health from execution_events, composed at read time.
Nothing here stores dashboard state; the substrate and the ledger are the
only sources.

Auth boundary: everything scopes to ``auth.user_id`` (the N=1 fallback the
radar service itself uses). Writes attribute ``operator`` (the ADR-209
route-side taxonomy — the save_identity precedent).
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

_TOPIC_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,58}[a-z0-9]$|^[a-z0-9]$")
_MAX_SOURCES = 12  # the TrackWebSources cap — reject loudly at the door


# ---------------------------------------------------------------------------
# Shapes
# ---------------------------------------------------------------------------


class HubSource(BaseModel):
    id: str
    url: str
    max_entries: int = Field(default=8, ge=1, le=20)


class CreateHubRequest(BaseModel):
    topic: str
    sources: list[HubSource]
    schedule: str = "0 21 * * *"  # daily 21:00 UTC default
    prompt: Optional[str] = None
    fire_on_activation: bool = True  # first brief within one tick


class UpdateHubRequest(BaseModel):
    """Partial update — absent fields keep their declared values."""

    paused: Optional[bool] = None
    schedule: Optional[str] = None
    prompt: Optional[str] = None
    sources: Optional[list[HubSource]] = None


class HubSummary(BaseModel):
    topic: str
    declaration_path: str
    schedule: Optional[Any] = None
    paused: bool = False
    prompt: Optional[str] = None
    sources: list[HubSource] = []
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    latest_brief_path: Optional[str] = None
    latest_brief_title: Optional[str] = None
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
    """The R2 composed view — summary + briefs shelf + sweep health,
    projected at read time from substrate + ledger."""

    briefs: list[BriefEntry] = []
    recent_sweeps: list[SweepEvent] = []
    signal_observed_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hub_path(topic: str) -> str:
    return f"/workspace/operation/{topic}/_radar.yaml"


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
    from services.settle import extract_title
    return extract_title(content or "")


def _date_prefix(path: str) -> Optional[str]:
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", path.rsplit("/", 1)[-1])
    return m.group(1) if m else None


def compose_declaration_yaml(
    *,
    schedule: Any,
    paused: bool,
    prompt: Optional[str],
    sources: list[dict],
    fire_on_activation: bool = False,
) -> str:
    """Compose the ``_radar.yaml`` body. Deterministic, machine-class
    (ADR-254 underscore-yaml): comment header + safe_dump payload."""
    payload: dict[str, Any] = {"schedule": schedule}
    if fire_on_activation:
        payload["fire_on_activation"] = True
    payload["paused"] = paused
    if prompt and prompt.strip():
        payload["prompt"] = prompt.strip() + "\n"
    payload["sources"] = sources
    header = (
        "# _radar.yaml — AI Radar hub declaration (ADR-486)\n"
        "# Standing sweep: schedule fires → sources fetched → what changed\n"
        "# lands as a cited brief in briefs/. Edit freely; the scheduler\n"
        "# re-reads this file every tick.\n"
    )
    return header + _yaml.safe_dump(payload, sort_keys=False, allow_unicode=True,
                                    default_flow_style=False)


def _summarize(client, user_id: str, hub, index_row: Optional[dict],
               sources: list[dict]) -> HubSummary:
    briefs = (
        client.table("workspace_files")
        .select("path, content")
        .eq("user_id", user_id)
        .like("path", f"{hub.root}/briefs/%")
        .order("path", desc=True)
        .execute()
    ).data or []
    latest = briefs[0] if briefs else None
    return HubSummary(
        topic=hub.topic,
        declaration_path=hub.declaration_path,
        schedule=hub.schedule,
        paused=hub.paused,
        prompt=(hub.options.get("prompt") or None),
        sources=[HubSource(**{k: v for k, v in s.items()
                              if k in {"id", "url", "max_entries"}})
                 for s in sources if isinstance(s, dict) and s.get("id") and s.get("url")],
        last_run_at=(index_row or {}).get("last_run_at"),
        next_run_at=(index_row or {}).get("next_run_at"),
        latest_brief_path=latest.get("path") if latest else None,
        latest_brief_title=_title_of(latest.get("content", "")) if latest else None,
        brief_count=len(briefs),
    )


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
    hubs = discover_radar_hubs(client).get(user_id, [])
    await materialize_radar_index(client, user_id, hubs)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/radar/hubs")
async def list_hubs(auth: UserClient) -> list[HubSummary]:
    from services.radar import discover_radar_hubs
    hubs = [h for h in discover_radar_hubs(auth.client).get(auth.user_id, [])]

    index_rows = (
        auth.client.table("tasks")
        .select("slug, last_run_at, next_run_at")
        .eq("user_id", auth.user_id)
        .eq("kind", "radar")
        .execute()
    ).data or []
    by_slug = {r["slug"]: r for r in index_rows}

    out: list[HubSummary] = []
    for hub in sorted(hubs, key=lambda h: h.topic):
        content = _read_declaration(auth.client, auth.user_id, hub.topic) or ""
        out.append(_summarize(auth.client, auth.user_id, hub,
                              by_slug.get(hub.slug), _declared_sources(content)))
    return out


@router.post("/radar/hubs", status_code=201)
async def create_hub(request: CreateHubRequest, auth: UserClient) -> HubSummary:
    topic = request.topic.strip().lower()
    if not _TOPIC_RE.match(topic):
        raise HTTPException(status_code=422, detail="topic must be a kebab-case slug (a-z, 0-9, hyphens)")
    if not request.sources:
        raise HTTPException(status_code=422, detail="a hub needs at least one source")
    if len(request.sources) > _MAX_SOURCES:
        raise HTTPException(status_code=422, detail=f"at most {_MAX_SOURCES} sources per hub")
    for s in request.sources:
        if not s.url.startswith(("http://", "https://")):
            raise HTTPException(status_code=422, detail=f"source {s.id!r}: url must be http(s)")

    if _read_declaration(auth.client, auth.user_id, topic) is not None:
        raise HTTPException(status_code=409, detail=f"hub '{topic}' already exists")

    content = compose_declaration_yaml(
        schedule=request.schedule,
        paused=False,
        prompt=request.prompt,
        sources=[s.model_dump() for s in request.sources],
        fire_on_activation=request.fire_on_activation,
    )

    from services.authored_substrate import write_revision
    write_revision(
        auth.client,
        user_id=auth.user_id,
        path=_hub_path(topic),
        content=content,
        authored_by="operator",
        message=f"declare radar hub '{topic}' ({len(request.sources)} sources, {request.schedule})",
        workspace_id=getattr(auth, "workspace_id", None),
    )
    await _materialize(auth.client, auth.user_id)

    from services.radar import parse_radar_yaml
    hub = parse_radar_yaml(content, topic=topic, declaration_path=_hub_path(topic),
                           user_id=auth.user_id)
    row = (
        auth.client.table("tasks").select("slug, last_run_at, next_run_at")
        .eq("user_id", auth.user_id).eq("kind", "radar")
        .eq("slug", f"radar:{topic}").limit(1).execute()
    ).data or []
    return _summarize(auth.client, auth.user_id, hub, row[0] if row else None,
                      [s.model_dump() for s in request.sources])


@router.patch("/radar/hubs/{topic}")
async def update_hub(topic: str, request: UpdateHubRequest, auth: UserClient) -> HubSummary:
    content = _read_declaration(auth.client, auth.user_id, topic)
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
    if request.prompt is not None:
        parsed["prompt"] = request.prompt
    if request.sources is not None:
        if not request.sources or len(request.sources) > _MAX_SOURCES:
            raise HTTPException(status_code=422, detail=f"1..{_MAX_SOURCES} sources per hub")
        parsed["sources"] = [s.model_dump() for s in request.sources]

    new_content = compose_declaration_yaml(
        schedule=parsed.get("schedule"),
        paused=bool(parsed.get("paused", False)),
        prompt=parsed.get("prompt"),
        sources=[s for s in (parsed.get("sources") or []) if isinstance(s, dict)],
        fire_on_activation=bool(parsed.get("fire_on_activation", False)),
    )

    from services.authored_substrate import write_revision
    write_revision(
        auth.client,
        user_id=auth.user_id,
        path=_hub_path(topic),
        content=new_content,
        authored_by="operator",
        message=f"update radar hub '{topic}'",
        workspace_id=getattr(auth, "workspace_id", None),
    )
    await _materialize(auth.client, auth.user_id)

    from services.radar import parse_radar_yaml
    hub = parse_radar_yaml(new_content, topic=topic, declaration_path=_hub_path(topic),
                           user_id=auth.user_id)
    row = (
        auth.client.table("tasks").select("slug, last_run_at, next_run_at")
        .eq("user_id", auth.user_id).eq("kind", "radar")
        .eq("slug", f"radar:{topic}").limit(1).execute()
    ).data or []
    return _summarize(auth.client, auth.user_id, hub, row[0] if row else None,
                      [s for s in (parsed.get("sources") or []) if isinstance(s, dict)])


@router.get("/radar/hubs/{topic}")
async def get_hub(topic: str, auth: UserClient) -> HubView:
    """R2 — the composed hub view, projected at read time (never stored)."""
    content = _read_declaration(auth.client, auth.user_id, topic)
    if content is None:
        raise HTTPException(status_code=404, detail=f"no hub '{topic}'")

    from services.radar import parse_radar_yaml
    hub = parse_radar_yaml(content, topic=topic, declaration_path=_hub_path(topic),
                           user_id=auth.user_id)
    if hub is None:
        raise HTTPException(status_code=422, detail="declaration unparseable")

    row = (
        auth.client.table("tasks").select("slug, last_run_at, next_run_at")
        .eq("user_id", auth.user_id).eq("kind", "radar")
        .eq("slug", hub.slug).limit(1).execute()
    ).data or []
    summary = _summarize(auth.client, auth.user_id, hub, row[0] if row else None,
                         _declared_sources(content))

    briefs_rows = (
        auth.client.table("workspace_files")
        .select("path, content")
        .eq("user_id", auth.user_id)
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
        .eq("user_id", auth.user_id)
        .in_("slug", [f"radar-sweep:{topic}", f"radar-brief:{topic}"])
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    ).data or []
    sweeps = [SweepEvent(**{k: e.get(k) for k in
                            ("slug", "status", "created_at", "error_reason")})
              for e in events]

    signal_observed = None
    sig_rows = (
        auth.client.table("workspace_files")
        .select("content")
        .eq("user_id", auth.user_id)
        .eq("path", hub.signal_path)
        .limit(1)
        .execute()
    ).data or []
    if sig_rows:
        try:
            sig = _yaml.safe_load(sig_rows[0].get("content") or "") or {}
            signal_observed = sig.get("observed_at")
        except _yaml.YAMLError:
            pass

    return HubView(**summary.model_dump(), briefs=briefs, recent_sweeps=sweeps,
                   signal_observed_at=signal_observed)


def _strip_frontmatter(content: str) -> str:
    m = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    return content[m.end():] if m else content
