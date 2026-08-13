"""AI Radar — the standing sweep lane (ADR-486 R0, re-cut by ADR-564/565).

The first standing (unaddressed) derive organ. A HUB is one meaning-folder
under ``operation/`` (any depth — ADR-565 D3) carrying:

    _radar.yaml     — pure machine config (ADR-254 underscore-yaml):
                        schedule: "0 13 * * *"   # UTC cron | @-semantic | list
                        paused: false
                        sources:                 # the TrackWebSources shape
                          - id: anthropic-blog   # (ADR-336) — the file IS the
                            url: https://...     # watch declaration
    CRITERION.md    — the member's declaration of what matters here
                      (ADR-564 D2 — prose, operator/lane-authored, NEVER
                      machine-parsed; the retired `prompt:` steer key's
                      successor)
    report.md       — the LIVING REPORT (ADR-565 D1): the folder's current
                      understanding, revised per sweep; the revision chain is
                      the delta history

One sweep = the ADR-486 D4 loop with the ADR-565 artifact:

    intake  — TrackWebSources fetches the declared sources, retains raws
              (revision_kind='observation', inbound/web/), distills
              ``{hub}/_watch_signal.yaml``  (mechanical, $0)
    derive  — ONE bounded judgment turn, governed by the CRITERION, folds the
              fresh signal into the current report (member edits in the head
              are corrections to preserve — correction-compounds). The model
              returns the full revised report, or the exact token NO_CHANGE
              (an empty sweep honestly reported — falsifier 4 counts these)
    place   — kernel-deterministic: the fixed leaf ``report.md``; the write is
              CONFINED to the hub subtree (ADR-564 D6 / ADR-565 D4)
    cite    — write_revision(revision_kind='derivation',
              derived_from=[signal + the sweep's raw observations])
    embed   — the retrieval fix (recall reads the report head)
    meter   — two execution_events rows per sweep (slugs UNCHANGED across the
              re-cut so every ledger reader keeps working):
              ``radar-sweep:{topic}``  (mechanical intake — falsifier 4 denominator)
              ``radar-brief:{topic}``  (judgment derive — falsifier 2/4 numerator;
              status='skipped' + error_reason='no_change' on NO_CHANGE)

The pre-ADR-565 dated-brief shelf (``briefs/{date}-{slug}.md``) is superseded;
existing briefs stay on the record, new sweeps stop adding to the shelf.

Scheduling rides the thin ``tasks`` index with ``kind='radar'`` (the ADR-393
precedent — one index, one CAS-claim mechanism, one market-context resolver;
kind-disjoint from 'judgment' recurrences + 'capture' rows). The drainer runs
in the scheduler tick inside AGENT_ENABLED but NOT behind
CONNECTOR_CAPTURE_ENABLED — radar hubs run on web watches + the commons; the
capture lane's dormancy is a connector decision, not a standing-sweep one
(ADR-486 §5, ADR-404 explicitly not reversed).

Standing intent lives on the DECLARATION, never on an agent (ADR-486 D3 —
ADR-460's no-authority discipline untouched). The loop is watch → observe →
derive → compose: reads, intake, derivation. Nothing here approaches the
ADR-307 consequential gate.

Attribution (ADR-209/288): intake writes as ``system:track-web-sources`` (the
primitive asserts its own actor); the brief writes as ``system:radar`` — the
``system:extract`` precedent (a kernel-run derive with no member turn); the
model rides the execution_events row, the sweep provenance rides the revision
message (the settle lesson: version messages are permanent, file metadata is
overwritten by the next revision).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Union

import yaml as _yaml

logger = logging.getLogger(__name__)

RADAR_KIND = "radar"

#: Hub declarations live at {folder}/_radar.yaml under operation/, any depth
#: (ADR-565 D3 — the single-level rule was an R0 scan simplification, never a
#: decision). A declaration INSIDE another hub's subtree is refused loudly in
#: discovery (nested criteria are named-deferred, ADR-565 D3).
_OPERATION_PREFIX = "/workspace/operation/"
RADAR_DECLARATION_LEAF = "_radar.yaml"

#: Per hub: the distilled signal, the criterion, the living report — and the
#: superseded briefs shelf (legacy reads only; new sweeps never write it).
SIGNAL_LEAF = "_watch_signal.yaml"
CRITERION_LEAF = "CRITERION.md"
REPORT_LEAF = "report.md"
BRIEFS_DIR = "briefs"

#: One bounded judgment turn. The ceiling is the JOB's: a living report is a
#: bounded document (~150 lines contracted), not an unbounded delta — the
#: 2048-token brief ceiling truncated 14 of 20 briefs mid-thought (ADR-565 §1).
_REPORT_MAX_TOKENS = 4096
_DERIVE_TIMEOUT_S = 120.0


# ── placement (kernel-deterministic; the model never holds these levers) ─────
#
# `extract_title` / `strip_fence` were `services/settle.py`'s until ADR-507
# deleted that module; re-homed here as the mechanics of placing ANY derived
# note. Settle's third helper, `_unique_path` (collision-suffix placement),
# retired with the dated-brief shelf (ADR-565 D1): the report is a FIXED leaf
# whose history lives on the revision chain, so there is no collision to dodge.


def extract_title(note: str) -> str:
    """The note's title, from its leading `# Title` line. Pure.

    Falls back to the first non-empty line, then to a generic. The model is
    contracted to lead with `# Title`; this never trusts that blindly.
    """
    for line in (note or "").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            return s.lstrip("#").strip() or "Untitled note"
        return s[:120]
    return "Untitled note"


def strip_fence(note: str) -> str:
    """Drop a whole-note ``` fence if the model wrapped it despite the contract.

    Pure. Only strips when the note OPENS with a fence and CLOSES with one —
    a fenced code block *inside* the note is content and stays.
    """
    s = (note or "").strip()
    if not s.startswith("```"):
        return s
    lines = s.splitlines()
    if len(lines) < 2 or not lines[-1].strip().startswith("```"):
        return s
    return "\n".join(lines[1:-1]).strip()


def extract_delta_headline(report: str) -> Optional[str]:
    """The first bullet under a "Recent developments" heading, if the report
    carries one — the sweep's delta, for the revision message (ADR-565 D1:
    the message carries the headline; the chain carries the delta). Pure."""
    in_recent = False
    for line in (report or "").splitlines():
        s = line.strip()
        if s.startswith("#") and "recent development" in s.lower():
            in_recent = True
            continue
        if in_recent:
            if s.startswith("#"):
                return None  # section ended without a bullet
            if s.startswith(("-", "*")):
                return s.lstrip("-* ").strip()[:140] or None
    return None


def _assert_hub_write(hub: "RadarHub", path: str) -> None:
    """ADR-564 D6 / ADR-565 D4 — the unattended sweep is write-confined to its
    hub subtree. A capability constraint asserted at the write site, never a
    read boundary. Raises rather than writes: a confined actor that would
    write outside its folder is a bug, not a judgment call."""
    if not (path == hub.root or path.startswith(hub.root + "/")):
        raise ValueError(
            f"radar write-confinement: {path!r} is outside hub root {hub.root!r}"
        )


def resolve_radar_resident() -> tuple[str, str]:
    """The sweep's resident colleague — Researcher (slug ``scout``).

    The Designer↔Studio precedent applied (operator-ratified 2026-07-28): a
    hardcoded model constant here was the same unnamed-engine smell as
    Studio's pre-Designer ``models[0]`` — an engine nobody chose answering
    "who swept this?". The agent ROW carries IDENTITY + ENGINE + CHARACTER
    (ADR-460/467); the radar posture below is the JOB overlay composed on
    top (character first, job second — the lane_runner order). No new agent
    was minted: the base roster is closed at three addressed operations
    (AGENT-TAXONOMY §5) and a sweep is un-addressed — it is Researcher's
    acquire/read operation running on a clock, so Researcher is the
    resident.

    The SLUG now comes from radar's registration above (ADR-562 D3) — one
    declaration, read back — while the model + posture still come from the
    agent row, which is where identity/engine/character live (ADR-460).

    Returns ``(model, character_posture)``.
    """
    import services.apps  # noqa: F401  (registration side-effect — see ADR-562)
    from services.agents_registry import KERNEL_AGENTS
    from services.authoring import resident_for_app

    slug = resident_for_app("radar") or "scout"
    row = KERNEL_AGENTS[slug]
    return row["model"], row["posture"]

#: The empty-sweep sentinel the posture contracts. Falsifier 4's honest zero.
#: "NO_BRIEF" is the pre-ADR-565 spelling, accepted at runtime so an engine
#: echoing the old contract mid-deploy still reads as an honest empty sweep.
NO_CHANGE_SENTINEL = "NO_CHANGE"
_EMPTY_SWEEP_TOKENS = {NO_CHANGE_SENTINEL, "NO_BRIEF"}

Schedule = Optional[Union[str, list[str]]]


# ---------------------------------------------------------------------------
# Declaration — parse + walk
# ---------------------------------------------------------------------------


@dataclass
class RadarHub:
    """One parsed hub declaration. Structurally compatible with
    ``services.scheduling.compute_next_run_at`` (slug/schedule/paused/
    paused_until/options — the CaptureDeclaration precedent)."""

    topic: str
    slug: str  # "radar:{topic}" — disjoint from recurrence + capture slugs
    schedule: Schedule = None
    paused: bool = False
    paused_until: Optional[datetime] = None
    options: dict = field(default_factory=dict)  # prompt steer et al.
    declaration_path: str = ""
    user_id: Optional[str] = None

    @property
    def root(self) -> str:
        return f"{_OPERATION_PREFIX}{self.topic}"

    @property
    def signal_path(self) -> str:
        return f"{self.root}/{SIGNAL_LEAF}"

    @property
    def criterion_path(self) -> str:
        return f"{self.root}/{CRITERION_LEAF}"

    @property
    def report_path(self) -> str:
        return f"{self.root}/{REPORT_LEAF}"


def topic_from_declaration_path(path: str) -> Optional[str]:
    """``/workspace/operation/{folder...}/_radar.yaml`` → the folder path
    relative to ``operation/`` (the topic identifier). Pure.

    Any depth is a valid hub (ADR-565 D3 — a hub attaches to any
    meaning-folder; the old single-segment rule was an R0 scan
    simplification). None for paths outside the convention. Nesting one hub
    INSIDE another is refused at discovery, not here — this parser has no
    cross-hub knowledge.
    """
    p = (path or "").strip()
    if not p.startswith(_OPERATION_PREFIX) or not p.endswith(f"/{RADAR_DECLARATION_LEAF}"):
        return None
    middle = p[len(_OPERATION_PREFIX):-(len(RADAR_DECLARATION_LEAF) + 1)]
    parts = [s for s in middle.split("/") if s]
    return "/".join(parts) if parts else None


def parse_radar_yaml(
    content: str, *, topic: str, declaration_path: str, user_id: Optional[str] = None
) -> Optional[RadarHub]:
    """Parse one ``_radar.yaml`` body into a RadarHub. None on unparseable.

    ``sources:`` stays IN the file for TrackWebSources to read directly (the
    file is both the hub declaration and the watch declaration — one file,
    one writer, ADR-286). This parser only lifts the scheduling + steer keys.
    """
    if not content or not content.strip():
        return None
    try:
        parsed = _yaml.safe_load(_strip_tier_frontmatter(content))
    except _yaml.YAMLError as e:
        logger.warning("[RADAR] %s unparseable: %s", declaration_path, e)
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

    options = {
        k: v for k, v in parsed.items()
        if k not in {"schedule", "paused", "paused_until", "sources"}
    }

    return RadarHub(
        topic=topic,
        slug=f"radar:{topic}",
        schedule=schedule,
        paused=bool(parsed.get("paused", False)),
        paused_until=_coerce_datetime(parsed.get("paused_until")),
        options=options,
        declaration_path=declaration_path,
        user_id=user_id,
    )


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


def discover_radar_hubs(client, *, workspace_id: Optional[str] = None) -> dict[str, list[RadarHub]]:
    """All hub declarations, grouped by the OWNER user_id of their workspace.

    One LIKE scan — the whole lane's cost when zero hubs are declared. The
    global scan is the R0 shape (no write-time materialization exists yet);
    R1's authoring route also materializes on write.

    `workspace_id` (ADR-501, Hat-B 2026-07-29) scopes the scan to ONE
    workspace for the request path. The scheduler omits it and keeps the
    global sweep. Two things made a member's radar dark without it: the scan
    read `user_id` off the FILE (the author — kvk), so a member's lookup key
    never matched; and an unscoped scan through a member's own RLS-filtered
    client returns their rows, not the workspace's. Scanning by workspace
    fixes both — `workspace_files` RLS is already grant-aware (migration 189),
    so a member's client legitimately sees the shared workspace's files.
    """
    try:
        q = (
            client.table("workspace_files")
            .select("user_id, workspace_id, path, content")
            .like("path", f"{_OPERATION_PREFIX}%/{RADAR_DECLARATION_LEAF}")
        )
        if workspace_id:
            q = q.eq("workspace_id", workspace_id)
        rows = q.execute().data or []
    except Exception as e:
        logger.warning("[RADAR] hub discovery scan failed: %s", e)
        return {}

    # The GROUPING KEY is the workspace's OWNER, not the file's author. Both
    # the request path (`_acting_owner`) and the scheduler (whose contract is
    # "user_id = workspace owner UUID") look up by that key; keying on the
    # author meant a hub authored by a member was filed under the member and
    # invisible to the workspace — and a hub authored by the owner was
    # unreachable for the member. Resolved once per workspace, owner-cached.
    from services.workspace_context import acting_workspace_owner

    owner_of: dict[str, str] = {}

    def _owner(row: dict) -> Optional[str]:
        ws = row.get("workspace_id")
        if not ws:
            return row.get("user_id")  # pre-re-key row (N=1): the author IS the owner
        if ws not in owner_of:
            try:
                # SERVICE client, deliberately: `workspaces` RLS is
                # `owner_id = auth.uid()`, so a MEMBER resolving their own
                # granted workspace's owner reads zero rows and falls back to
                # the file's author — a key their request never looks up
                # under, leaving the hub list empty (probe-verified). The
                # owner id of a workspace the caller is already authorized in
                # is not a secret; the authorization happened upstream (the
                # scan is scoped to the acting workspace, and workspace_files
                # RLS is grant-aware).
                from services.supabase import get_service_client

                res = (
                    get_service_client()
                    .table("workspaces").select("owner_id").eq("id", ws).limit(1).execute()
                ).data or []
                owner_of[ws] = (res[0].get("owner_id") if res else None) or row.get("user_id")
            except Exception:  # noqa: BLE001 — fall back to the author
                owner_of[ws] = row.get("user_id")
        return owner_of[ws]

    by_user: dict[str, list[RadarHub]] = {}
    for row in rows:
        path = row.get("path") or ""
        topic = topic_from_declaration_path(path)
        if topic is None:
            logger.warning("[RADAR] %s is not a hub declaration path; skipping", path)
            continue
        key = _owner(row)
        if not key:
            continue
        hub = parse_radar_yaml(
            row.get("content") or "",
            topic=topic,
            declaration_path=path,
            user_id=key,
        )
        if hub is None:
            continue
        by_user.setdefault(key, []).append(hub)

    # Nested criteria are named-deferred (ADR-565 D3): a declaration inside
    # another hub's subtree is refused LOUDLY, never silently — the outer hub
    # keeps governing its whole subtree (the cascade rule waits for a real
    # case). Refusal keys on the folder boundary, not string prefix.
    for key, hubs in by_user.items():
        roots = {h.topic for h in hubs}
        kept: list[RadarHub] = []
        for h in hubs:
            ancestors = [t for t in roots
                         if t != h.topic and h.topic.startswith(t + "/")]
            if ancestors:
                logger.warning(
                    "[RADAR] hub %r is nested inside hub %r — refused "
                    "(nested criteria are named-deferred, ADR-565 D3)",
                    h.topic, min(ancestors, key=len),
                )
                continue
            kept.append(h)
        by_user[key] = kept
    return by_user


# ---------------------------------------------------------------------------
# Scheduling — the kind='radar' slice of the tasks index (ADR-393 precedent)
# ---------------------------------------------------------------------------


async def materialize_radar_index(
    client, user_id: str, hubs: list[RadarHub], *, now: Optional[datetime] = None
) -> int:
    """Sync the tasks index (kind='radar' rows) against this user's hubs.

    Idempotent; only touches its own kind (the disjointness invariant the
    recurrence materializer now also honors). Returns rows touched.
    """
    from services.scheduling import compute_next_run_at, _parse_iso
    from services.schedule_utils import get_user_timezone

    if now is None:
        now = datetime.now(timezone.utc)
    by_slug = {h.slug: h for h in hubs}

    try:
        existing = (
            client.table("tasks")
            .select("id, slug, last_run_at, next_run_at, kind")
            .eq("user_id", user_id)
            .eq("kind", RADAR_KIND)
            .execute()
        )
        existing_by_slug = {r["slug"]: r for r in (existing.data or [])}
    except Exception as e:
        logger.warning("[RADAR_SCHED] index read failed for %s: %s", user_id[:8], e)
        return 0

    user_tz = get_user_timezone(client, user_id)
    touched = 0

    for slug, hub in by_slug.items():
        existing_row = existing_by_slug.get(slug)
        last_run_at = _parse_iso(existing_row.get("last_run_at") if existing_row else None)
        try:
            next_run = compute_next_run_at(
                hub, last_run_at=last_run_at, now=now, user_timezone=user_tz,
            )
        except ValueError as e:
            logger.error("[RADAR_SCHED] %s/%s schedule resolution failed: %s",
                         user_id[:8], slug, e)
            next_run = None

        import json as _json
        row = {
            "user_id": user_id,
            "slug": slug,
            "status": "active",
            "kind": RADAR_KIND,
            "schedule": _json.dumps(hub.schedule) if isinstance(hub.schedule, list) else hub.schedule,
            "next_run_at": next_run.isoformat() if next_run else None,
            "declaration_path": hub.declaration_path,
            "paused": hub.paused,
        }
        try:
            if existing_row:
                client.table("tasks").update(row).eq("id", existing_row["id"]).execute()
            else:
                client.table("tasks").insert(row).execute()
            touched += 1
        except Exception as e:
            logger.warning("[RADAR_SCHED] upsert failed for %s/%s: %s", user_id[:8], slug, e)

    for slug, existing_row in existing_by_slug.items():
        if slug not in by_slug:
            try:
                client.table("tasks").delete().eq("id", existing_row["id"]).execute()
                touched += 1
                logger.info("[RADAR_SCHED] dropped radar row %s/%s (declaration gone)",
                            user_id[:8], slug)
            except Exception as e:
                logger.warning("[RADAR_SCHED] delete failed for %s/%s: %s", user_id[:8], slug, e)

    return touched


def claim_radar_run(client, user_id: str, slug: str, original_next_run: Optional[str],
                    *, sentinel_hours: int = 2) -> bool:
    """CAS atomic claim, kind-scoped (the capture mechanism verbatim)."""
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
            .eq("kind", RADAR_KIND)
            .eq("next_run_at", original_next_run)
            .execute()
        )
        return bool(result.data)
    except Exception as e:
        logger.warning("[RADAR_SCHED] claim failed for %s/%s: %s", user_id[:8], slug, e)
        return False


def record_radar_run(client, user_id: str, hub: RadarHub, *, last_run_at: datetime) -> None:
    """Advance last_run_at + next_run_at post-sweep (clears the CAS sentinel)."""
    from services.scheduling import compute_next_run_at
    from services.schedule_utils import get_user_timezone

    try:
        next_run = compute_next_run_at(
            hub, last_run_at=last_run_at, now=last_run_at,
            user_timezone=get_user_timezone(client, user_id),
        )
    except ValueError:
        next_run = None
    try:
        client.table("tasks").update({
            "last_run_at": last_run_at.isoformat(),
            "next_run_at": next_run.isoformat() if next_run else None,
        }).eq("user_id", user_id).eq("slug", hub.slug).eq("kind", RADAR_KIND).execute()
    except Exception as e:
        logger.warning("[RADAR_SCHED] record run failed for %s/%s: %s", user_id[:8], hub.slug, e)


# ---------------------------------------------------------------------------
# The sweep — intake → derive → place → cite → embed → meter
# ---------------------------------------------------------------------------


class _RadarAuth:
    """Auth shape for the intake primitive (the _CaptureAuth precedent)."""

    def __init__(self, user_id: str, client: Any):
        self.user_id = user_id
        self.client = client
        self.caller_identity = "system:radar"


#: The report posture — the JOB overlay, composed at sweep time UNDER the
#: resident's character (Researcher's row posture leads; this section follows
#: — the lane_runner character-then-job order). Never stored. Carries ONLY
#: what the model needs to distill; the kernel holds placement/citation/embed
#: (the settle division of labour). The hub's CRITERION rides the user message
#: (per-hub content beside the report + signal), not this overlay.
_RADAR_POSTURE = """THE STANDING RADAR JOB — the living report for "{topic}".

A scheduled sweep fired in the member's workspace. Nobody is present; the
report you maintain will be read later. You are handed THE CRITERION (the
member's declaration of what matters in this folder), THE CURRENT REPORT
(the folder's living understanding — it may carry the member's own edits;
treat those as corrections to preserve, never as noise), and THE FRESH WATCH
SIGNAL (entries fetched just now from the declared sources).

Return the FULL REVISED REPORT: fold what the signal changes into the current
understanding, under the criterion. Selection IS the job — nobody will refine
this query; what the criterion excludes stays out, however interesting.

THE BAR
- If the signal changes nothing under the criterion, reply with exactly:
  NO_CHANGE
  An empty sweep honestly reported beats a manufactured update — never pad.
- Under ~150 lines. The report is the current understanding, not a log —
  fold, don't append; prune what has stopped mattering.
- Preserve the member's corrections and voice where the signal doesn't
  contradict them; when it does, update the claim and cite why.
- Every new claim cites its signal entry's url inline as a markdown link.
  NEVER invent facts, numbers, or sources.

THE SHAPE
- A `# Title` first line naming the topic's current picture.
- A short "## Recent developments" section first — what this sweep changed,
  as dated bullets (prune bullets older than a few sweeps).
- Then the standing sections of the understanding itself.

THE OUTPUT CONTRACT
Return the full report's markdown and NOTHING else — or the exact token
NO_CHANGE. No preamble, no code fence around the whole thing.
"""


def build_radar_posture(topic: str) -> str:
    """The sweep's derive posture — pure. (The pre-ADR-565 `steer` parameter
    is retired with the `prompt:` key; the criterion rides the user message.)"""
    return _RADAR_POSTURE.format(topic=topic)


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
        logger.warning("[RADAR] read failed for %s: %s", path, e)
        return None


def _read_criterion(client, user_id: str, hub: RadarHub) -> Optional[str]:
    """The hub's criterion body (`CRITERION.md`), or — migration fallback —
    the legacy `prompt:` steer still sitting in a pre-ADR-565 declaration.
    The fallback exists ONLY so a legacy hub keeps its steer until its first
    touch migrates it (routes/radar.py writes the criterion file on the next
    authoring pass); it is not a second home for the criterion."""
    body = _read_file(client, user_id, hub.criterion_path)
    if body and body.strip():
        return body
    legacy = hub.options.get("prompt")
    return legacy if isinstance(legacy, str) and legacy.strip() else None


async def run_radar_sweep(client, user_id: str, hub: RadarHub) -> dict:
    """One sweep of one hub. Returns {success, slug, report_path?, no_change?,
    error_reason?}. Never raises past its own boundary — the drainer records
    the run either way.
    """
    from services.telemetry import record_execution_event

    started = datetime.now(timezone.utc)
    auth = _RadarAuth(user_id, client)

    # ── 1. intake (mechanical, $0) — TrackWebSources reads _radar.yaml's
    #       `sources:` key directly and distills the hub's signal ─────────
    from services.primitives.track_web_sources import handle_track_web_sources
    try:
        intake = await handle_track_web_sources(auth, {
            "declaration": hub.declaration_path,
            "distills_to": hub.signal_path,
        })
    except Exception as e:
        logger.exception("[RADAR] intake raised for %s/%s: %s", user_id[:8], hub.slug, e)
        intake = {"success": False, "error": f"intake_raised:{e}", "items_processed": 0,
                  "paths_written": [], "errors": [str(e)]}

    items = int(intake.get("items_processed") or 0)
    sweep_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
    sweep_ok = bool(intake.get("success")) and items > 0
    record_execution_event(
        client, user_id=user_id, slug=f"radar-sweep:{hub.topic}",
        mode="mechanical", trigger_type="scheduled",
        status="success" if sweep_ok else "failed",
        error_reason=None if sweep_ok else (intake.get("error") or "no_sources_fetched"),
        duration_ms=sweep_ms, funnel_decision="radar",
        # ADR-445 attribution carve: the standing sweep runs FOR the workspace on
        # the cron — the owner is the accountable principal (the recurrence/wake
        # convention). Costed rows must never land in the NULL bucket.
        principal_id=user_id,
    )
    if not sweep_ok:
        return {"success": False, "slug": hub.slug,
                "error_reason": intake.get("error") or "no_sources_fetched"}

    paths_written = [p for p in (intake.get("paths_written") or []) if p]
    signal_path = paths_written[0] if paths_written else hub.signal_path
    raw_paths = paths_written[1:]

    # ── 2. derive (one bounded, criterion-governed judgment turn, no tools).
    #      The current report HEAD is the previous understanding — member
    #      edits included, which is what makes correction compound
    #      (ADR-565 D1; single-head-many-authors, ADR-384 D4). ─────────────
    signal_body = _read_file(client, user_id, signal_path) or ""
    current_report = _read_file(client, user_id, hub.report_path)
    criterion = _read_criterion(client, user_id, hub)

    user_msg = (
        (f"THE CRITERION (what matters in this folder):\n\n{criterion}\n\n"
         if criterion else
         "THERE IS NO CRITERION DECLARED YET — hold a conservative bar: only "
         "clearly substantive developments on the folder's topic.\n\n")
        + (f"THE CURRENT REPORT:\n\n{current_report}\n\n" if current_report
           else "THERE IS NO REPORT YET — this is the hub's first sweep. "
                "Write the baseline report from what stands out in the signal.\n\n")
        + f"THE FRESH WATCH SIGNAL (just swept):\n\n{signal_body}\n"
    )

    # ADR-557 D1 — radar was the ONE routed caller with no flag check. The
    # transport now refuses (RouterDisabled) rather than reaching a provider on
    # whatever key is in env, but a sweep should still say WHY it produced no
    # brief: "the router is off" is configuration, not a failed derive, and
    # metering it as `derive_raised` would read as weather.
    from services.model_router import RouterDisabled, model_router_enabled, route_completion
    if not model_router_enabled():
        logger.info(
            "[RADAR] router off — skipping derive for %s/%s", user_id[:8], hub.slug,
        )
        record_execution_event(
            client, user_id=user_id, slug=f"radar-brief:{hub.topic}",
            mode="judgment", trigger_type="scheduled", status="skipped",
            error_reason="router_disabled",
            funnel_decision="radar", principal_id=user_id,
        )
        return {"success": False, "slug": hub.slug, "error_reason": "router_disabled"}

    resident_model, resident_character = resolve_radar_resident()
    derive_started = datetime.now(timezone.utc)
    try:
        routed = await route_completion(
            resident_model,
            [{"role": "user", "content": user_msg}],
            # Character first, job second — Researcher's row posture leads,
            # the radar job overlay follows (the lane_runner composition
            # order; see resolve_radar_resident).
            system=resident_character + "\n\n" + build_radar_posture(hub.topic),
            max_tokens=_REPORT_MAX_TOKENS,
            timeout=_DERIVE_TIMEOUT_S,
        )
    except Exception as e:
        logger.exception("[RADAR] derive failed for %s/%s: %s", user_id[:8], hub.slug, e)
        record_execution_event(
            client, user_id=user_id, slug=f"radar-brief:{hub.topic}",
            mode="judgment", trigger_type="scheduled", status="failed",
            error_reason="derive_raised", error_detail=str(e)[:500],
            funnel_decision="radar", principal_id=user_id,
        )
        return {"success": False, "slug": hub.slug, "error_reason": "derive_raised"}

    note = strip_fence(routed.text or "")
    derive_ms = int((datetime.now(timezone.utc) - derive_started).total_seconds() * 1000)

    if not note.strip() or note.strip() in _EMPTY_SWEEP_TOKENS:
        # The honest empty sweep — metered as skipped so falsifier 4 reads it.
        record_execution_event(
            client, user_id=user_id, slug=f"radar-brief:{hub.topic}",
            mode="judgment", trigger_type="scheduled", status="skipped",
            error_reason="no_change", model=routed.ledger_model,
            duration_ms=derive_ms, funnel_decision="radar", principal_id=user_id,
            **routed.usage,
        )
        return {"success": True, "slug": hub.slug, "no_change": True}

    # ── 3. place (kernel-deterministic: the FIXED report leaf — history is
    #       the revision chain, not the namespace; ADR-565 D1) + confine ───
    title = extract_title(note)
    path = hub.report_path
    _assert_hub_write(hub, path)

    # ── 4. write + cite (ADR-423 kind, ADR-448 edges). The revision message
    #       carries the sweep's delta headline — the chain IS the delta rail.
    headline = extract_delta_headline(note)
    from services.authored_substrate import write_revision
    revision_id = write_revision(
        client,
        user_id=user_id,
        path=path,
        content=note,
        # The face is the resident, the fact is the ledger (ADR-460 D2):
        # the member reads "Researcher"; authored_by stays the mechanism.
        authored_by="system:radar",
        message=(f"Researcher revised the living report: {headline}" if headline
                 else f"Researcher revised the living report for '{hub.topic}' "
                      f"(standing sweep, {items} sources)"),
        revision_kind="derivation",
        derived_from=[signal_path, *raw_paths],
    )

    # ── 5. embed (retrieval — a report nobody can recall is a dead report) ─
    try:
        from services.primitives.workspace import _embed_workspace_file
        await _embed_workspace_file(client, user_id, path, note)
    except Exception as e:
        logger.warning("[RADAR] embed failed for %s: %s", path, e)

    # ── 6. meter (falsifiers 2 + 4 key on this slug — UNCHANGED slugs) ────
    record_execution_event(
        client, user_id=user_id, slug=f"radar-brief:{hub.topic}",
        mode="judgment", trigger_type="scheduled", status="success",
        model=routed.ledger_model, duration_ms=derive_ms,
        funnel_decision="radar", principal_id=user_id, **routed.usage,
    )

    logger.info("[RADAR] %s/%s → %s (rev %s)", user_id[:8], hub.slug, path, revision_id[:8])
    return {"success": True, "slug": hub.slug, "report_path": path,
            "revision_id": revision_id, "title": title}


# ---------------------------------------------------------------------------
# Drainer — the scheduler-tick entry point
# ---------------------------------------------------------------------------


async def drain_due_radar_sweeps(client) -> tuple[int, int, int]:
    """Discover hubs, sync the kind='radar' index, run due sweeps.

    Returns (found, succeeded, failed). Zero hubs declared → one LIKE scan,
    nothing else — the lane costs nothing on an empty world.
    """
    now = datetime.now(timezone.utc)
    hubs_by_user = discover_radar_hubs(client)

    # Sync index for every user with hubs; also drop stale rows for users
    # whose last declaration vanished (their rows surface in the due query
    # with no matching declaration and get cleaned on the next authoring
    # write — R0 accepts that; the due path below skips them safely).
    for uid, hubs in hubs_by_user.items():
        try:
            await materialize_radar_index(client, uid, hubs, now=now)
        except Exception as e:
            logger.warning("[RADAR] materialize failed for %s: %s", uid[:8], e)

    # Due rows, kind-scoped.
    try:
        due_rows = (
            client.table("tasks")
            .select("id, user_id, slug, next_run_at")
            .eq("status", "active")
            .eq("kind", RADAR_KIND)
            .lte("next_run_at", now.isoformat())
            .execute()
        ).data or []
    except Exception as e:
        logger.warning("[RADAR] due query failed: %s", e)
        return 0, 0, 0

    found = succeeded = failed = 0
    for row in due_rows:
        uid = row["user_id"]
        hub = next(
            (h for h in hubs_by_user.get(uid, []) if h.slug == row.get("slug")), None
        )
        if hub is None or hub.paused:
            continue
        found += 1

        if not claim_radar_run(client, uid, hub.slug, row.get("next_run_at")):
            continue
        try:
            result = await run_radar_sweep(client, uid, hub)
            if result.get("success"):
                succeeded += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            logger.exception("[RADAR] sweep raised for %s/%s: %s", uid[:8], hub.slug, e)
        finally:
            try:
                record_radar_run(client, uid, hub, last_run_at=datetime.now(timezone.utc))
            except Exception as e:
                logger.warning("[RADAR] record run failed for %s/%s: %s", uid[:8], hub.slug, e)

    return found, succeeded, failed


__all__ = [
    "RADAR_KIND",
    "RADAR_DECLARATION_LEAF",
    "CRITERION_LEAF",
    "REPORT_LEAF",
    "resolve_radar_resident",
    "NO_CHANGE_SENTINEL",
    "RadarHub",
    "topic_from_declaration_path",
    "parse_radar_yaml",
    "discover_radar_hubs",
    "materialize_radar_index",
    "claim_radar_run",
    "record_radar_run",
    "build_radar_posture",
    "run_radar_sweep",
    "drain_due_radar_sweeps",
]
