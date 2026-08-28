"""Strings routes — ADR-569 (the maintained file, kept under contract).

The composed view is a LAZY PROJECTION over the string's folder + the ledgers
(the radar R2 pattern, ADR-486 D5 — derived-never-stored): declaration +
contract + the maintained leaf's head + run health from execution_events +
the CONSUMERS list (D5 — which files cite this leaf, derived at read time),
composed per request. Nothing here stores desk state.

Creation is CONVERSATIONAL (D7): the desk's colleague authors CONTRACT.md +
_string.yaml through its lane; the tick discovers. There is deliberately NO create route —
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
    finding).

    The trailing fields are the ADR-595 D3 enrichment — the source as a
    PARTY to the string (standing · receipts · contribution), derived at
    read time on the DESK VIEW only; the roster list leaves them None."""

    id: str
    url: Optional[str] = None
    connector: Optional[str] = None
    selector: Optional[str] = None
    #: newest landed receipt under this source's deterministic prefix
    last_landed_at: Optional[str] = None
    last_landed_path: Optional[str] = None
    #: connector sources only — is the selector inside the connection's
    #: aperture (ADR-594's intersection law, made visible)? None for HTTP.
    in_aperture: Optional[bool] = None
    #: newest leaf revision whose derived_from cites this source's receipts
    last_contributed_at: Optional[str] = None


class UpdateStringRequest(BaseModel):
    """The direct switches (D7). Everything else is the conversation's —
    target/sources/shape/contract revisions land through the desk's lane, and a
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
    """The desk view — ADR-595 D1: the tending surface NEVER serves the
    maintained file's contents. Head FACTS ride instead (enough for the
    glance, not the document); reading happens at the file's own surface."""

    shape: dict = {}
    recent_runs: list[RunEvent] = []
    repair: Optional[RepairState] = None
    #: D5 — the consumers list: which files cite this leaf (reference edges +
    #: in-content path citations), derived at read time, never stored.
    consumers: list[str] = []
    #: ADR-595 D1 — head facts (never the head itself).
    head_updated_at: Optional[str] = None
    head_lines: Optional[int] = None
    head_bytes: Optional[int] = None


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


def _receipt_prefix(src: StringSource) -> Optional[str]:
    """The source's deterministic landing prefix — /workspace-absolute, with
    the trailing slash. The grammar is a LAW (ADR-594 D1), so this is pure
    derivation: `inbound/{platform}/{selector}/` for a connector slice,
    `inbound/web/{slug(id)}/` for an HTTP pull (the `_retain_raw` home)."""
    if src.connector and src.selector:
        from services.connectors import capture_destination
        return f"/workspace/{capture_destination(src.connector, src.selector)}/"
    if src.url:
        from services.primitives.track_web_sources import _slug as _source_slug
        return f"/workspace/inbound/web/{_source_slug(src.id)}/"
    return None


def _enrich_sources(
    client, user_id: str, sources: list[StringSource], target_path: Optional[str],
) -> None:
    """ADR-595 D3 — the source as a PARTY, composed at read time (never
    stored): newest landed receipt · aperture standing · last contribution.
    Best-effort per block; the instrument never takes down the view."""
    prefixes = {s.id: _receipt_prefix(s) for s in sources}

    # Receipts — newest landed file under each source's prefix.
    for src in sources:
        prefix = prefixes.get(src.id)
        if not prefix:
            continue
        try:
            rows = (
                client.table("workspace_files")
                .select("path, created_at")
                .eq("user_id", user_id)
                .like("path", f"{prefix}%")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            ).data or []
        except Exception as e:  # noqa: BLE001
            logger.warning("[STRINGS] receipt probe failed for %s: %s", src.id, e)
            rows = []
        if rows:
            src.last_landed_path = rows[0].get("path")
            src.last_landed_at = rows[0].get("created_at")

    # Standing — the aperture check, one connection read per platform.
    platforms = {s.connector for s in sources if s.connector and s.selector}
    for plat in platforms:
        try:
            from services.connectors import connection_row, selected_ids_from_row
            row = connection_row(client, user_id, plat)
            selected = set(selected_ids_from_row(row)) if row else set()
        except Exception as e:  # noqa: BLE001
            logger.warning("[STRINGS] aperture probe failed for %s: %s", plat, e)
            continue
        for src in sources:
            if src.connector == plat and src.selector:
                src.in_aperture = src.selector in selected

    # Contribution — newest leaf revision citing each source's receipts
    # (the N→1 edge at revision grain; derived_from carries absolute paths).
    if target_path:
        try:
            revs = (
                client.table("workspace_file_versions")
                .select("created_at, derived_from")
                .eq("user_id", user_id)
                .eq("path", target_path)
                .order("created_at", desc=True)
                .limit(40)
                .execute()
            ).data or []
        except Exception as e:  # noqa: BLE001
            logger.warning("[STRINGS] contribution probe failed: %s", e)
            revs = []
        for rev in revs:
            cited = rev.get("derived_from") or []
            if not isinstance(cited, list):
                continue
            for src in sources:
                if src.last_contributed_at is not None:
                    continue
                prefix = prefixes.get(src.id)
                if prefix and any(
                    isinstance(p, str) and p.startswith(prefix) for p in cited
                ):
                    src.last_contributed_at = rev.get("created_at")


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

    # Head FACTS, never the head (ADR-595 D1) — the pane is the tending
    # surface; the document is read at its own surface through the Open door.
    head_updated_at = None
    head_lines = None
    head_bytes = None
    if decl.target:
        try:
            head_rows = (
                auth.client.table("workspace_files")
                .select("content, updated_at")
                .eq("user_id", actor)
                .eq("path", decl.target_path)
                .limit(1)
                .execute()
            ).data or []
        except Exception as e:
            logger.warning("[STRINGS] head-fact probe failed for %s: %s", topic, e)
            head_rows = []
        if head_rows and head_rows[0].get("content") is not None:
            body = head_rows[0]["content"]
            head_updated_at = head_rows[0].get("updated_at")
            head_lines = body.count("\n") + (0 if body.endswith("\n") or not body else 1)
            head_bytes = len(body.encode("utf-8"))

    view = StringView(
        **summary.model_dump(),
        shape=decl.shape,
        recent_runs=runs,
        repair=_compose_repair(runs),
        consumers=_consumers(auth.client, actor, decl),
        head_updated_at=head_updated_at,
        head_lines=head_lines,
        head_bytes=head_bytes,
    )
    _enrich_sources(auth.client, actor, view.sources,
                    decl.target_path if decl.target else None)
    return view


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

    # ── The manual fire takes the SAME CAS CLAIM the scheduled drain takes
    #    (ADR-618). Without it, Run-now racing a tick executes the string
    #    TWICE — two derives, two writes, two charges — and then both callers
    #    call `record_string_run`, so the schedule anchor is rewritten twice
    #    from two different "now"s. "Exactly one scheduled run's body" (this
    #    route's own docstring) has to mean the claim too, or it is only the
    #    body and not the run.
    #
    #    Losing the claim is a SUCCESSFUL no-op, not an error: the string IS
    #    running, just not on this caller's thread. 409 would tell the operator
    #    something went wrong when nothing did.
    from services.strings import claim_string_run, read_string_task_row

    _row = read_string_task_row(auth.client, actor, decl.slug)
    _claimed = claim_string_run(
        auth.client, actor, decl.slug, (_row or {}).get("next_run_at"),
    )
    if _row is not None and not _claimed:
        return {"success": True, "slug": decl.slug, "no_change": True,
                "detail": "already running — a scheduled run claimed this string"}

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
