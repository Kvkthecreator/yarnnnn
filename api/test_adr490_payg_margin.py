"""ADR-490 gate — two free seats + the pay-as-you-go platform margin.

Behavioural where it matters (the lesson of the ADR-445 audit: a config-only
gate proves nothing — [[feedback_config_gate_is_not_evidence]]):

  1. CONFIG: multiplier 1.30; every tier grants $0 allowance; included_seats=2.
  2. WRITE SITE (behavioural): record_execution_event() against a fake client —
     the inserted row carries billed_usd == cost × 1.30 while cost_usd stays the
     UNMARKED provider cost (the 2026-07-06 ruling + ADR-408 D4 cost-mirror).
     Override rows (BYOK $0 / per-call image pricing) multiply uniformly.
  3. READERS (behavioural): get_daily_spend + budget.window_spend against a fake
     client — billed_usd preferred, cost_usd fallback on pre-migration rows
     (COALESCE semantics; an omission UNDER-charges, never $0s the pool).
  4. BOUNDARY: 2 humans free on every tier; the 3rd human is billable; the
     invite-gate copy names two people (old solo copy gone).
  5. MIGRATION: 224 exists and both RPCs coalesce billed over cost.

Usage:
    cd api
    python3 test_adr490_payg_margin.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PASSED = 0
FAILED = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        print(f"  ✓ {label}")
        PASSED += 1
    else:
        print(f"  ✗ {label}{(' — ' + detail) if detail else ''}")
        FAILED += 1


# ── Fake supabase client (captures inserts, serves canned selects) ───────────

class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, table, sink, rows):
        self._table = table
        self._sink = sink
        self._rows = rows

    def insert(self, row):
        self._sink.append((self._table, row))
        return self

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def gte(self, *_a, **_k):
        return self

    def gt(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def in_(self, *_a, **_k):
        return self

    def execute(self):
        if self._sink and self._sink[-1][0] == self._table and self._rows is None:
            # insert path: echo the inserted row with an id
            row = dict(self._sink[-1][1])
            row.setdefault("id", "fake-id")
            return _FakeResult([row])
        return _FakeResult(self._rows if self._rows is not None else [])


class _FakeClient:
    def __init__(self, rows=None):
        self.inserted = []
        self._rows = rows

    def table(self, name):
        return _FakeQuery(name, self.inserted, self._rows)


def main() -> int:
    sys.path.insert(0, str(Path(__file__).parent))

    # ── 1. Config ────────────────────────────────────────────────────────────
    print("\n[config] the ADR-490 numbers (single source: billing_tiers.py)")
    from services.billing_tiers import (
        TIER_CONFIG,
        USAGE_BILLING_MULTIPLIER,
        billed_usd_for_cost,
        billable_seats,
        tier_included_seats,
    )

    check("USAGE_BILLING_MULTIPLIER == 1.30", USAGE_BILLING_MULTIPLIER == 1.30)
    check("billed_usd_for_cost(0.10) == 0.13", billed_usd_for_cost(0.10) == 0.13)
    check("billed_usd_for_cost(0) == 0 (BYOK/free bills zero)", billed_usd_for_cost(0.0) == 0.0)
    for tier, spec in TIER_CONFIG.items():
        check(f"{tier}: monthly_allowance_usd == 0 (allowance retired, §1③)",
              spec["monthly_allowance_usd"] == 0.0,
              f"got {spec['monthly_allowance_usd']}")
        check(f"{tier}: included_seats == 2 (two free humans, §1①)",
              spec["included_seats"] == 2,
              f"got {spec['included_seats']}")

    # ── 2. The write site stamps billed_usd (behavioural) ────────────────────
    print("\n[write] record_execution_event stamps billed = cost × 1.30; cost stays provider-true")
    from services.telemetry import record_execution_event, compute_cost_usd_inclusive

    fake = _FakeClient()
    record_execution_event(
        fake,
        user_id="00000000-0000-0000-0000-000000000000",
        slug="gate-test",
        mode="judgment",
        trigger_type="manual",
        status="success",
        input_tokens=1_000_000,
        output_tokens=0,
        model="claude-sonnet-4-6",
    )
    rows = [r for (t, r) in fake.inserted if t == "execution_events"]
    check("one execution_events row inserted", len(rows) == 1)
    if rows:
        row = rows[0]
        expected_cost = compute_cost_usd_inclusive(
            model="claude-sonnet-4-6", input_tokens=1_000_000, output_tokens=0
        )
        check("cost_usd == provider list cost (UNMARKED — $3.00/mtok sonnet input)",
              row.get("cost_usd") == expected_cost == 3.00,
              f"cost_usd={row.get('cost_usd')} expected={expected_cost}")
        check("billed_usd == cost × 1.30",
              row.get("billed_usd") == round(expected_cost * 1.30, 6),
              f"billed_usd={row.get('billed_usd')}")

    # Override path (BYOK $0 and real per-call figures) multiplies uniformly.
    fake2 = _FakeClient()
    record_execution_event(
        fake2,
        user_id="00000000-0000-0000-0000-000000000000",
        slug="gate-test-override",
        mode="judgment",
        trigger_type="manual",
        status="success",
        cost_override_usd=0.0,
    )
    row2 = [r for (t, r) in fake2.inserted if t == "execution_events"][0]
    check("BYOK override 0.0 → billed_usd == 0 (no margin on the customer's key)",
          row2.get("billed_usd") == 0.0 and row2.get("cost_usd") == 0.0)

    fake3 = _FakeClient()
    record_execution_event(
        fake3,
        user_id="00000000-0000-0000-0000-000000000000",
        slug="gate-test-image",
        mode="judgment",
        trigger_type="manual",
        status="success",
        cost_override_usd=0.04,
    )
    row3 = [r for (t, r) in fake3.inserted if t == "execution_events"][0]
    check("per-call override 0.04 → billed_usd == 0.052 (margin applies to rented calls)",
          row3.get("billed_usd") == round(0.04 * 1.30, 6),
          f"billed_usd={row3.get('billed_usd')}")

    # ── 3. Readers coalesce billed over cost (behavioural) ───────────────────
    print("\n[readers] pool reads prefer billed_usd, fall back to cost_usd")
    ledger_rows = [
        {"cost_usd": 1.00, "billed_usd": 1.30},   # post-490 row
        {"cost_usd": 2.00, "billed_usd": None},    # pre-migration row → at cost
        {"cost_usd": None, "billed_usd": None},    # cost-less row → 0
    ]
    from services.telemetry import get_daily_spend
    spent = get_daily_spend(_FakeClient(rows=ledger_rows), "00000000-0000-0000-0000-000000000000")
    check("get_daily_spend sums 1.30 + 2.00 = 3.30", spent == 3.30, f"got {spent}")

    from services.budget import window_spend
    ws_spent = window_spend(_FakeClient(rows=ledger_rows), "00000000-0000-0000-0000-000000000000", "monthly")
    check("budget.window_spend sums 1.30 + 2.00 = 3.30", ws_spent == 3.30, f"got {ws_spent}")

    # ── 4. The seat boundary + the invite copy ───────────────────────────────
    print("\n[boundary] two humans free; the 3rd is the free→paid boundary")
    check("free: 2 humans → 0 billable", billable_seats("free", 2) == 0)
    check("starter: 3 humans → 1 billable", billable_seats("starter", 3) == 1)
    check("included seats uniform at 2 across tiers",
          all(tier_included_seats(t) == 2 for t in TIER_CONFIG))

    invites_src = (Path(__file__).parent / "services" / "workspace_invites.py").read_text()
    check("invite gate copy names two people",
          "The free plan covers two people" in invites_src)
    check("old solo invite copy removed",
          "The free plan is for one person" not in invites_src)

    # The boundary is stated on FOUR surfaces, and this gate only ever checked
    # ONE (workspace_invites.py). So the FE warning at the invite affordance kept
    # saying "The free plan is for one person" for a full day after ADR-490 moved
    # the boundary — the operator hit it live: a 1-human free workspace told to
    # upgrade with the pre-490 reason. A boundary stated in N places needs a gate
    # that sweeps N places (cf. [[feedback_gates_grep_text_not_execution]]).
    print("\n[boundary-copy] every surface that STATES the boundary says two")
    web = Path(__file__).parent.parent / "web"
    docs = Path(__file__).parent.parent / "docs"
    stale = []
    for root, pats in ((web, ("*.ts", "*.tsx")), (docs / "gitbook", ("*.md",))):
        for pat in pats:
            for p in root.rglob(pat):
                if ".next" in p.parts or "node_modules" in p.parts:
                    continue
                txt = p.read_text(errors="ignore")
                # Strip code comments before scanning: a comment DOCUMENTING the
                # retired boundary is the opposite of the defect, and grepping
                # prose punishes the fix's own explanation (the same trap this
                # session hit twice — scan RENDERED copy, not commentary).
                scan = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
                scan = re.sub(r"^\s*//.*$", "", scan, flags=re.M)
                for line in scan.splitlines():
                    low = line.lower()
                    if "free plan is for one person" in low or (
                        "free for one person" in low and "Jul 12–22" not in line
                    ):
                        # The dated changelog entry is a HISTORICAL record of what
                        # shipped that week — correcting it would falsify history.
                        if "changelog" in str(p) and "Jul 12" in txt[:txt.find(line)][-400:]:
                            continue
                        stale.append(f"{p.relative_to(root.parent)}: {line.strip()[:60]}")
    check("no surface still states the one-person boundary", not stale,
          "; ".join(stale[:3]))

    members_card = web / "components" / "workspace-concepts" / "WorkspaceMembersCard.tsx"
    if members_card.exists():
        src_mc = members_card.read_text()
        check("the invite warning DERIVES the count (cannot go stale again)",
              "seatInfo.included === 1 ? 'one person'" in src_mc
              and "${seatInfo.included} people" in src_mc)

    # ── 5. Migration 224 shape ───────────────────────────────────────────────
    print("\n[migration] 224 — billed_usd + both RPCs coalesce")
    mig = Path(__file__).parent.parent / "supabase" / "migrations" / "224_adr490_billed_usd_payg_margin.sql"
    check("migration 224 exists", mig.exists())
    if mig.exists():
        sql = mig.read_text()
        check("adds billed_usd column", "ADD COLUMN IF NOT EXISTS billed_usd" in sql)
        check("backfills history at cost", "SET billed_usd = cost_usd" in sql)
        check("get_effective_balance coalesces billed",
              sql.count("COALESCE(ee.billed_usd, ee.cost_usd)") >= 2)

    print(f"\n{'='*60}\nADR-490 gate: {PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
