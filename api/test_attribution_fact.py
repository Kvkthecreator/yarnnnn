"""Unit gate for the attribution fact (ADR-387 follow-on, 2026-06-30).

The bare-Freddie steward eval (docs/evaluations/2026-06-29-freddie-bare-
workspace-steward-FINDING.md, Finding 1) found the steward placed a
mis-attributed file but ACCEPTED the authored_by lie because nothing in the
wake envelope surfaced attribution. This gate locks the fix: the envelope now
carries an `attribution_fact` — recent revisions + their authored_by, presented
raw (DP19-clean: the kernel presents, Freddie's attribution-integrity rule
judges) — and the user-message renderer emits it under a header that routes the
steward to verify voice-vs-attribution.

Pure offline: a minimal stub client over workspace_file_versions. No LLM, no DB.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

PASSED = 0
FAILED = 0


def check(cond: bool, label: str) -> None:
    global PASSED, FAILED
    if cond:
        print(f"  ✓ {label}")
        PASSED += 1
    else:
        print(f"  ✗ {label}")
        FAILED += 1


class _Result:
    def __init__(self, data):
        self.data = data


class _VersionsQuery:
    """Stub over workspace_file_versions supporting select/eq/gte/order/limit."""

    def __init__(self, rows):
        self._rows = rows
        self._eq = {}
        self._gte = None
        self._limit = None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._eq[col] = val
        return self

    def gte(self, col, val):
        self._gte = (col, val)
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def execute(self):
        rows = [r for r in self._rows if all(r.get(c) == v for c, v in self._eq.items())]
        if self._gte:
            col, val = self._gte
            rows = [r for r in rows if (r.get(col) or "") >= val]
        rows = sorted(rows, key=lambda r: r.get("created_at", ""), reverse=True)
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Result(rows)


class _Client:
    def __init__(self, versions):
        self._versions = versions

    def table(self, name):
        if name == "workspace_file_versions":
            return _VersionsQuery(self._versions)
        raise NotImplementedError(name)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# Recent revisions: an honest operator write, an honestly-attributed foreign-LLM
# dump, and the eval's mis-attribution (AI-voiced content stamped operator).
_RECENT = "2026-06-30T06:00:00+00:00"
_VERSIONS = [
    {"user_id": "u", "path": "/workspace/operation/memory/q3-pricing-note.md",
     "authored_by": "yarnnn:mcp:claude-desktop", "message": "intake: raw remember dump (unplaced)",
     "created_at": _RECENT},
    {"user_id": "u", "path": "/workspace/operation/memory/competitor-scan.md",
     "authored_by": "operator", "message": "competitor scan", "created_at": _RECENT},
    {"user_id": "u", "path": "/workspace/persona/standing_intent.md",
     "authored_by": "freddie:ai-sonnet-v8", "message": "sweep note", "created_at": _RECENT},
]


def test_presents_recent_attribution():
    print("\n[attribution] presents recent revisions + authored_by (the perception surface)")
    from services.freddie_envelope import _attribution_fact
    fact = _run(_attribution_fact(_Client(_VERSIONS), "u"))
    check(bool(fact.strip()), "fact is non-empty when there are recent revisions")
    check("competitor-scan.md" in fact, "names the (mis-attributed) path")
    check("authored_by: operator" in fact, "surfaces the authored_by stamp (the lie is now VISIBLE)")
    check("yarnnn:mcp:claude-desktop" in fact, "surfaces the foreign-LLM principal on the dump")
    check("/workspace/" not in fact, "paths are workspace-relative (tight scan lines)")


def test_empty_on_quiet_workspace():
    print("\n[attribution] empty on a quiet workspace (no noise on program wakes)")
    from services.freddie_envelope import _attribution_fact
    fact = _run(_attribution_fact(_Client([]), "u"))
    check(fact == "", "no recent revisions → empty string (silent)")


def test_dedupes_to_current_head_per_path():
    print("\n[attribution] presents the CURRENT head per path (not the raw stream)")
    from services.freddie_envelope import _attribution_fact
    # A churny path: 4 revisions (head = operator) + tombstone noise, like the
    # live re-run's seed/restore churn that buried the signal.
    churn = [
        {"user_id": "u", "path": "/workspace/operation/memory/competitor-scan.md",
         "authored_by": "operator", "message": "competitor scan", "created_at": "2026-06-30T06:05:00+00:00"},
        {"user_id": "u", "path": "/workspace/operation/memory/competitor-scan.md",
         "authored_by": "operator", "message": "restore: remove seed", "created_at": "2026-06-30T06:03:00+00:00"},
        {"user_id": "u", "path": "/workspace/operation/memory/competitor-scan.md",
         "authored_by": "operator", "message": "competitor scan", "created_at": "2026-06-30T06:01:00+00:00"},
        {"user_id": "u", "path": "/workspace/operation/memory/q3-pricing-note.md",
         "authored_by": "yarnnn:mcp:claude-desktop", "message": "dump", "created_at": "2026-06-30T06:04:00+00:00"},
    ]
    fact = _run(_attribution_fact(_Client(churn), "u"))
    lines = fact.splitlines()
    check(len(lines) == 2, f"4 revisions over 2 paths → 2 lines (one head each), got {len(lines)}")
    comp = [l for l in lines if "competitor-scan.md" in l]
    check(len(comp) == 1, "competitor-scan.md appears exactly once (its head)")
    check("authored_by: operator" in comp[0] and "competitor scan" in comp[0],
          "the head line carries the latest revision's author + message (the live mismatch)")


def test_bounded_by_limit():
    print("\n[attribution] bounded to the row cap (DP19 discovery surface, not a dump)")
    from services.freddie_envelope import _attribution_fact, _ATTRIBUTION_FACT_LIMIT
    many = [
        {"user_id": "u", "path": f"/workspace/operation/memory/f{i}.md",
         "authored_by": "operator", "message": f"m{i}", "created_at": _RECENT}
        for i in range(_ATTRIBUTION_FACT_LIMIT + 8)
    ]
    fact = _run(_attribution_fact(_Client(many), "u"))
    check(len(fact.splitlines()) == _ATTRIBUTION_FACT_LIMIT,
          f"capped at _ATTRIBUTION_FACT_LIMIT={_ATTRIBUTION_FACT_LIMIT} lines")


def test_wired_into_contract_and_envelope():
    print("\n[wiring] attribution_fact is a contract field + envelope key + rendered")
    from agents.occupant_contract import FreddieContext
    check("attribution_fact" in FreddieContext.__annotations__,
          "FreddieContext declares attribution_fact")
    env_src = (_API_ROOT / "services" / "freddie_envelope.py").read_text()
    check('envelope["attribution_fact"]' in env_src, "envelope sets attribution_fact")
    agent_src = (_API_ROOT / "agents" / "freddie_agent.py").read_text()
    check('ctx.get("attribution_fact")' in agent_src, "user message renders attribution_fact")
    check("Attribution fact —" in agent_src, "renders under the Attribution-fact header")
    # The header routes the steward to verify voice-vs-attribution (the eval
    # gap) and to apply the two rules by name. (The "verify voice / against
    # attribution" sentence spans a string-concat boundary in source, so assert
    # on the rule names + the stamp-honesty cue, which live in single literals.)
    check("attribution-integrity" in agent_src and "intake-placement" in agent_src,
          "header names both stewardship rules the fact serves")
    check("Don't assume the stamp is honest" in agent_src,
          "header cues the steward not to trust the stamp at face value (the eval gap)")


if __name__ == "__main__":
    test_presents_recent_attribution()
    test_empty_on_quiet_workspace()
    test_dedupes_to_current_head_per_path()
    test_bounded_by_limit()
    test_wired_into_contract_and_envelope()
    print(f"\n  {PASSED} passed, {FAILED} failed")
    sys.exit(1 if FAILED else 0)
