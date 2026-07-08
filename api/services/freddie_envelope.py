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

from services.workspace_context import substrate_scope_filter
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
    # — Seat Occupant (ADR-284) — current occupant identity, runtime-truth-aligned
    ("occupant_md", PERSONA_OCCUPANT_PATH),
    # — Standing Intent (ADR-284) — what the Reviewer was watching for last cycle.
    # The Reviewer reads this on every wake, compares against current world state,
    # and updates it before standing down. The substrate counterpart to a no-fire
    # judgment is an updated standing_intent.md. Steward-base: a steward carries
    # standing intent over ANY workspace (what it was watching to tend).
    ("standing_intent_md", PERSONA_STANDING_INTENT_PATH),
    # NOTE (ADR-390 removal pass): expected_output_yaml, schedule_index_md,
    # recent_execution_md, and calibration_md were UNIVERSAL reads. They are
    # capital-OPERATION machinery (the output contract, the pulse, the cadence-vs-
    # outcome calibration) — a bare steward has no operation that owes output, no
    # cadence it must calibrate. They moved OUT of the universal set into the
    # hired-agent branch of load_freddie_governance_envelope so a bare steward
    # never reads (nor renders) them. Single-ownership: each is read in exactly
    # ONE place, gated on `judgment_home` (the hire grant — ADR-414 D5). See ADR-390 D3.
]

# ADR-414 D5/§9a — the judgment-home override. The paths above are the
# STEWARD-ERA workspace-root layout (still valid on no-hire workspaces); when
# a hire grant exists, each of these envelope keys reads the hired agent's
# home (`agents/{slug}/{file}`) instead. Workspace-level keys (precedent,
# budget) are absent from this map — they stay workspace reads regardless.
_JUDGMENT_HOME_FILES: dict[str, str] = {
    "identity_md": "IDENTITY.md",
    "principles_md": "principles.md",
    "mandate_md": "MANDATE.md",
    "autonomy_md": "AUTONOMY.md",
    "preferences_yaml": "_preferences.yaml",
    "standing_intent_md": "standing_intent.md",
    # hired-agent branch (not in _UNIVERSAL_ENVELOPE_DECLS):
    "expected_output_yaml": "_expected_output.yaml",
}


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
                .eq(*substrate_scope_filter(user_id))
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

    # --- ADR-414 D5/§9a: resolve the judgment home ONCE ---
    # A hired agent's judgment load-out lives in agents/{slug}/ (the hire
    # grant is the activation record); a steward-only workspace has no
    # judgment home and rides the kernel constants. Keys on the GRANT, never
    # on program_active (a platform connection alone raises the latter —
    # chrome/capabilities, not installed judgment).
    from services.programs import resolve_judgment_home

    judgment_home = resolve_judgment_home(user_id)  # "agents/{slug}/" | None

    universal_decls: list[tuple[str, str]] = []
    for key, steward_path in _UNIVERSAL_ENVELOPE_DECLS:
        if judgment_home and key in _JUDGMENT_HOME_FILES:
            universal_decls.append((key, f"{judgment_home}{_JUDGMENT_HOME_FILES[key]}"))
        elif judgment_home and key == "occupant_md":
            # The occupant fact is kernel data for a hired agent (ADR-414 D2
            # — no per-agent OCCUPANT.md); the legacy steward-era file is
            # read only on no-hire workspaces where it may still exist.
            continue
        else:
            universal_decls.append((key, steward_path))

    # --- Universal reads (kernel-shipped, parallel) ---
    universal_results = await _asyncio.gather(
        *[_read(path) for _, path in universal_decls]
    )
    envelope: dict[str, str] = {
        key: value
        for (key, _path), value in zip(universal_decls, universal_results)
    }
    if judgment_home:
        envelope["occupant_md"] = ""  # keep the FreddieContext key shape stable
    # The renderer uses this to label the standing-intent/judgment paths
    # honestly (agents/{slug}/… when hired, persona/… for the steward).
    envelope["judgment_home"] = judgment_home or ""

    # --- ADR-414 D2: the steward's constitution is a KERNEL CONSTANT ---
    # A bare workspace's persona/mandate files were seeded copies of the
    # kernel's steward defaults (ADR-383) — a constant wearing a file costume
    # (DP33). The envelope sources them from the kernel directly: when the
    # file is absent or still carries the steward-default marker, the kernel
    # constant rides the envelope (DP22-safe — constitution content lands in
    # the envelope, never the system frame). Operator- or program-authored
    # content always wins (no marker → untouched). This also makes the
    # content drift-proof: a kernel-side improvement reaches every bare
    # workspace at the next wake, no reapply pass. Phase C stops seeding
    # these files at genesis; this substitution is what makes that safe.
    # STEWARD wakes only (ADR-414 §9a) — a hired agent's home content is the
    # program's/operator's; absence there is reasoned about honestly (ADR-314
    # index-not-assert), never papered over with steward defaults.
    if not judgment_home:
        from services.orchestration import (
            DEFAULT_STEWARD_IDENTITY_MD,
            DEFAULT_STEWARD_MANDATE_MD,
            DEFAULT_STEWARD_PRINCIPLES_MD,
            STEWARD_DEFAULT_MARKER,
        )

        # Two substitution triggers, and note their differing reach post-ADR-414:
        #   - `not _val.strip()` (ABSENT file) — the LIVE trigger on a pure-genesis
        #     workspace (Phase C stopped seeding these files, so they are simply
        #     missing; the kernel constant rides in their place).
        #   - `STEWARD_DEFAULT_MARKER in _val` (SEEDED marker file) — reachable
        #     ONLY on a PRE-ADR-414 workspace that still carries a seeded
        #     marker-bearing file from before genesis stopped seeding. Retained so
        #     those legacy workspaces stay drift-proof (a kernel-side steward-copy
        #     improvement reaches them too); harmless on pure-genesis workspaces
        #     (no marker file exists → the absent-file branch fires instead).
        for _key, _const in (
            ("mandate_md", DEFAULT_STEWARD_MANDATE_MD),
            ("identity_md", DEFAULT_STEWARD_IDENTITY_MD),
            ("principles_md", DEFAULT_STEWARD_PRINCIPLES_MD),
        ):
            _val = envelope.get(_key) or ""
            if not _val.strip() or STEWARD_DEFAULT_MARKER in _val:
                envelope[_key] = _const

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

    # NOTE on activation signals (ADR-414 D5): `program_decls` above drove the
    # program-shaped READS (ground-truth/risk/signals) — that is the CONNECTION-
    # or-hire chrome truth (a platform connection alone raises it). The operation-
    # machinery gate below keys on `judgment_home` (the HIRE GRANT) instead — the
    # installed-judgment signal, which a bare connection does NOT raise. Two
    # distinct signals, deliberately: chrome follows connection; machinery follows
    # the hire.

    # --- Operating Context (ADR-274 + ADR-301 D5 consolidation) ---
    # now/tz/tenure. Steward-base — a steward reasons about time regardless of
    # whether a program runs. Always present.
    envelope["operating_context_block"] = build_operating_context_block(
        client, user_id
    )

    # --- Perception facts (steward-base — ALWAYS present) ---
    # The steward's job over ANY workspace is to tend the commons: who wrote
    # what, is it honestly attributed, is intake placed (the principal commons +
    # attribution detail), and is the perimeter healthy (the peripheral field).
    # These are the base case — present whether or not a program runs. Folded
    # into ONE commons-perception surface at the render layer (ADR-390 D2):
    # roster → recent authorship → per-path attribution → peripheral health, one
    # header, one owner. Each empty-graceful (silent on a quiet single-owner bare
    # workspace — no noise). DP19-clean.
    envelope["principal_commons_fact"] = await _principal_commons_fact(client, user_id)
    envelope["attribution_fact"] = await _attribution_fact(client, user_id)
    envelope["peripheral_field_fact"] = await _peripheral_field_fact(client, user_id)

    # --- Operation machinery (HIRED-AGENT ONLY — ADR-390 D3 + ADR-414 D5) ---
    # specs inventory, the reflection gap-fact, pulse (schedule/recent-execution),
    # calibration, and the expected-output contract are ALL capital-operation
    # machinery: they describe a value-moving operation's specs, its closed
    # intent→outcome loop, its cadence-vs-outcome calibration, and its output
    # contract. A BARE STEWARD has no operation — it does not run cadence it must
    # calibrate, has no ground-truth outcomes to reflect on, no specs, no owed
    # output. Rendering empty-state scaffolding for all of it DILUTED the steward's
    # attention across machinery for an operation it doesn't have (ADR-390).
    #
    # ADR-414 D5: this gate keys on `judgment_home` (the HIRE GRANT), NOT on
    # `has_program_envelope` (which a platform connection alone raises). The two
    # signals are DIFFERENT: a connection installs CHROME + CAPABILITIES; only a
    # hire installs JUDGMENT. Pre-fix, a connection-only workspace (e.g. Alpaca
    # connected, trader never hired) got `program_active=True` and mounted
    # operation machinery reading STEWARD-ERA workspace-root paths (the incoherent
    # `expected_output` fallback below) for an operation it had never hired. The
    # machinery an operation owns lives in that operation's agent home — so if
    # there is no agent home, there is no operation to describe. `expected_output`
    # then reads unconditionally from the agent home (no steward-path fallback —
    # that branch was only reachable in the incoherent connection-only state).
    # The keys are still set (empty when steward-only) so the FreddieContext shape
    # is stable and the render layer skips empties.
    if judgment_home:
        envelope["specs_inventory"] = await _inventory_specs(client, user_id)
        envelope["reflection_gap_fact"] = await _reflection_gap_fact(client, user_id)
        envelope["schedule_index_md"] = await _read(SYSTEM_SCHEDULE_INDEX_PATH)
        envelope["recent_execution_md"] = await _read(SYSTEM_RECENT_EXECUTION_PATH)
        envelope["calibration_md"] = await _read(SYSTEM_CALIBRATION_PATH)
        envelope["expected_output_yaml"] = await _read(
            f"{judgment_home}{_JUDGMENT_HOME_FILES['expected_output_yaml']}"
        )
    else:
        # Steward-only workspace (no hire grant) — operation machinery is not its
        # concern, regardless of whether a bundle's chrome is connection-active.
        # Empty keys keep the contract shape stable; the render layer omits
        # empties (ADR-390 D3).
        envelope["specs_inventory"] = ""
        envelope["reflection_gap_fact"] = ""
        envelope["schedule_index_md"] = ""
        envelope["recent_execution_md"] = ""
        envelope["calibration_md"] = ""
        envelope["expected_output_yaml"] = ""

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
            .eq(*substrate_scope_filter(user_id))
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
            .eq(*substrate_scope_filter(user_id))
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
            .eq(*substrate_scope_filter(user_id))
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
    READ-AND-PRESENT. The kernel presents `path · authored_by · message` for the
    CURRENT head of each recently-touched path; it does NOT label any of them
    wrong (that judgment is the LLM's — Freddie's `attribution-integrity` rule
    reads the content vs the attribution and decides). Bounded to recent activity
    (_ATTRIBUTION_FACT_WINDOW_HOURS) and a distinct-path cap
    (_ATTRIBUTION_FACT_LIMIT) — a discovery surface, not the full ledger; the
    steward ListRevisions a specific path on demand.

    PRESENTS THE CURRENT HEAD PER PATH (not the raw revision stream): the live
    2026-06-30 re-run showed the un-deduped stream buries the signal — a churny
    path appears N times across superseded revisions + tombstones, so "who
    CURRENTLY owns this file" (what the rule judges) is lost. Dedup to the latest
    revision per path makes the mismatch legible. Empty string when no recent
    revisions (a quiet workspace has nothing to tend — no noise on program wakes).
    """
    try:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=_ATTRIBUTION_FACT_WINDOW_HOURS)
        ).isoformat()
        res = (
            client.table("workspace_file_versions")
            .select("path, authored_by, message, created_at")
            .eq(*substrate_scope_filter(user_id))
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            # Fetch a wider raw window than the line cap: the rows dedupe to one
            # head per path (below), so N raw revisions of a churny path collapse
            # to one line. Over-fetch so the deduped result can reach the cap of
            # DISTINCT paths, not run dry on one path's history.
            .limit(_ATTRIBUTION_FACT_LIMIT * 6)
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

    # Present the CURRENT head per path, not the raw revision stream. The live
    # eval (2026-06-30 re-run) showed the un-deduped stream buries the signal:
    # one path appears N times across superseded revisions + tombstone churn, so
    # "who CURRENTLY owns this file" — the thing the attribution-integrity rule
    # judges — is lost in history. Dedupe to the latest revision per path (rows
    # are created_at DESC, so the first occurrence of each path IS its head).
    seen: set[str] = set()
    lines: list[str] = []
    for r in rows:
        path = (r.get("path") or "").replace("/workspace/", "")
        if path in seen:
            continue
        seen.add(path)
        author = (r.get("authored_by") or "?").strip() or "?"
        msg = (r.get("message") or "").strip()
        # Keep the line tight — path · who · why. The full body is one ReadFile
        # away; this is the scan surface, not the content.
        msg_str = f" — {msg[:80]}" if msg else ""
        lines.append(f"- {path} · authored_by: {author}{msg_str}")
        if len(lines) >= _ATTRIBUTION_FACT_LIMIT:  # cap DISTINCT paths
            break
    return "\n".join(lines)


async def _principal_commons_fact(client: Any, user_id: str) -> str:
    """The principal-commons fact — WHO can write this workspace, and who DID
    recently (the steward-envelope re-scope, 2026-06-30; see
    docs/analysis/perception-and-the-principal-commons-first-principles-2026-06-30.md).

    The attribution fact (above) presents `path · authored_by` — but a bare
    `authored_by: operator` string has no REFERENT: the steward cannot judge
    whether the stamp is honest without knowing who the workspace's principals
    are. This fact is that referent. It presents two things:

      1. THE ROSTER — each active principal_grants row: principal · role · the
         write-regions it may author (ADR-373). This is the set the
         attribution-integrity rule checks a stamp against ("the only `operator`
         principal is human X; this AI-voiced content stamped `operator` does not
         fit any human principal").
      2. RECENT AUTHORSHIP BY PRINCIPAL — a GROUP-BY over recent
         workspace_file_versions: per distinct authored_by, how many revisions in
         the window. Shows the steward who is ACTIVELY writing (a foreign-LLM
         dumping, a `system:` mechanism mirroring) vs merely granted.

    DP19-clean (present, don't judge): the kernel presents the roster + the
    counts; the steward's `attribution-integrity` rule decides whether any write
    is mis-attributed. Forward-compatible with the re-founding (provenance-as-
    metadata): the recent-authorship half IS a `GROUP BY principal` over the
    ledger, which is what the re-founding wants the commons to be. Sourced from
    the SAME roster logic as the Workspace Members surface (services.principals).

    Empty string when there is neither a roster beyond the lone owner NOR recent
    authorship — a quiet single-owner workspace has no commons to reconcile (no
    noise on program wakes). Never raises.
    """
    from services.principals import load_principal_roster

    try:
        roster = load_principal_roster(client, user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEWER_ENVELOPE] principal-commons roster read failed user=%s: %s",
            user_id[:8], exc,
        )
        roster = []

    # Recent authorship GROUP-BY (the active half of the commons). Reuse the
    # attribution window so the two facts describe the same recent slice.
    counts: dict[str, int] = {}
    try:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=_ATTRIBUTION_FACT_WINDOW_HOURS)
        ).isoformat()
        res = (
            client.table("workspace_file_versions")
            .select("authored_by")
            .eq(*substrate_scope_filter(user_id))
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            .limit(_ATTRIBUTION_FACT_LIMIT * 12)  # over-fetch; collapses to a few authors
            .execute()
        )
        for r in res.data or []:
            who = (r.get("authored_by") or "?").strip() or "?"
            counts[who] = counts.get(who, 0) + 1
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEWER_ENVELOPE] principal-commons authorship read failed user=%s: %s",
            user_id[:8], exc,
        )

    # A single-owner workspace with no foreign principals and no recent
    # cross-principal activity has no commons to tend — stay silent.
    non_owner_principals = [p for p in roster if p.get("role") != "owner"]
    if not non_owner_principals and len(counts) <= 1:
        return ""

    lines: list[str] = []
    if roster:
        lines.append("Principals (who holds a grant to write this workspace):")
        for p in roster:
            role = p.get("role") or "?"
            regions = ", ".join(p.get("write_regions") or []) or "(none)"
            # Name WHAT KIND of principal, so the attribution check has a referent.
            # An owner's principal_id is the user_id (a UUID) — don't leak it;
            # name it as the human operator (the `operator` stamp's true author).
            # foreign-llm/platform/a2a get their humanized room label. The KIND is
            # the load-bearing fact: `operator` stamps must match the human owner's
            # voice; `yarnnn:mcp:*` stamps must match a foreign-LLM principal.
            if role == "owner":
                who = "the human operator (writes as `operator`)"
            elif p.get("label"):
                kind = "foreign LLM" if role == "foreign-llm" else role
                who = f"{p['label']} ({kind}, writes as `yarnnn:mcp:{p['label']}`)" \
                    if role in ("foreign-llm", "platform", "a2a") else p["label"]
            else:
                who = role
            lines.append(f"- {who} · role: {role} · may write: {regions}")
    if counts:
        lines.append("")
        lines.append("Recent authorship (revisions in the last "
                     f"{_ATTRIBUTION_FACT_WINDOW_HOURS}h, by attribution):")
        for who, n in sorted(counts.items(), key=lambda kv: kv[1], reverse=True):
            lines.append(f"- {who} · {n} revision{'s' if n != 1 else ''}")
    return "\n".join(lines)


async def _peripheral_field_fact(client: Any, user_id: str) -> str:
    """The peripheral-field fact — the HEALTH of the non-principal transports that
    feed the operation (the steward-envelope re-scope, 2026-06-30).

    A PERIPHERAL (ADR-335: "transports are peripherals, driver-class, transport-
    blind judgment") is a feed or an API — no intent, no grant, attributed to the
    `system:` mechanism that operated it. The steward's duty over peripherals is
    not HONESTY (there is no "who" to lie) but HEALTH: is what feeds the operation
    live and current? This is the substrate the persona-frame's `connection-
    hygiene` duty ("are declared connections live?") needs — without it the duty
    has no perceptible state, the gap the 2026-06-30 perception-envelope-
    completeness finding named.

    Presents two peripheral classes:
      - CONNECTIONS — platform_connections rows: platform · status. The OAuth/
        capability layer (ADR-153/264): a connection gates tools + (via
        SyncPlatformState) mirrors external state into substrate as
        `system:sync-platform-state`.
      - SOURCES — declared web/RSS watches (ADR-335/336): presented as their
        count + last-observed freshness IF a watch-signal file exists. (The
        steward ReadFiles the signal for detail; this is the discovery surface.)

    DP19-clean: presents status, does not judge. Empty string when the workspace
    has neither connections nor declared sources (a bare workspace has no
    perimeter — no noise). Never raises.
    """
    lines: list[str] = []

    # --- Connections (platform_connections) ---
    try:
        res = (
            client.table("platform_connections")
            .select("platform, status")
            .eq(*substrate_scope_filter(user_id))
            .execute()
        )
        conns = res.data or []
        if conns:
            lines.append("Connections (platform transports — capability + mirrored state):")
            for c in conns:
                platform = c.get("platform") or "?"
                status = c.get("status") or "?"
                lines.append(f"- {platform} · status: {status}")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEWER_ENVELOPE] peripheral connections read failed user=%s: %s",
            user_id[:8], exc,
        )

    # --- Captures (per-declaration freshness — the real health signal) ---
    # ADR-393 D3: the capture lane writes a per-declaration health block to
    # _capture_signal.yaml (slug · status · observed_at · items). THIS is the
    # freshness the peripheral-field fact was pointing at — the steward's
    # connection-hygiene duty ("is what feeds the operation live and current?")
    # gets real per-declaration state instead of only bare connection status.
    # Best-effort: absent on workspaces with no captures (bare steward).
    try:
        from services.capture.declarations import read_capture_signal
        signal = await read_capture_signal(client, user_id)
        blocks = (signal.get("captures") or {}) if isinstance(signal, dict) else {}
        if blocks:
            if lines:
                lines.append("")
            lines.append("Captures (deterministic intake — freshness + health):")
            for slug in sorted(blocks):
                b = blocks[slug] if isinstance(blocks[slug], dict) else {}
                status = b.get("status") or "?"
                observed = b.get("observed_at") or "never"
                detail = f"- {slug} · {status} · last observed: {observed}"
                if b.get("last_error"):
                    detail += f" · error: {b['last_error']}"
                lines.append(detail)
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "[REVIEWER_ENVELOPE] capture-signal read skipped user=%s: %s",
            user_id[:8], exc,
        )

    # --- Sources (declared web/RSS watches) ---
    # Discovery-surface only: the count of declared sources, sourced from the
    # active bundle's watch declarations. Per-source distillation detail lives in
    # the watch signal file; per-declaration freshness is the Captures block above
    # (ADR-393). Best-effort: bundle reader may have no watches.
    try:
        from services import bundle_reader
        watches = bundle_reader.get_watches_for_workspace(user_id, client) or []
        if watches:
            if lines:
                lines.append("")
            lines.append(f"Sources (declared standing watches — perception field): "
                         f"{len(watches)} declared. ReadFile the watch signal for "
                         f"per-source distillation detail.")
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "[REVIEWER_ENVELOPE] peripheral sources read skipped user=%s: %s",
            user_id[:8], exc,
        )

    return "\n".join(lines)
