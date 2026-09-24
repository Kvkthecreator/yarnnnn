"""Standing work routes — ADR-639 (the kernel lane) · ADR-658 (its surface).

    GET    /standing                 — what stands: every declaration in the
                                       acting workspace, with its last run
    GET    /standing/starts          — the pre-shaped starts (ADR-658 D7):
                                       derived from the connections that
                                       hold a capture binding, never a table
    POST   /standing                 — the door (ADR-658 D4): compose + write
                                       CONTRACT.md and _standing.yaml through
                                       the ONE composer and the ONE write path
    GET    /standing/{topic}         — the detail (ADR-658 D6): the summary,
                                       the instructions, the runs, the minder
    PATCH  /standing/{topic}         — pause / resume, and the composer's own
                                       fields (schedule · sources · shape ·
                                       target), refused by problem name
    DELETE /standing/{topic}         — retire (ADR-658 §6.2): archive the
                                       declaration ONLY; the kept file and its
                                       instructions stay, history intact
    POST   /standing/{topic}/run     — Run now (the manual fire, ADR-618 D2);
                                       for browser work (ADR-666 D4) it opens
                                       the run in the work's own conversation
                                       and the member's page performs it

A RUN IS A ROW (ADR-666 D2). Every run this lane makes is in `runs`; the
roster's last run, the detail's runs and what each one wrote and cost are read
from there — served as `routes.runs.RunOut`, the one shape of a run.
`execution_events` is the cost ledger and nothing here reads it.

Rendered by two mounts of one row (ADR-340 D8): the Notifications "Standing
work" pane (the mirror) and the Supervisor app's `work` band (the composition,
which also holds the starts and the detail). Creation, revision and the
browser's member stamp are `services.standing_door` — the ONE door, called by
these routes and by the lane tool `DeclareWork` (ADR-667 D2), which is how the
Supervisor's conversation sets work up. No route here formats YAML.

Repair states stay LOUD (ADR-569 D3): a declaration that parses but cannot
run carries `problem`; the last run's status rides each row from the ledger,
so a refused write is visible where the roster is.

Auth boundary (ADR-501): everything scopes to the ACTING WORKSPACE'S OWNER
user_id via ``_acting_owner``. Authority (ADR-658 D2): no route here takes or
stores an agent slug — the minder is DERIVED at read time from the target's
app and displayed, never written.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from routes.runs import RunOut, run_out, serve_runs
from services import standing_door as door
from services.standing_door import DoorRefusal
from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


def _http(refusal: DoorRefusal) -> HTTPException:
    """A door refusal, served BY NAME: `{problem, message}` (ADR-658 D4)."""
    return HTTPException(status_code=refusal.status_code,
                         detail={"problem": refusal.problem, "message": refusal.message})


def _validate_topic(topic: str) -> str:
    try:
        return door.validate_topic(topic)
    except DoorRefusal as e:
        raise _http(e) from e

#: How many runs the detail shows (ADR-658 D6). A bound read.
_DETAIL_RUNS = 20

#: A browser run queued this long ago whose turn never began was abandoned
#: (the member closed the page before it started) — Run now starts afresh.
_QUEUED_ABANDONED_S = 600


# ---------------------------------------------------------------------------
# Shapes
# ---------------------------------------------------------------------------


class StandingSource(BaseModel):
    """One declared source — an HTTP pull (`url`), a connector slice
    (`connector` + `selector`, ADR-582 D6 / ADR-594 D4), or a workspace path
    (`path`; a trailing slash is a folder — ADR-659 D4). All three served."""
    #: What a connector slice actually CAPTURES — the binding's own `reads`
    #: statement (services.connectors), surfaced at the declaration door so a
    #: member can see that GitHub reads issue + pull-request activity, not a
    #: commit log, BEFORE a run reports "no landed snapshot" (Part P owed 2).
    #: Derived from the machinery that enacts it; never a parallel copy.
    reads: Optional[str] = None

    id: str
    url: Optional[str] = None
    connector: Optional[str] = None
    selector: Optional[str] = None
    path: Optional[str] = None


class StandingBrowser(BaseModel):
    """ADR-666 D1 — whose browser does this work, on which sites."""

    member: str
    member_name: Optional[str] = None
    sites: list[str] = []


class StandingMinder(BaseModel):
    """Who is minding this piece of work — DERIVED (ADR-658 D2), never stored.
    `target's type → its app → that app's standing executor` at read time.
    None for a structured target, which runs mechanically and has no minder."""

    slug: str
    name: str


class UpdateStandingRequest(BaseModel):
    """The direct switch (`paused`) plus the composer's own fields (ADR-658
    D6). Every field is one `compose_standing_yaml` already takes; a request
    cannot reach a key the parser does not name."""

    paused: Optional[bool] = None
    schedule: Optional[Any] = None
    sources: Optional[list[dict]] = None
    shape: Optional[dict] = None
    target: Optional[str] = None
    #: ADR-666 D1 — browser work's sites. Its member never changes here.
    browser_sites: Optional[list[str]] = None


class CreateStandingRequest(BaseModel):
    """The door (ADR-658 D4). `folder` is the topic — an existing or new
    meaning-folder; `target` the designated leaf, one segment, md/csv/json/txt;
    `contract` the instructions prose (load-bearing — refused when blank)."""

    folder: str
    target: str
    schedule: Any
    contract: str
    app: Optional[str] = None
    sources: list[dict] = []
    shape: Optional[dict] = None
    #: ADR-666 D1 — present = browser work on these sites, in the SIGNED-IN
    #: member's browser (the door stamps who; a client never names a member).
    browser_sites: Optional[list[str]] = None


class StandingSummary(BaseModel):
    topic: str
    declaration_path: str
    target: str = ""
    target_path: Optional[str] = None
    format: Optional[str] = None
    #: The app whose executor runs a prose declaration — explicit or derived
    #: (ADR-639 D3). None for a structured target (mechanical).
    app: Optional[str] = None
    #: Who minds it — derived from `app` (ADR-658 D2). Never a stored field.
    minder: Optional[StandingMinder] = None
    schedule: Optional[Any] = None
    #: The clock `schedule` is read in — the ACTING WORKSPACE's declared
    #: timezone (`workspaces.timezone`, migration 247), "UTC" when none is
    #: declared. Served because a bare cron does not say which clock it means:
    #: `0 13 * * *` in an Asia/Seoul workspace fires at 04:00 UTC, and the pane
    #: rendered the raw string beside a browser-local "next" — two times, one
    #: of them nobody's.
    timezone: str = "UTC"
    paused: bool = False
    sources: list[StandingSource] = []
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    #: Parseable-but-cannot-run (missing_target | invalid_target |
    #: unsupported_format | sources_invalid | app_invalid | source_cycle |
    #: browser_invalid) — served, never swallowed (ADR-569 D3).
    problem: Optional[str] = None
    #: ADR-666 — the newest ENDED run, and the run going or waiting now.
    last_run: Optional[RunOut] = None
    live_run: Optional[RunOut] = None
    #: ADR-666 D1 — present for browser work.
    browser: Optional[StandingBrowser] = None


class StandingDetail(BaseModel):
    """The detail (ADR-658 D6): the summary, the instructions as text, the
    recent runs (ADR-666 — from `runs`, each carrying what it wrote). Browser
    work also serves its conversation, where a run is started and watched."""

    summary: StandingSummary
    contract_path: str
    contract: Optional[str] = None
    runs: list[RunOut] = []
    lane_id: Optional[str] = None


class StandingStart(BaseModel):
    """A pre-shaped start (ADR-658 D7): a verb bound to a connection the
    member already holds, DERIVED from the capture bindings — or the HTTP
    start, always offered. The door opens pre-filled from one."""

    kind: str  # "connector" | "browser" | "path" | "url"
    connector: Optional[str] = None
    name: str
    #: The binding's own statement of what a slice reads (connector starts).
    reads: Optional[str] = None
    #: The selectors chosen at the connection's aperture — what a source may name.
    selectors: list[str] = []
    title: str
    suggested_folder: str
    suggested_target: str
    suggested_schedule: str
    contract_seed: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _index_rows(client, user_id: str) -> dict[str, dict]:
    from services.standing_work import STANDING_KIND

    rows = (
        client.table("tasks").select("slug, last_run_at, next_run_at")
        .eq("user_id", user_id).eq("kind", STANDING_KIND).execute()
    ).data or []
    return {r["slug"]: r for r in rows}


def _runs_by_topic(auth, topics: list[str]) -> dict[str, tuple[Optional[dict], Optional[dict]]]:
    """ADR-666 — per topic, `(newest ended run, live run)`, in one read. Never
    raises: an unreadable ledger is a roster without runs, not a broken one."""
    from services.runs import ENDED_STATES, list_runs

    ws = door.acting_workspace(auth)
    if not ws or not topics:
        return {}
    rows = list_runs(auth.client, ws, topics=topics, limit=6 * len(topics) + 20)
    out: dict[str, list] = {}
    for r in rows:  # newest first
        pair = out.setdefault(r.get("topic") or "", [None, None])
        if r.get("state") in ENDED_STATES:
            pair[0] = pair[0] or r
        else:
            pair[1] = pair[1] or r
    return {t: (p[0], p[1]) for t, p in out.items()}


def _connector_reads(platform: Optional[str]) -> Optional[str]:
    """The capture binding's own statement of what it reads, for a connector
    source — or None for an HTTP source / an unbound platform."""
    if not platform:
        return None
    from services.connectors import CONNECTOR_CAPTURE_BINDINGS

    binding = CONNECTOR_CAPTURE_BINDINGS.get(str(platform).strip().lower())
    return (binding or {}).get("reads")


def _minder(app: Optional[str]) -> Optional[StandingMinder]:
    """ADR-658 D2 — the derivation, displayed. `app → standing_executor_for_app
    → the register's name`. None when there is no app (a structured target)
    or the app names no executor. Reads the register; writes nothing."""
    if not app:
        return None
    try:
        import services.apps  # noqa: F401  (registration side-effect — ADR-562)
        from services.agents_registry import get_agent
        from services.authoring import standing_executor_for_app

        slug = standing_executor_for_app(app)
        row = get_agent(slug) if slug else None
        if not slug or row is None:
            return None
        return StandingMinder(slug=slug, name=str(row.get("name") or slug))
    except Exception as e:  # noqa: BLE001 — a display derivation never fails the roster
        logger.warning("[STANDING] minder derivation failed for app %r: %s", app, e)
        return None


def _browser_out(decl, names: dict[str, str]) -> Optional[StandingBrowser]:
    if decl.browser is None:
        return None
    member = str(decl.browser.get("member") or "")
    return StandingBrowser(member=member, member_name=names.get(member),
                           sites=list(decl.browser.get("sites") or []))


def _member_names(decls) -> dict[str, str]:
    from services.principal_display import resolve_member_names
    from services.supabase import get_service_client

    ids = [str(d.browser.get("member") or "") for d in decls if d.browser]
    return resolve_member_names(get_service_client(), ids) if ids else {}


def _summarize(auth, client, user_id: str, decl, index_row: Optional[dict],
               runs_pair: tuple[Optional[dict], Optional[dict]],
               tz: Optional[str] = None,
               names: Optional[dict[str, str]] = None) -> StandingSummary:
    from services.standing_work import _read_file

    # The workspace clock the cadence is read in. Resolved by the caller for a
    # roster (one query for the whole list); resolved here for a single row.
    if tz is None:
        from services.schedule_utils import get_workspace_timezone
        tz = get_workspace_timezone(client, user_id)

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
        minder=_minder(decl.app),
        schedule=decl.schedule,
        paused=decl.paused,
        sources=[
            StandingSource(
                id=str(s.get("id")),
                url=(str(s["url"]) if s.get("url") else None),
                connector=(str(s["connector"]) if s.get("connector") else None),
                selector=(str(s["selector"]) if s.get("selector") else None),
                path=(str(s["path"]) if s.get("path") else None),
                reads=_connector_reads(s.get("connector")),
            )
            for s in decl.sources
            if isinstance(s, dict) and s.get("id")
            and (s.get("url") or s.get("path")
                 or (s.get("connector") and s.get("selector")))
        ],
        timezone=tz,
        last_run_at=(index_row or {}).get("last_run_at"),
        next_run_at=(index_row or {}).get("next_run_at"),
        problem=decl.problem,
        last_run=run_out(auth, runs_pair[0]),
        live_run=run_out(auth, runs_pair[1]),
        browser=_browser_out(decl, names if names is not None else _member_names([decl])),
    )


def _summary_for(auth, user_id: str, decl) -> StandingSummary:
    return _summarize(
        auth, auth.client, user_id, decl, _index_rows(auth.client, user_id).get(decl.slug),
        _runs_by_topic(auth, [decl.topic]).get(decl.topic, (None, None)),
    )


# ---------------------------------------------------------------------------
# The starts (ADR-658 D7) — derived from reach, never a table
# ---------------------------------------------------------------------------

#: The verb each capture binding's slice naturally supports, in the member's
#: words. Keyed by the binding's platform; a platform with no binding has no
#: start here by construction (the D7 rule: the kernel must be able to read
#: the source the start names).
_CONNECTOR_STARTS: dict[str, dict[str, str]] = {
    "slack": {
        "title": "Keep a brief of your Slack channels current",
        "folder": "team-brief",
        "target": "brief.md",
        "schedule": "0 9 * * 1-5",
        "contract": (
            "A short brief of what moved in the chosen Slack channels since the "
            "last update: decisions made, questions asked, and anything waiting "
            "on someone. Plain sentences, dated, newest first. Leave out chatter."
        ),
    },
    "notion": {
        "title": "Keep a summary of your Notion pages current",
        "folder": "notion-summary",
        "target": "summary.md",
        "schedule": "0 9 * * 1",
        "contract": (
            "A summary of the chosen Notion pages as they stand today: what each "
            "page is for and what changed since the last update. One section per "
            "page, plain sentences, no copied blocks."
        ),
    },
    "github": {
        "title": "Keep a changelog of your repositories current",
        "folder": "changelog",
        "target": "changelog.md",
        "schedule": "0 9 * * 1",
        "contract": (
            "A changelog of the chosen repositories: issues opened and closed and "
            "pull requests merged since the last update, grouped by repository, "
            "newest first. Name the change, not the commit."
        ),
    },
}

_URL_START = StandingStart(
    kind="url",
    connector=None,
    name="A web page",
    reads=None,
    selectors=[],
    title="Keep a page's summary current",
    suggested_folder="watch",
    suggested_target="summary.md",
    suggested_schedule="0 9 * * *",
    contract_seed=(
        "A summary of what the page says today and what changed since the last "
        "update. Plain sentences, dated, newest first."
    ),
)


_WORKSPACE_START = StandingStart(
    kind="path",
    connector=None,
    name="Something in your workspace",
    reads="A file, or a folder — Downloads, a project, another kept file.",
    selectors=[],
    title="Keep a summary of a folder current",
    suggested_folder="overview",
    suggested_target="overview.md",
    suggested_schedule="0 9 * * *",
    contract_seed=(
        "An overview of what is in the folder: what each file is, what changed "
        "since the last update, and what looks unfinished. Plain sentences, "
        "newest first, each point naming the file it came from."
    ),
)


#: ADR-666 D1 — browser work: always offered, like the workspace start. The
#: browser is the member's own reach (ADR-664 D3: absent, it is still named);
#: whether this page can perform it is the extension's to answer, at Run now.
_BROWSER_START = StandingStart(
    kind="browser",
    connector=None,
    name="Your browser",
    reads="Websites you name, in your own browser, with your sign-ins.",
    selectors=[],
    title="Do something on websites",
    suggested_folder="web-work",
    suggested_target="results.md",
    suggested_schedule="0 9 * * 1",
    contract_seed=(
        "Open each site, find what's needed, and keep the file up to date. Say "
        "which site needs me to sign in if one does."
    ),
)


def standing_starts(client, user_id: str) -> list[StandingStart]:
    """The pre-shaped starts for this workspace (ADR-658 D7), DERIVED:
    connections that are active AND hold a capture binding, each carrying the
    binding's `reads` sentence and the selectors chosen at its aperture. The
    HTTP start is always last. Never raises — an unreadable connection row
    yields no start, not a broken door."""
    from services.connectors import (
        CONNECTOR_CAPTURE_BINDINGS, connection_row, platform_display_name,
        selected_ids_from_row,
    )

    out: list[StandingStart] = []
    for plat, binding in CONNECTOR_CAPTURE_BINDINGS.items():
        shape = _CONNECTOR_STARTS.get(plat)
        if shape is None:
            continue
        row = connection_row(client, user_id, plat)
        if row is None or (row.get("status") or "active") != "active":
            continue
        out.append(StandingStart(
            kind="connector",
            connector=plat,
            name=platform_display_name(plat),
            reads=binding.get("reads"),
            selectors=selected_ids_from_row(row),
            title=shape["title"],
            suggested_folder=shape["folder"],
            suggested_target=shape["target"],
            suggested_schedule=shape["schedule"],
            contract_seed=shape["contract"],
        ))
    # Always offered, connection or none (ADR-659 D7 · ADR-666 D1): the
    # member's browser and the workspace are reach every member already has.
    out.append(_BROWSER_START)
    out.append(_WORKSPACE_START)
    out.append(_URL_START)
    return out


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/standing")
async def list_standing(auth: UserClient) -> list[StandingSummary]:
    """What stands in the acting workspace, with each declaration's last run."""
    from services.standing_work import discover_standing

    actor = door.acting_owner(auth)
    decls = sorted(
        discover_standing(auth.client, workspace_id=door.acting_workspace(auth)).get(actor, []),
        key=lambda d: d.topic,
    )
    by_slug = _index_rows(auth.client, actor)
    runs = _runs_by_topic(auth, [d.topic for d in decls])
    names = _member_names(decls)
    # One clock for the whole roster — it is the WORKSPACE's, not per-row.
    from services.schedule_utils import get_workspace_timezone
    tz = get_workspace_timezone(auth.client, actor)
    return [
        _summarize(auth, auth.client, actor, d, by_slug.get(d.slug),
                   runs.get(d.topic, (None, None)), tz, names)
        for d in decls
    ]


# Declared BEFORE `/standing/{topic:path}` — a path parameter would otherwise
# swallow the literal segment and answer 404 for a topic named "starts".
@router.get("/standing/starts")
async def list_standing_starts(auth: UserClient) -> list[StandingStart]:
    """The pre-shaped starts (ADR-658 D7), derived from what the workspace's
    owner has connected — the connections a run will actually reach through."""
    return standing_starts(auth.client, door.acting_owner(auth))


@router.post("/standing", status_code=201)
async def create_standing(request: CreateStandingRequest, auth: UserClient) -> StandingSummary:
    """The door (ADR-658 D4) — `services.standing_door.declare`, the one door
    a conversation's `DeclareWork` also calls (ADR-667 D2). Refuses BY NAME."""
    try:
        decl = await door.declare(
            auth, folder=request.folder, target=request.target, schedule=request.schedule,
            contract=request.contract, app=request.app, sources=request.sources,
            shape=request.shape, browser_sites=request.browser_sites,
        )
    except DoorRefusal as e:
        raise _http(e) from e
    return _summary_for(auth, door.acting_owner(auth), decl)


@router.get("/standing/{topic:path}")
async def get_standing(topic: str, auth: UserClient) -> StandingDetail:
    """The detail (ADR-658 D6): the summary, the instructions, the runs."""
    from services.standing_work import _read_file

    actor = door.acting_owner(auth)
    topic = _validate_topic(topic)
    content = door.read_declaration(auth.client, actor, topic)
    if content is None:
        raise HTTPException(status_code=404, detail=f"no standing declaration in '{topic}'")
    decl = door.parse(content, topic, actor)
    if decl is None:
        raise HTTPException(status_code=422, detail="declaration unparseable — repair it first")
    from services.runs import list_runs

    ws = door.acting_workspace(auth)
    return StandingDetail(
        summary=_summary_for(auth, actor, decl),
        contract_path=decl.contract_path,
        contract=_read_file(auth.client, actor, decl.contract_path),
        runs=serve_runs(auth, list_runs(auth.client, ws, topic=topic, limit=_DETAIL_RUNS) if ws else []),
        lane_id=(_find_work_lane(auth, decl) if decl.browser is not None else None),
    )


@router.patch("/standing/{topic:path}")
async def update_standing(topic: str, request: UpdateStandingRequest, auth: UserClient) -> StandingSummary:
    """Pause / Resume, and the composer's own fields (ADR-658 D6) —
    `services.standing_door.revise`. A change that would leave the declaration
    unable to run is refused BY NAME and writes nothing; the pause switch
    alone is never refused."""
    try:
        decl = await door.revise(
            auth, topic, paused=request.paused, schedule=request.schedule,
            sources=request.sources, shape=request.shape, target=request.target,
            browser_sites=request.browser_sites,
        )
    except DoorRefusal as e:
        raise _http(e) from e
    return _summary_for(auth, door.acting_owner(auth), decl)


@router.delete("/standing/{topic:path}")
async def retire_standing(topic: str, auth: UserClient) -> dict:
    """Retire (ADR-658 §6.2): the declaration goes to Trash — the ONE delete,
    attributed, restorable in one act. The kept file and its instructions are
    NOT touched: retiring stops a file being kept current, it does not destroy
    what was made. The index drops the row now."""
    actor = door.acting_owner(auth)
    topic = _validate_topic(topic)
    content = door.read_declaration(auth.client, actor, topic)
    if content is None:
        raise HTTPException(status_code=404, detail=f"no standing declaration in '{topic}'")
    decl = door.parse(content, topic, actor)
    decl_path = door.decl_path(topic)
    try:
        door.write_access(auth, decl_path)
    except DoorRefusal as e:
        raise _http(e) from e

    from services.authored_substrate import archive_live_file
    tombstone = archive_live_file(
        auth.client,
        user_id=actor,
        path=decl_path,
        authored_by="operator",
        author_identity_uuid=auth.user_id,
        message=f"retire standing work in '{topic}' — the file and its instructions stay",
        workspace_id=getattr(auth, "workspace_id", None),
    )
    if tombstone is None:
        raise HTTPException(status_code=404, detail=f"no standing declaration in '{topic}'")
    await door.materialize(auth.client, actor)
    kept = [door.contract_path(topic)]
    if decl is not None and decl.target:
        kept.insert(0, decl.target_path)
    return {
        "success": True,
        "topic": topic,
        "archived_path": decl_path,
        "tombstone_revision_id": tombstone,
        "kept": kept,
    }


@router.post("/standing/{topic:path}/run")
async def run_standing_now(topic: str, auth: UserClient) -> dict:
    """Run now — the manual fire. Runs inline and records, exactly one
    scheduled run's body, INCLUDING its claim (ADR-618 D2)."""
    from datetime import datetime, timezone as _tz
    from services.scheduling import claim_run, record_run
    from services.standing_work import STANDING_KIND, run_standing_sweep

    actor = door.acting_owner(auth)
    topic = _validate_topic(topic)
    content = door.read_declaration(auth.client, actor, topic)
    if content is None:
        raise HTTPException(status_code=404, detail=f"no standing declaration in '{topic}'")
    decl = door.parse(content, topic, actor)
    if decl is None:
        raise HTTPException(status_code=422, detail="declaration unparseable — repair it first")
    if decl.problem is not None:
        raise HTTPException(status_code=422, detail=f"the declaration cannot run: {decl.problem}")
    if decl.browser is not None:
        return await _start_browser_run(auth, actor, decl)

    # The manual fire takes the SAME LOCK the scheduled drain takes (ADR-618 D2,
    # ADR-659 D1). Without it, Run-now racing a tick executes the declaration
    # TWICE — two derives, two writes, two charges (driven with money on it,
    # ADR-658 A1.8). Losing the claim is a SUCCESSFUL no-op, not an error: the
    # run IS happening, just not on this caller's thread.
    #
    # Materialize FIRST: a declaration written since the last tick has no index
    # row, and "no row" must never mean "free to run unclaimed" — the tick could
    # index and claim it a second later.
    await door.materialize(auth.client, actor)
    if not claim_run(auth.client, actor, decl.slug, STANDING_KIND):
        # `already`, not `no_change`: the run IS happening and may well change
        # the file — reported as "nothing changed" it contradicted the run card
        # beneath it (driven 2026-09-24, ADR-666 click-pass).
        return {"success": True, "slug": decl.slug, "already": True,
                "detail": "already running — another run holds this declaration"}

    # The member ASKED, so the pace rule does not apply (ADR-659 D6). The record
    # is in a `finally`, as in the drain: it releases the hold, and a run that
    # raised must not strand its own declaration behind it.
    try:
        return await run_standing_sweep(auth.client, actor, decl, force=True)
    finally:
        try:
            record_run(auth.client, actor, decl, STANDING_KIND,
                       last_run_at=datetime.now(_tz.utc))
        except Exception as e:  # noqa: BLE001
            logger.warning("[STANDING] manual-run record failed for %s: %s", topic, e)


def _find_work_lane(auth, decl) -> Optional[str]:
    """The work's own conversation (ADR-666 D4): the member's active lane bound
    to the kept file under its app — the ADR-653 R3 binding, keyed `(app, path)`
    the way every app keys a file's conversation. A conversation is the
    MEMBER's (ADR-411), so the lookup lives with the lanes, member-keyed."""
    from routes.lanes import find_bound_lane

    return find_bound_lane(auth, app=decl.app, artifact_path=decl.target_path)


async def _work_lane(auth, decl) -> str:
    """Find or create the work's conversation. Created through the ONE lane
    door (`routes.lanes.create_lane`), so the resident and the engine resolve
    exactly as they do for any app's conversation about a file."""
    found = _find_work_lane(auth, decl)
    if found:
        return found
    from routes.lanes import CreateLaneRequest, create_lane

    created = await create_lane(
        CreateLaneRequest(app=decl.app, artifact_path=decl.target_path, name=decl.topic), auth,
    )
    return str(created["id"])


async def _start_browser_run(auth, actor: str, decl) -> dict:
    """Run now on browser work (ADR-666 D4). Only its own member may — it is
    their browser. The run's opening message is written into the work's
    conversation as THEIR ask; their page then streams the turn and performs
    the acts (`POST /lanes/{id}/regenerate` with the run). A run already going
    is returned, never doubled."""
    from datetime import datetime, timezone as _tz

    from services import runs
    from services.narrative import write_narrative_entry
    from services.standing_work import _read_file, browser_run_ask

    if decl.browser.get("member") != auth.user_id:
        raise _http(DoorRefusal("browser_not_yours", status_code=403))

    live = runs.live_for_topic(auth.client, decl.workspace_id or door.acting_workspace(auth), decl.topic)
    if live and live.get("state") in ("queued", "running"):
        try:
            age = (datetime.now(_tz.utc) - datetime.fromisoformat(
                str(live.get("updated_at")).replace("Z", "+00:00"))).total_seconds()
        except (TypeError, ValueError):
            age = 0
        if live.get("state") == "running" or age < _QUEUED_ABANDONED_S:
            return {"success": True, "browser": True, "already": True,
                    "run_id": live["id"], "lane_id": live.get("lane_id")}
        runs.finish_run(live["id"], state="failed", outcome="not_started")

    lane_id = await _work_lane(auth, decl)
    run_id = runs.start_browser_run(decl, lane_id=lane_id)
    if not run_id:
        raise HTTPException(status_code=500, detail="The run could not be recorded — try again.")
    write_narrative_entry(
        auth.client, lane_id,
        role="user",
        summary=browser_run_ask(decl, _read_file(auth.client, actor, decl.contract_path)),
        pulse="addressed",
        authored_by=f"member:{auth.user_id}",
        extra_metadata={"author_principal_id": auth.user_id, "run_id": run_id},
    )
    return {"success": True, "browser": True, "run_id": run_id, "lane_id": lane_id}


