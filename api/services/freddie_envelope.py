"""Reviewer wake envelope assembly (ADR-276 + ADR-281).

The Reviewer perceives full operator-authored governance substrate +
program-shaped substrate at every wake, regardless of trigger shape
(addressed | reactive). This module is the single canonical assembly
point for that substrate — called by both `services/wake.py` (cron-tick
+ substrate-event + manual-fire + proposal-arrival wakes) and the
addressed-stream entry within `services/wake.py::stream_addressed_wake`
(driven by `routes/feed.py` per ADR-296 v2 D1).

Pre-loading discipline (FOUNDATIONS v8.5 Axiom 4 + Derived Principle 18 +
ADR-275 refinement learning): load-bearing substrate arrives in the wake
envelope, NOT as a prose-named "remember to ReadFile X" side-quest. Run-1
vs run-2 of the ADR-275 e2e empirically validated the structural difference:
the same operator-says-hi prompt produced zero Schedule calls when
`_preferences.yaml` was prose-named, but three Schedule calls when it was
pre-loaded in the envelope.

ADR-281: program-shaped envelope inputs are read from the active bundle's
MANIFEST `substrate_abi.reviewer_wake_envelope` declaration via
`services.bundle_reader.get_substrate_abi_for_workspace`. **One declaration
shape: `{key, path, optional}`.** No `path_glob`, no `summarizer`. Per
Derived Principle 19 ("The kernel does not compute for the prompt") the
envelope helper reads substrate; it does not derive new state at
prompt-assembly time. Substrate that needs compaction (signal-state
summary, customer aggregates, position summaries — any future case) is
written by mechanical-mode recurrences invoking deterministic primitives
that write substrate at known cadence; the envelope reads the resulting
substrate file like every other path entry.

Universal envelope inputs (the six operator-authored governance files
every workspace has) remain hardcoded as kernel-universal constants.
Adding a new program requires zero edits to this module — the new bundle
declares its envelope; bundle_reader exposes it; this module reads it.

Singular Implementation: one helper, used by every wake source through
`services/wake.py` (ADR-296 v2 D1).

Observability (2026-05-15 hardening):
The helper returns `(envelope_dict, elapsed_ms)` so callers can record
the dominant Reviewer DB-read pattern to `execution_events.envelope_load_ms`
(migration 175). Reactive callers route the elapsed ms through telemetry;
addressed callers log it to the structured logger.
"""

from __future__ import annotations

import asyncio as _asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Awaitable

from services.workspace_paths import (
    PERSONA_IDENTITY_PATH,
    PERSONA_PRINCIPLES_PATH,
    PERSONA_OCCUPANT_PATH,
    PERSONA_STANDING_INTENT_PATH,
    CONSTITUTION_PRECEDENT_PATH,
    CONSTITUTION_MANDATE_PATH,
    GOVERNANCE_AUTONOMY_PATH,
    GOVERNANCE_BUDGET_PATH,
    CONTRACT_PREFERENCES_PATH,
    CONTRACT_EXPECTED_OUTPUT_PATH,
    SPECS_PREFIX,
    SYSTEM_SCHEDULE_INDEX_PATH,
    SYSTEM_RECENT_EXECUTION_PATH,
    SYSTEM_CALIBRATION_PATH,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Universal envelope inputs (kernel-shipped — present in every workspace)
# ---------------------------------------------------------------------------
# Per ADR-281 D2 the kernel ships the universal "how" envelope; bundles
# declare their program-shaped additions via MANIFEST `substrate_abi.reviewer_wake_envelope`.
# This list is the kernel side. Each entry: (key, workspace-relative-path).

_UNIVERSAL_ENVELOPE_DECLS: list[tuple[str, str]] = [
    # — Governance (Persona + Framework class) —
    ("identity_md", PERSONA_IDENTITY_PATH),
    ("principles_md", PERSONA_PRINCIPLES_PATH),
    ("precedent_md", CONSTITUTION_PRECEDENT_PATH),
    ("mandate_md", CONSTITUTION_MANDATE_PATH),
    ("autonomy_md", GOVERNANCE_AUTONOMY_PATH),
    ("preferences_yaml", CONTRACT_PREFERENCES_PATH),
    # ADR-327: budget is the Trigger-dimension operator dial (Budget +
    # Autonomy + Identity trifecta). The Reviewer reads the spend envelope
    # at every wake so its wake-allocation judgment (mid-loop Schedule()
    # cadence authoring) lands within the operator's declared budget. When
    # read returns empty (no _budget.yaml authored yet) the helper still
    # yields ("budget_yaml", "") so the FreddieContext key is present.
    ("budget_yaml", GOVERNANCE_BUDGET_PATH),
    # ADR-345: the operation's output contract (Expected Output) — what the
    # workspace owes (kind + delivery-cadence + bar). Orthogonal to budget
    # (Rhythm = rate of attention; Expected Output = the deliverable). The
    # standing-obligation check (DP30) reads it declared-then-derive: when
    # present it is the shared referent for "behind on the contract"; when
    # empty the ADR-344 derivation is the fallback. Empty string keeps the
    # FreddieContext key present (same shape as budget_yaml).
    ("expected_output_yaml", CONTRACT_EXPECTED_OUTPUT_PATH),
    # — Seat Occupant (ADR-284) — current occupant identity, runtime-truth-aligned
    ("occupant_md", PERSONA_OCCUPANT_PATH),
    # — Standing Intent (ADR-284) — what the Reviewer was watching for last cycle.
    # The Reviewer reads this on every wake, compares against current world state,
    # and updates it before standing down. The substrate counterpart to a no-fire
    # judgment is an updated standing_intent.md.
    ("standing_intent_md", PERSONA_STANDING_INTENT_PATH),
    # — Pulse (ADR-301) — Reviewer's own cadence + recent fires.
    # Mechanically mirrored from `tasks` (scheduling index) +
    # `execution_events` (ledger) by `services.kernel_mirrors`, run per
    # scheduler tick in the maintenance phase. Both files are diff-aware
    # writes (most ticks produce zero revisions). The Reviewer reads them
    # to reason correctly about its own pulse — closes the schedule-
    # hallucination class documented in docs/evaluations/2026-05-24-
    # 045348-reviewer-schedule-self-misdiagnosis/findings.md.
    ("schedule_index_md", SYSTEM_SCHEDULE_INDEX_PATH),
    ("recent_execution_md", SYSTEM_RECENT_EXECUTION_PATH),
    # ADR-327 D6 — calibration evidence for the self-improving loop. Mirrors
    # the Reviewer's cadence-authoring history against ground-truth outcome
    # quality (per-recurrence fires vs proposals-produced + ground-truth
    # head). The Reviewer reads this BEFORE reasoning about cadence; where its
    # prior cadence choices are falsified by ground truth, it re-authors.
    # NOTE: this is `system/_calibration.md` (ADR-327 D6, mechanically mirrored,
    # cadence-vs-outcome evidence) — NOT the retired persona-side `calibration.md`
    # (the old ADR-211 per-occupant aggregate-windows file, superseded by
    # `persona/reflection.md` per ADR-364 D4). Same word, different mechanism.
    ("calibration_md", SYSTEM_CALIBRATION_PATH),
]


# ---------------------------------------------------------------------------
# Envelope assembly — substrate-only, no kernel-side computation
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Operating Context block (ADR-274 + ADR-301 consolidation)
#
# Per FOUNDATIONS v8.5 Axiom 4 amendment + Derived Principle 18, time is a
# wake-envelope concern, NOT workspace substrate (mirrors Claude Code's
# runtime model). The Reviewer perceives `now`, operator timezone, and
# market state at every wake — load-bearing for Trigger-authoring decisions.
#
# Pre-ADR-301 this function lived in `agents/freddie_agent.py` and was
# composed by `wake.py` at three call sites. ADR-301 D5 consolidates
# composition here so the envelope helper is the singular envelope
# assembly point — one home, one function, one contract. The thin
# re-export in `agents.freddie_agent` preserves the ADR-274 import
# contract for `build_operating_context_block` callers.
# ---------------------------------------------------------------------------

def build_operating_context_block(client: Any, user_id: str) -> str:
    """Assemble the Operating Context block injected into the Reviewer's
    wake envelope. Pulls now + operator timezone + market state from
    existing services. Pure projection — no new infrastructure.

    Format (~5 lines, ~50 tokens):
        ## Operating Context (Axiom 4 v8.5)

        **Now**: <UTC ISO> (<weekday>, in tz: <local time>)
        **Operator timezone**: <tz>
        **Market state**: <pre-market | RTH | post-market | closed | n/a> (<context>)
        **Workspace tenure**: <N days> since activation
    """
    from services.scheduling import get_user_timezone
    try:
        from services.bundle_reader import get_market_context_for_user
    except Exception:
        get_market_context_for_user = None  # type: ignore

    now_utc = datetime.now(timezone.utc)
    try:
        tz_name = get_user_timezone(client, user_id) or "UTC"
    except Exception:
        tz_name = "UTC"

    # Local-time projection without pytz dep (kernel uses zoneinfo)
    try:
        from zoneinfo import ZoneInfo
        local = now_utc.astimezone(ZoneInfo(tz_name))
        local_str = local.strftime("%a %H:%M %Z")
    except Exception:
        local_str = now_utc.strftime("%a %H:%M UTC")

    lines = [
        "## Operating Context (Axiom 4 v8.5)",
        "",
        f"**Now**: {now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')} ({local_str})",
        f"**Operator timezone**: {tz_name}",
    ]

    # Market state — only when the workspace has a market-context bundle.
    if get_market_context_for_user is not None:
        try:
            mc = get_market_context_for_user(user_id, client)
        except Exception:
            mc = None
        if mc:
            mstate = mc.get("state") or mc.get("market_state") or "unknown"
            mnote = mc.get("note") or ""
            line = f"**Market state**: {mstate}"
            if mnote:
                line += f" ({mnote})"
            lines.append(line)

    # Workspace tenure
    try:
        ws = (
            client.table("workspaces")
            .select("created_at")
            .eq("owner_id", user_id)
            .limit(1)
            .execute()
        )
        if ws.data:
            ws_created_raw = ws.data[0].get("created_at")
            if ws_created_raw:
                try:
                    ws_created = datetime.fromisoformat(
                        ws_created_raw.replace("Z", "+00:00")
                    )
                    days = (now_utc - ws_created).days
                    lines.append(
                        f"**Workspace tenure**: {days} days since activation"
                    )
                except Exception:
                    pass
    except Exception:
        pass

    return "\n".join(lines)


async def load_freddie_governance_envelope(
    client: Any, user_id: str
) -> tuple[dict, int]:
    """Assemble the Reviewer's wake envelope substrate.

    Returns `(envelope_dict, elapsed_ms)`:
      - envelope_dict: keyed by `FreddieContext` field names — drop
        directly into the context bag passed to `invoke_freddie()`. All
        reads happen in parallel via `asyncio.gather` to minimize
        wake-envelope latency.
      - elapsed_ms: wall-clock ms spent in this call. Callers route it
        to `execution_events.envelope_load_ms` (reactive path) or to the
        structured logger (addressed path) per ADR-276 hardening.

    Universal envelope (always present, kernel-shipped):
      - identity_md          → /workspace/persona/IDENTITY.md
      - principles_md        → /workspace/persona/principles.md
      - precedent_md         → /workspace/constitution/PRECEDENT.md
      - mandate_md           → /workspace/constitution/MANDATE.md
      - autonomy_md          → /workspace/governance/AUTONOMY.md
      - preferences_yaml     → /workspace/contract/_preferences.yaml
      - occupant_md          → /workspace/persona/OCCUPANT.md            (ADR-284)
      - standing_intent_md   → /workspace/persona/standing_intent.md     (ADR-284)

    Program-shaped envelope (read from active bundle's MANIFEST per ADR-281
    D2): substrate paths declared in `substrate_abi.reviewer_wake_envelope`.
    For alpha-trader workspaces today this includes `operator_profile_md`,
    `risk_md`, `ground_truth_md`, and `signal_files` (which reads the
    `_signals_summary.md` substrate file written by alpha-trader's
    `mirror-signal-state` mechanical recurrence per ADR-281 D3).

    Adding a new program requires zero edits to this function. The new
    bundle declares its envelope; `bundle_reader.get_substrate_abi_for_workspace`
    exposes it; the loop below reads it. All values returned are str (empty
    string when absent — never raises) so the Reviewer's envelope renderer
    (`_build_user_message`) skips absent sections gracefully.

    Per Derived Principle 19: the kernel reads substrate; it does not
    derive state at prompt-assembly time. Substrate that needs compaction
    is written by mechanical primitives, not summarized at envelope-load
    time.
    """
    _started_at = datetime.now(timezone.utc)

    async def _read(path: str) -> str:
        """Read a workspace file by relative path, return '' on miss."""
        full = f"/workspace/{path.lstrip('/')}" if not path.startswith("/workspace/") else path
        try:
            res = (
                client.table("workspace_files")
                .select("content")
                .eq("user_id", user_id)
                .eq("path", full)
                .limit(1)
                .execute()
            )
            return (res.data or [{}])[0].get("content") or ""
        except Exception as exc:
            logger.warning(
                "[REVIEWER_ENVELOPE] read failed for user=%s path=%s: %s",
                user_id[:8], path, exc,
            )
            return ""

    # --- Universal reads (kernel-shipped, parallel) ---
    universal_results = await _asyncio.gather(
        *[_read(path) for _, path in _UNIVERSAL_ENVELOPE_DECLS]
    )
    envelope: dict[str, str] = {
        key: value
        for (key, _path), value in zip(_UNIVERSAL_ENVELOPE_DECLS, universal_results)
    }

    # --- Program-shaped reads (from active bundle's substrate_abi) ---
    # Per ADR-281 D1: one declaration shape per envelope entry: {key, path, optional}.
    # No path_glob, no summarizer. The kernel reads substrate; mechanical
    # primitives write derivative-compaction substrate.
    from services import bundle_reader

    abi = bundle_reader.get_substrate_abi_for_workspace(user_id, client)
    program_decls = abi.get("reviewer_wake_envelope", []) or []

    program_tasks: list[Awaitable[str]] = []
    program_keys: list[str] = []
    for decl in program_decls:
        if not isinstance(decl, dict):
            continue
        key = decl.get("key")
        path = decl.get("path")
        if not key or not isinstance(path, str):
            continue
        # Skip duplicates of universal entries — kernel universals win.
        if key in envelope:
            logger.warning(
                "[REVIEWER_ENVELOPE] bundle envelope key %s collides with "
                "kernel-universal entry; kernel value wins", key,
            )
            continue
        program_keys.append(key)
        program_tasks.append(_read(path))

    if program_tasks:
        program_results = await _asyncio.gather(*program_tasks)
        for key, value in zip(program_keys, program_results):
            envelope[key] = value
        # Record which keys came from the bundle envelope so the wake-message
        # renderer can emit ANY program-declared signal generically — without a
        # per-key render site in _build_user_message. Without this, a bundle key
        # that has no bespoke renderer (e.g. watch_signal, repo_signal) lands in
        # the dict but never reaches the agent (the pre-ADR-336 gap). The
        # generic renderer skips keys already rendered with a bespoke header.
        envelope["_program_envelope_keys"] = list(program_keys)

    # --- Operating Context (ADR-274 + ADR-301 D5 consolidation) ---
    # Composed here so the envelope helper is the singular envelope
    # assembly point. Same content as the pre-ADR-301 build_operating_
    # context_block. Callers no longer need to compose it separately;
    # the envelope dict carries it through to the Reviewer's user message
    # renderer alongside every other envelope key.
    envelope["operating_context_block"] = build_operating_context_block(
        client, user_id
    )

    # --- Specs inventory (name + title only, no bodies) ---
    # Program bundles fork capability specs into /workspace/operation/specs/ at activation
    # (per ADR-261 D6 + ADR-275). The Reviewer's _PERSONA_FRAME tells it specs
    # exist but doesn't enumerate them — without an inventory, the Reviewer
    # ends up asking the operator "do those spec files exist?" when it could
    # have known. The inventory is a name+title list, NOT spec bodies — bodies
    # are read on demand via ReadFile. Cheap (one indexed query), bounded
    # (typical bundle ships ~5-10 specs), and respects Derived Principle 19
    # (substrate read, no LLM-time derivation).
    envelope["specs_inventory"] = await _inventory_specs(client, user_id)

    # --- Reflection gap-fact (ADR-364 D2) ---
    # The closed intent→outcome loop, presented (not computed). For each recent
    # material verdict in judgment_log carrying a proposal_id, joined to its
    # outcome event (value + attestation) in the active bundle's ground-truth
    # file by that proposal_id (the ADR-364 D1 keystone FK). DP19-clean: a
    # bounded read-and-present (same shape as _inventory_specs) — the kernel
    # presents the raw join; it does NOT label matched/diverged (that analytical
    # state is the LLM's judgment, authored into persona/reflection.md). Honest
    # by construction: the outcome carries ADR-330 attestation the agent can't
    # fake. Empty string when no joinable verdict↔outcome pairs exist yet.
    envelope["reflection_gap_fact"] = await _reflection_gap_fact(client, user_id)

    # --- Attribution fact (ADR-387 follow-on) ---
    # Recent revisions + their authored_by, presented raw — the steward's
    # perception surface for intake-placement + attribution-integrity. DP19-clean
    # (present, don't judge). Empty on a quiet workspace (no noise). Closes the
    # bare-Freddie eval gap (Finding 1): a sweep can now SEE attribution drift.
    envelope["attribution_fact"] = await _attribution_fact(client, user_id)

    elapsed_ms = int(
        (datetime.now(timezone.utc) - _started_at).total_seconds() * 1000
    )
    return envelope, elapsed_ms


async def _inventory_specs(client: Any, user_id: str) -> str:
    """List bundle-shipped capability specs under /workspace/operation/specs/.

    Returns a multi-line string, one line per spec:
        - {path} — {first-heading title or "(no heading)"}
    Empty string when no specs exist. The Reviewer ReadFiles individual
    specs on demand; this inventory is the discovery surface.
    """
    try:
        res = (
            client.table("workspace_files")
            .select("path, content")
            .eq("user_id", user_id)
            .like("path", f"{SPECS_PREFIX}%.md")
            .order("path")
            .execute()
        )
    except Exception as exc:
        logger.warning(
            "[REVIEWER_ENVELOPE] specs inventory read failed for user=%s: %s",
            user_id[:8], exc,
        )
        return ""

    rows = res.data or []
    if not rows:
        return ""

    lines: list[str] = []
    for row in rows:
        path = row.get("path") or ""
        content = row.get("content") or ""
        # Extract first markdown H1 heading; fall back to filename.
        title = "(no heading)"
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                break
        lines.append(f"- {path} — {title}")
    return "\n".join(lines)


#: How many recent verdict↔outcome pairs to present in the gap-fact. Bounded
#: per DP19 + the _inventory_specs precedent — a discovery surface, not a dump;
#: the Reviewer ReadFiles the full judgment_log / ground-truth file on demand.
_REFLECTION_GAP_LIMIT = 8

#: How many recent revisions to present in the attribution fact, and the
#: look-back window. Bounded per DP19 (same discipline as the gap-fact): a
#: discovery surface the steward scans for attribution/placement drift, not a
#: full ledger — the steward ListRevisions a specific path on demand. The window
#: keeps it to RECENT activity (the cross-principal writes a sweep should tend),
#: not the whole history.
_ATTRIBUTION_FACT_LIMIT = 12
_ATTRIBUTION_FACT_WINDOW_HOURS = 48


def _extract_ground_truth_events(content: str) -> list[dict[str, Any]]:
    """Extract the `events` array (each event a dict possibly carrying
    proposal_id, value_cents, attestation, action_type) from a ground-truth
    file's JSON frontmatter. Returns [] on any parse failure — perception is a
    flow, never a gate; the gap-fact degrades to empty gracefully.
    """
    import json as _json
    import re as _re
    m = _re.match(r"^---\s*\n(.*?)\n---", content, _re.DOTALL)
    raw = m.group(1) if m else content
    try:
        data = _json.loads(raw)
    except Exception:
        return []
    events = data.get("events") if isinstance(data, dict) else None
    return events if isinstance(events, list) else []


#: Decided-verdict statuses on `action_proposals` that carry a real verdict to
#: join. `pending`/`expired` rows have no decision yet, so they cannot join.
_DECIDED_PROPOSAL_STATUSES = ("approved", "executed", "rejected")


def _decisions_from_action_proposals(client: Any, user_id: str) -> dict[str, dict[str, str]]:
    """ADR-364 D2a (2026-06-25): the gap-fact's verdict source is the
    `action_proposals` verdict-of-record — NOT the agent-overwritable
    `judgment_log.md` narrative (File Format Discipline §9 + ADR-286: that file
    is LLM-facing prose with three writers, one of which — the occupant's own
    bundle-directed WriteFile — can overwrite the join-bearing blocks).

    Returns {proposal_id: {action_type, decision, timestamp, headline}} keyed by
    the proposal row `id` (= the D1 keystone FK). Program-neutral: every program's
    ProposeAction → verdict cycle writes this table; the kernel names the mechanism,
    the program supplies the instance. Bounded read; the agent never rewrites this
    table (only ExecuteProposal/RejectProposal mutate it), so the join is
    tamper-proof and survives any judgment_log.md rewrite.
    """
    try:
        res = (
            client.table("action_proposals")
            .select("id,status,family,primitive,reviewer_identity,reviewer_reasoning,"
                    "approved_at,executed_at,created_at")
            .eq("user_id", user_id)
            .in_("status", list(_DECIDED_PROPOSAL_STATUSES))
            .order("created_at", desc=True)
            # bound the read generously above the gap-limit; the join + cap below
            # narrows to the joinable set.
            .limit(200)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEWER_ENVELOPE] gap-fact action_proposals read failed user=%s: %s",
            user_id[:8], exc,
        )
        return {}
    decisions: dict[str, dict[str, str]] = {}
    for row in (res.data or []):
        pid = row.get("id")
        if not pid:
            continue
        # decision ← status ('executed' presents as 'approve'-class for the read;
        # we surface the raw status so the LLM judges from ground truth, DP19).
        decision = "approve" if row.get("status") in ("approved", "executed") else "reject"
        action_type = row.get("primitive") or row.get("family") or "?"
        # the verdict's gist: reviewer_reasoning first non-empty line.
        reasoning = (row.get("reviewer_reasoning") or "").strip()
        headline = reasoning.splitlines()[0].strip()[:160] if reasoning else ""
        ts = row.get("approved_at") or row.get("executed_at") or row.get("created_at") or ""
        decisions[str(pid)] = {
            "action_type": str(action_type),
            "decision": decision,
            "timestamp": str(ts),
            "headline": headline,
        }
    return decisions


async def _reflection_gap_fact(client: Any, user_id: str) -> str:
    """ADR-364 D2: present the closed intent→outcome loop as raw joined rows.

    Reads recent decided verdicts (`action_proposals`, the verdict-of-record per
    D2a) + the active program's ground-truth events, joins on proposal_id (the D1
    keystone FK), and presents one line per joinable pair. Presents — does not
    judge (DP19): no matched/diverged labeling; the Reviewer authors that into
    reflection.md. Empty string when nothing joins (no FK overlap yet, or no
    ground-truth file). Program-neutral: the ground-truth path is program-declared
    via `substrate_abi.ground_truth`; the verdict table is kernel-universal.
    """
    from services.bundle_reader import get_ground_truth_for_workspace

    # workspace_files store the /workspace/-prefixed path; the path CONSTANTS are
    # bare (no prefix). The _UNIVERSAL_ENVELOPE_DECLS reads above go through the
    # `_read()` helper which prepends the prefix — the ground-truth read below must
    # do the same, or the .eq("path", ...) lookup misses every row (the gap-fact
    # then silently returns "" and the loop never fires — the bug the offline
    # reflection probe surfaced 2026-06-24, present since the D2 helper shipped).
    def _full(path: str) -> str:
        return path if path.startswith("/workspace/") else f"/workspace/{path.lstrip('/')}"

    # 1) Verdicts keyed by proposal_id — the action_proposals verdict-of-record
    #    (D2a). Tamper-proof: the agent does not rewrite this table.
    decisions = _decisions_from_action_proposals(client, user_id)
    if not decisions:
        return ""

    # 2) Outcome events keyed by proposal_id (bounded read of ground-truth file).
    gt_path = get_ground_truth_for_workspace(user_id, client)
    if not gt_path:
        return ""
    try:
        res = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", _full(gt_path))
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEWER_ENVELOPE] gap-fact ground-truth read failed user=%s: %s",
            user_id[:8], exc,
        )
        return ""
    rows = res.data or []
    if not rows:
        return ""
    events = _extract_ground_truth_events(rows[0].get("content") or "")
    outcomes_by_pid: dict[str, dict[str, Any]] = {}
    for ev in events:
        if isinstance(ev, dict) and ev.get("proposal_id"):
            # Keep the latest event per proposal_id (events are append-order).
            outcomes_by_pid[str(ev["proposal_id"])] = ev

    # 3) Join + present (newest decisions first, bounded). Present the raw pair;
    #    do NOT compute whether it "worked" — that judgment is the LLM's.
    joined = [
        (pid, d, outcomes_by_pid[pid])
        for pid, d in decisions.items()
        if pid in outcomes_by_pid
    ]
    if not joined:
        return ""
    joined.sort(key=lambda t: t[1].get("timestamp", ""), reverse=True)

    lines: list[str] = []
    for pid, d, ev in joined[:_REFLECTION_GAP_LIMIT]:
        value = ev.get("value_cents")
        val_str = (
            f"{value/100:+.2f}" if isinstance(value, (int, float)) else "unrealized"
        )
        attest = ev.get("attestation") or "platform"
        head = d.get("headline") or f"{d.get('decision', '?')} {d.get('action_type', '?')}"
        lines.append(
            f"- {d.get('decision', '?')} {d.get('action_type', '?')} "
            f"→ outcome {val_str} [{attest}] — verdict: {head}"
        )
    return "\n".join(lines)


async def _attribution_fact(client: Any, user_id: str) -> str:
    """ADR-387 follow-on (2026-06-30): present recent substrate revisions with
    their attribution, as raw rows — the steward's perception surface for the
    intake-placement + attribution-integrity duties.

    The bare-Freddie eval (docs/evaluations/2026-06-29-freddie-bare-workspace-
    steward-FINDING.md, Finding 1) found the steward placed a mis-attributed
    file but ACCEPTED the `authored_by=operator` lie on AI-voiced content —
    because nothing in the wake envelope surfaced attribution. A steward sweep
    had to ListRevisions every file to perceive a mismatch, which it had no cue
    to do. This is the missing signal: the attribution analogue of the ADR-364
    reflection gap-fact.

    DP19-clean (the same discipline as `_reflection_gap_fact`): a bounded
    READ-AND-PRESENT. The kernel presents `path · authored_by · message · when`
    for the most recent revisions; it does NOT label any of them wrong (that
    judgment is the LLM's — Freddie's `attribution-integrity` rule reads the
    content vs the attribution and decides). Bounded to recent activity
    (_ATTRIBUTION_FACT_WINDOW_HOURS) and a row cap (_ATTRIBUTION_FACT_LIMIT) —
    a discovery surface, not the full ledger; the steward ListRevisions a
    specific path on demand. Empty string when no recent revisions (a quiet
    workspace has nothing to tend — no noise on program wakes either).
    """
    try:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=_ATTRIBUTION_FACT_WINDOW_HOURS)
        ).isoformat()
        res = (
            client.table("workspace_file_versions")
            .select("path, authored_by, message, created_at")
            .eq("user_id", user_id)
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            .limit(_ATTRIBUTION_FACT_LIMIT)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEWER_ENVELOPE] attribution-fact read failed user=%s: %s",
            user_id[:8], exc,
        )
        return ""
    rows = res.data or []
    if not rows:
        return ""

    lines: list[str] = []
    for r in rows:
        path = (r.get("path") or "").replace("/workspace/", "")
        author = (r.get("authored_by") or "?").strip() or "?"
        msg = (r.get("message") or "").strip()
        # Keep the line tight — path · who · why. The full body is one ReadFile
        # away; this is the scan surface, not the content.
        msg_str = f" — {msg[:80]}" if msg else ""
        lines.append(f"- {path} · authored_by: {author}{msg_str}")
    return "\n".join(lines)
