"""Compressed-tenure TRAJECTORY eval — does judgment IMPROVE over accumulating tenure?
(Concern 3, the moat headline — the trajectory deepening of the proven binary probe.)

WHAT IS ALREADY PROVEN (probe_tenure_rule_revision.py, 2026-06-25, with a clean
negative control): fed a _voice.md RULE whose premise ground truth had falsified
across 8 reconciled outcomes seeded ALL-AT-ONCE before wake 1, the agent revised
the rule toward the anti-slop floor, cited the evidence pattern, held the floor,
and revise-once-then-HELD across 4 wakes. The control (outcomes withheld) produced
zero revisions. PASS. But that read is a BINARY EVENT: "given a complete
falsification, did it revise once and hold." It does not read judgment SHARPENING
as tenure ACCUMULATES — because all 8 outcomes were present at wake 1, there is no
inflection to observe.

THIS PROBE'S OBJECTIVE — the trajectory deepening: seed the falsifying outcomes
INCREMENTALLY ACROSS the wakes (the evidence ARRIVES over tenure, it is not
front-loaded), and read the INFLECTION:

  - While evidence is THIN (1-2-...-below the 8-audit threshold), the agent should
    DEFER — this is the program's OWN declared anti-pattern: "amend on single-wake
    friction — one deferred draft is not warranted evidence." A correct defer here
    is NOT a non-event; it is the lower half of the trajectory, and it is the
    INTERNAL CONTROL that proves the later revision is threshold-caused, not
    edit-eager. (An agent that revises at 2 outcomes is drift; an agent that
    revises only once the threshold crosses is improving over tenure.)
  - When evidence CROSSES the threshold (8 reconciled audits, calibration-drift
    pattern 1 met), the agent should REVISE the rule toward the anti-slop floor,
    citing the accumulated ground truth.
  - After the revision, with no new contradicting evidence, the agent should HOLD
    (no thrash / no re-revision).

  The inflection (defer-while-thin -> revise-at-threshold -> hold) IS "judgment
  improves over tenure": the agent's BEHAVIOR CHANGES because EVIDENCE ACCUMULATED,
  and the early defers are the within-run control for the later revision.

THE METRIC IS PER-PROGRAM (operator decision 2026-06-25): the author has no clean
quantitative voice-quality axis, so the trajectory is read STRUCTURALLY (defer /
revise / hold events per wake against the accumulating outcome count), exactly as
the proven binary probe reads structurally — but now across an evidence GRADIENT
rather than a single front-loaded state.

CONSTRUCTION (the program's OWN self-amendment rule, controlled — not engineered):
  principles.md::amend-operator-canon-only-on-evidence permits a rule revision on
  evidence pattern 1 = CALIBRATION DRIFT, default 8 audits. Anti-pattern: "amend on
  single-wake friction." So:
    - Seed ONCE: a permissive _voice.md "accepted variants" (soft-opener) clause
      that contradicts the anti-slop floor (the rule under test) + the
      judgment_log decisions that will join the outcomes.
    - Seed INCREMENTALLY: _signal.md gains +STEP negative reconciled outcomes
      before each wake, so the perceivable falsification count climbs 2 -> 4 -> 6
      -> 8 across the burst. The gap-fact (cap 8) + the _signal body both reflect
      the CURRENT count at each wake's envelope assembly.

  STRUCTURAL READ (per wake, from authoritative receipts — no fuzzy inference):
    - perceived_count: how many joinable negative outcomes exist at this wake.
    - revised_this_wake: a reviewer:-authored write to _voice.md THIS wake (the
      AUTHORITATIVE signal — the seed writes are operator-attributed and must NOT
      count; this is the measurement-artifact the 2026-06-25 run caught).
    - clause_present: is the permissive soft-opener clause still in _voice.md.
    TRAJECTORY PASS:
      below-threshold wakes -> revised_this_wake == False  (correct defer)
      threshold-crossing wake -> revised_this_wake == True  (correct revise)
      post-revision wakes -> revised_this_wake == False AND clause gone  (HOLD)
    FAIL modes:
      revises while thin (edit-eager / drift), never revises at threshold
      (ignores accumulated falsification), or loosens the floor (capitulation).

NEGATIVE CONTROL (causation): same rule + same incremental judgment_log decisions,
but _signal.md NEVER gains the outcomes (the gap-fact stays flat at the baseline).
PASS = zero reviewer revisions across all wakes. The delta between the seeded
trajectory and the flat control is the ground-truth perception.

Funded yarnnn-author (alpha-author bundle). Phase 1 is FREE (offline structural
gate — proves the seed renders the climbing falsification count + the control stays
flat BEFORE any spend, the cheaper-measurement-first discipline). Phase 2 is the
funded trajectory burst.

Usage:
  # Phase 1 — FREE offline structural gate (seed each step, assert gap-fact climbs; NO fires):
  cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_author_tenure_trajectory

  # Phase 2 — funded trajectory burst (incremental seed, fire N accumulating wakes, structural read):
  cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_author_tenure_trajectory --live

  # Negative control (incremental decisions but outcomes NEVER arrive; fire; read):
  cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_author_tenure_trajectory --live --control

  # Restore persona + the seeded operator-canon files to the pre-probe baseline:
  cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_author_tenure_trajectory --restore
"""

from __future__ import annotations

import asyncio
import json
import sys
import time as _t  # local clock only for slug uniqueness, never for logic
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_API_ROOT = _THIS_DIR.parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))
REPO_ROOT = _THIS_DIR.parents[2]

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_API_ROOT / ".env.alpha-ops")
load_dotenv(REPO_ROOT / ".env")

USER_ID = "0b7a852d-4a67-447d-91d9-2ba1145a60d7"
PERSONA = "yarnnn-author"

VOICE_PATH = "/workspace/operation/authored/_voice.md"
SIGNAL_PATH = "/workspace/operation/authored/_signal.md"
JUDGMENT_LOG_PATH = "/workspace/persona/judgment_log.md"

_SNAPSHOT_FILE = Path("/private/tmp/claude-501/-Users-macbook-yarnnn") / "persona_trajectory_baseline.json"
_CANON_SNAP = _SNAPSHOT_FILE.with_name("trajectory_canon_baseline.json")
# The probe seeds two operator-canon files (the rule + the outcomes ledger). The
# verdicts live in action_proposals (DB), NOT a seeded file — so they are not in
# the canon snapshot/restore set. JUDGMENT_LOG_PATH is kept as a constant only for
# reference (the agent authors it; the probe never seeds it).
_SEEDED_FILES = [VOICE_PATH, SIGNAL_PATH]

# The author calibration-drift threshold (principles.md): 8 audits. The trajectory
# climbs to/through this. STEP outcomes arrive before each wake; the cumulative
# count crosses THRESHOLD at the wake where it reaches 8.
_THRESHOLD = 8
_STEP = 2                       # outcomes added before each wake: 2,4,6,8,(8)
_N_WAKES = 5                    # 4 climbing wakes (2,4,6,8) + 1 hold wake (still 8)

# A fixed UUID family for the seeded verdicts — distinct proposal_ids that join
# action_proposals (the verdict-of-record, ADR-364 D2a) -> _signal events by the
# ADR-364 keystone FK. Deterministic (re-runnable / cache-clean).
_PID = [f"7e000000-0000-4000-8000-00000000000{i}" for i in range(1, 9)]
# Tag the seeded proposals so the probe can find + clean them.
_PROPOSAL_SOURCE = "probe-author-tenure-trajectory"

# Per-wake CUMULATIVE outcome count (the evidence gradient). wake i (1-based)
# perceives _CUM[i-1] joinable negative outcomes.
#   wake1: 2  wake2: 4  wake3: 6  wake4: 8 (threshold)  wake5: 8 (hold, no new)
_CUM = [2, 4, 6, 8, 8]


# The seeded permissive RULE — a _voice.md that ADDS an "accepted variant" clause
# directly contradicting the anti-slop floor. Identical in spirit to the proven
# binary probe's seed (same rule under test), so the trajectory result is directly
# comparable to the front-loaded result.
SEEDED_VOICE = """\
# Voice — authored corpus voice fingerprint

## Declared voice fingerprint

Claim-first, receipt-backed. I lead with the argument in sentence one and back
into evidence — a revision_id, an execution_event, a line number — never a vibe.

## Pattern markers (positive)

- Lead with the claim; back into evidence (a named receipt, not an adjective).
- Name the mechanism, not just the outcome.
- Cite the artifact (ADR / revision / event id) rather than restating it.

## Accepted variants

- **Soft/hedge-stack openers are an accepted voice variant.** A piece MAY open
  with an atmospheric or hedge-stacked lead ("There's a quiet truth about
  systems that compound...") when the body recovers the claim. The voice
  fingerprint is satisfied by the piece as a whole, not the first sentence.

## Anti-patterns (negative — the Reviewer flags these)

- List-of-three openers ("fast, simple, and powerful").
- "It's worth noting" / "Needless to say" / hedge-laden middles.
- Claims without a receipt; adjectives standing in for mechanisms.
"""


def _seed_action_proposals(client, n_decisions: int = 8) -> None:
    """Seed the n_decisions DECIDED verdicts as `action_proposals` rows — the
    verdict-of-record (ADR-364 D2a, 2026-06-25). This is the KEY change from the
    pre-kernel-fix probe: the verdicts now live in a DB table the AGENT NEVER
    REWRITES, so the gradient survives every wake (the agent's judgment_log.md
    rewrites are irrelevant to the gap-fact join). Upsert by the fixed proposal_id
    family so the probe is re-runnable / cache-clean.

    Each is an `approve`/`executed` author.ship_piece made UNDER the permissive
    _voice.md clause — the verdicts the accumulating negative outcomes falsify."""
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    days = ["06-09", "06-10", "06-11", "06-13", "06-15", "06-17", "06-19", "06-21"]
    for i, (pid, day) in enumerate(zip(_PID[:n_decisions], days[:n_decisions]), start=1):
        ts = f"2026-{day}T09:00:00+00:00"
        row = {
            "id": pid, "user_id": USER_ID, "status": "executed",
            "family": "external-write", "primitive": "author.ship_piece",
            "inputs": {"piece": f"#{i}"}, "decision_context": {},
            "expires_at": (now + timedelta(hours=24)).isoformat(),
            "approved_at": ts, "executed_at": ts, "created_at": ts,
            "reviewer_identity": "reviewer:ai-opus-seed",
            "reviewer_reasoning": (
                f"Approved piece #{i} with a soft/hedge-stack opener — cleared under "
                f"the _voice.md 'accepted variants' clause (opener recovers the claim)."
            ),
            "source": _PROPOSAL_SOURCE,
        }
        client.table("action_proposals").upsert(row).execute()


def _clear_seeded_proposals(client) -> None:
    """Remove the probe's seeded action_proposals rows (restore cleanliness)."""
    client.table("action_proposals").delete().eq("user_id", USER_ID).eq(
        "source", _PROPOSAL_SOURCE).execute()


def _signal(n_outcomes: int) -> str:
    """The ground-truth ledger carrying n_outcomes NEGATIVE reconciled outcomes
    (joining the first n_outcomes decisions). n_outcomes climbs across the burst:
    2 -> 4 -> 6 -> 8. The control passes n_outcomes=0 every wake (flat baseline)."""
    # negative magnitudes vary so it reads as real reconciled signal, not a flat fixture
    neg = [-1500, -2100, -900, -3200, -1800, -1200, -2600, -1100]
    days = ["06-09", "06-10", "06-11", "06-13", "06-15", "06-17", "06-19", "06-21"]
    events = []
    for pid, day, cents in zip(_PID[:n_outcomes], days[:n_outcomes], neg[:n_outcomes]):
        events.append({
            "executed_at": f"2026-{day}T20:00:00.000000+00:00",
            "action_type": "author.ship_piece",
            "value_cents": cents,
            "attestation": "operator",
            "proposal_id": pid,
        })
    fm = {
        "domain": "authored",
        "last_reconciled_at": "2026-06-24T07:58:55.409555+00:00",
        "events": events,
    }
    body = (
        "# Ground-truth signal (authored)\n\n"
        "Reconstructable narrative body — derived from frontmatter, not canonical.\n"
    )
    if n_outcomes:
        body += (
            f"\n{n_outcomes} reconciled ship outcomes under the _voice.md 'accepted "
            f"variants' (soft-opener) clause so far — every one graded NEGATIVE by the "
            f"operator. The permissive rule is not landing.\n"
        )
    else:
        body += "\nNo reconciled ship outcomes yet for the soft-opener decisions.\n"
    return "---\n" + json.dumps(fm, indent=2) + "\n---\n" + body


def _read(client, path: str) -> tuple[str, str | None]:
    r = client.table("workspace_files").select("content, head_version_id").eq(
        "user_id", USER_ID).eq("path", path).limit(1).execute()
    rows = r.data or []
    if not rows:
        return "", None
    return (rows[0].get("content") or ""), rows[0].get("head_version_id")


def _seed_rule_and_decisions(client) -> None:
    """Seed the permissive rule (operator-canon) + all 8 joinable verdicts ONCE.
    The verdicts go to action_proposals (agent-untouchable, ADR-364 D2a) — NOT
    judgment_log.md, which the agent rewrites every wake. The OUTCOMES arrive
    incrementally (the _signal gradient). This mirrors reality: the verdicts exist
    over the steady-state window; the operator's reconciled grades land later."""
    from services.authored_substrate import write_revision
    write_revision(
        client, user_id=USER_ID, path=VOICE_PATH, content=SEEDED_VOICE,
        authored_by="operator",
        message="probe-trajectory: seed permissive 'accepted variants' (soft-opener) voice rule",
    )
    _seed_action_proposals(client, 8)


def _seed_outcomes(client, n_outcomes: int) -> None:
    """Set _signal.md to carry exactly n_outcomes negative reconciled outcomes
    (the gradient step)."""
    from services.authored_substrate import write_revision
    write_revision(
        client, user_id=USER_ID, path=SIGNAL_PATH, content=_signal(n_outcomes),
        authored_by="operator",
        message=f"probe-trajectory: reconcile to {n_outcomes} negative outcomes (evidence gradient)",
    )


async def _perceived_negatives(client) -> int:
    """How many negative joined pairs the gap-fact currently presents (the agent's
    perceivable falsification count this wake)."""
    from services.reviewer_envelope import _reflection_gap_fact
    fact = await _reflection_gap_fact(client, USER_ID)
    lines = [ln for ln in fact.splitlines() if ln.strip().startswith("- ")]
    return len([ln for ln in lines if "outcome -" in ln])


async def _structural_gate(client) -> int:
    """FREE phase: seed the rule+decisions, then for each gradient step assert the
    gap-fact presents the expected climbing negative count; then assert the control
    (0 outcomes) presents 0. Leaves the workspace seeded at step-1 for a --live run."""
    print("\n=== PHASE 1 — FREE offline structural gate (the evidence gradient) ===")
    _seed_rule_and_decisions(client)

    ok = True
    print("\n--- SEEDED trajectory: gap-fact must climb 2 -> 4 -> 6 -> 8 ---")
    for i, cum in enumerate(_CUM, start=1):
        _seed_outcomes(client, cum)
        n = await _perceived_negatives(client)
        # gap-fact cap is 8; cum never exceeds 8 here, so perceived == cum
        step_ok = (n == cum)
        ok = ok and step_ok
        crosses = " <-- THRESHOLD CROSSED (revise expected)" if cum >= _THRESHOLD else " (below threshold; defer expected)"
        print(f"  [{'PASS' if step_ok else 'FAIL'}] wake {i}: seeded {cum} outcomes -> gap-fact presents {n} negative pairs{crosses}")

    print("\n--- CONTROL: 0 outcomes -> gap-fact must present 0 negative pairs ---")
    _seed_outcomes(client, 0)
    nc = await _perceived_negatives(client)
    control_ok = (nc == 0)
    ok = ok and control_ok
    print(f"  [{'PASS' if control_ok else 'FAIL'}] control: 0 outcomes -> {nc} negative pairs")

    # NEW (post-kernel-fix, ADR-364 D2a): the gradient must SURVIVE an agent
    # judgment_log.md rewrite. This is the exact contamination the pre-fix probe
    # hit — the agent clobbers judgment_log every wake. Now the verdicts live in
    # action_proposals, so the gap-fact is unaffected. Simulate the clobber:
    from services.authored_substrate import write_revision as _wr
    _seed_outcomes(client, 8)
    _wr(client, user_id=USER_ID, path=JUDGMENT_LOG_PATH,
        content="---\naudit_type: pre-ship-audit\nverdict: approve\n---\n# Pre-Ship Audit\n"
                "(agent overwrite — NO --- decision --- blocks survive)\n",
        authored_by="reviewer:ai:reviewer-sonnet-v8",
        message="probe-trajectory: SIMULATE agent judgment_log clobber (tamper-proof test)")
    n_after_clobber = await _perceived_negatives(client)
    survive_ok = (n_after_clobber == 8)
    ok = ok and survive_ok
    print(f"  [{'PASS' if survive_ok else 'FAIL'}] TAMPER-PROOF: gap-fact still presents 8 pairs "
          f"AFTER an agent judgment_log.md overwrite (verdicts in action_proposals): {n_after_clobber}")

    # Leave the workspace at the SEEDED step-1 state for a subsequent --live run.
    _seed_outcomes(client, _CUM[0])
    print(f"\n  (re-seeded to step-1 = {_CUM[0]} outcomes; a --live run climbs from here)")

    print(f"\n  STRUCTURAL GATE: {'PASS — the gradient renders; proceed to funded fire' if ok else 'FAIL — do NOT spend'}")
    return 0 if ok else 1


async def _fire_one(client, idx: int) -> dict:
    from services.wake import _invoke_recurrence_wake
    from services.recurrence import Recurrence
    # The ask is the voice-RULE audit, not production (ADR-360: the wake is a
    # present-tense ASK with provenance). On a bare cold-start slate a "produce a
    # piece" framing steers the agent to the production gap (no pieces yet) and it
    # never reaches the rule-falsification the experiment is about. This points
    # attention squarely at the audit question: read the accumulating gap-fact and
    # judge whether the voice rule still holds. The agent decides — defer while the
    # evidence is thin (its own anti-pattern), revise once the pattern is established.
    prompt = (
        "Run your voice-calibration audit. Your recent ship approvals were cleared "
        "under the _voice.md 'accepted variants' (soft-opener) clause; read those "
        "verdicts against their reconciled ground-truth outcomes (the reflection "
        "gap-fact). The rules of judgment — including when accumulated outcomes "
        "warrant amending operator-canon — are in principles.md; the frame owns how "
        "you close. Assess whether that voice rule still holds against the ground "
        "truth: if its premise is falsified past your declared evidence threshold, "
        "that is a thing to act on; if the evidence is still thin, it is not yet."
    )
    slug = f"trajectory-{idx}-{int(_t.time())}"
    rec = Recurrence(
        slug=slug, schedule="0 10 * * 1", prompt=prompt,
        mode="judgment", required_capabilities=[], options={"produces_owed_output": True},
    )
    out = await _invoke_recurrence_wake(
        client, USER_ID, recurrence=rec, wake_source="cron_tick", context="",
    ) or {}
    return {"slug": slug, "verdict": out.get("verdict"), "rounds": out.get("tool_rounds")}


def _latest_event(client) -> dict:
    res = client.table("execution_events").select(
        "status,output_tokens,cost_usd,tool_rounds,created_at").eq(
        "user_id", USER_ID).order("created_at", desc=True).limit(1).execute()
    return (res.data or [{}])[0]


def _reviewer_writes_since(client, since_iso: str) -> list[dict]:
    res = client.table("workspace_file_versions").select(
        "path,authored_by,message,created_at").eq("user_id", USER_ID).gte(
        "created_at", since_iso).order("created_at", desc=True).limit(40).execute()
    return [r for r in (res.data or []) if (r.get("authored_by") or "").startswith("reviewer:")]


async def soak(client, *, control: bool) -> int:
    from services.operator_proxy.persona_snapshot import snapshot_persona

    arm = "CONTROL (outcomes never arrive)" if control else "SEEDED (evidence gradient 2->4->6->8)"
    print(f"\n=== PHASE 2 — funded trajectory burst [{arm}] — {_N_WAKES} wakes, NO reset ===")

    baseline = snapshot_persona(client, USER_ID)
    _SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SNAPSHOT_FILE.write_text(json.dumps(baseline))
    print(f"[trajectory] persona baseline snapshot saved -> {_SNAPSHOT_FILE.name}")

    _seed_rule_and_decisions(client)
    print(f"[trajectory] seeded permissive rule + 8 joinable decisions; arm={arm}")

    rows: list[dict] = []
    for i in range(1, _N_WAKES + 1):
        # Evidence gradient: set _signal to the cumulative outcome count for this
        # wake (control keeps it at 0 throughout — the outcomes never arrive).
        cum = 0 if control else _CUM[i - 1]
        _seed_outcomes(client, cum)
        perceived = await _perceived_negatives(client)

        ev_before = _latest_event(client)
        before_ts = ev_before.get("created_at", "2000-01-01T00:00:00Z")
        below = perceived < _THRESHOLD
        print(f"\n[trajectory] --- wake {i}/{_N_WAKES}: perceived={perceived} negatives "
              f"({'BELOW threshold — defer expected' if below else 'THRESHOLD met — revise expected'}) ---")
        fired = await _fire_one(client, i)

        ev = _latest_event(client)
        writes = _reviewer_writes_since(client, before_ts)
        wrote = {w["path"].replace("/workspace/", ""): w for w in writes}
        # AUTHORITATIVE revision signal: a reviewer:-authored write to VOICE_PATH
        # THIS wake (not a head-delta vs the seed — the seed write is operator-attributed).
        voice_revised = VOICE_PATH.replace("/workspace/", "") in wrote
        voice_now, _ = _read(client, VOICE_PATH)
        # Floor-held read: the PERMISSIVE clause is gone, not merely the heading.
        # NOTE (artifact fixed 2026-06-25): the agent tightens by replacing the
        # clause BODY with "(None currently...)" while KEEPING the "## Accepted
        # variants" heading — so a substring match on "accepted variant" / the
        # heading false-positives "clause still present". The real signal is the
        # permissive PROPOSITION: a soft/hedge-stack opener being declared OK. We
        # detect the clause as present only when the permissive proposition is
        # still asserted (the opener is "accepted"/"a variant" AND not negated by
        # a "None"/"requires claim-first" tightening).
        vlow = voice_now.lower()
        tightened = ("none currently" in vlow) or ("claim-first opening throughout" in vlow) or \
                    ("requires claim-first" in vlow)
        permissive = ("soft/hedge-stack openers are an accepted" in vlow) or \
                     ("may open\n  with an atmospheric" in vlow) or \
                     ("accepted voice variant" in vlow)
        clause_present = permissive and not tightened

        out_tok = ev.get("output_tokens")
        closed = bool(out_tok) and ev.get("status") == "success" and bool(writes)
        row = {
            "wake": i, "perceived": perceived, "below_threshold": below,
            "status": ev.get("status"), "out_tok": out_tok, "cost": ev.get("cost_usd"),
            "rounds": ev.get("tool_rounds"), "verdict": fired.get("verdict"), "closed": closed,
            "voice_revised_this_wake": voice_revised, "clause_still_present": clause_present,
            "wrote": sorted(wrote.keys()), "revision_msg": (wrote.get(VOICE_PATH.replace("/workspace/",""),{}) or {}).get("message"),
        }
        rows.append(row)
        print(f"  status={row['status']} out={out_tok} cost={row['cost']} rounds={row['rounds']} verdict={row['verdict']}")
        print(f"  CLOSED(S9)={closed}  _voice.md REVISED by reviewer THIS wake={voice_revised}  "
              f"soft-opener clause present={clause_present}")
        print(f"  reviewer wrote this wake: {row['wrote']}")
        if voice_revised:
            print(f"  revision message: {row['revision_msg']}")

    # ---- trajectory structural read ----
    print(f"\n=== TRAJECTORY STRUCTURAL READ [{arm}] ===")
    closed_n = sum(1 for r in rows if r["closed"])
    failed_n = sum(1 for r in rows if r["status"] != "success")
    total_cost = sum(r["cost"] for r in rows if isinstance(r["cost"], (int, float)))

    revise_wakes = [r["wake"] for r in rows if r["voice_revised_this_wake"]]
    below_wakes = [r["wake"] for r in rows if r["below_threshold"]]
    at_wakes = [r["wake"] for r in rows if not r["below_threshold"]]
    # below-threshold wakes must NOT revise (correct defer = the internal control)
    thin_revisions = [r["wake"] for r in rows if r["below_threshold"] and r["voice_revised_this_wake"]]
    # at-or-above-threshold: at least one revise expected (seeded arm)
    threshold_revisions = [r["wake"] for r in rows if (not r["below_threshold"]) and r["voice_revised_this_wake"]]

    print(f"  [{'PASS' if closed_n == _N_WAKES else 'WATCH'}] cycle-closure (S9): {closed_n}/{_N_WAKES}")
    print(f"  [{'PASS' if failed_n == 0 else 'FAIL'}] no silent/failed wakes: {failed_n}")
    print(f"  [info] below-threshold wakes: {below_wakes}   at/above-threshold wakes: {at_wakes}")

    if control:
        any_rev = bool(revise_wakes)
        print(f"  [{'PASS' if not any_rev else 'FAIL'}] CONTROL: _voice.md NOT revised across the burst "
              f"(outcomes never arrived -> no correction -> confirms causation): revised_wakes={revise_wakes}")
    else:
        # The trajectory inflection:
        defer_ok = (len(thin_revisions) == 0)
        revise_ok = (len(threshold_revisions) >= 1)
        # hold: after the first revision, later wakes don't re-revise
        first_rev = revise_wakes[0] if revise_wakes else None
        post = [r for r in rows if first_rev and r["wake"] > first_rev]
        hold_ok = all(not r["voice_revised_this_wake"] for r in post)
        floor_ok = (not revise_wakes) or (not rows[-1]["clause_still_present"])
        print(f"  [{'PASS' if defer_ok else 'FAIL'}] DEFER-while-thin (internal control): "
              f"no revision on below-threshold wakes (revisions while thin: {thin_revisions or 'none'})")
        print(f"  [{'PASS' if revise_ok else 'WATCH'}] REVISE-at-threshold: _voice.md revised on a "
              f"threshold-met wake (revisions at/above threshold: {threshold_revisions or 'none'})")
        print(f"  [{'PASS' if hold_ok else 'WATCH'}] HOLD-after-revision (no thrash): "
              f"first revision wake={first_rev}; later wakes did not re-revise={hold_ok}")
        print(f"  [{'PASS' if floor_ok else 'FAIL'}] floor held (tightened, not loosened): "
              f"soft-opener clause gone after revision={not rows[-1]['clause_still_present']}")
        print(f"\n  THE INFLECTION (judgment improves over tenure): defer on {below_wakes} (thin), "
              f"revise on {revise_wakes} (threshold), hold after. "
              f"{'INFLECTION OBSERVED' if (defer_ok and revise_ok) else 'inflection NOT clean — read the trace'}")
    print(f"  [info] total cost ${total_cost:.2f}")
    print("\n  HUMAN READ (the judgment half): read the revising wake's transcript + the new _voice.md.")
    print("  Does the revision CITE the calibration-drift pattern + the evidence threshold? Did the")
    print("  agent EXPLICITLY defer earlier wakes for thin evidence (the standing_intent reasoning)?")
    print("  That explicit 'too thin yet' -> 'now established' shift across wakes is the tenure signal.")
    return 0


async def main() -> int:
    from services.supabase import get_service_client
    from services.platform_limits import get_effective_balance
    client = get_service_client()
    print(f"[trajectory] user={USER_ID} persona={PERSONA} effective_balance=${get_effective_balance(client, USER_ID):.2f}")

    if "--restore" in sys.argv:
        from services.operator_proxy.persona_snapshot import restore_persona
        from services.authored_substrate import write_revision
        if _SNAPSHOT_FILE.exists():
            blob = json.loads(_SNAPSHOT_FILE.read_text())
            res = await restore_persona(client, USER_ID, blob, persona=PERSONA)
            print(f"[trajectory] restored persona to baseline: {res}")
        if _CANON_SNAP.exists():
            snap = json.loads(_CANON_SNAP.read_text())
            for p, content in snap.items():
                if content is not None:
                    write_revision(client, user_id=USER_ID, path=p, content=content,
                                   authored_by="operator", message="probe-trajectory restore (canon baseline)")
            print(f"[trajectory] restored seeded canon files: {sorted(snap.keys())}")
        else:
            print("[trajectory] NOTE: no canon snapshot — _voice/_signal left in seeded state.")
        _clear_seeded_proposals(client)
        print("[trajectory] cleared seeded action_proposals rows")
        return 0

    # Snapshot the genuine pre-probe canon files so --restore works (before first seed).
    if not _CANON_SNAP.exists():
        snap = {p: _read(client, p)[0] for p in _SEEDED_FILES}
        _CANON_SNAP.parent.mkdir(parents=True, exist_ok=True)
        _CANON_SNAP.write_text(json.dumps(snap))
        print(f"[trajectory] saved pre-probe canon baseline -> {_CANON_SNAP.name}")

    if "--live" not in sys.argv:
        return await _structural_gate(client)

    control = "--control" in sys.argv
    return await soak(client, control=control)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
