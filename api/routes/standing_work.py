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
    POST   /standing/{topic}/run     — Run now (the manual fire, ADR-618 D2)

Rendered by two mounts of one row (ADR-340 D8): the Notifications "Standing
work" pane (the mirror) and the Supervisor app's `work` band (the composition,
which also holds the door, the starts and the detail). Creation is ALSO
conversational (ADR-569 D7): a colleague authors the two files through any
lane under `declaring-standing-work`; both paths emit what the one parser
accepts, and the ADR-658 gate holds them to it.

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

#: How many ledger rows the detail shows (ADR-658 D6). A bound read.
_DETAIL_RUNS = 20


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
    if segments[0] == "system":
        # The kernel mirror is never a member's meaning-folder (the skill's
        # own anti-pattern: "declaring a file that lives under system/").
        raise HTTPException(status_code=422, detail="standing work cannot live under system/")
    return "/".join(segments)


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


class LastRun(BaseModel):
    """The newest ledger row for this declaration — what the pane says about
    the last run, read from `execution_events` at request time."""

    status: str
    error_reason: Optional[str] = None
    at: Optional[str] = None


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
    #: unsupported_format | sources_invalid | app_invalid | source_cycle) — served, never
    #: swallowed (ADR-569 D3).
    problem: Optional[str] = None
    last_run: Optional[LastRun] = None


class StandingRun(BaseModel):
    """One ledger row of this declaration (ADR-658 D6) — the step (`sweep`
    fetches, `write` revises), its outcome, when."""

    step: str
    status: str
    error_reason: Optional[str] = None
    at: Optional[str] = None
    cost_usd: Optional[float] = None
    #: ADR-659 D2 — what this run WROTE: the `system:standing` revision of the
    #: kept file a successful write produced, and what it was made from.
    #: DERIVED at read time from the revision chain; the cost ledger stores no
    #: pointer. None on every row that wrote nothing.
    revision_id: Optional[str] = None
    derived_from: list[str] = []


class StandingDetail(BaseModel):
    """The detail (ADR-658 D6): the summary, the instructions as text, the
    recent runs. Bounded to the declaration's own facts — the strings pane's
    parties/consumers/head-facts chrome (ADR-639 D4) is not rebuilt here."""

    summary: StandingSummary
    contract_path: str
    contract: Optional[str] = None
    runs: list[StandingRun] = []


class StandingStart(BaseModel):
    """A pre-shaped start (ADR-658 D7): a verb bound to a connection the
    member already holds, DERIVED from the capture bindings — or the HTTP
    start, always offered. The door opens pre-filled from one."""

    kind: str  # "connector" | "path" | "url"
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


def _decl_path(topic: str) -> str:
    from services.standing_work import DECLARATION_LEAF

    return f"/workspace/{topic}/{DECLARATION_LEAF}"


def _contract_path(topic: str) -> str:
    from services.standing_work import CONTRACT_LEAF

    return f"/workspace/{topic}/{CONTRACT_LEAF}"


def _acting_workspace(auth) -> Optional[str]:
    from services.workspace_context import effective_workspace_id
    return effective_workspace_id(auth.user_id, getattr(auth, "workspace_id", None))


def _acting_owner(auth) -> str:
    from services.workspace_context import acting_workspace_owner
    return acting_workspace_owner(
        auth.client, auth.user_id, getattr(auth, "workspace_id", None)
    )


def _read_declaration(client, user_id: str, topic: str) -> Optional[str]:
    """The LIVE declaration's body, or None. Not-in-Trash by construction —
    the same predicate discovery owes (2026-09-07): a retired declaration
    must read as absent here, or Run now would fire what the roster hides."""
    from services.workspace_context import live_files_filter

    rows = (
        live_files_filter(
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", _decl_path(topic))
        )
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
    Deterministic, machine-class (ADR-254): comment header + safe_dump.

    THE ONE COMPOSER (ADR-658 D4). The door, the switch and the widened PATCH
    all emit through here; a second formatter is the drift `DECLARATION_KEYS`
    was created to end."""
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
    from services.workspace_context import effective_workspace_id
    return parse_standing_yaml(
        content, topic=topic, declaration_path=_decl_path(topic), user_id=user_id,
        workspace_id=effective_workspace_id(user_id),
    )


def _guard_sources(auth, user_id: str, decl) -> None:
    """The two source rules only the DOOR can ask (ADR-659 D4 rule 6, D5).

    `source_unreadable` — a run reads with the OWNER's reach, so a source the
    DECLARER cannot read would launder it into a file they can. Asked of the
    ONE matcher the ReadFile gate uses.

    `source_cycle` — a loop is a property of the workspace's declarations
    TOGETHER, which the one-file parse cannot see: the candidate is set among
    the live ones and the same marker discovery uses decides.
    """
    from services.primitives.workspace import _is_path_readable_for_principal
    from services.standing_work import discover_standing, mark_source_cycles

    for rel, is_folder in decl.path_sources():
        if not _is_path_readable_for_principal(auth, rel + ("/" if is_folder else "")):
            raise _refuse("source_unreadable")

    if not decl.path_sources():
        return
    others = [
        d for d in discover_standing(
            auth.client, workspace_id=decl.workspace_id
        ).get(user_id, [])
        if d.slug != decl.slug
    ]
    mark_source_cycles(others + [decl])
    if decl.problem is not None:
        raise _refuse(decl.problem)


async def _materialize(client, user_id: str) -> None:
    """Immediate index sync post-write — a switched declaration re-arms now,
    not at the next global discovery; a retired one drops its row now."""
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


def _ledger_slugs(topic: str) -> list[str]:
    return (
        [f"standing-write:{topic}", f"standing-sweep:{topic}"]
        + [f"{p}{topic}" for p in _LEGACY_LEDGER_PREFIXES]
    )


def _last_runs(client, user_id: str, topics: list[str]) -> dict[str, LastRun]:
    """The newest ledger row per topic — one query, the write step preferred
    over the sweep step when both exist (the write is the outcome). Reads the
    pre-ADR-639 slugs too, so a declaration renamed by migration keeps its
    history on the roster."""
    if not topics:
        return {}
    slugs: list[str] = []
    for t in topics:
        slugs += _ledger_slugs(t)
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


#: A successful write row is recorded moments AFTER the revision it wrote
#: (the embed sits between them). The join's window, generous on one side only.
_RUN_REVISION_WINDOW_S = 180


def _written_revisions(client, user_id: str, target_path: Optional[str]) -> list[dict]:
    """The kept file's `system:standing` revisions, newest first — each IS one
    successful run's product. Never raises."""
    if not target_path:
        return []
    try:
        from services.authored_substrate import list_revisions

        revs = list_revisions(client, user_id=user_id, path=target_path, limit=40)
    except Exception as e:  # noqa: BLE001
        logger.warning("[STANDING] revisions read failed for %s: %s", target_path, e)
        return []
    return [r for r in revs
            if str(r.get("authored_by") or "") in ("system:standing", "system:strings")]


def _join_revision(run_at: Optional[str], revisions: list[dict]) -> Optional[dict]:
    """The revision a successful write row produced (ADR-659 D2): the newest
    standing revision at or just before the row. Pure."""
    from datetime import datetime as _dt

    def _ts(v):
        try:
            return _dt.fromisoformat(str(v).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None

    at = _ts(run_at)
    if at is None:
        return None
    for rev in revisions:  # newest first
        made = _ts(rev.get("created_at"))
        if made is None:
            continue
        gap = (at - made).total_seconds()
        if -5 <= gap <= _RUN_REVISION_WINDOW_S:
            return rev
    return None


def _recent_runs(client, user_id: str, topic: str, limit: int = _DETAIL_RUNS,
                 *, target_path: Optional[str] = None) -> list[StandingRun]:
    """The detail's ledger read (ADR-658 D6): this topic's rows, newest first,
    each successful write joined to the revision it produced (ADR-659 D2).
    Never fails the detail — an unreadable ledger is an empty list."""
    try:
        events = (
            client.table("execution_events")
            .select("slug, status, created_at, error_reason, cost_usd")
            .eq("user_id", user_id)
            .in_("slug", _ledger_slugs(topic))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        ).data or []
    except Exception as e:  # noqa: BLE001
        logger.warning("[STANDING] runs read failed for %s: %s", topic, e)
        return []
    revisions = _written_revisions(client, user_id, target_path)
    out: list[StandingRun] = []
    for e in events:
        slug = str(e.get("slug") or "")
        head = slug.split(":", 1)[0]
        step = "write" if head.endswith("write") else "sweep"
        cost = e.get("cost_usd")
        wrote = (_join_revision(e.get("created_at"), revisions)
                 if step == "write" and e.get("status") == "success" else None)
        out.append(StandingRun(
            step=step,
            status=e.get("status") or "unknown",
            error_reason=e.get("error_reason"),
            at=e.get("created_at"),
            cost_usd=(float(cost) if cost is not None else None),
            revision_id=(wrote or {}).get("id"),
            derived_from=[str(p) for p in ((wrote or {}).get("derived_from") or [])],
        ))
    return out


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


def _summarize(client, user_id: str, decl, index_row: Optional[dict],
               last_run: Optional[LastRun],
               tz: Optional[str] = None) -> StandingSummary:
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
        last_run=last_run,
    )


def _summary_for(client, user_id: str, decl) -> StandingSummary:
    return _summarize(
        client, user_id, decl, _index_rows(client, user_id).get(decl.slug),
        _last_runs(client, user_id, [decl.topic]).get(decl.topic),
    )


def _refuse(problem: str, status_code: int = 422) -> HTTPException:
    """A refusal BY NAME (ADR-658 D4): the problem token the parser would
    have served rides `detail.problem`, so the door can say which rule
    refused rather than "invalid"."""
    words = {
        "missing_target": "Name the file to keep current.",
        "invalid_target": "The file to keep current must be in this folder, one plain name.",
        "unsupported_format": "Only md, csv, json and txt files can be kept current.",
        "sources_invalid": (
            "Add at least one source. A csv, json or txt file takes exactly one, "
            "and a file rather than a folder."
        ),
        "source_cycle": (
            "That would make a loop: this file would be kept from a file that is "
            "kept from it. Choose a different source."
        ),
        "source_unreadable": "You can't read that part of the workspace, so it can't be a source.",
        "app_invalid": "That app does not exist.",
        "missing_contract": "Write what the file must stay true to.",
        "already_declared": "This folder already has standing work. Open it instead.",
    }
    return HTTPException(
        status_code=status_code,
        detail={"problem": problem, "message": words.get(problem, problem)},
    )


def _write_access(auth, path: str) -> None:
    # ADR-643 D2 — a declaration schedules UNATTENDED spend (ADR-618), which
    # makes it one of the sharper writes in the substrate; the door asks the
    # ONE decider before composing.
    from services.access import resolve_access

    decision = resolve_access(auth, path, "write")
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)


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
    # Always offered, connection or none (ADR-659 D7): the workspace is the one
    # source every member already has.
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

    actor = _acting_owner(auth)
    decls = sorted(
        discover_standing(auth.client, workspace_id=_acting_workspace(auth)).get(actor, []),
        key=lambda d: d.topic,
    )
    by_slug = _index_rows(auth.client, actor)
    last = _last_runs(auth.client, actor, [d.topic for d in decls])
    # One clock for the whole roster — it is the WORKSPACE's, not per-row.
    from services.schedule_utils import get_workspace_timezone
    tz = get_workspace_timezone(auth.client, actor)
    return [
        _summarize(auth.client, actor, d, by_slug.get(d.slug), last.get(d.topic), tz)
        for d in decls
    ]


# Declared BEFORE `/standing/{topic:path}` — a path parameter would otherwise
# swallow the literal segment and answer 404 for a topic named "starts".
@router.get("/standing/starts")
async def list_standing_starts(auth: UserClient) -> list[StandingStart]:
    """The pre-shaped starts (ADR-658 D7), derived from what the workspace's
    owner has connected — the connections a run will actually reach through."""
    return standing_starts(auth.client, _acting_owner(auth))


@router.post("/standing", status_code=201)
async def create_standing(request: CreateStandingRequest, auth: UserClient) -> StandingSummary:
    """The door (ADR-658 D4). Composes through the ONE composer, parses through
    the ONE parser, writes through the ONE write path — and refuses BY NAME.

    Order: the folder is validated; a blank contract is refused (the contract
    is the load-bearing half — without it no run can be judged); a folder
    that already holds a LIVE declaration is refused (one per folder, ADR-569
    D2); the composed YAML is parsed and any problem refuses the write; access
    is asked; then CONTRACT.md and _standing.yaml land as `lifecycle='active'`
    revisions (a retired declaration at this path is REVIVED, never left in
    Trash — ADR-658 A1.6); the index is synced so the roster shows it now.
    """
    actor = _acting_owner(auth)
    topic = _validate_topic(request.folder)
    decl_path = _decl_path(topic)
    contract_path = _contract_path(topic)

    contract = (request.contract or "").strip()
    if not contract:
        raise _refuse("missing_contract")
    if _read_declaration(auth.client, actor, topic) is not None:
        raise _refuse("already_declared", status_code=409)

    sources = [s for s in (request.sources or []) if isinstance(s, dict)]
    app = (str(request.app).strip() if request.app else None) or None
    shape = request.shape if isinstance(request.shape, dict) and request.shape else None
    content = compose_standing_yaml(
        target=(request.target or "").strip(),
        app=app,
        schedule=request.schedule,
        paused=False,
        sources=sources,
        shape=shape,
        # The first run fires on the next tick, not at the first cron boundary
        # (ADR-658 D7): the member sees the file change within minutes.
        fire_on_activation=True,
    )
    decl = _parse_or_none(content, topic, actor)
    if decl is None:  # cannot happen for content we just composed — fail loud
        raise HTTPException(status_code=500, detail="composed declaration unparseable")
    if decl.problem is not None:
        raise _refuse(decl.problem)
    _guard_sources(auth, actor, decl)

    _write_access(auth, decl_path)

    from services.authored_substrate import write_revision
    ws = getattr(auth, "workspace_id", None)
    write_revision(
        auth.client,
        user_id=actor,
        path=contract_path,
        content=contract + "\n",
        authored_by="operator",
        author_identity_uuid=auth.user_id,
        message=f"declare standing work in '{topic}': the instructions",
        workspace_id=ws,
        lifecycle="active",
    )
    write_revision(
        auth.client,
        user_id=actor,
        path=decl_path,
        content=content,
        authored_by="operator",
        author_identity_uuid=auth.user_id,
        message=f"declare standing work in '{topic}': keep '{decl.target}' current",
        workspace_id=ws,
        lifecycle="active",
    )
    await _materialize(auth.client, actor)
    return _summary_for(auth.client, actor, decl)


@router.get("/standing/{topic:path}")
async def get_standing(topic: str, auth: UserClient) -> StandingDetail:
    """The detail (ADR-658 D6): the summary, the instructions, the runs."""
    from services.standing_work import _read_file

    actor = _acting_owner(auth)
    topic = _validate_topic(topic)
    content = _read_declaration(auth.client, actor, topic)
    if content is None:
        raise HTTPException(status_code=404, detail=f"no standing declaration in '{topic}'")
    decl = _parse_or_none(content, topic, actor)
    if decl is None:
        raise HTTPException(status_code=422, detail="declaration unparseable — repair it first")
    return StandingDetail(
        summary=_summary_for(auth.client, actor, decl),
        contract_path=decl.contract_path,
        contract=_read_file(auth.client, actor, decl.contract_path),
        runs=_recent_runs(auth.client, actor, topic, target_path=decl.target_path),
    )


@router.patch("/standing/{topic:path}")
async def update_standing(topic: str, request: UpdateStandingRequest, auth: UserClient) -> StandingSummary:
    """Pause / Resume, and the composer's own fields (ADR-658 D6). A change
    that would leave the declaration unable to run is refused BY NAME and
    writes nothing; the pause switch alone is never refused."""
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
    edited = False
    if request.schedule is not None:
        parsed["schedule"] = request.schedule
        edited = True
    if request.sources is not None:
        parsed["sources"] = [s for s in request.sources if isinstance(s, dict)]
        edited = True
    if request.shape is not None:
        parsed["shape"] = request.shape if request.shape else None
        edited = True
    if request.target is not None:
        parsed["target"] = str(request.target).strip()
        edited = True

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
    decl = _parse_or_none(new_content, topic, actor)
    if decl is None:  # cannot happen for content we just composed — fail loud
        raise HTTPException(status_code=500, detail="recomposed declaration unparseable")
    if edited and decl.problem is not None:
        raise _refuse(decl.problem)
    if edited:
        _guard_sources(auth, actor, decl)

    _write_access(auth, _decl_path(topic))

    from services.authored_substrate import write_revision
    if edited:
        message = f"edit standing work in '{topic}'"
    else:
        message = f"{'pause' if parsed.get('paused') else 'resume'} standing work in '{topic}'"
    write_revision(
        auth.client,
        user_id=actor,
        path=_decl_path(topic),
        content=new_content,
        authored_by="operator",
        author_identity_uuid=auth.user_id,
        message=message,
        workspace_id=getattr(auth, "workspace_id", None),
    )
    await _materialize(auth.client, actor)
    return _summary_for(auth.client, actor, decl)


@router.delete("/standing/{topic:path}")
async def retire_standing(topic: str, auth: UserClient) -> dict:
    """Retire (ADR-658 §6.2): the declaration goes to Trash — the ONE delete,
    attributed, restorable in one act. The kept file and its instructions are
    NOT touched: retiring stops a file being kept current, it does not destroy
    what was made. The index drops the row now."""
    actor = _acting_owner(auth)
    topic = _validate_topic(topic)
    content = _read_declaration(auth.client, actor, topic)
    if content is None:
        raise HTTPException(status_code=404, detail=f"no standing declaration in '{topic}'")
    decl = _parse_or_none(content, topic, actor)
    decl_path = _decl_path(topic)
    _write_access(auth, decl_path)

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
    await _materialize(auth.client, actor)
    kept = [_contract_path(topic)]
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

    # The manual fire takes the SAME LOCK the scheduled drain takes (ADR-618 D2,
    # ADR-659 D1). Without it, Run-now racing a tick executes the declaration
    # TWICE — two derives, two writes, two charges (driven with money on it,
    # ADR-658 A1.8). Losing the claim is a SUCCESSFUL no-op, not an error: the
    # run IS happening, just not on this caller's thread.
    #
    # Materialize FIRST: a declaration written since the last tick has no index
    # row, and "no row" must never mean "free to run unclaimed" — the tick could
    # index and claim it a second later.
    await _materialize(auth.client, actor)
    if not claim_run(auth.client, actor, decl.slug, STANDING_KIND):
        return {"success": True, "slug": decl.slug, "no_change": True,
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


def _strip_frontmatter(content: str) -> str:
    m = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    return content[m.end():] if m else content
