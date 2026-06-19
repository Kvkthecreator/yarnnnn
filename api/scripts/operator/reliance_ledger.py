"""RELIANCE-LEDGER — the §12 test #1 mechanized (the desire axis, not capability).

Hat-B developer-surface tooling (NOT system canon). Closes the measurement gap
named in `docs/analysis/os-as-product-vs-capability-and-the-validatable-
autonomy-spectrum-2026-06-19.md` §§11–12: *every eval to date validates that
the seat CAN judge (capability); none validates that a principal LETS its
consequential calls stand (reliance/desire).*

WHAT THIS IS
------------
§12 test #1 (the founder-reliance test) asks, verbatim:

    "Name one consequential thing in the next 30 days where you'd let the
     Reviewer's call stand without checking it."

That question is empirically answerable from substrate, not opinion. Under
ADR-345's autonomy-as-witness model, an autonomously-executed consequential
proposal IS "the Reviewer's call stood without the operator checking it" — the
witness dial routed it to act, the operator did not separately approve. So the
reliance count is:

    consequential (`family in CONSEQUENTIAL_FAMILIES`) proposals that
    REACHED an acted state (`status='executed'`) WITHOUT an operator witness
    (`approved_by` is null / not an operator), EXCLUDING fixtures.

The fixture-discriminator is load-bearing: kvk's only-ever executed capital
proposal (id 0e4ed324, 2026-06-05) is an explicit `[FIXTURE] off-hours
execution-link validation` — a test artifact, not an acted-on judgment. A
reliance ledger that counts it reports a false "1"; the honest count is 0.
Fixtures are detected by `[FIXTURE]` in reviewer_reasoning or the
decision_context rationale (the convention the trader harness already uses).

WHAT THIS IS NOT
----------------
It RENDERS the reliance ledger fact; it does NOT judge whether reliance=0 is a
problem. Whether nobody-relies-yet means "the bet is under-desired" (§12 lean)
or "desire is latent, built by the demo" (§12 adversarial read) is the
operator's read, written into a finding — NOT something this script decides.
The only verdict it emits is the mechanical ledger state:

    RELIANCE-ZERO   — no real unwitnessed consequential call has ever stood.
    RELIANCE-N      — N real unwitnessed consequential calls have stood.

That is a substrate fact (a count over action_proposals), not a judgment about
the product. The capability suite (alpha-trader-autonomous-loop.yaml) reads the
ORTHOGONAL axis — "did the seat judge well." Both are needed; neither is the
other.

WHY A SEPARATE INSTRUMENT (not an eval)
---------------------------------------
The eval suites are EPISODIC (fire one situation, read the trace) and read the
CAPABILITY axis (calibration + cycle-closure; "no trade today is success").
They structurally cannot surface reliance — they measure whether the judgment
was sound, never whether a call was acted-on-and-left-alone. Reliance is a
LONGITUDINAL substrate fact across the whole proposal history, like TENURE-READ
Read 1 — so it is a substrate read (mirror `tenure_curve.py`), not a scenario.

USAGE
-----
    # by persona slug (resolves user_id from docs/alpha/personas.yaml):
    python api/scripts/operator/reliance_ledger.py --persona kvk

    # by explicit workspace + a custom window (default: all history):
    python api/scripts/operator/reliance_ledger.py \
        --user-id 2abf3f96-118b-4987-9d95-40f2d9be9a18 --days 30
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_API_ROOT = _THIS_DIR.parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

REPO_ROOT = _THIS_DIR.parents[2]

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_API_ROOT / ".env.alpha-ops")
load_dotenv(REPO_ROOT / ".env")


# Consequential = irreversible-or-capital families (DP23 consequential-gate
# class). A reversible substrate write (family='substrate') is NOT a reliance
# act — it is auditable + revertible (ADR-209). The reliance question is about
# the rung-4 act the operator would most want to check: capital / external send.
CONSEQUENTIAL_FAMILIES = ("capital", "trade", "send", "external")

# An acted state — the proposal reached real-world effect. A pending/rejected/
# expired proposal never acted, so it never "stood."
ACTED_STATUS = "executed"

# Fixture marker convention (trader harness): a test artifact, not an acted-on
# judgment. Excluded from the real reliance count.
FIXTURE_MARKER = "[FIXTURE]"


def _resolve_user_id(persona: str | None, user_id: str | None) -> tuple[str, str]:
    """Return (user_id, label). Persona slug resolves via personas.yaml."""
    if user_id:
        return user_id, user_id[:8]
    if not persona:
        raise SystemExit("provide --persona <slug> or --user-id <uuid>")
    import yaml
    reg = yaml.safe_load((REPO_ROOT / "docs" / "alpha" / "personas.yaml").read_text())
    for row in reg.get("personas", []):
        if row.get("slug") == persona:
            return row["user_id"], f"{persona} ({row['user_id'][:8]})"
    raise SystemExit(f"persona {persona!r} not found in personas.yaml")


def _is_fixture(row: dict) -> bool:
    reasoning = (row.get("reviewer_reasoning") or "")
    dc = row.get("decision_context") or {}
    rationale = (dc.get("rationale") or "") if isinstance(dc, dict) else ""
    return FIXTURE_MARKER in reasoning or FIXTURE_MARKER in rationale


def _is_operator_witnessed(row: dict) -> bool:
    """True if a human operator separately approved before the act.

    Under autonomous auto-execute, approved_by is null OR carries the
    reviewer/system identity (the seat acted, not the operator). An
    operator-witnessed proposal carries an operator approver — its call did
    NOT 'stand without checking'; the operator checked it.
    """
    approver = (row.get("approved_by") or "").strip().lower()
    if not approver:
        return False
    # The seat / system acting on its own is NOT an operator witness.
    if approver.startswith(("reviewer", "system", "operator-proxy")):
        return False
    return True  # a real operator identity approved it


def run(user_id: str, label: str, *, days: int | None) -> int:
    from services.supabase import get_service_client

    client = get_service_client()
    q = (
        client.table("action_proposals")
        .select(
            "id, primitive, family, status, source, approved_by, "
            "reviewer_identity, reviewer_reasoning, decision_context, "
            "created_at, executed_at"
        )
        .eq("user_id", user_id)
        .in_("family", list(CONSEQUENTIAL_FAMILIES))
    )
    if days:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        q = q.gte("created_at", since)
    rows = (q.order("created_at", desc=True).execute().data) or []

    acted = [r for r in rows if r.get("status") == ACTED_STATUS]
    fixtures = [r for r in acted if _is_fixture(r)]
    real_acted = [r for r in acted if not _is_fixture(r)]
    unwitnessed = [r for r in real_acted if not _is_operator_witnessed(r)]
    witnessed = [r for r in real_acted if _is_operator_witnessed(r)]

    window = f"last {days}d" if days else "all history"
    reliance = len(unwitnessed)
    verdict = "RELIANCE-ZERO" if reliance == 0 else f"RELIANCE-{reliance}"

    print(f"\n=== RELIANCE LEDGER — {label} ({window}) ===\n")
    print(f"Consequential proposals (family∈{CONSEQUENTIAL_FAMILIES}): {len(rows)}")
    print(f"  ├─ reached '{ACTED_STATUS}' (acted):            {len(acted)}")
    print(f"  │    ├─ fixtures (excluded):                  {len(fixtures)}")
    print(f"  │    └─ real acted-on calls:                  {len(real_acted)}")
    print(f"  │         ├─ operator-witnessed (checked):    {len(witnessed)}")
    print(f"  │         └─ UNWITNESSED (call stood alone):  {len(unwitnessed)}  ← the reliance count")
    print(f"  └─ never acted (pending/rejected/expired):   {len(rows) - len(acted)}\n")
    print(f"LEDGER STATE: {verdict}")
    print(
        "  (mechanical substrate fact — NOT a judgment. Whether reliance=0 means\n"
        "   'under-desired' or 'latent-desire-built-by-the-demo' is the operator's\n"
        "   read, per the §12 lean vs its adversarial counter. This instrument\n"
        "   only counts; it does not decide.)\n"
    )

    if unwitnessed:
        print("Unwitnessed real consequential calls that STOOD (the §12 answer):")
        for r in unwitnessed:
            print(
                f"  • {r['id'][:8]} {r.get('primitive')} [{r.get('family')}] "
                f"executed {r.get('executed_at') or '?'} "
                f"seat={r.get('reviewer_identity') or '?'}"
            )
        print()
    elif fixtures:
        print("The ONLY acted-on consequential proposal(s) are FIXTURES:")
        for r in fixtures:
            print(f"  • {r['id'][:8]} {r.get('primitive')} — {(r.get('reviewer_reasoning') or '')[:70]}")
        print(
            "\n→ The §12 test #1 answer for this workspace is currently: NONE.\n"
            "  No real consequential call has stood without the operator checking it.\n"
        )
    else:
        print(
            "→ The §12 test #1 answer for this workspace is currently: NONE.\n"
            "  No consequential call has ever reached an acted state.\n"
        )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Reliance ledger — §12 test #1 mechanized")
    ap.add_argument("--persona", help="persona slug from docs/alpha/personas.yaml")
    ap.add_argument("--user-id", help="explicit workspace user_id (overrides --persona)")
    ap.add_argument("--days", type=int, default=None, help="window in days (default: all history)")
    args = ap.parse_args()
    uid, label = _resolve_user_id(args.persona, args.user_id)
    return run(uid, label, days=args.days)


if __name__ == "__main__":
    raise SystemExit(main())
