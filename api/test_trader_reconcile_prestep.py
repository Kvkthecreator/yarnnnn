"""Regression gate — the mechanical pre-fold for platform-attested outcome loops.

Locks the invariants that make the orphaned-reconciler repair (2026-06-26)
canon-coherent. The `outcome-reconciliation` judgment wake has TWO shapes,
split by attestation source (ADR-330):
  - platform-attested (trader/commerce): an external oracle must be POLLED and
    matched mechanically BEFORE the agent reads it → a zero-LLM `reconcile_user`
    pre-step runs ahead of envelope assembly. (The prompt reads, doesn't fold.)
  - operator/agent-attested (alpha-author): the ground truth is already
    LLM-readable substrate → the JUDGMENT wake folds it itself, NO pre-step.

The repair restores the platform pre-step's scheduler caller (dissolved when
ADR-260/261 collapsed back-office tasks). The gate
`has_platform_attested_provider` keeps it TIGHT — a true no-op for
operator/agent-attested programs, so the pre-step never writes a spurious empty
`trading` _money_truth.md into an author workspace.

  Audit:  docs/evaluations/2026-06-25-trader-money-truth-orphaned-reconciler-AUDIT.md

Pure-offline assertions (a fake client; no DB, no network). Run:
    .venv/bin/python -m pytest api/test_trader_reconcile_prestep.py -q
or directly:
    .venv/bin/python api/test_trader_reconcile_prestep.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from services.outcomes.reconciler import (  # noqa: E402
    DEFAULT_PROVIDERS,
    PLATFORM_ATTESTED_PLATFORMS,
    has_platform_attested_provider,
)

PASS = 0
FAIL = 0


def check(name: str, cond: bool) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}")


# ── A fake supabase client that records the platform-connections query ──────
class _FakeTable:
    def __init__(self, rows, raise_on_execute=False):
        self._rows = rows
        self._raise = raise_on_execute
        self._platform_filter = None
        self._in_filter = None

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        if col == "platform":
            self._platform_filter = val
        return self

    def in_(self, col, vals):
        if col == "platform":
            self._in_filter = list(vals)
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        if self._raise:
            raise RuntimeError("simulated postgrest outage")

        class _R:
            pass

        r = _R()
        # Honor the in_(platform) filter the gate uses.
        rows = self._rows
        if self._in_filter is not None:
            rows = [row for row in rows if row.get("platform") in self._in_filter]
        r.data = rows
        return r


class _FakeClient:
    def __init__(self, conn_rows, raise_on_execute=False):
        # conn_rows: the active platform_connections rows for the user.
        self._rows = conn_rows
        self._raise = raise_on_execute

    def table(self, name):
        assert name == "platform_connections", name
        return _FakeTable(self._rows, self._raise)


# ── 1. the platform set stays in lockstep with the providers ────────────────
_provider_domains = {p.context_domain for p in DEFAULT_PROVIDERS}
check(
    "DEFAULT_PROVIDERS is exactly trading + commerce (revenue)",
    _provider_domains == {"trading", "revenue"},
)
check(
    "PLATFORM_ATTESTED_PLATFORMS == ('trading', 'commerce')",
    PLATFORM_ATTESTED_PLATFORMS == ("trading", "commerce"),
)
check(
    "every platform-attested platform has a provider behind it (len match)",
    len(PLATFORM_ATTESTED_PLATFORMS) == len(DEFAULT_PROVIDERS),
)

# ── 2. trader workspace (active trading connection) → gate True ─────────────
trader = _FakeClient([{"platform": "trading"}])
check(
    "active trading connection → has_platform_attested_provider True",
    has_platform_attested_provider(trader, "trader-user") is True,
)

commerce = _FakeClient([{"platform": "commerce"}])
check(
    "active commerce connection → has_platform_attested_provider True",
    has_platform_attested_provider(commerce, "commerce-user") is True,
)

# ── 3. author workspace (slack/notion/github, no trading/commerce) → False ──
# This is the no-pollution invariant: the pre-step never runs for the author,
# so it cannot write a spurious empty `trading` _money_truth.md stub.
author = _FakeClient([
    {"platform": "slack"},
    {"platform": "notion"},
    {"platform": "github"},
])
check(
    "author connections (no trading/commerce) → gate False (no pollution)",
    has_platform_attested_provider(author, "author-user") is False,
)

# ── 4. no active connections at all → False ─────────────────────────────────
bare = _FakeClient([])
check(
    "no active platform connections → gate False",
    has_platform_attested_provider(bare, "bare-user") is False,
)

# ── 5. lookup failure is fail-safe (returns False, never raises) ────────────
broken = _FakeClient([{"platform": "trading"}], raise_on_execute=True)
try:
    res = has_platform_attested_provider(broken, "broken-user")
    check("lookup failure → gate False (fail-safe, never raises)", res is False)
except Exception:  # noqa: BLE001
    check("lookup failure → gate False (fail-safe, never raises)", False)

# ── 6. the wake pre-step is gated on the outcome-reconciliation slug ────────
# Source-level invariant: the pre-step only fires for the reconciliation slug
# (costs nothing for any other recurrence), mirroring the daily-pnl post-step.
_wake_src = (Path(__file__).resolve().parent / "services" / "wake.py").read_text()
check(
    "wake pre-step gated on slug == 'outcome-reconciliation'",
    'if recurrence.slug == "outcome-reconciliation":' in _wake_src,
)
check(
    "wake pre-step calls has_platform_attested_provider before reconcile_user",
    "has_platform_attested_provider(client, user_id)" in _wake_src
    and "reconcile_user" in _wake_src,
)
# The pre-step must precede envelope assembly so the freshly-folded organ is in
# the substrate the envelope reads.
_pre = _wake_src.find("Mechanical pre-fold for platform-attested")
_env = _wake_src.find("Build the Reviewer prompt envelope")
check(
    "pre-step is placed BEFORE envelope assembly",
    _pre != -1 and _env != -1 and _pre < _env,
)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
