"""Standing work routes — ADR-639 (the kept file's direct switches + the roster).

The pane the strings app carried is DELETED (ADR-639 D4). What survives is
what had exactly one caller each and answers a question no other surface can:

    GET   /standing                 — what stands: every declaration in the
                                      acting workspace, with its last run
    PATCH /standing/{topic}         — Pause / Resume (the direct switch)
    POST  /standing/{topic}/run     — Run now (the manual fire, ADR-618 D2)

Rendered by the Notifications "Standing work" pane. Creation stays
CONVERSATIONAL (ADR-569 D7): a colleague authors CONTRACT.md + _standing.yaml
through any lane under `declaring-standing-work`; the tick discovers. There
is deliberately NO create route, and no composed per-declaration VIEW — the
sources-as-parties, consumers and head-fact projections were pane chrome
(ADR-595 D3) and left with it. Reading happens at the file's own surface.

Repair states stay LOUD (ADR-569 D3): a declaration that parses but cannot
run carries `problem`; the last run's status rides each row from the ledger,
so a refused write is visible where the roster is.

Auth boundary (ADR-501): everything scopes to the ACTING WORKSPACE'S OWNER
user_id via ``_acting_owner``.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

import yaml as _yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_TOPIC_DEPTH = 6
_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,62}$")

#: Ledger slugs this lane stamped before ADR-639 renamed it. Read for the
#: roster's "last run" so history stays legible; never written again.
_LEGACY_LEDGER_PREFIXES = ("string-write:", "string-sweep:")


def _validate_topic(topic: str) -> str:
    """A topic is its folder path relative to /workspace/ — an EXISTING
    meaning-folder, so validation is path hygiene (no traversal, no
    machinery segments), not a naming law. Returns normalized or raises 422."""
    t = (topic or "").strip().strip("/")
    segments = t.split("/") if t else []
    if (
        not segments
        or len(segments) > _MAX_TOPIC_DEPTH
        or any(not _SEGMENT_RE.match(s) or s in (".", "..") for s in segments)
    ):
        raise HTTPException(
            status_code=422,
            detail="topic must be 1..6 plain path segments (no traversal, no leading dots)",
        )
    return "/".join(segments)


# ---------------------------------------------------------------------------
# Shapes
# ---------------------------------------------------------------------------


class StandingSource(BaseModel):
    """One declared source — an HTTP pull (`url`) or a connector slice
    (`connector` + `selector`, ADR-582 D6 / ADR-594 D4). Both shapes served."""

    id: str
    url: Optional[str] = None
    connector: Optional[str] = None
    selector: Optional[str] = None


class LastRun(BaseModel):
    """The newest ledger row for this declaration — what the pane says about
    the last run, read from `execution_events` at request time."""

    status: str
    error_reason: Optional[str] = None
    at: Optional[str] = None


class UpdateStandingRequest(BaseModel):
    """The direct switch (ADR-569 D7). Everything else is the conversation's
    — a silently-widened PATCH here would rebuild the form ADR-567 D3
    replaced."""

    paused: Optional[bool] = None


class StandingSummary(BaseModel):
    topic: str
    declaration_path: str
    target: str = ""
    target_path: Optional[str] = None
    format: Optional[str] = None
    #: The app whose executor runs a prose declaration — explicit or derived
    #: (ADR-639 D3). None for a structured target (mechanical).
    app: Optional[str] = None
    schedule: Optional[Any] = None
    paused: bool = False
    sources: list[StandingSource] = []
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    #: Parseable-but-cannot-run (missing_target | invalid_target |
    #: unsupported_format | sources_invalid | app_invalid) — served, never
    #: swallowed (ADR-569 D3).
    problem: Optional[str] = None
    last_run: Optional[LastRun] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _decl_path(topic: str) -> str:
    from services.standing_work import DECLARATION_LEAF

    return f"/workspace/{topic}/{DECLARATION_LEAF}"


def _acting_workspace(auth) -> Optional[str]:
    from services.workspace_context import effective_workspace_id
    return effective_workspace_id(auth.user_id, getattr(auth, "workspace_id", None))


def _acting_owner(auth) -> str:
    from services.workspace_context import acting_workspace_owner
    return acting_workspace_owner(
        auth.client, auth.user_id, getattr(auth, "workspace_id", None)
    )


def _read_declaration(client, user_id: str, topic: str) -> Optional[str]:
    rows = (
        client.table("workspace_files")
        .select("content")
        .eq("user_id", user_id)
        .eq("path", _decl_path(topic))
        .limit(1)
        .execute()
    ).data or []
    return rows[0].get("content") if rows else None


def compose_standing_yaml(
    *,
    target: str,
    schedule: Any,
    paused: bool,
    sources: list[dict],
    app: Optional[str] = None,
    shape: Optional[dict] = None,
    fire_on_activation: bool = False,
) -> str:
    """Compose the ``_standing.yaml`` body — PURE machine config (ADR-569 D2:
    judgment prose lives in CONTRACT.md, which no machine writer touches).
    Deterministic, machine-class (ADR-254): comment header + safe_dump."""
    payload: dict[str, Any] = {"target": target}
    if app:
        payload["app"] = app
    payload["schedule"] = schedule
    if fire_on_activation:
        payload["fire_on_activation"] = True
    payload["paused"] = paused
    payload["sources"] = sources
    if shape:
        payload["shape"] = shape
    header = (
        "# _standing.yaml — standing declaration (ADR-639: the kept file)\n"
        "# On its schedule the sources are fetched and the designated target\n"
        "# is revised under CONTRACT.md. Machine config only — what the file\n"
        "# must stay true to belongs in CONTRACT.md, not here.\n"
    )
    return header + _yaml.safe_dump(payload, sort_keys=False, allow_unicode=True,
                                    default_flow_style=False)


def _parse_or_none(content: str, topic: str, user_id: str):
    from services.standing_work import parse_standing_yaml
    return parse_standing_yaml(
        content, topic=topic, declaration_path=_decl_path(topic), user_id=user_id
    )


async def _materialize(client, user_id: str) -> None:
    """Immediate index sync post-write — a switched declaration re-arms now,
    not at the next global discovery."""
    from services.standing_work import discover_standing, materialize_standing_index
    from services.workspace_context import effective_workspace_id
    decls = discover_standing(
        client, workspace_id=effective_workspace_id(user_id)
    ).get(user_id, [])
    await materialize_standing_index(client, user_id, decls)


def _index_rows(client, user_id: str) -> dict[str, dict]:
    from services.standing_work import STANDING_KIND

    rows = (
        client.table("tasks").select("slug, last_run_at, next_run_at")
        .eq("user_id", user_id).eq("kind", STANDING_KIND).execute()
    ).data or []
    return {r["slug"]: r for r in rows}


def _last_runs(client, user_id: str, topics: list[str]) -> dict[str, LastRun]:
    """The newest ledger row per topic — one query, the write step preferred
    over the sweep step when both exist (the write is the outcome). Reads the
    pre-ADR-639 slugs too, so a declaration renamed by migration keeps its
    history on the roster."""
    if not topics:
        return {}
    slugs: list[str] = []
    for t in topics:
        slugs += [f"standing-write:{t}", f"standing-sweep:{t}"]
        slugs += [f"{p}{t}" for p in _LEGACY_LEDGER_PREFIXES]
    try:
        events = (
            client.table("execution_events")
            .select("slug, status, created_at, error_reason")
            .eq("user_id", user_id)
            .in_("slug", slugs)
            .order("created_at", desc=True)
            .limit(4 * len(topics) + 20)
            .execute()
        ).data or []
    except Exception as e:  # noqa: BLE001 — the roster never fails on its ledger read
        logger.warning("[STANDING] last-run read failed: %s", e)
        return {}
    out: dict[str, LastRun] = {}
    for e in events:
        slug = e.get("slug") or ""
        topic = slug.split(":", 1)[1] if ":" in slug else ""
        if not topic or topic in out:
            continue
        out[topic] = LastRun(
            status=e.get("status") or "unknown",
            error_reason=e.get("error_reason"),
            at=e.get("created_at"),
        )
    return out


def _summarize(client, user_id: str, decl, index_row: Optional[dict],
               last_run: Optional[LastRun]) -> StandingSummary:
    from services.standing_work import _read_file

    target_head = (
        _read_file(client, user_id, decl.target_path) if decl.target else None
    )
    return StandingSummary(
        topic=decl.topic,
        declaration_path=decl.declaration_path,
        target=decl.target,
        target_path=decl.target_path if (decl.target and target_head is not None) else None,
        format=decl.format,
        app=decl.app,
        schedule=decl.schedule,
        paused=decl.paused,
        sources=[
            StandingSource(
                id=str(s.get("id")),
                url=(str(s["url"]) if s.get("url") else None),
                connector=(str(s["connector"]) if s.get("connector") else None),
                selector=(str(s["selector"]) if s.get("selector") else None),
            )
            for s in decl.sources
            if isinstance(s, dict) and s.get("id")
            and (s.get("url") or (s.get("connector") and s.get("selector")))
        ],
        last_run_at=(index_row or {}).get("last_run_at"),
        next_run_at=(index_row or {}).get("next_run_at"),
        problem=decl.problem,
        last_run=last_run,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/standing")
async def list_standing(auth: UserClient) -> list[StandingSummary]:
    """What stands in the acting workspace, with each declaration's last run."""
    from services.standing_work import discover_standing

    actor = _acting_owner(auth)
    decls = sorted(
        discover_standing(auth.client, workspace_id=_acting_workspace(auth)).get(actor, []),
        key=lambda d: d.topic,
    )
    by_slug = _index_rows(auth.client, actor)
    last = _last_runs(auth.client, actor, [d.topic for d in decls])
    return [
        _summarize(auth.client, actor, d, by_slug.get(d.slug), last.get(d.topic))
        for d in decls
    ]


@router.patch("/standing/{topic:path}")
async def update_standing(topic: str, request: UpdateStandingRequest, auth: UserClient) -> StandingSummary:
    """The direct switch only: Pause / Resume. Everything else is the
    conversation's."""
    actor = _acting_owner(auth)
    topic = _validate_topic(topic)
    content = _read_declaration(auth.client, actor, topic)
    if content is None:
        raise HTTPException(status_code=404, detail=f"no standing declaration in '{topic}'")

    try:
        parsed = _yaml.safe_load(_strip_frontmatter(content)) or {}
    except _yaml.YAMLError:
        raise HTTPException(status_code=422, detail="existing declaration unparseable — repair it in the conversation")
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail="existing declaration unparseable — repair it in the conversation")

    if request.paused is not None:
        parsed["paused"] = request.paused

    # fire_on_activation is consume-on-first-update (the radar lesson: a
    # re-emitted create-time flag kept a never-run declaration permanently
    # armed through every pause/resume).
    new_content = compose_standing_yaml(
        target=str(parsed.get("target") or ""),
        app=(str(parsed.get("app")).strip() if parsed.get("app") else None),
        schedule=parsed.get("schedule"),
        paused=bool(parsed.get("paused", False)),
        sources=[s for s in (parsed.get("sources") or []) if isinstance(s, dict)],
        shape=parsed.get("shape") if isinstance(parsed.get("shape"), dict) else None,
    )

    from services.authored_substrate import write_revision
    write_revision(
        auth.client,
        user_id=actor,
        path=_decl_path(topic),
        content=new_content,
        authored_by="operator",
        message=f"{'pause' if parsed.get('paused') else 'resume'} standing work in '{topic}'",
        workspace_id=getattr(auth, "workspace_id", None),
    )
    await _materialize(auth.client, actor)

    decl = _parse_or_none(new_content, topic, actor)
    if decl is None:  # cannot happen for content we just composed — fail loud
        raise HTTPException(status_code=500, detail="recomposed declaration unparseable")
    return _summarize(
        auth.client, actor, decl, _index_rows(auth.client, actor).get(decl.slug),
        _last_runs(auth.client, actor, [topic]).get(topic),
    )


@router.post("/standing/{topic:path}/run")
async def run_standing_now(topic: str, auth: UserClient) -> dict:
    """Run now — the manual fire. Runs inline and records, exactly one
    scheduled run's body, INCLUDING its claim (ADR-618 D2)."""
    from datetime import datetime, timezone as _tz
    from services.scheduling import claim_run, record_run
    from services.standing_work import (
        STANDING_KIND, read_standing_task_row, run_standing_sweep,
    )

    actor = _acting_owner(auth)
    topic = _validate_topic(topic)
    content = _read_declaration(auth.client, actor, topic)
    if content is None:
        raise HTTPException(status_code=404, detail=f"no standing declaration in '{topic}'")
    decl = _parse_or_none(content, topic, actor)
    if decl is None:
        raise HTTPException(status_code=422, detail="declaration unparseable — repair it first")
    if decl.problem is not None:
        raise HTTPException(status_code=422, detail=f"the declaration cannot run: {decl.problem}")

    # The manual fire takes the SAME CAS CLAIM the scheduled drain takes
    # (ADR-618 D2). Without it, Run-now racing a tick executes the declaration
    # TWICE — two derives, two writes, two charges. Losing the claim is a
    # SUCCESSFUL no-op, not an error: the run IS happening, just not on this
    # caller's thread. A never-indexed declaration (no row yet) stays
    # claimable rather than being read as a lost race.
    _row = read_standing_task_row(auth.client, actor, decl.slug)
    _claimed = claim_run(
        auth.client, actor, decl.slug, STANDING_KIND, (_row or {}).get("next_run_at"),
    )
    if _row is not None and not _claimed:
        return {"success": True, "slug": decl.slug, "no_change": True,
                "detail": "already running — a scheduled run claimed this declaration"}

    result = await run_standing_sweep(auth.client, actor, decl)
    try:
        record_run(auth.client, actor, decl, STANDING_KIND,
                   last_run_at=datetime.now(_tz.utc))
    except Exception as e:  # noqa: BLE001
        logger.warning("[STANDING] manual-run record failed for %s: %s", topic, e)
    return result


def _strip_frontmatter(content: str) -> str:
    m = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    return content[m.end():] if m else content
