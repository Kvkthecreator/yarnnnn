"""Every producer of a lane payload returns the SAME KEYS.

Script-style (run: cd api && python3 test_lane_payload_shape_is_one_shape.py).

THE DEFECT (operator-observed in production 2026-08-27): a chat started with
Supervisor rendered "Claude Sonnet 5" in its header while the reply bubble
correctly said "Supervisor". Everything upstream was right — the cast row was
seeded (`member_kind='agent'`, `agent_slug='supervisor'`), `_beings_payload`
served the being (`is_promoted('supervisor')` is True), and `beingBySlug`
resolved it. Only `create_lane`'s RESPONSE omitted the `participants` key.

Why an omitted key is worse than a missing value: the FE renderers read the
cast to name a conversation and fall back to the ENGINE label when it is
empty (`laneOthers` → `modelLabel(lane.model)`). So the omission does not
render "unknown" — it renders a confident wrong answer in the place a
colleague's name belongs. That is the ADR-373 D6 incorrect-success shape, and
it healed itself on the next list refetch, which is exactly what made it look
like a stale cache rather than a payload bug.

⭐ THIS IS NOT THE ADR-614 NAMING DEFECT (`a732ccf`). That one was fixed by
routing ten roster lookups through one resolver, and the naming was already
correct here. This is PAYLOAD-SHAPE divergence: two endpoints handing the FE
lane dicts that the same renderers read differently. A naming gate cannot
catch it, which is why this one exists separately.

⭐ WHY A SHAPE GATE AND NOT A SUPERVISOR GATE. The defect is not per-being and
not per-app: any producer that builds a lane dict inherits it, so a being
added tomorrow would arrive broken through no fault of its own. The invariant
that survives future scaffolds is about the SHAPE, so that is what is pinned.

What this gate holds:
  1. `_lane_row_to_dict` ALWAYS emits `participants` — a list, never absent,
     with no cast passed (the create-path condition that shipped the bug).
  2. It carries a cast THROUGH when given one (the parameter is real, not
     decorative).
  3. EVERY call site passes a cast or is the list path that assigns one, so a
     new producer cannot quietly re-open the gap.
  4. Falsification: the pre-fix shape (no `participants` key) FAILS assertion
     1 — the gate is made to fail against the real defect, not merely to pass
     against the fix.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
sys.path.insert(0, str(API))

FAILURES: list[str] = []


def _assert(cond: bool, msg: str) -> None:
    print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
    if not cond:
        FAILURES.append(msg)


LANES = API / "routes" / "lanes.py"
SRC = LANES.read_text()

# ---------------------------------------------------------------------------
# 1 + 2 — the function itself, DRIVEN (not grepped: a grep for the key name
# passes on a comment mentioning it, and this file is full of such comments).
# ---------------------------------------------------------------------------
print("\n1. `_lane_row_to_dict` emits `participants` from every call shape")

# Exec'd in isolation rather than imported: `routes.lanes` pulls the FastAPI
# app, Supabase clients and the whole service tree at import time, none of
# which this pure row->dict mapping needs. The function's own dependencies are
# supplied below — and ONLY those, so a future dependency this stub silently
# satisfies (the `re`-shaped trap from ADR-609's gate) surfaces as a NameError
# here instead of passing on a convenience prod does not have.
_mod = ast.parse(SRC)
_fn = next(
    (n for n in _mod.body
     if isinstance(n, ast.FunctionDef) and n.name == "_lane_row_to_dict"),
    None,
)
_assert(_fn is not None, "_lane_row_to_dict is defined in routes/lanes.py")

if _fn is not None:
    ns: dict = {"Optional": __import__("typing").Optional}

    # `_lane_agent` is the one helper the body calls. Stubbed to the identity
    # of the stored slug: this gate is about the SHAPE of the payload, and the
    # resident-derivation it performs is ADR-597's own gate to hold.
    ns["_lane_agent"] = lambda meta: meta.get("agent") or None

    exec(compile(ast.Module(body=[_fn], type_ignores=[]), "<gate>", "exec"), ns)
    lane_row_to_dict = ns["_lane_row_to_dict"]

    row = {
        "id": "637408a6-f52b-4787-af50-e38bb0a8057d",
        "context_metadata": {"lane": {"name": "can you access github",
                                      "model": "anthropic/claude-sonnet-5"}},
        "status": "active",
    }

    # THE CREATE-PATH CONDITION — the exact call that shipped the defect.
    bare = lane_row_to_dict(row)
    _assert("participants" in bare,
            "with NO cast passed, the key is PRESENT (the create-path shape)")
    _assert(bare.get("participants") == [],
            "...and it is an empty LIST, not None (a real state, not a gap)")

    print("\n2. a cast passed in is carried through")
    cast = [
        {"member_kind": "human", "agent_slug": None},
        {"member_kind": "agent", "agent_slug": "supervisor"},
    ]
    # Guarded, NOT called bare: against the pre-fix signature this raises
    # TypeError, and an unhandled raise here would abort the run and hide
    # every assertion below — including section 4, the one that stops a NEW
    # producer re-opening the gap. A gate that crashes on the defect it guards
    # reports less than a gate that fails on it.
    try:
        withcast = lane_row_to_dict(row, cast)
    except TypeError as exc:
        withcast = None
        _assert(False, f"the cast parameter exists and accepts a cast ({exc})")

    _assert(withcast is not None and withcast.get("participants") == cast,
            "the cast reaches the payload verbatim (the parameter is real)")
    _assert(
        withcast is not None and any(
            p.get("agent_slug") == "supervisor"
            for p in withcast.get("participants") or []
        ),
        "the production shape that rendered wrong now carries `supervisor`",
    )

    # The two shapes must differ ONLY in the cast — a producer that also drops
    # `agent` or `model` would render wrong for a different reason.
    _assert(
        withcast is not None and set(bare) == set(withcast),
        "both call shapes emit the IDENTICAL key set (one shape, two callers)",
    )

    print("\n3. falsification — the PRE-FIX shape fails assertion 1")
    # The defect verbatim: the same mapping with the key omitted. If this
    # "passes", the gate is not testing what it claims and every result above
    # is decorative.
    pre_fix = {k: v for k, v in bare.items() if k != "participants"}
    _assert("participants" not in pre_fix,
            "the pre-fix payload genuinely lacks the key (falsifier is real)")
    _assert(
        not ("participants" in pre_fix and pre_fix.get("participants") == []),
        "...so assertion 1 would have FAILED against the shipped defect",
    )

# ---------------------------------------------------------------------------
# 4 — every call site, so a NEW producer cannot re-open the gap
# ---------------------------------------------------------------------------
print("\n4. every `_lane_row_to_dict` call site supplies a cast")

calls = [
    n for n in ast.walk(_mod)
    if isinstance(n, ast.Call)
    and isinstance(n.func, ast.Name)
    and n.func.id == "_lane_row_to_dict"
]
_assert(len(calls) >= 3,
        f"found {len(calls)} call sites (list · create · rename)")

# A call with one arg is only acceptable when the caller assigns the cast
# itself immediately after — the list path does this from ONE batched read
# rather than N per-row reads, which is a deliberate performance shape, not
# an omission. Anything else is the create-path bug returning.
one_arg = [c for c in calls if len(c.args) == 1]
assigns_after = "ln[\"participants\"] = _reconcile_cast_agent(" in SRC
_assert(
    len(one_arg) <= 1,
    f"at most ONE single-arg call (the batched list path); found {len(one_arg)}",
)
_assert(
    assigns_after,
    "the list path assigns `participants` from its batched cast read",
)

two_arg = [c for c in calls if len(c.args) == 2]
_assert(
    len(two_arg) >= 2,
    f"create + rename BOTH pass a cast explicitly; found {len(two_arg)}",
)

# The cast a producer passes must come from the SAME source the list reads,
# or the lane a member receives can disagree with the one they refetch.
# Read off the CALL NODES, not the file text: `"list_participants(lane_id)" in
# SRC` passed against the reverted code because the phrase also occurs in a
# prose comment. A grep-shaped assertion that a comment can satisfy is the
# vacuous-pass shape — assert the argument the parser actually saw.
def _cast_arg_srcs() -> list[str]:
    out = []
    for c in two_arg:
        try:
            out.append(ast.unparse(c.args[1]))
        except Exception:  # noqa: BLE001 — py<3.9 has no unparse; treated as unknown
            out.append("")
    return out


_cast_args = _cast_arg_srcs()
_assert(
    any("list_participants" in a for a in _cast_args),
    f"a producer passes the cast READ BACK via list_participants; saw {_cast_args}",
)
_assert(
    sum("list_participants" in a for a in _cast_args) >= 2,
    "BOTH explicit producers read the cast from that one source, not two",
)

# ---------------------------------------------------------------------------
print()
if FAILURES:
    print(f"FAILED ({len(FAILURES)}):")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print("All lane-payload-shape assertions passed.")
