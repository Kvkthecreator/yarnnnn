"""Eval-suite session runner (v2) — operator-question prose reads.

Codified by docs/evaluations/EVAL-SUITE-DISCIPLINE.md (2026-05-29 rewrite).
One session = one suite manifest → N evals run sequentially against the
same workspace → one SESSION.md the OPERATOR writes (the runner emits a
prose scaffold; the read is human, by design — §1).

What the runner does honestly (and ONLY this):
  - Pre-flight `requires:` check per eval (§3, C2). An eval whose
    precondition is not satisfied is NOT fired — the c51c44f
    fire-against-violated-state class is structurally impossible.
  - Pre-flight `setup:` / reset-to-clean establishment (§3.1, C3).
  - Orchestrate the existing ScenarioRunner (no parallel scenario path).
  - Capture per-eval receipts to raw/ (revisions, proposals WITH family,
    execution_events WITH wake_source/status) so the human can check
    *architecture-shape*, not just outcome (§5 of the audit).
  - Emit the cost appendix — the one honest automated number (C6).
  - Flag empty/near-empty Reviewer responses as INCONCLUSIVE, never a
    pass, and require an execution_events receipt before a turn counts
    as a real wake (the empty-wake-guard, §6.2 / S1).

What the runner does NOT do: score dimensions, fill Pass? cells,
auto-classify the read. There are no cells (§1.3, §10).

Usage:
    .venv/bin/python -m api.scripts.operator.run_eval_suite \\
        --suite docs/evaluations/eval-suites/yarnnn-author-judgment.yaml \\
        [--caller eval-suite-runner]

v1 is removed entirely (no dual-schema branch — Singular Implementation).
The four pre-v2 session folders stay as frozen historical artifact (§7.4);
they are read as markdown, never re-run.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

_THIS_DIR = Path(__file__).resolve().parent
_API_ROOT = _THIS_DIR.parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

REPO_ROOT = _THIS_DIR.parents[2]

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_API_ROOT / ".env.alpha-ops")
load_dotenv(REPO_ROOT / ".env")


# v2 = the 2026-05-29 clean-slate rewrite (read_kind, requires, prior,
# accumulates; no expected_dimensions, no qualitative scoring).
SUITE_SCHEMA_VERSION = 2

# Cost is the only automated number, surfaced as a finding, never a gate (S6).
# The v1 qualitative floors (per_eval_usd / trace_completeness_floor /
# m6_drift_ceiling) are deleted — the qualitative read no longer resolves to
# numbers, so its floors have no meaning.
DEFAULT_BUDGET = {
    "per_session_usd": 6.0,
}

# Below this char count a Reviewer response carries no narration to read —
# the empty-wake false-negative trap (§6.2). Sub-threshold → INCONCLUSIVE,
# never a pass.
EMPTY_RESPONSE_CHAR_THRESHOLD = 40

VALID_READ_KINDS = {"judgment_coherence", "substrate_responsiveness"}


# ---------------------------------------------------------------------------
# Suite loading + validation (C1)
# ---------------------------------------------------------------------------


class SuiteError(Exception):
    """Raised on malformed suite manifest."""


def load_suite(path: Path) -> dict:
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise SuiteError(f"Suite manifest must be a YAML dict, got {type(raw).__name__}")
    version = int(raw.get("eval_suite_schema_version", SUITE_SCHEMA_VERSION))
    if version != SUITE_SCHEMA_VERSION:
        raise SuiteError(
            f"Unsupported eval_suite_schema_version {version}; runner only supports "
            f"v{SUITE_SCHEMA_VERSION} (the 2026-05-29 prose-read rewrite). v1 suites are "
            f"frozen historical artifact and are not re-run."
        )
    for required in ("eval_suite", "read_kind", "persona", "evals"):
        if required not in raw:
            raise SuiteError(f"Suite manifest missing required field: {required!r}")
    if raw["read_kind"] not in VALID_READ_KINDS:
        raise SuiteError(
            f"read_kind must be one of {sorted(VALID_READ_KINDS)}; got {raw['read_kind']!r}"
        )
    if not isinstance(raw["evals"], list) or not raw["evals"]:
        raise SuiteError("Suite manifest 'evals' must be a non-empty list")

    raw.setdefault("description", "")
    raw.setdefault("budget", {})
    for k, v in DEFAULT_BUDGET.items():
        raw["budget"].setdefault(k, v)

    docs_evals_root = REPO_ROOT / "docs" / "evaluations"
    eval_slugs: set[str] = set()
    for i, eval_def in enumerate(raw["evals"]):
        for required in ("eval", "scenario"):
            if required not in eval_def:
                raise SuiteError(f"Eval[{i}] missing required field: {required!r}")
        slug = eval_def["eval"]
        if slug in eval_slugs:
            raise SuiteError(f"Duplicate eval slug within suite: {slug!r}")
        eval_slugs.add(slug)
        scen_abs = docs_evals_root / eval_def["scenario"]
        if not scen_abs.is_file():
            raise SuiteError(f"Eval[{i}] {slug!r} scenario not found: {scen_abs}")
        eval_def["_scenario_abs"] = scen_abs

        # v2 optional fields with safe defaults.
        eval_def.setdefault("requires", [])
        eval_def.setdefault("prior", "")
        eval_def.setdefault("accumulates", False)
        eval_def.setdefault("inherits", [])
        # Validate inherits references resolve within the suite.
        for inh in eval_def["inherits"]:
            if inh not in eval_slugs and inh not in {e["eval"] for e in raw["evals"]}:
                raise SuiteError(f"Eval {slug!r} inherits unknown eval {inh!r}")

    return raw


# ---------------------------------------------------------------------------
# Session folder
# ---------------------------------------------------------------------------


def session_folder(suite_slug: str) -> Path:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    return REPO_ROOT / "docs" / "evaluations" / f"{now}-{suite_slug}-session"


# ---------------------------------------------------------------------------
# Pre-flight (C2 check + C3 establish)
# ---------------------------------------------------------------------------


async def preflight_eval(
    user_id: str,
    eval_def: dict,
    *,
    persona_slug: str,
) -> dict:
    """Establish clean state (unless accumulates), then check preconditions.

    Returns {fired_ok: bool, established: {...}, precondition: {...}}. When
    fired_ok is False the eval is NOT fired (§3, S2): a read against a
    violated precondition cannot be trusted, so no tokens are spent.

    Order matters: establish FIRST (writes declared setup + deletes
    absent-files), THEN check (so the check reads the established state).
    For accumulating evals we still check (the precondition asserts the
    inherited state is what the arc expects) but do NOT reset.
    """
    from services.operator_proxy.scenarios import (
        Scenario,
        check_preconditions,
        establish_substrate,
    )

    authored_by = f"operator-proxy:eval-suite-runner:acting-as-{persona_slug}"
    requires = eval_def.get("requires", [])

    established = {"deleted": [], "wrote": [], "skipped_reset": False}
    if eval_def.get("accumulates"):
        # Ordered-arc eval — inherit prior state; do NOT reset. Still honor
        # explicit setup writes (the scenario's own setup runs in the runner;
        # here we only apply suite-level absent-deletes, which an accumulating
        # eval normally has none of).
        established["skipped_reset"] = True
    else:
        # Default reset-to-clean: delete absent-files + apply the scenario's
        # substrate-shaped setup so the situation is known and independent.
        scenario = Scenario.from_file(eval_def["_scenario_abs"])
        setup = list(getattr(scenario, "setup", []) or [])
        established = await establish_substrate(
            user_id,
            requires=requires,
            setup=[s for s in setup if "write_substrate" in s or "delete_substrate" in s],
            authored_by=authored_by,
        )
        established["skipped_reset"] = False

    precondition = await check_preconditions(user_id, requires)
    return {
        "fired_ok": precondition["satisfied"],
        "established": established,
        "precondition": precondition,
    }


# ---------------------------------------------------------------------------
# Per-eval execution
# ---------------------------------------------------------------------------


async def run_one_eval(
    eval_def: dict,
    eval_index: int,
    raw_folder: Path,
    caller: str,
    *,
    user_id: str,
    persona_slug: str,
) -> dict:
    """Pre-flight, then (if preconditions hold) execute via ScenarioRunner."""
    from services.operator_proxy.scenarios import Scenario, ScenarioRunner

    eval_slug = eval_def["eval"]
    scen_path = eval_def["_scenario_abs"]
    eval_folder = raw_folder / f"eval-{eval_index + 1}-{eval_slug}"

    print(f"\n=== Eval {eval_index + 1} — {eval_slug} ===")
    print(f"    scenario: {Scenario.from_file(scen_path).slug}")
    print(f"    capture:  {eval_folder}")

    # --- pre-flight (C2 + C3) ---
    pf = await preflight_eval(user_id, eval_def, persona_slug=persona_slug)
    if not pf["fired_ok"]:
        failed = [c for c in pf["precondition"]["checks"] if not c["ok"]]
        detail = "; ".join(f"{c['assertion'].get('path')}: {c['detail']}" for c in failed)
        print(f"    REFUSED (precondition violation): {detail}")
        return {
            "eval": eval_slug,
            "scenario": Scenario.from_file(scen_path).slug,
            "folder": str(eval_folder.relative_to(raw_folder.parent)),
            "eval_folder_abs": str(eval_folder),
            "fired": False,
            "outcome": "refused",
            "preflight": pf,
            "prior": eval_def.get("prior", ""),
            "description": eval_def.get("description", ""),
            "accumulates": eval_def.get("accumulates", False),
            "inherits": eval_def.get("inherits", []),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "duration_sec": 0,
            "turns_executed": 0,
            "triggering_revision_ids": [],
            "evaluations": [],
            "response_inconclusive": False,
        }

    scenario = Scenario.from_file(scen_path)
    runner = ScenarioRunner(scenario, caller=caller)

    started_at = datetime.now(timezone.utc)
    try:
        scenario_result = await runner.run(eval_folder)
        outcome = "completed"
        error = None
    except Exception as exc:
        scenario_result = None
        outcome = "failed"
        error = f"{type(exc).__name__}: {exc}"
        print(f"    FAIL: {error}")
    finished_at = datetime.now(timezone.utc)

    triggering_revision_ids = _extract_triggering_revision_ids(runner.evaluations)

    # Empty-wake guard (§6.2 / S1): flag near-empty Reviewer responses. A
    # send_message turn that returned sub-threshold text carries no narration
    # to read — INCONCLUSIVE, never a clean read.
    response_inconclusive = _detect_empty_responses(runner.evaluations)
    if response_inconclusive:
        print(f"    WARN: {response_inconclusive} near-empty response(s) — flagged INCONCLUSIVE")

    return {
        "eval": eval_slug,
        "scenario": scenario.slug,
        "folder": str(eval_folder.relative_to(raw_folder.parent)),
        "eval_folder_abs": str(eval_folder),
        "fired": True,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_sec": int((finished_at - started_at).total_seconds()),
        "outcome": outcome,
        "error": error,
        "turns_executed": (scenario_result or {}).get("turns_executed", 0),
        "preflight": pf,
        "prior": eval_def.get("prior", ""),
        "description": eval_def.get("description", ""),
        "accumulates": eval_def.get("accumulates", False),
        "inherits": eval_def.get("inherits", []),
        "triggering_revision_ids": triggering_revision_ids,
        "evaluations": runner.evaluations,
        "response_inconclusive": response_inconclusive,
    }


def _detect_empty_responses(evaluations: list[dict]) -> int:
    """Count send_message turns whose Reviewer response was sub-threshold.

    The empty-wake false-negative trap (§6.2): a zero-or-near-zero-char
    response contains no narration to check, so "no confabulation found" is
    trivially true and is NOT a pass. Returns the count of near-empty
    responses so the runner can flag the eval INCONCLUSIVE.
    """
    count = 0
    for ev in evaluations:
        if ev.get("phase") != "turn" or ev.get("action") != "send_message":
            continue
        # The scenario runner records the response text/length under varying
        # keys depending on capture version; check the common ones.
        text = ev.get("response_text") or ev.get("text") or ""
        resp = ev.get("response") if isinstance(ev.get("response"), dict) else {}
        text = text or (resp.get("text") or "")
        if len(text.strip()) < EMPTY_RESPONSE_CHAR_THRESHOLD:
            count += 1
    return count


def _extract_triggering_revision_ids(evaluations: list[dict]) -> list[str]:
    """Pull revision_ids that should trigger Reviewer substrate-event wakes.

    flip_frontmatter_field / write_substrate turns on hook-bound paths fire
    the bundle's substrate-event hook; the revision_id becomes the wake_queue
    dedup_key (ADR-298 D6). Seed_draft first-writes don't transition status,
    so they don't trigger — excluded.
    """
    revs: list[str] = []
    for ev in evaluations:
        if ev.get("phase") == "turn" and ev.get("action") in ("flip_frontmatter_field", "write_substrate"):
            rev_id = ev.get("revision_id")
            if rev_id:
                revs.append(rev_id)
    return revs


# ---------------------------------------------------------------------------
# Completion gate — poll wake_queue + execution_events until wakes settle
# (read-kind-agnostic; survives the v2 reshape unchanged)
# ---------------------------------------------------------------------------


COMPLETION_GATE_TIMEOUT_SEC = 600
COMPLETION_GATE_POLL_SEC = 10


async def wait_for_completion(
    user_id: str,
    eval_results: list[dict],
    session_started_at: datetime,
) -> dict:
    from services.supabase import get_service_client

    expected_revs: set[str] = set()
    addressed_turn_count = 0
    for r in eval_results:
        if not r.get("fired"):
            continue
        for rev in r.get("triggering_revision_ids", []) or []:
            expected_revs.add(rev)
        for ev in r.get("evaluations", []) or []:
            if ev.get("phase") == "turn" and ev.get("action") == "send_message":
                addressed_turn_count += 1

    print(f"    expected substrate_event wakes: {len(expected_revs)}")
    print(f"    expected addressed wakes: {addressed_turn_count}")

    if not expected_revs and addressed_turn_count == 0:
        print("    no Reviewer wakes expected; skipping completion gate")
        return {
            "elapsed_sec": 0,
            "substrate_event_settled": 0,
            "substrate_event_pending": 0,
            "substrate_event_expected": 0,
            "addressed_settled": 0,
            "addressed_expected": 0,
            "timed_out": False,
        }

    client = get_service_client()
    loop = asyncio.get_running_loop()
    started_at = datetime.now(timezone.utc)

    def query_substrate_event_status() -> dict[str, str]:
        if not expected_revs:
            return {}
        resp = (
            client.table("wake_queue")
            .select("dedup_key, status")
            .eq("user_id", user_id)
            .eq("wake_source", "substrate_event")
            .in_("dedup_key", list(expected_revs))
            .execute()
        )
        return {row["dedup_key"]: row["status"] for row in (resp.data or [])}

    def query_addressed_count() -> int:
        resp = (
            client.table("execution_events")
            .select("id")
            .eq("user_id", user_id)
            .eq("wake_source", "addressed")
            .gte("created_at", session_started_at.isoformat())
            .execute()
        )
        return len(resp.data or [])

    timed_out = False
    while True:
        elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
        if elapsed >= COMPLETION_GATE_TIMEOUT_SEC:
            timed_out = True
            break

        substrate_status = await loop.run_in_executor(None, query_substrate_event_status)
        addressed_count = await loop.run_in_executor(None, query_addressed_count)

        substrate_settled = sum(1 for s in substrate_status.values() if s in ("completed", "failed", "dropped"))
        substrate_pending = sum(1 for s in substrate_status.values() if s in ("pending", "locked"))
        substrate_missing = len(expected_revs) - len(substrate_status)
        addressed_done = addressed_count >= addressed_turn_count

        all_substrate_done = (substrate_settled == len(expected_revs))

        print(f"    [{int(elapsed):3d}s] substrate_event: {substrate_settled}/{len(expected_revs)} settled "
              f"({substrate_pending} pending, {substrate_missing} not-yet-queued); "
              f"addressed: {addressed_count}/{addressed_turn_count}")

        if all_substrate_done and addressed_done:
            break

        await asyncio.sleep(COMPLETION_GATE_POLL_SEC)

    elapsed = int((datetime.now(timezone.utc) - started_at).total_seconds())
    final_substrate = await loop.run_in_executor(None, query_substrate_event_status)
    final_addressed = await loop.run_in_executor(None, query_addressed_count)

    return {
        "elapsed_sec": elapsed,
        "substrate_event_settled": sum(1 for s in final_substrate.values() if s in ("completed", "failed", "dropped")),
        "substrate_event_pending": sum(1 for s in final_substrate.values() if s in ("pending", "locked")),
        "substrate_event_expected": len(expected_revs),
        "addressed_settled": final_addressed,
        "addressed_expected": addressed_turn_count,
        "timed_out": timed_out,
    }


# ---------------------------------------------------------------------------
# Re-snapshot per-eval captures after the completion gate (post-wake state)
# ---------------------------------------------------------------------------


async def resnapshot_eval(user_id: str, eval_result: dict) -> None:
    from services.operator_proxy.capture import CaptureSession

    folder = Path(eval_result["eval_folder_abs"])
    session = CaptureSession(user_id, folder, scenario_name=eval_result["scenario"])
    eval_started_at = datetime.fromisoformat(eval_result["started_at"])
    session.baseline = await _baseline_at_time(user_id, eval_started_at)
    await session.snapshot()


async def _baseline_at_time(user_id: str, baseline_at: datetime) -> "CaptureSnapshot":
    from services.operator_proxy.capture import CaptureSnapshot
    from services.supabase import get_service_client

    client = get_service_client()
    loop = asyncio.get_running_loop()

    def query():
        rev_resp = client.table("workspace_file_versions").select("id").eq("user_id", user_id).lt("created_at", baseline_at.isoformat()).execute()
        msg_resp = client.table("session_messages").select("id, session_id").lt("created_at", baseline_at.isoformat()).execute()
        prop_resp = client.table("action_proposals").select("id").eq("user_id", user_id).lt("created_at", baseline_at.isoformat()).execute()
        ee_resp = client.table("execution_events").select("id").eq("user_id", user_id).lt("created_at", baseline_at.isoformat()).execute()
        return rev_resp, msg_resp, prop_resp, ee_resp

    rev_resp, msg_resp, prop_resp, ee_resp = await loop.run_in_executor(None, query)
    return CaptureSnapshot(
        user_id=user_id,
        captured_at=baseline_at.isoformat(),
        revision_ids={r["id"] for r in (rev_resp.data or [])},
        proposal_ids={r["id"] for r in (prop_resp.data or [])},
        message_ids={r["id"] for r in (msg_resp.data or [])},
        execution_event_ids={r["id"] for r in (ee_resp.data or [])},
    )


# ---------------------------------------------------------------------------
# Architecture-shape receipt capture (§5 of the audit) — per-eval
# ---------------------------------------------------------------------------


async def capture_shape_receipts(user_id: str, eval_result: dict) -> dict:
    """Capture the rows that let a human check architecture-SHAPE, not just
    outcome (the ADR-307 transferable lesson): action_proposals WITH family,
    execution_events WITH wake_source/status, and the self-wake count. Written
    to raw/{eval}/shape-receipts.md so shape-correctness is checkable inline.
    """
    from services.supabase import get_service_client

    if not eval_result.get("fired"):
        return {"proposals": [], "events": [], "self_wakes": 0}

    client = get_service_client()
    loop = asyncio.get_running_loop()
    start = eval_result["started_at"]
    end = eval_result["finished_at"]
    # pad for reactive wakes that land just after a turn write
    end_padded = (_parse_iso8601_lenient(end) + timedelta(minutes=5)).isoformat()

    def query():
        props = (
            client.table("action_proposals")
            .select("id, primitive, family, status, source, decision_context, created_at")
            .eq("user_id", user_id).gte("created_at", start).lte("created_at", end_padded)
            .order("created_at").execute()
        )
        events = (
            client.table("execution_events")
            .select("id, slug, trigger_type, wake_source, mode, status, created_at")
            .eq("user_id", user_id).gte("created_at", start).lte("created_at", end_padded)
            .order("created_at").execute()
        )
        return props.data or [], events.data or []

    proposals, events = await loop.run_in_executor(None, query)
    # self-wake = a proposal_arrival execution_event on the Reviewer's OWN
    # queued write (source='reviewer:*'). ADR-307 closed this; capturing the
    # count makes the closure checkable per-eval.
    reviewer_sourced_ids = {p["id"] for p in proposals if str(p.get("source") or "").startswith("reviewer:")}
    self_wakes = sum(1 for e in events if e.get("wake_source") == "proposal_arrival") if reviewer_sourced_ids else 0

    receipts = {"proposals": proposals, "events": events, "self_wakes": self_wakes}
    _write_shape_receipts_md(eval_result, receipts)
    return receipts


def _write_shape_receipts_md(eval_result: dict, receipts: dict) -> None:
    folder = Path(eval_result["eval_folder_abs"])
    folder.mkdir(parents=True, exist_ok=True)
    lines = [f"# Shape receipts — {eval_result['eval']}\n",
             "_Architecture-shape evidence (not just outcome). Per the ADR-307 "
             "lesson: check the action landed in the architecturally-correct "
             "shape — family, status, source, self-wake count._\n"]
    lines.append("## action_proposals in window")
    if receipts["proposals"]:
        lines.append("| id | family | primitive | status | source | dc_keys |")
        lines.append("|---|---|---|---|---|---|")
        for p in receipts["proposals"]:
            dc = sorted((p.get("decision_context") or {}).keys())
            lines.append(f"| `{p['id'][:8]}` | {p.get('family')} | {p.get('primitive')} | "
                         f"{p.get('status')} | {p.get('source')} | {dc} |")
    else:
        lines.append("_(none)_")
    lines.append("\n## execution_events in window")
    if receipts["events"]:
        lines.append("| created_at | trigger | wake_source | mode | status |")
        lines.append("|---|---|---|---|---|")
        for e in receipts["events"]:
            lines.append(f"| {e.get('created_at')} | {e.get('trigger_type')} | "
                         f"{e.get('wake_source')} | {e.get('mode')} | {e.get('status')} |")
    else:
        lines.append("_(none)_")
    lines.append(f"\n## Self-wake count (Reviewer re-waking on its own queued write)")
    lines.append(f"**{receipts['self_wakes']}** — should be 0 (ADR-307 source-skip guard).")
    (folder / "shape-receipts.md").write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Cost rollup (C6 — windowed by created_at, the one honest number)
# ---------------------------------------------------------------------------


async def compose_cost_rollup(
    user_id: str,
    session_started_at: datetime,
    session_finished_at: datetime,
) -> dict:
    from services.supabase import get_service_client

    client = get_service_client()
    loop = asyncio.get_running_loop()

    def query():
        return (
            client.table("execution_events")
            .select("id, slug, mode, wake_source, status, tool_rounds, input_tokens, output_tokens, cache_read_tokens, cache_create_tokens, cost_usd, duration_ms, created_at")
            .eq("user_id", user_id)
            .gte("created_at", session_started_at.isoformat())
            .lte("created_at", session_finished_at.isoformat())
            .order("created_at")
            .execute()
        )

    response = await loop.run_in_executor(None, query)
    rows = response.data or []

    total_usd = sum((r.get("cost_usd") or 0) for r in rows)
    total_in = sum((r.get("input_tokens") or 0) for r in rows)
    total_out = sum((r.get("output_tokens") or 0) for r in rows)
    judgment_rows = [r for r in rows if r.get("mode") == "judgment"]
    mechanical_rows = [r for r in rows if r.get("mode") == "mechanical"]

    per_slug: dict[str, dict] = {}
    for r in rows:
        slug = r.get("slug") or "(unknown)"
        bucket = per_slug.setdefault(slug, {"wakes": 0, "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0})
        bucket["wakes"] += 1
        bucket["cost_usd"] += r.get("cost_usd") or 0
        bucket["input_tokens"] += r.get("input_tokens") or 0
        bucket["output_tokens"] += r.get("output_tokens") or 0

    return {
        "session_window_start": session_started_at.isoformat(),
        "session_window_end": session_finished_at.isoformat(),
        "wake_count": len(rows),
        "judgment_wake_count": len(judgment_rows),
        "mechanical_wake_count": len(mechanical_rows),
        "total_cost_usd": round(total_usd, 4),
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "per_slug": per_slug,
        "raw_rows": rows,
    }


def _parse_iso8601_lenient(raw: str) -> datetime:
    """Parse ISO 8601 with tolerance for non-6-digit microseconds + 'Z'
    (Python 3.9 fromisoformat is strict)."""
    import re
    normalized = raw.replace("Z", "+00:00")
    match = re.match(r"^(.+\.)(\d{1,5})((?:[+-]\d{2}:\d{2})?)$", normalized)
    if match:
        prefix, micros, tz = match.groups()
        normalized = f"{prefix}{micros.ljust(6, '0')}{tz}"
    return datetime.fromisoformat(normalized)


# ---------------------------------------------------------------------------
# SESSION.md prose scaffold (C4 + C5) — the runner emits prompts; the
# operator writes the read. NO Pass? cells, NO dimension tables (§1.3).
# ---------------------------------------------------------------------------


def render_session_md(
    *,
    suite: dict,
    user_id: str,
    user_email: str,
    eval_results: list[dict],
    cost_rollup: dict,
    completion: dict,
    session_started_at: datetime,
    session_finished_at: datetime,
) -> str:
    duration_min = int((session_finished_at - session_started_at).total_seconds() / 60)
    session_total_usd = cost_rollup["total_cost_usd"]
    per_session_budget = suite["budget"]["per_session_usd"]
    fired = [r for r in eval_results if r.get("fired")]
    refused = [r for r in eval_results if not r.get("fired")]

    lines: list[str] = []
    lines.append(f"# Eval-suite session — {suite['eval_suite']}\n")
    lines.append(f"**Captured**: {session_started_at.isoformat()}   "
                 f"**Persona**: {suite['persona']}   "
                 f"**Workspace**: `{user_id[:8]}` ({user_email})")
    lines.append(f"**Read kind**: {suite['read_kind']}")
    lines.append(f"**Suite**: `docs/evaluations/eval-suites/{suite['eval_suite']}.yaml`")
    lines.append(f"**Evals fired**: {len(fired)} of {len(suite['evals'])}"
                 + (f"   ({len(refused)} REFUSED pre-flight — see §Preconditions)" if refused else ""))
    lines.append(f"**Duration**: {duration_min} min wall-clock")
    cost_label = "within" if session_total_usd <= per_session_budget else "EXCEEDS"
    lines.append(f"**Session cost**: ${session_total_usd:.4f} (budget ${per_session_budget:.2f}) — {cost_label}\n")

    if completion["substrate_event_expected"] > 0 or completion["addressed_expected"] > 0:
        gate_ok = (
            not completion["timed_out"]
            and completion["substrate_event_settled"] == completion["substrate_event_expected"]
            and completion["addressed_settled"] >= completion["addressed_expected"]
        )
        lines.append(
            f"**Completion gate**: {'all settled' if gate_ok else 'PARTIAL / TIMED OUT'} "
            f"(elapsed {completion['elapsed_sec']}s, "
            f"substrate_event {completion['substrate_event_settled']}/{completion['substrate_event_expected']}, "
            f"addressed {completion['addressed_settled']}/{completion['addressed_expected']})\n"
        )
    lines.append("---\n")

    # §Preconditions (automated)
    lines.append("## §Preconditions (automated)\n")
    lines.append("Per-eval `requires:` check at fire time. An eval that failed pre-flight did NOT fire (§3, S2).\n")
    lines.append("| Eval | requires | satisfied? | fired? |")
    lines.append("|---|---|---|---|")
    for r in eval_results:
        pf = r.get("preflight", {})
        checks = pf.get("precondition", {}).get("checks", [])
        if checks:
            req_summary = "; ".join(
                f"{c['assertion'].get('path', '?').split('/')[-1]}: {c['detail']}" for c in checks
            )
            satisfied = "YES" if pf.get("fired_ok") else "NO"
        else:
            req_summary = "_(none)_"
            satisfied = "n/a"
        fired_label = "yes" if r.get("fired") else "**REFUSED**"
        lines.append(f"| `{r['eval']}` | {req_summary} | {satisfied} | {fired_label} |")
    lines.append("")
    # Show establishment detail for transparency.
    est_lines = []
    for r in eval_results:
        est = r.get("preflight", {}).get("established", {})
        if est.get("deleted") or est.get("wrote"):
            est_lines.append(f"- `{r['eval']}`: deleted {est.get('deleted', [])}, "
                             f"wrote {[w['path'] for w in est.get('wrote', [])]}")
        elif est.get("skipped_reset"):
            est_lines.append(f"- `{r['eval']}`: accumulates — no reset (inherits prior state)")
    if est_lines:
        lines.append("**Establishment** (C3 reset-to-clean / accumulation):")
        lines.extend(est_lines)
        lines.append("")
    lines.append("---\n")

    # §The read — runner leaves blank; operator writes (§6.1)
    lines.append("## §The read   ← operator writes this; runner leaves it blank\n")
    lines.append("_For each fired eval: read `raw/{eval}/transcript.md` + `substrate-diff.md` + "
                 "`shape-receipts.md`, then write prose answering whether the Reviewer reasoned "
                 "the way a mandate-holder would. There are no cells to fill (§1.3)._\n")
    for r in fired:
        lines.append(f"### {r['eval']}  — {(r.get('description') or '').strip().splitlines()[0] if r.get('description') else ''}\n")
        if r.get("response_inconclusive"):
            lines.append(f"> ⚠ **INCONCLUSIVE flag**: {r['response_inconclusive']} near-empty Reviewer "
                         f"response(s) (< {EMPTY_RESPONSE_CHAR_THRESHOLD} chars). Per §6.2, an empty "
                         f"response contains no narration to read — this is NOT a clean read. Verify the "
                         f"`execution_events` receipt in `shape-receipts.md` before scoring.\n")
        lines.append(f"**Prior**: {(r.get('prior') or '_(none declared)_').strip()}\n")
        lines.append("**What the Reviewer did**: _<!-- operator: prose from transcript + substrate-diff -->_\n")
        lines.append("**Coherent with the mandate?**: _<!-- operator: judgment against MANDATE + principles. "
                     "If diverged from prior — defensible alternative or real gap? If a gap, which cause "
                     "(a substrate / b Reviewer-read / c envelope / d canon, §1.2)? -->_\n")
        lines.append("**Receipts**: _<!-- operator: revision_ids, proposal rows (family!), execution_event ids — "
                     "inline, from shape-receipts.md -->_\n")
    for r in refused:
        failed = [c for c in r.get("preflight", {}).get("precondition", {}).get("checks", []) if not c["ok"]]
        detail = "; ".join(f"{c['assertion'].get('path')}: {c['detail']}" for c in failed)
        lines.append(f"### {r['eval']}  — REFUSED (precondition violation)\n")
        lines.append(f"Not fired. Preconditions not satisfied at fire time: {detail}. "
                     f"No read — the situation could not be established (§3).\n")
    lines.append("---\n")

    # §What the session says overall
    lines.append("## §What the session says overall   ← operator writes\n")
    lines.append("_One-to-three paragraphs. The load-bearing finding — what this session establishes "
                 "about whether the Reviewer reasons like a mandate-holder. Cross-eval patterns. "
                 "Each load-bearing claim carries a receipt._\n")
    lines.append("<!-- TODO operator -->\n")
    lines.append("---\n")

    # §Recommendations
    lines.append("## §Recommendations (if any)   ← operator writes\n")
    lines.append("_Hat-A system-canon changes this read recommends, each gated on a specific read above. "
                 "May be \"none — behavior is canon-coherent.\" Multi-rec or architectural → separate "
                 "commits (README rule 6)._\n")
    lines.append("<!-- TODO operator -->\n")
    lines.append("---\n")

    # §Cost (automated appendix)
    lines.append("## §Cost (automated appendix)\n")
    lines.append(f"**Session total**: ${session_total_usd:.4f} across {cost_rollup['wake_count']} wakes "
                 f"({cost_rollup['judgment_wake_count']} judgment, {cost_rollup['mechanical_wake_count']} mechanical). "
                 f"Budget ${per_session_budget:.2f} — {cost_label}.")
    lines.append(f"**Tokens**: {cost_rollup['total_input_tokens']:,} in / {cost_rollup['total_output_tokens']:,} out.\n")
    if cost_rollup["per_slug"]:
        lines.append("| Slug | Wakes | Cost USD | Tokens (in/out) |")
        lines.append("|---|---|---|---|")
        for slug, b in sorted(cost_rollup["per_slug"].items(), key=lambda kv: kv[1]["cost_usd"], reverse=True):
            lines.append(f"| `{slug}` | {b['wakes']} | ${b['cost_usd']:.4f} | {b['input_tokens']:,}/{b['output_tokens']:,} |")
        lines.append("")
    lines.append("**Per-eval capture folders**:")
    for r in eval_results:
        if r.get("fired"):
            lines.append(f"- `raw/{Path(r['folder']).name}/` — {r['turns_executed']} turns, {r['duration_sec']}s, {r['outcome']}")
        else:
            lines.append(f"- `raw/{Path(r['folder']).name}/` — REFUSED (precondition violation), not fired")
    lines.append("")
    lines.append("**Reproducible SQL** for re-pulling the session window:")
    lines.append("```sql")
    lines.append(
        f"SELECT slug, mode, wake_source, status, tool_rounds, input_tokens, output_tokens, cost_usd, created_at\n"
        f"FROM execution_events\n"
        f"WHERE user_id = '{user_id}'\n"
        f"  AND created_at >= '{session_started_at.isoformat()}'\n"
        f"  AND created_at <= '{session_finished_at.isoformat()}'\n"
        f"ORDER BY created_at;"
    )
    lines.append("```\n")
    lines.append("---\n")

    # §Read-state (C5 — replaces DRAFT/POPULATED)
    lines.append("## §Read-state\n")
    lines.append(f"Read: nothing yet — runner scaffold only. {len(fired)} eval(s) fired, "
                 f"{len(refused)} refused pre-flight. The operator reads raw/ artifacts and writes "
                 f"§The read + §What the session says. Name what was read here (e.g. \"evals 1-3 read; "
                 f"4-6 not yet\") — there is no DRAFT/POPULATED flag (§6.2 / S7).\n")
    lines.append(f"## Last updated\n\n{session_started_at.isoformat()} — runner emit.\n")
    return "\n".join(lines)


def emit_cost_rollup_csv(cost_rollup: dict, csv_path: Path) -> None:
    import csv
    raw = cost_rollup["raw_rows"]
    if not raw:
        csv_path.write_text("(no execution_events rows in session window)\n")
        return
    fieldnames = list(raw[0].keys())
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in raw:
            writer.writerow(row)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def run_suite(suite_path: Path, caller: str) -> int:
    from services.operator_proxy.client import OperatorProxy

    suite = load_suite(suite_path)
    print(f"suite: {suite['eval_suite']} (read_kind={suite['read_kind']})")
    print(f"persona: {suite['persona']}")
    print(f"evals: {len(suite['evals'])}")
    print(f"budget: per-session ${suite['budget']['per_session_usd']}")

    proxy = OperatorProxy.from_persona(suite["persona"], caller=caller)
    user_id = proxy.config.user_id
    user_email = proxy.config.email or "(unknown)"
    print(f"workspace: {user_id[:8]} ({user_email})")

    folder = session_folder(suite["eval_suite"])
    raw_folder = folder / "raw"
    raw_folder.mkdir(parents=True, exist_ok=True)
    print(f"session folder: {folder}\n")

    session_started_at = datetime.now(timezone.utc)
    eval_results: list[dict] = []
    for i, eval_def in enumerate(suite["evals"]):
        result = await run_one_eval(
            eval_def, i, raw_folder, caller,
            user_id=user_id, persona_slug=suite["persona"],
        )
        eval_results.append(result)

    write_phase_finished_at = datetime.now(timezone.utc)
    print(f"\n=== Write phase complete in {int((write_phase_finished_at - session_started_at).total_seconds())}s ===")
    print(f"=== Completion gate: polling wake_queue + execution_events ===")
    completion = await wait_for_completion(user_id, eval_results, session_started_at)
    print(f"    completion gate: elapsed {completion['elapsed_sec']}s, timed_out={completion['timed_out']}")

    print("\n=== Re-snapshotting per-eval captures + shape receipts (post-wake) ===")
    for r in eval_results:
        if not r.get("fired") or r["outcome"] != "completed":
            continue
        try:
            await resnapshot_eval(user_id, r)
            await capture_shape_receipts(user_id, r)
            print(f"    captured: {r['eval']}")
        except Exception as exc:
            print(f"    capture FAILED for {r['eval']}: {type(exc).__name__}: {exc}")

    session_finished_at = datetime.now(timezone.utc)

    print("\n=== Composing cost rollup ===")
    cost_rollup = await compose_cost_rollup(user_id, session_started_at, session_finished_at)
    print(f"    wakes: {cost_rollup['wake_count']} (judgment: {cost_rollup['judgment_wake_count']})")
    print(f"    total cost: ${cost_rollup['total_cost_usd']:.4f}")

    emit_cost_rollup_csv(cost_rollup, raw_folder / "cost-rollup.csv")

    print("\n=== Rendering SESSION.md ===")
    session_md = render_session_md(
        suite=suite,
        user_id=user_id,
        user_email=user_email,
        eval_results=eval_results,
        cost_rollup=cost_rollup,
        completion=completion,
        session_started_at=session_started_at,
        session_finished_at=session_finished_at,
    )
    (folder / "SESSION.md").write_text(session_md)
    print(f"\nsession complete: {folder / 'SESSION.md'}")
    print("(read raw/ artifacts, then write §The read + §What the session says — no cells to fill)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Eval-suite session runner v2 (EVAL-SUITE-DISCIPLINE.md)")
    ap.add_argument("--suite", required=True, type=Path, help="Path to eval-suite YAML manifest")
    ap.add_argument("--caller", default="eval-suite-runner", help="Caller identity tag")
    args = ap.parse_args()

    if not args.suite.is_file():
        print(f"suite file not found: {args.suite}", file=sys.stderr)
        return 2
    return asyncio.run(run_suite(args.suite, args.caller))


if __name__ == "__main__":
    raise SystemExit(main())
