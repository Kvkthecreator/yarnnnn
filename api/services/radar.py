"""AI Radar — the standing sweep lane (ADR-486 R0).

The first standing (unaddressed) derive organ. A HUB is one meaning-folder
``operation/{topic}/`` carrying a machine-parsed declaration ``_radar.yaml``:

    # _radar.yaml — AI Radar hub declaration (ADR-486)
    schedule: "0 13 * * *"        # UTC cron | @-semantic | list (ADR-268 grammar)
    paused: false
    prompt: |                     # optional operator steer for the brief
      Watch for pricing moves.
    sources:                      # the TrackWebSources shape (ADR-336) — this
      - id: anthropic-blog        # file IS the watch declaration; the intake
        url: https://...          # primitive reads its `sources:` key directly

One sweep = the ADR-486 D4 loop, the settle pattern made standing:

    intake  — TrackWebSources fetches the declared sources, retains raws
              (revision_kind='observation', inbound/web/), distills
              ``operation/{topic}/_watch_signal.yaml``  (mechanical, $0)
    derive  — ONE bounded judgment turn distills what CHANGED against the
              hub's previous brief. The model returns CONTENT ONLY; it may
              return the exact token NO_BRIEF (an empty sweep honestly
              reported — falsifier 4 counts these)
    place   — kernel-deterministic: ``operation/{topic}/briefs/{date}-{slug}.md``
              (never overwrites — collision suffixes, the settle rule)
    cite    — write_revision(revision_kind='derivation',
              derived_from=[signal + the sweep's raw observations])
    embed   — the retrieval fix (recall reads briefs)
    meter   — two execution_events rows per sweep:
              ``radar-sweep:{topic}``  (mechanical intake — falsifier 4 denominator)
              ``radar-brief:{topic}``  (judgment derive — falsifier 2/4 numerator;
              status='skipped' + error_reason='no_brief' on NO_BRIEF)

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

#: Hub declarations live at operation/{topic}/_radar.yaml — single-level topic
#: folders only (the D4 meaning-folder convention; deeper nesting is skipped
#: loudly, never silently).
_OPERATION_PREFIX = "/workspace/operation/"
RADAR_DECLARATION_LEAF = "_radar.yaml"

#: The distilled signal + the briefs shelf, per hub.
SIGNAL_LEAF = "_watch_signal.yaml"
BRIEFS_DIR = "briefs"

#: One bounded judgment turn — a brief is ~80 lines, not a report.
RADAR_MODEL = "anthropic/claude-sonnet-4-6"
_BRIEF_MAX_TOKENS = 2048
_BRIEF_TIMEOUT_S = 120.0

#: The empty-sweep sentinel the posture contracts. Falsifier 4's honest zero.
NO_BRIEF_SENTINEL = "NO_BRIEF"

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


def topic_from_declaration_path(path: str) -> Optional[str]:
    """``/workspace/operation/{topic}/_radar.yaml`` → ``topic``. Pure.

    None for anything else — including deeper nesting (a hub is ONE
    single-level meaning-folder; ``operation/a/b/_radar.yaml`` is not a hub).
    """
    p = (path or "").strip()
    if not p.startswith(_OPERATION_PREFIX) or not p.endswith(f"/{RADAR_DECLARATION_LEAF}"):
        return None
    middle = p[len(_OPERATION_PREFIX):-(len(RADAR_DECLARATION_LEAF) + 1)]
    parts = [s for s in middle.split("/") if s]
    return parts[0] if len(parts) == 1 else None


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


def discover_radar_hubs(client) -> dict[str, list[RadarHub]]:
    """All hub declarations across all workspaces, grouped by user_id.

    One LIKE scan — the whole lane's cost when zero hubs are declared. The
    global scan is the R0 shape (no write-time materialization exists yet);
    R1's authoring route also materializes on write.
    """
    try:
        rows = (
            client.table("workspace_files")
            .select("user_id, path, content")
            .like("path", f"{_OPERATION_PREFIX}%/{RADAR_DECLARATION_LEAF}")
            .execute()
        ).data or []
    except Exception as e:
        logger.warning("[RADAR] hub discovery scan failed: %s", e)
        return {}

    by_user: dict[str, list[RadarHub]] = {}
    for row in rows:
        path = row.get("path") or ""
        topic = topic_from_declaration_path(path)
        if topic is None:
            logger.warning("[RADAR] %s is not a single-level hub declaration; skipping", path)
            continue
        hub = parse_radar_yaml(
            row.get("content") or "",
            topic=topic,
            declaration_path=path,
            user_id=row.get("user_id"),
        )
        if hub is None:
            continue
        by_user.setdefault(row["user_id"], []).append(hub)
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


#: The brief posture — composed at sweep time, never stored. Carries ONLY what
#: the model needs to distill; the kernel holds placement/citation/embed (the
#: settle division of labour).
_RADAR_POSTURE = """You are the standing radar on "{topic}" — a scheduled sweep \
in a YARNNN workspace. Nobody is present; your brief will be read later.

THE JOB
You are handed the fresh watch signal (distilled entries from the hub's declared
web sources, fetched just now) and the hub's previous brief (if one exists).
Write ONE brief: what changed on this topic that matters, since the previous brief.
{steer}
THE BAR
- If nothing meaningfully NEW appears in the signal versus the previous brief,
  reply with exactly: NO_BRIEF
  An empty sweep honestly reported beats a manufactured insight — never pad.
- Under ~80 lines. Selective beats complete: drop what a reader wouldn't act on.
- Every claim traceable to an entry in the signal — cite the entry's url inline
  as a markdown link. NEVER invent facts, numbers, or sources.

THE SHAPE
- A `# Title` first line naming what changed — not "Radar brief".
- The delta: what is new and why it matters for this topic.
- Optionally end with "Watching:" — threads likely to matter next sweep.

THE OUTPUT CONTRACT
Return the brief's markdown and NOTHING else — or the exact token NO_BRIEF.
No preamble, no code fence around the whole thing.
"""


def build_radar_posture(topic: str, steer: Optional[str] = None) -> str:
    """The sweep's derive posture — pure."""
    steer_block = ""
    if steer and steer.strip():
        steer_block = f"\nOPERATOR STEER\n{steer.strip()}\n"
    return _RADAR_POSTURE.format(topic=topic, steer=steer_block)


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


def _latest_brief(client, user_id: str, hub: RadarHub) -> Optional[str]:
    """The hub's most recent brief body, or None. Date-prefixed leaf names
    sort chronologically, so max(path) is the latest."""
    try:
        rows = (
            client.table("workspace_files")
            .select("path, content")
            .eq("user_id", user_id)
            .like("path", f"{hub.root}/{BRIEFS_DIR}/%")
            .order("path", desc=True)
            .limit(1)
            .execute()
        ).data or []
        return rows[0].get("content") if rows else None
    except Exception as e:
        logger.warning("[RADAR] latest-brief read failed for %s: %s", hub.slug, e)
        return None


async def run_radar_sweep(client, user_id: str, hub: RadarHub) -> dict:
    """One sweep of one hub. Returns {success, slug, brief_path?, no_brief?,
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
    )
    if not sweep_ok:
        return {"success": False, "slug": hub.slug,
                "error_reason": intake.get("error") or "no_sources_fetched"}

    paths_written = [p for p in (intake.get("paths_written") or []) if p]
    signal_path = paths_written[0] if paths_written else hub.signal_path
    raw_paths = paths_written[1:]

    # ── 2. derive (one bounded judgment turn, no tools) ──────────────────
    signal_body = _read_file(client, user_id, signal_path) or ""
    previous = _latest_brief(client, user_id, hub)
    steer = hub.options.get("prompt") if isinstance(hub.options.get("prompt"), str) else None

    user_msg = (
        f"THE FRESH WATCH SIGNAL (just swept):\n\n{signal_body}\n\n"
        + (f"THE PREVIOUS BRIEF:\n\n{previous}\n" if previous
           else "THERE IS NO PREVIOUS BRIEF — this is the hub's first sweep. "
                "Brief what stands out in the signal as the baseline.\n")
    )

    from services.model_router import route_completion
    derive_started = datetime.now(timezone.utc)
    try:
        routed = await route_completion(
            RADAR_MODEL,
            [{"role": "user", "content": user_msg}],
            system=build_radar_posture(hub.topic, steer),
            max_tokens=_BRIEF_MAX_TOKENS,
            timeout=_BRIEF_TIMEOUT_S,
        )
    except Exception as e:
        logger.exception("[RADAR] derive failed for %s/%s: %s", user_id[:8], hub.slug, e)
        record_execution_event(
            client, user_id=user_id, slug=f"radar-brief:{hub.topic}",
            mode="judgment", trigger_type="scheduled", status="failed",
            error_reason="derive_raised", error_detail=str(e)[:500],
            funnel_decision="radar",
        )
        return {"success": False, "slug": hub.slug, "error_reason": "derive_raised"}

    from services.settle import extract_title, slugify, strip_fence, _unique_path
    note = strip_fence(routed.text or "")
    derive_ms = int((datetime.now(timezone.utc) - derive_started).total_seconds() * 1000)

    if not note.strip() or note.strip() == NO_BRIEF_SENTINEL:
        # The honest empty sweep — metered as skipped so falsifier 4 reads it.
        record_execution_event(
            client, user_id=user_id, slug=f"radar-brief:{hub.topic}",
            mode="judgment", trigger_type="scheduled", status="skipped",
            error_reason="no_brief", model=routed.ledger_model,
            duration_ms=derive_ms, funnel_decision="radar", **routed.usage,
        )
        return {"success": True, "slug": hub.slug, "no_brief": True}

    # ── 3. place (kernel-deterministic; never overwrites) ────────────────
    title = extract_title(note)
    date = started.strftime("%Y-%m-%d")
    path = _unique_path(
        client, user_id, None,
        f"{hub.root}/{BRIEFS_DIR}/{date}-{slugify(title)}.md",
    )

    # ── 4. write + cite (ADR-423 kind, ADR-448 edges) ────────────────────
    from services.authored_substrate import write_revision
    revision_id = write_revision(
        client,
        user_id=user_id,
        path=path,
        content=note,
        authored_by="system:radar",
        message=f"radar brief for hub '{hub.topic}' (standing sweep, {items} sources)",
        revision_kind="derivation",
        derived_from=[signal_path, *raw_paths],
    )

    # ── 5. embed (retrieval — a brief nobody can recall is a dead brief) ──
    try:
        from services.primitives.workspace import _embed_workspace_file
        await _embed_workspace_file(client, user_id, path, note)
    except Exception as e:
        logger.warning("[RADAR] embed failed for %s: %s", path, e)

    # ── 6. meter (falsifiers 2 + 4 key on this slug) ─────────────────────
    record_execution_event(
        client, user_id=user_id, slug=f"radar-brief:{hub.topic}",
        mode="judgment", trigger_type="scheduled", status="success",
        model=routed.ledger_model, duration_ms=derive_ms,
        funnel_decision="radar", **routed.usage,
    )

    logger.info("[RADAR] %s/%s → %s (rev %s)", user_id[:8], hub.slug, path, revision_id[:8])
    return {"success": True, "slug": hub.slug, "brief_path": path,
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
    "RADAR_MODEL",
    "NO_BRIEF_SENTINEL",
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
