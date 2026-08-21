"""Strings routes — ADR-569 (the maintained file, kept by Keeper).

The composed view is a LAZY PROJECTION over the string's folder + the ledgers
(the radar R2 pattern, ADR-486 D5 — derived-never-stored): declaration +
contract + the maintained leaf's head + run health from execution_events +
the CONSUMERS list (D5 — which files cite this leaf, derived at read time),
composed per request. Nothing here stores desk state.

Creation is CONVERSATIONAL (D7): Keeper authors CONTRACT.md + _string.yaml
through its lane; the tick discovers. There is deliberately NO create route —
the two doors (the app's picker, Files' "Keep this current…") both open the
desk on a folder and hand the gesture to the conversation. The routes here
are the direct switches (Pause/Resume, Run now) and the projections the desk
reads.

Repair states, all LOUD (D3 / ADR-567 D6):
  404          — no declaration (the undesignated/unconfigured desk)
  422 on GET   — the declaration exists and fails to parse
  problem      — the declaration parses but cannot run (missing/invalid/
                 unsupported target, invalid sources) — served on the view
  repair       — the last write refused (shape_violation et al.), read from
                 the ledger, cleared by the next successful write

Auth boundary (ADR-501): everything scopes to the ACTING WORKSPACE'S OWNER
user_id via ``_acting_owner`` — the radar seam verbatim.
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


def _validate_topic(topic: str) -> str:
    """A string's topic is its folder path relative to /workspace/ — an
    EXISTING meaning-folder, so validation is path hygiene (no traversal, no
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


class StringSource(BaseModel):
    """One declared source — either shape (ADR-582 D6 / ADR-594 D4): an HTTP
    pull (`url`) or a connector slice (`connector` + `selector`). The
    projection serves BOTH — filtering on `url` silently hid connector
    sources from the very desk that manages them (the ADR-594 audit's
    finding)."""

    id: str
    url: Optional[str] = None
    connector: Optional[str] = None
    selector: Optional[str] = None


class UpdateStringRequest(BaseModel):
    """The direct switches (D7). Everything else is the conversation's —
    target/sources/shape/contract revisions land through Keeper's lane, and a
    silently-widened PATCH here would rebuild the form ADR-567 D3 replaced."""

    paused: Optional[bool] = None


class StringSummary(BaseModel):
    topic: str
    declaration_path: str
    target: str = ""
    target_path: Optional[str] = None
    format: Optional[str] = None
    schedule: Optional[Any] = None
    paused: bool = False
    sources: list[StringSource] = []
    contract: Optional[str] = None
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    #: The parseable-but-cannot-run states (missing_target | invalid_target |
    #: unsupported_format | sources_invalid) — served, never swallowed (D3).
    problem: Optional[str] = None


class RunEvent(BaseModel):
    slug: str
    status: str
    created_at: Optional[str] = None
    error_reason: Optional[str] = None


class RepairState(BaseModel):
    """The last write REFUSED — read from the ledger at composition time,
    cleared by the next success (derived-never-stored)."""

    reason: str
    detail: Optional[str] = None
    at: Optional[str] = None


class StringView(StringSummary):
    content: Optional[str] = None  # the maintained leaf's head
    shape: dict = {}
    recent_runs: list[RunEvent] = []
    repair: Optional[RepairState] = None
    #: D5 — the consumers list: which files cite this leaf (reference edges +
    #: in-content path citations), derived at read time, never stored.
    consumers: list[str] = []


# ---------------------------------------------------------------------------
# Helpers (the radar seam, verbatim where it is the same fact)
# ---------------------------------------------------------------------------


def _decl_path(topic: str) -> str:
    return f"/workspace/{topic}/_string.yaml"


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


def compose_string_yaml(
    *,
    target: str,
    schedule: Any,
    paused: bool,
    sources: list[dict],
    shape: Optional[dict] = None,
    fire_on_activation: bool = False,
) -> str:
    """Compose the ``_string.yaml`` body — PURE machine config (ADR-569 D2:
    judgment prose lives in CONTRACT.md, which no machine writer touches).
    Deterministic, machine-class (ADR-254): comment header + safe_dump."""
    payload: dict[str, Any] = {"target": target, "schedule": schedule}
    if fire_on_activation:
        payload["fire_on_activation"] = True
    payload["paused"] = paused
    payload["sources"] = sources
    if shape:
        payload["shape"] = shape
    header = (
        "# _string.yaml — string declaration (ADR-569: the maintained file)\n"
        "# Standing pull: schedule fires → sources fetched → the designated\n"
        "# target leaf is revised under CONTRACT.md. Machine config only —\n"
        "# what the file must stay true to belongs in CONTRACT.md, not here.\n"
    )
    return header + _yaml.safe_dump(payload, sort_keys=False, allow_unicode=True,
                                    default_flow_style=False)


def _summarize(client, user_id: str, decl, index_row: Optional[dict]) -> StringSummary:
    from services.strings import _read_file

    target_head = (
        _read_file(client, user_id, decl.target_path) if decl.target else None
    )
    return StringSummary(
        topic=decl.topic,
        declaration_path=decl.declaration_path,
        target=decl.target,
        target_path=decl.target_path if (decl.target and target_head is not None) else None,
        format=decl.format,
        schedule=decl.schedule,
        paused=decl.paused,
        sources=[
            StringSource(
                id=str(s.get("id")),
                url=(str(s["url"]) if s.get("url") else None),
                connector=(str(s["connector"]) if s.get("connector") else None),
                selector=(str(s["selector"]) if s.get("selector") else None),
            )
            for s in decl.sources
            if isinstance(s, dict) and s.get("id")
            and (s.get("url") or (s.get("connector") and s.get("selector")))
        ],
        contract=_read_file(client, user_id, decl.contract_path),
        last_run_at=(index_row or {}).get("last_run_at"),
        next_run_at=(index_row or {}).get("next_run_at"),
        problem=decl.problem,
    )


#: Write refusals the desk names as a repair state (vs weather like a failed
#: fetch, which the run events already narrate).
_REPAIR_REASONS = {"shape_violation", "unsupported_format", "derive_raised"}


def _compose_repair(events: list[RunEvent]) -> Optional[RepairState]:
    """The ledger's answer to "is this string in repair?": the most recent
    write event decides — a refusal stands until a later success or honest
    no-change clears it."""
    for e in events:
        if not e.slug.startswith("string-write:"):
            continue
        if e.status == "success" or (e.status == "skipped" and e.error_reason == "no_change"):
            return None
        if e.status == "failed" and (e.error_reason or "") in _REPAIR_REASONS:
            return RepairState(reason=e.error_reason or "failed", at=e.created_at)
        return None
    return None


_MAX_CONSUMERS = 20


def _consumers(client, user_id: str, decl) -> list[str]:
    """D5 — which files cite the maintained leaf. Two read-time probes, never
    stored: (a) revision reference edges (derived_from ∋ target_path,
    ADR-448), (b) in-content citations (data-ref / chart blocks / links carry
    the path as text). Best-effort — the instrument never takes down the view."""
    target = decl.target_path
    found: list[str] = []
    try:
        edge_rows = (
            client.table("workspace_file_versions")
            .select("path")
            .eq("user_id", user_id)
            .contains("derived_from", [target])
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        ).data or []
        found.extend(r["path"] for r in edge_rows if r.get("path"))
    except Exception as e:
        logger.warning("[STRINGS] consumer edge probe failed for %s: %s", decl.topic, e)
    try:
        content_rows = (
            client.table("workspace_files")
            .select("path")
            .eq("user_id", user_id)
            .like("content", f"%{target}%")
            .limit(200)
            .execute()
        ).data or []
        found.extend(r["path"] for r in content_rows if r.get("path"))
    except Exception as e:
        logger.warning("[STRINGS] consumer content probe failed for %s: %s", decl.topic, e)

    out: list[str] = []
    for p in found:
        if p == target or p == decl.declaration_path or p == decl.contract_path:
            continue
        if p.startswith("/workspace/inbound/"):
            continue  # raws cite nothing; they are the evidence, not readers
        if p not in out:
            out.append(p)
        if len(out) >= _MAX_CONSUMERS:
            break
    return out


def _parse_or_none(content: str, topic: str, user_id: str):
    from services.strings import parse_string_yaml
    return parse_string_yaml(
        content, topic=topic, declaration_path=_decl_path(topic), user_id=user_id
    )


async def _materialize(client, user_id: str) -> None:
    """Immediate index sync post-write — a switched string re-arms now, not at
    the next global discovery."""
    from services.strings import discover_strings, materialize_string_index
    from services.workspace_context import effective_workspace_id
    decls = discover_strings(
        client, workspace_id=effective_workspace_id(user_id)
    ).get(user_id, [])
    await materialize_string_index(client, user_id, decls)


def _index_row(client, user_id: str, topic: str) -> Optional[dict]:
    rows = (
        client.table("tasks").select("slug, last_run_at, next_run_at")
        .eq("user_id", user_id).eq("kind", "string")
        .eq("slug", f"string:{topic}").limit(1).execute()
    ).data or []
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/strings")
async def list_strings(auth: UserClient) -> list[StringSummary]:
    from services.strings import discover_strings
    actor = _acting_owner(auth)
    decls = discover_strings(
        auth.client, workspace_id=_acting_workspace(auth)
    ).get(actor, [])

    index_rows = (
        auth.client.table("tasks")
        .select("slug, last_run_at, next_run_at")
        .eq("user_id", actor)
        .eq("kind", "string")
        .execute()
    ).data or []
    by_slug = {r["slug"]: r for r in index_rows}

    return [
        _summarize(auth.client, actor, d, by_slug.get(d.slug))
        for d in sorted(decls, key=lambda d: d.topic)
    ]


@router.get("/strings/{topic:path}")
async def get_string(topic: str, auth: UserClient) -> StringView:
    """The composed desk view, projected at read time (never stored)."""
    actor = _acting_owner(auth)
    topic = _validate_topic(topic)
    content = _read_declaration(auth.client, actor, topic)
    if content is None:
        raise HTTPException(status_code=404, detail=f"no string in '{topic}'")

    decl = _parse_or_none(content, topic, actor)
    if decl is None:
        raise HTTPException(status_code=422, detail="declaration unparseable")

    summary = _summarize(auth.client, actor, decl, _index_row(auth.client, actor, topic))

    # Run health — the ledger is the source.
    events = (
        auth.client.table("execution_events")
        .select("slug, status, created_at, error_reason")
        .eq("user_id", actor)
        .in_("slug", [f"string-sweep:{topic}", f"string-write:{topic}"])
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    ).data or []
    runs = [RunEvent(**{k: e.get(k) for k in
                        ("slug", "status", "created_at", "error_reason")})
            for e in events]

    from services.strings import _read_file
    head = _read_file(auth.client, actor, decl.target_path) if decl.target else None

    return StringView(
        **summary.model_dump(),
        content=head,
        shape=decl.shape,
        recent_runs=runs,
        repair=_compose_repair(runs),
        consumers=_consumers(auth.client, actor, decl),
    )


@router.patch("/strings/{topic:path}")
async def update_string(topic: str, request: UpdateStringRequest, auth: UserClient) -> StringSummary:
    """The direct switches only (D7): Pause/Resume. Everything else is the
    conversation's."""
    actor = _acting_owner(auth)
    topic = _validate_topic(topic)
    content = _read_declaration(auth.client, actor, topic)
    if content is None:
        raise HTTPException(status_code=404, detail=f"no string in '{topic}'")

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
    new_content = compose_string_yaml(
        target=str(parsed.get("target") or ""),
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
        message=f"{'pause' if parsed.get('paused') else 'resume'} the string in '{topic}'",
        workspace_id=getattr(auth, "workspace_id", None),
    )
    await _materialize(auth.client, actor)

    decl = _parse_or_none(new_content, topic, actor)
    if decl is None:  # cannot happen for content we just composed — fail loud
        raise HTTPException(status_code=500, detail="recomposed declaration unparseable")
    return _summarize(auth.client, actor, decl, _index_row(auth.client, actor, topic))


@router.post("/strings/{topic:path}/run")
async def run_string_now(topic: str, auth: UserClient) -> dict:
    """Run now (D7) — the manual fire. For a maintained file it is table
    stakes; runs inline and records, exactly one scheduled run's body."""
    from datetime import datetime, timezone as _tz
    from services.strings import record_string_run, run_string_sweep

    actor = _acting_owner(auth)
    topic = _validate_topic(topic)
    content = _read_declaration(auth.client, actor, topic)
    if content is None:
        raise HTTPException(status_code=404, detail=f"no string in '{topic}'")
    decl = _parse_or_none(content, topic, actor)
    if decl is None:
        raise HTTPException(status_code=422, detail="declaration unparseable — repair it first")
    if decl.problem is not None:
        raise HTTPException(status_code=422, detail=f"the string cannot run: {decl.problem}")

    result = await run_string_sweep(auth.client, actor, decl)
    try:
        record_string_run(auth.client, actor, decl,
                          last_run_at=datetime.now(_tz.utc))
    except Exception as e:
        logger.warning("[STRINGS] manual-run record failed for %s: %s", topic, e)
    return result


def _strip_frontmatter(content: str) -> str:
    m = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    return content[m.end():] if m else content
