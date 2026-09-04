"""Standing work — the maintained file, kept on a declared contract (ADR-639).

The kernel lane behind "keep this file current": a member DESIGNATES one file
in a folder as kept current — a declared contract (what it must stay true
to), declared sources (where currency comes from), a cadence — and a standing
run revises its head, while the member corrects it like any file and every
correction compounds (single-head-many-authors, ADR-384 D4).

THIS IS A LANE, NOT AN APP (ADR-639). The strings app, its pane and the
Supervisor agent are DELETED. What a member declares lives beside the file;
what runs it is this daemon; how it is done is a SKILL
(`system/skills/keeping-a-file-current`, composed into the run by binding);
who does it DERIVES from what the file is (the target's type → its app → that
app's standing executor — ADR-603 D2, one derivation deeper). Nothing in that
sentence is an agent, and no key here may name one.

THE LAW (ADR-569 D1, unchanged): un-designated files are NEVER a standing
writer's target. Designation is the member's explicit act; authored artifacts
stay current through reference (data-ref), never standing writes.

One folder holds ONE declaration, split on the ADR-564 D2 bright line:

    _standing.yaml  — pure machine config (ADR-254 underscore-yaml):
                        target: metrics.csv      # the designated leaf,
                                                 # folder-relative, ONE segment
                        app: text                # OPTIONAL — explicit wins;
                                                 # absent → derived from the
                                                 # target's type (prose → text)
                        schedule: "0 13 * * *"   # UTC cron | @-semantic | list
                        paused: false
                        sources:                 # HTTP pull, or a connector
                          - id: main             # slice (ADR-582 D6 / 594 D2):
                            url: https://…       # {connector, selector} reading
                                                 # LANDED snapshots
                        shape:                   # structured formats only —
                          columns: [date, mrr]   # csv: required column set
                          # keys: [mrr, churn]   # json: required top-level keys
    CONTRACT.md     — what this file means and must stay true to (prose,
                      member/lane-authored, NEVER machine-parsed)

`DECLARATION_KEYS` IS the parser's whitelist. It used to live in a thin rule
module nothing read, and drifted from the one instance (it said `subject`;
the file said `target`). A rule with no reader is prose.

Designation scope (D1): ``md · csv · json · txt`` — formats whose unattended
revision does not fight an authoring surface's editing model. Designating an
authoring-app artifact (a deck, an image stage, a post) is NAMED-DEFERRED,
never silently allowed. The refusal here is the ``unsupported_format`` problem.

One run = fetch → map/derive → validate → write, at the depth the format
demands (D4):

    fetch    — HTTP pull of the declared sources (httpx, honest UA); each raw
               body retained as an immutable observation under inbound/web/
               (the ADR-376/DP32 raw lane — the evidence the write CITES); a
               connector source reaches-with-a-receipt through the ONE capture
               writer and reads the landed snapshot (ADR-594 D2)
    map      — csv: parse + project to the declared columns; json: parse +
               require the declared keys; txt: passthrough; md: ONE bounded
               judgment turn governed by CONTRACT.md, composed through the
               lane module's standing frame (ADR-639 D1: the same commons
               contract, citation rule, mandate head and character every lane
               gets; the kernel JOB; the craft skill's body) — returning the
               full revised document or the exact token NO_CHANGE
    validate — the machine-checkable half of the contract (``shape``). A
               violating write is REFUSED into a LOUD repair state: no silent
               bad numbers. Metered ``status='failed',
               error_reason='shape_violation'``.
    write    — CONFINED to the declared leaf ONLY (the ``_assert_hub_write``
               shape, D3), via write_revision(revision_kind='derivation',
               derived_from=[raws]). History is the revision chain, never the
               namespace (ADR-209). An unchanged pull is an honest no-op.
    meter    — two execution_events rows per run:
               ``standing-sweep:{topic}``  (mechanical fetch)
               ``standing-write:{topic}``  (the write step — mechanical for
               structured formats, judgment for prose)

Scheduling rides the thin ``tasks`` index with ``kind='standing'`` and the ONE
drain loop in ``services/scheduling.py`` (ADR-639 D3 — capture rides the same
loop): the tick discovers declarations, materializes the slice
(``preserve_due_commitment`` applies by construction — b8ac1c7), claims via
CAS, runs, records. The run is BOUNDED BY THE POOL before the fetch (ADR-618).

The topic is the folder path relative to ``/workspace/`` (any meaning-folder —
the designated file lives where it lives).

Attribution: raws as ``system:standing`` observations; the leaf write as
``system:standing`` — machinery, no face (ADR-596 D1). Historical rows carry
``system:strings`` and are display-resolved (ADR-639 D5). This module carries
no module-level ``services.*`` imports (cycle-free).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Union

import yaml as _yaml

logger = logging.getLogger(__name__)

STANDING_KIND = "standing"

#: Declarations live at {folder}/_standing.yaml, any meaning-folder under
#: /workspace/ — the designated file's own folder (ADR-569 D2 / ADR-639 D3).
_WORKSPACE_PREFIX = "/workspace/"
DECLARATION_LEAF = "_standing.yaml"
CONTRACT_LEAF = "CONTRACT.md"

#: The v1 designation scope (ADR-569 D1) — formats whose unattended revision
#: does not fight an authoring surface. Extending this set is a canon change
#: (the named-deferred authoring-artifact collision), never a convenience.
SUPPORTED_FORMATS = ("md", "csv", "json", "txt")

#: Structured formats map ONE endpoint to the leaf; prose folds several.
_MAX_SOURCES_PROSE = 12
_FETCH_TIMEOUT_S = 15.0
_MAX_FETCH_CHARS = 500_000
_USER_AGENT = "yarnnn-standing/1.0 (+https://yarnnn.com)"

#: One bounded judgment turn for a prose declaration (the radar report ceiling).
_STANDING_MAX_TOKENS = 4096
_DERIVE_TIMEOUT_S = 120.0

#: The empty-run sentinel the OUTPUT CONTRACT names (radar's, verbatim). A
#: machine contract — it is parsed — so it stays in code, not in the skill.
NO_CHANGE_SENTINEL = "NO_CHANGE"

#: The craft skill the run composes by binding (ADR-639 D2). A toolless turn
#: cannot ReadFile, so the body is pushed, never indexed.
KEEPING_SKILL = "keeping-a-file-current"

#: The keys a declaration may carry — the parser's whitelist (ADR-639 D3).
#: `app` is the executor field: an APP slug, never an agent's (ADR-603 D2 —
#: authority attaches to declarations and gates, never to agents). No key here
#: names an agent, ever; the gate asserts it against the live register.
DECLARATION_KEYS = frozenset(
    {"target", "app", "schedule", "sources", "shape", "paused", "paused_until"}
)

#: Which app a target's TYPE belongs to when the declaration names none —
#: the ADR-602 D7 rule (the app follows the artifact) one layer up. Prose is
#: Text's; structured formats run mechanically and need no executor.
_APP_BY_FORMAT = {"md": "text", "txt": "text"}

Schedule = Optional[Union[str, list[str]]]


# ---------------------------------------------------------------------------
# Declaration — parse + walk
# ---------------------------------------------------------------------------


@dataclass
class StandingDecl:
    """One parsed standing declaration. Structurally compatible with
    ``services.scheduling.compute_next_run_at`` (slug/schedule/paused/
    paused_until/options — the RadarHub precedent)."""

    topic: str  # folder path relative to /workspace/
    slug: str  # "standing:{topic}" — disjoint from capture slugs
    target: str = ""  # the designated leaf, folder-relative (one segment)
    #: The APP whose standing executor runs a prose declaration — explicit in
    #: the file, else derived from the target's type (ADR-639 D3). None for a
    #: structured target (mechanical; no executor). NEVER an agent slug.
    app: Optional[str] = None
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
    #: unsupported_format | sources_invalid | app_invalid.
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
    """``/workspace/{folder...}/_standing.yaml`` → the folder path relative to
    ``/workspace/`` (the declaration's topic identifier). Pure. None for paths
    outside the convention (including a declaration at the workspace root —
    a declaration lives in a meaning-folder, not the root)."""
    p = (path or "").strip()
    if not p.startswith(_WORKSPACE_PREFIX) or not p.endswith(f"/{DECLARATION_LEAF}"):
        return None
    middle = p[len(_WORKSPACE_PREFIX):-(len(DECLARATION_LEAF) + 1)]
    parts = [s for s in middle.split("/") if s]
    return "/".join(parts) if parts else None


def _classify_target(target: str) -> Optional[str]:
    """The designation boundary, machine-checked. None = healthy; else the
    problem token (ADR-569 D1: designation, not file-type, is the boundary —
    but the v1 SCOPE is format-bounded, and the refusal is loud)."""
    if not target:
        return "missing_target"
    if "/" in target or target.startswith("_") or target in (CONTRACT_LEAF,):
        # One segment, in the declaration's own folder; never the machinery files.
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


def _derive_app(fmt: Optional[str]) -> Optional[str]:
    """The app a target's type belongs to (ADR-639 D3). Pure."""
    return _APP_BY_FORMAT.get(fmt or "")


def _classify_app(app: Optional[str], fmt: Optional[str]) -> Optional[str]:
    """The executor field, machine-checked. None = healthy; else `app_invalid`.

    An explicit `app` must be a REGISTERED app — which is also how "never an
    agent" is enforced without a second rule: `app: editor` is not an app,
    so it is refused loudly rather than parked or honoured. A prose target
    with no resolvable app cannot run (no executor); a structured target
    needs none.
    """
    if app:
        import services.apps  # noqa: F401  (registration side-effect — ADR-562)
        from services.authoring import resolve_app

        return None if resolve_app(app) else "app_invalid"
    if fmt in ("md",) and _derive_app(fmt) is None:
        return "app_invalid"
    return None


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


def parse_standing_yaml(
    content: str, *, topic: str, declaration_path: str, user_id: Optional[str] = None
) -> Optional[StandingDecl]:
    """Parse one ``_standing.yaml`` body. None on unparseable (the caller's 422
    repair state); a PARSEABLE declaration that cannot run comes back with
    ``problem`` set — visible, never silently dark (D3). Unknown keys are
    parked in ``options`` as inert residue: the parser cannot be talked into
    reading a key `DECLARATION_KEYS` does not name."""
    if not content or not content.strip():
        return None
    try:
        parsed = _yaml.safe_load(_strip_tier_frontmatter(content))
    except _yaml.YAMLError as e:
        logger.warning("[STANDING] %s unparseable: %s", declaration_path, e)
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

    options = {k: v for k, v in parsed.items() if k not in DECLARATION_KEYS}
    explicit_app = str(parsed.get("app") or "").strip() or None

    decl = StandingDecl(
        topic=topic,
        slug=f"standing:{topic}",
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
    # Explicit wins; absent derives from the target's type (ADR-639 D3).
    decl.app = explicit_app or _derive_app(decl.format)
    decl.problem = (
        _classify_target(target)
        or _classify_sources(sources, decl.format)
        or _classify_app(explicit_app, decl.format)
    )
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


def discover_standing(client, *, workspace_id: Optional[str] = None) -> dict[str, list[StandingDecl]]:
    """All standing declarations, grouped by the OWNER user_id of their
    workspace — the discover_radar_hubs shape verbatim (ADR-501 keying: the
    grouping key is the workspace's owner, resolved through the service
    client, never the file's author)."""
    try:
        q = (
            client.table("workspace_files")
            .select("user_id, workspace_id, path, content")
            .like("path", f"{_WORKSPACE_PREFIX}%/{DECLARATION_LEAF}")
        )
        if workspace_id:
            q = q.eq("workspace_id", workspace_id)
        rows = q.execute().data or []
    except Exception as e:
        logger.warning("[STANDING] discovery scan failed: %s", e)
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

    by_user: dict[str, list[StandingDecl]] = {}
    for row in rows:
        path = row.get("path") or ""
        topic = topic_from_declaration_path(path)
        if topic is None:
            logger.warning("[STANDING] %s is not a declaration path; skipping", path)
            continue
        key = _owner(row)
        if not key:
            continue
        decl = parse_standing_yaml(
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


def _assert_standing_write(decl: StandingDecl, path: str) -> None:
    """The standing writer revises ONLY the designated leaf — stricter than
    radar's subtree confinement, because designation is per-FILE (D1). A
    capability constraint asserted at the write site; raises rather than
    writes — a confined actor aiming anywhere else is a bug, not a judgment
    call."""
    if path != decl.target_path:
        raise ValueError(
            f"standing write-confinement: {path!r} is not the designated leaf "
            f"{decl.target_path!r} (un-designated files are never a standing "
            "writer's target — ADR-569 D1)"
        )


# ---------------------------------------------------------------------------
# Scheduling — the kind='standing' slice of the tasks index (ADR-393 precedent)
# ---------------------------------------------------------------------------


async def materialize_standing_index(
    client, user_id: str, decls: list[StandingDecl], *, now: Optional[datetime] = None
) -> int:
    """Sync the tasks index (kind='standing' rows) against this user's declarations.
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
            .eq("kind", STANDING_KIND)
            .execute()
        )
        existing_by_slug = {r["slug"]: r for r in (existing.data or [])}
    except Exception as e:
        logger.warning("[STANDING_SCHED] index read failed for %s: %s", user_id[:8], e)
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
            logger.error("[STANDING_SCHED] %s/%s schedule resolution failed: %s",
                         user_id[:8], slug, e)
            next_run = None

        # A due-but-unfired next_run_at is a COMMITMENT (b8ac1c7): this
        # materializer runs at the top of the drain tick, and the due scan
        # below must still find the stored time — without this, a never-run
        # declaration created conversationally could never fire.
        next_run = preserve_due_commitment(
            _parse_iso(existing_row.get("next_run_at") if existing_row else None),
            next_run, now=now, paused=decl.paused,
        )

        import json as _json
        row = {
            "user_id": user_id,
            "slug": slug,
            "status": "active",
            "kind": STANDING_KIND,
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
            logger.warning("[STANDING_SCHED] upsert failed for %s/%s: %s", user_id[:8], slug, e)

    for slug, existing_row in existing_by_slug.items():
        if slug not in by_slug:
            try:
                client.table("tasks").delete().eq("id", existing_row["id"]).execute()
                touched += 1
                logger.info("[STANDING_SCHED] dropped row %s/%s (declaration gone or in repair)",
                            user_id[:8], slug)
            except Exception as e:
                logger.warning("[STANDING_SCHED] delete failed for %s/%s: %s", user_id[:8], slug, e)

    return touched


def read_standing_task_row(client, user_id: str, slug: str) -> Optional[dict]:
    """This declaration's index row, or None when it has never been materialized.

    ADR-618 — the manual door needs the CURRENT `next_run_at` to take the same
    CAS claim the drain takes; the drain already holds it from its due-scan.
    None means "not indexed yet" (a declaration since the last tick), which
    the caller must treat as claimable rather than as a lost race — there is no
    scheduled run to collide with.
    """
    try:
        rows = (
            client.table("tasks")
            .select("id, slug, next_run_at, last_run_at")
            .eq("user_id", user_id)
            .eq("slug", slug)
            .eq("kind", STANDING_KIND)
            .limit(1)
            .execute()
        ).data or []
    except Exception as e:  # noqa: BLE001
        logger.warning("[STANDING] task-row read failed for %s: %s", slug, e)
        return None
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# The executor — DERIVED from what the file is (ADR-603 D2 / ADR-639 D3)
# ---------------------------------------------------------------------------


def resolve_executor(decl: StandingDecl) -> tuple[str, str, str]:
    """The agent whose model + character power this declaration's judgment
    run: ``(slug, model, character)``.

    The declaration names an APP (explicit, or derived from the target's type
    at parse time); the app's registration names its standing executor (else
    its resident — ADR-604 D2's seam, ADR-610 D2's value); the register names
    the engine. No step here reads an agent slug from the declaration, and the
    gate asserts none can be written into one.

    No plausible-default fallback: a prose declaration whose app has no
    registered executor is a bug that raises, never a reason to quietly pick
    an agent (the ADR-548 lesson).
    """
    import services.apps  # noqa: F401  (registration side-effect — ADR-562)
    from services.agents_registry import get_agent
    from services.authoring import standing_executor_for_app

    slug = standing_executor_for_app(decl.app)
    if not slug:
        raise KeyError(
            f"declaration {decl.slug!r} names app {decl.app!r}, which has no "
            "registered standing executor"
        )
    row = get_agent(slug)
    if row is None:  # a registration naming a ghost is a bug, not a fallback
        raise KeyError(f"executor {slug!r} for app {decl.app!r} is not a kernel agent")
    return slug, row["model"], row["posture"]


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
#: declarations sharing a selector cost one platform read per window.
_CONNECTOR_CAPTURE_MIN_INTERVAL_S = 600


async def _reach_connector_sources(
    client, user_id: str, conn_sources: list[dict], *, observed_at: str,
) -> None:
    """ADR-594 D2 — reach with a receipt: before reading, invoke the ONE
    capture writer for this run's declared selectors (grouped per platform),
    which lands attributed observations at the fixed intake lane. The
    effective set is the intersection with the connection's aperture — a
    declaration narrows the operator's consent, never widens it. Failure degrades
    to the newest landed snapshot (stale-but-honest; the app states
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
            logger.warning("[STANDING] connector reach failed %s/%s: %s",
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
        logger.warning("[STANDING] connector source read failed %s: %s", rel, e)
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
        authored_by="system:standing",
        message=f"raw standing observation: {url} @ {observed_at}",
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
# The kernel JOB — what only the run can say (ADR-639 D1/D2)
# ---------------------------------------------------------------------------
#
# The craft that used to live here as `_STANDING_RUN_POSTURE` (fold don't
# append · preserve corrections · cite inline · name a source/contract
# disagreement · NO_CHANGE honestly) is a SKILL now —
# `keeping-a-file-current`, composed into the run by the lane module's
# standing frame. The pane posture (`_STANDING_PANE_FRAME`, the three-file
# lifecycle a colleague taught at the strings pane) is the
# `declaring-standing-work` skill, offered in every lane's index. What stays
# in code is the OUTPUT CONTRACT — the sentinel is parsed, so it is a machine
# fact — and the per-run facts the frame cannot know.

_STANDING_JOB = """## This run
A scheduled run fired in the member's workspace for the kept file "{target}"
in {root}. Nobody is present; the file you return will be read later, and
other artifacts cite it by reference. The message hands you THE CONTRACT
(what this file means and must stay true to), THE CURRENT FILE (it may carry
the member's own corrections), and THE FRESH SOURCE MATERIAL.

## The output contract
Return the full revised file and NOTHING else — or the exact token
NO_CHANGE. No preamble, no code fence around the whole thing."""


def build_standing_job(decl: StandingDecl) -> str:
    """The run's job section — pure. The frame composes it under the
    executor's character (character first, job second — the lane order)."""
    return _STANDING_JOB.format(target=decl.target, root=decl.root)


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
        logger.warning("[STANDING] read failed for %s: %s", path, e)
        return None


# ---------------------------------------------------------------------------
# The run — fetch → map/derive → validate → place → cite → embed → meter
# ---------------------------------------------------------------------------


async def run_standing_sweep(client, user_id: str, decl: StandingDecl) -> dict:
    """One run of one declaration. Returns {success, slug, target_path?,
    no_change?, error_reason?, detail?}. Never raises past its own boundary —
    the drain loop records the run either way."""
    from services.telemetry import record_execution_event

    started = datetime.now(timezone.utc)
    topic = decl.topic

    # A declaration in a problem state never runs — the pane already says so.
    if decl.problem is not None or decl.format is None:
        return {"success": False, "slug": decl.slug,
                "error_reason": decl.problem or "unsupported_format"}

    # ── 0. THE BALANCE GATE (ADR-618) ────────────────────────────────────────
    # A prose declaration's derive is METERED JUDGMENT SPEND, and until ADR-618
    # the only thing between a declared file and an operator's balance was
    # `AGENT_ENABLED` — which defaults ON. That is precisely the property the
    # scheduler cites for DELETING radar rather than hiding it ("a dormant
    # spend lane is precisely the ambiguity a future session would have to
    # re-derive", unified_scheduler.py), and the comment there calls this lane
    # radar's "sibling, same posture". It inherited the posture without the
    # guard.
    #
    # ⭐ `check_balance`, NOT `check_draw`. Standing work attributes to the
    # OWNER, who is never member-capped — `check_draw`'s second half would be a
    # no-op here, and reaching for it would imply a per-member bound this lane
    # does not have. This is the pool hard-stop the wake lane already uses
    # (`wake.py`), which is the established convention for unattended spend and
    # is stated as such in `check_draw`'s own docstring.
    #
    # Placed BEFORE the fetch, not just before the derive. The fetch is $0 in
    # model terms but it writes retained observations and reaches connectors —
    # work whose only purpose is to feed a derive that cannot run. A gate that
    # lets the pointless half proceed is a half-gate.
    #
    # ⚠️ Fail-OPEN on a read error, deliberately, matching `wake.py` exactly: a
    # DB hiccup must not silently stop an operator's standing work. The
    # hard-stop backstops at the next tick, and `check_balance` itself already
    # returns 0.0 → blocked on a balance-read failure, so the fail-open here
    # covers only the case where the CHECK could not run at all.
    try:
        from services.platform_limits import check_balance
        _balance_ok, _balance = check_balance(client, user_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("[STANDING] balance check failed for %s (proceeding): %s",
                       topic, e)
        _balance_ok = True
    if not _balance_ok:
        # A refusal is a RECORDED run, not a silent skip: the pane must be able
        # to say why nothing moved, and the drain loop records either way.
        record_execution_event(
            client, user_id=user_id, slug=f"standing-sweep:{topic}",
            mode="mechanical", trigger_type="scheduled",
            status="failed", error_reason="balance_exhausted",
            error_detail="workspace balance is exhausted — the run did not fire",
            duration_ms=0, funnel_decision="standing",
            # ADR-445: every ledger row names its principal — the refusal row
            # was the one site that did not (found by the ADR-445 census once
            # ADR-632 un-crashed it).
            principal_id=user_id,
        )
        return {"success": False, "slug": decl.slug,
                "error_reason": "balance_exhausted"}

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
        client, user_id=user_id, slug=f"standing-sweep:{topic}",
        mode="mechanical", trigger_type="scheduled",
        status="success" if sweep_ok else "failed",
        error_reason=None if sweep_ok else "no_sources_fetched",
        error_detail=("; ".join(errors)[:500] or None) if errors else None,
        duration_ms=sweep_ms, funnel_decision="standing",
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
            # says why, the app reads the ledger, the lane repairs. No
            # silent bad numbers.
            record_execution_event(
                client, user_id=user_id, slug=f"standing-write:{topic}",
                mode="mechanical", trigger_type="scheduled", status="failed",
                error_reason="shape_violation", error_detail=str(e)[:500],
                funnel_decision="standing", principal_id=user_id,
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
        # Its SYSTEM PROMPT is the lane module's standing frame (ADR-639 D1):
        # the same commons contract, citation rule, mandate head and
        # character every lane gets, the kernel job, and the craft skill's
        # body — never a system string composed here.
        from services.derive_turn import run_bounded_derive_turn
        from services.lane_runner import build_standing_frame

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
               else "THE FILE DOES NOT EXIST YET — this is the first run. Write "
                    "the baseline from the source material.\n\n")
            + f"THE FRESH SOURCE MATERIAL (just fetched):\n\n{material}\n"
        )
        executor, executor_model, _character = resolve_executor(decl)
        turn = await run_bounded_derive_turn(
            model=executor_model,
            system=build_standing_frame(
                client, user_id, model=executor_model, executor=executor,
                job=build_standing_job(decl), skill=KEEPING_SKILL,
            ),
            user_msg=user_msg,
            max_tokens=_STANDING_MAX_TOKENS,
            timeout=_DERIVE_TIMEOUT_S,
            no_change_tokens=(NO_CHANGE_SENTINEL,),
        )
        if turn.status == "router_disabled":
            record_execution_event(
                client, user_id=user_id, slug=f"standing-write:{topic}",
                mode="judgment", trigger_type="scheduled", status="skipped",
                error_reason="router_disabled",
                funnel_decision="standing", principal_id=user_id,
            )
            return {"success": False, "slug": decl.slug, "error_reason": "router_disabled"}
        if turn.status == "raised":
            logger.error("[STANDING] derive failed for %s/%s: %s", user_id[:8], decl.slug, turn.error)
            record_execution_event(
                client, user_id=user_id, slug=f"standing-write:{topic}",
                mode="judgment", trigger_type="scheduled", status="failed",
                error_reason="derive_raised", error_detail=(turn.error or "")[:500],
                funnel_decision="standing", principal_id=user_id,
            )
            return {"success": False, "slug": decl.slug, "error_reason": "derive_raised"}
        write_mode = "judgment"
        ledger_model = turn.ledger_model
        usage = turn.usage
        if turn.status == "no_change":
            record_execution_event(
                client, user_id=user_id, slug=f"standing-write:{topic}",
                mode="judgment", trigger_type="scheduled", status="skipped",
                error_reason="no_change", model=ledger_model,
                funnel_decision="standing", principal_id=user_id, **usage,
            )
            return {"success": True, "slug": decl.slug, "no_change": True}
        text = turn.text
        content = text + ("\n" if not text.endswith("\n") else "")

    write_ms = int((datetime.now(timezone.utc) - write_started).total_seconds() * 1000)

    # An unchanged pull is an honest no-op — no manufactured revision.
    if current is not None and content == current:
        record_execution_event(
            client, user_id=user_id, slug=f"standing-write:{topic}",
            mode=write_mode, trigger_type="scheduled", status="skipped",
            error_reason="no_change", model=ledger_model,
            duration_ms=write_ms, funnel_decision="standing",
            principal_id=user_id, **usage,
        )
        return {"success": True, "slug": decl.slug, "no_change": True}

    # ── 3. place + cite — CONFINED to the designated leaf ONLY (D3) ───────
    path = decl.target_path
    _assert_standing_write(decl, path)

    from services.authored_substrate import write_revision
    revision_id = write_revision(
        client,
        user_id=user_id,
        path=path,
        content=content,
        # Machinery, no face (ADR-596 D1 / ADR-639 D5): the fact is the ledger.
        authored_by="system:standing",
        message=f"kept '{decl.target}' current "
                f"(standing run, {len(bodies)} source{'s' if len(bodies) != 1 else ''})",
        revision_kind="derivation",
        derived_from=raw_paths,
    )

    # ── 4. embed (retrieval — a maintained file nobody can recall is dead) ─
    try:
        from services.primitives.workspace import _embed_workspace_file
        await _embed_workspace_file(client, user_id, path, content)
    except Exception as e:
        logger.warning("[STANDING] embed failed for %s: %s", path, e)

    # ── 5. meter ──────────────────────────────────────────────────────────
    record_execution_event(
        client, user_id=user_id, slug=f"standing-write:{topic}",
        mode=write_mode, trigger_type="scheduled", status="success",
        model=ledger_model, duration_ms=write_ms,
        funnel_decision="standing", principal_id=user_id, **usage,
    )

    logger.info("[STANDING] %s/%s → %s (rev %s)", user_id[:8], decl.slug, path, revision_id[:8])
    return {"success": True, "slug": decl.slug, "target_path": path,
            "revision_id": revision_id}


# ---------------------------------------------------------------------------
# The scheduler-tick entry point — an ADAPTER on the one drain loop (ADR-639 D3)
# ---------------------------------------------------------------------------


async def _due_standing(client, now: datetime) -> list[tuple[str, StandingDecl, Optional[str]]]:
    """Discover, sync the index, and return the rows due now — each with the
    stored `next_run_at` the claim compares against. Paused and problem
    declarations never reach the loop (a problem is a loud repair state, not
    a failure to retry)."""
    decls_by_user = discover_standing(client)
    for uid, decls in decls_by_user.items():
        try:
            await materialize_standing_index(client, uid, decls, now=now)
        except Exception as e:  # noqa: BLE001
            logger.warning("[STANDING] materialize failed for %s: %s", uid[:8], e)

    due_rows = (
        client.table("tasks")
        .select("id, user_id, slug, next_run_at")
        .eq("status", "active")
        .eq("kind", STANDING_KIND)
        .lte("next_run_at", now.isoformat())
        .execute()
    ).data or []

    out: list[tuple[str, StandingDecl, Optional[str]]] = []
    for row in due_rows:
        uid = row["user_id"]
        decl = next(
            (d for d in decls_by_user.get(uid, []) if d.slug == row.get("slug")), None
        )
        if decl is None or decl.paused or decl.problem is not None:
            continue
        out.append((uid, decl, row.get("next_run_at")))
    return out


def _record_standing(client, user_id: str, decl: StandingDecl, last_run_at: datetime) -> None:
    from services.scheduling import record_run

    record_run(client, user_id, decl, STANDING_KIND, last_run_at=last_run_at)


async def drain_due_standing_work(client) -> tuple[int, int, int]:
    """Discover declarations, sync the kind='standing' index, run the due ones
    through the ONE drain loop. Returns (found, succeeded, failed). Zero
    declarations → one LIKE scan, nothing else."""
    from services.scheduling import drain_due

    return await drain_due(
        client, STANDING_KIND,
        due=_due_standing, run=run_standing_sweep, record=_record_standing,
    )


__all__ = [
    "STANDING_KIND",
    "DECLARATION_LEAF",
    "CONTRACT_LEAF",
    "SUPPORTED_FORMATS",
    "NO_CHANGE_SENTINEL",
    "KEEPING_SKILL",
    "DECLARATION_KEYS",
    "StandingDecl",
    "ShapeViolation",
    "topic_from_declaration_path",
    "parse_standing_yaml",
    "discover_standing",
    "materialize_standing_index",
    "read_standing_task_row",
    "resolve_executor",
    "map_structured",
    "build_standing_job",
    "run_standing_sweep",
    "drain_due_standing_work",
]
