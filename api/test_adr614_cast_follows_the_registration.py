"""ADR-614 — a sole stale cast agent answers as the lane's live resident.

Script-style (run: cd api && python3 test_adr614_cast_follows_the_registration.py).

THE DEFECT (measured in production 2026-08-27, 40 of 78 live conversations):
ADR-597 D1 derives a bound lane's resident at read time; ADR-602 re-registered
`slides`/`text` onto `editor`. Derivation followed; `conversation_members`
did not — ADR-602 reasoned about RESOLUTION ("designer is still a live being,
nothing orphans") and not about ROUTING. `select_responder`'s `sole_agent`
rung reads the CAST, so 39 authoring desks rendered "Editor" and were answered
by Designer. The single `keeper` row is worse: ADR-610 DELETED that being, so
`build_agent_posture` returns "" and the turn ran with NO character.

What this gate holds:
  1. The reconciliation EXECUTES (the function is driven, not grepped) and
     re-seats a sole stale agent onto the derived resident.
  2. Its three narrowing conditions hold: multi-agent casts untouched,
     unbound (chat) lanes untouched, already-correct casts untouched.
  3. It is READ-ONLY — no cast row is rewritten (no `add_participant` /
     `update` / `upsert` reachable from it).
  4. BOTH read points apply it (serve + turn), so the roster a member READS
     names the being that will ANSWER.
  5. The two real production shapes reconcile correctly, INCLUDING the
     context-dependence that forbids a slug→slug map: an IMAGES lane must
     stay Designer while a slides lane becomes Editor.
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


def _agent(slug):
    return {"member_kind": "agent", "agent_slug": slug}


HUMAN = {"member_kind": "human", "principal_id": "u-1"}

import services.apps  # noqa: F401,E402  (registration side-effect)
from routes.lanes import _lane_agent, _reconcile_cast_agent  # noqa: E402

print("1. the reconciliation EXECUTES and re-seats a sole stale agent")

# The 39-lane shape: a slides deck, cast frozen on `designer` by ADR-602.
SLIDES = {"artifact_path": "operation/deck.html"}
_assert(_lane_agent(SLIDES) == "editor",
        "a slides-shaped lane derives `editor` (ADR-602 D1)")
out = _reconcile_cast_agent([HUMAN, _agent("designer")], SLIDES)
_assert([p.get("agent_slug") for p in out if p.get("member_kind") == "agent"] == ["editor"],
        "a sole `designer` on a slides desk answers as Editor")
_assert(any(p.get("member_kind") == "human" for p in out),
        "the human participant survives reconciliation")

# The 1-lane shape: ADR-610 deleted `keeper`; its character VANISHED.
STRINGS = {"app": "strings", "artifact_path": "operation/notes.md"}
from services.agents_registry import build_agent_posture, resolve_agent  # noqa: E402
_assert(resolve_agent("keeper") is None, "`keeper` is a deleted being (ADR-610 D1)")
_assert(build_agent_posture("keeper") == "",
        "the deleted being composes NO character — the defect's real severity")
out = _reconcile_cast_agent([HUMAN, _agent("keeper")], STRINGS)
seated = [p.get("agent_slug") for p in out if p.get("member_kind") == "agent"]
_assert(seated == ["supervisor"], f"a sole `keeper` answers as Supervisor (got {seated})")
_assert(build_agent_posture(seated[0]) != "",
        "and that being composes a real character (the turn is no longer blank)")

print("2. the narrowing conditions hold")

multi = [HUMAN, _agent("designer"), _agent("supervisor")]
_assert([p.get("agent_slug") for p in _reconcile_cast_agent(multi, SLIDES)
         if p.get("member_kind") == "agent"] == ["designer", "supervisor"],
        "a MULTI-agent cast is untouched (@mention + continuity must not move)")

_assert(_lane_agent({}) is None, "an unbound chat lane derives no resident")
_assert(_reconcile_cast_agent([HUMAN, _agent("designer")], {}) ==
        [HUMAN, _agent("designer")],
        "an UNBOUND chat lane's cast is untouched (ADR-558 unchanged for chat)")

correct = [HUMAN, _agent("editor")]
_assert(_reconcile_cast_agent(correct, SLIDES) == correct,
        "an already-correct cast is returned unchanged")
_assert(_reconcile_cast_agent([HUMAN], SLIDES) == [HUMAN],
        "a cast with no agent at all is untouched")

print("3. the context-dependence a slug map would get WRONG")

IMAGES = {"app": "images", "artifact_path": "operation/art.html"}
_assert(_lane_agent(IMAGES) == "designer",
        "an IMAGES lane still derives `designer` (ADR-602 D2 carve-out)")
_assert([p.get("agent_slug") for p in _reconcile_cast_agent([HUMAN, _agent("designer")], IMAGES)
         if p.get("member_kind") == "agent"] == ["designer"],
        "an IMAGES lane KEEPS Designer — a blanket designer→editor map would break it")

print("4. it is READ-ONLY, and both read points apply it")

src = (API / "routes" / "lanes.py").read_text()
tree = ast.parse(src)
fn = next((n for n in ast.walk(tree)
           if isinstance(n, ast.FunctionDef) and n.name == "_reconcile_cast_agent"), None)
_assert(fn is not None, "`_reconcile_cast_agent` is defined in routes/lanes.py")
called = {n.func.attr if isinstance(n.func, ast.Attribute) else
          (n.func.id if isinstance(n.func, ast.Name) else "")
          for n in ast.walk(fn) if isinstance(n, ast.Call)}
for forbidden in ("add_participant", "remove_participant", "update", "upsert", "insert"):
    _assert(forbidden not in called,
            f"the reconciliation calls no `{forbidden}` — history is not rewritten")

# Driven, not grepped: both callers must reach it.
callers = [n.name for n in ast.walk(tree)
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
           and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                   and c.func.id == "_reconcile_cast_agent" for c in ast.walk(n))]
_assert("list_lanes" in callers,
        f"the SERVE path reconciles (callers: {callers})")
_assert(any("turn" in c or "message" in c or "_core" in c for c in callers),
        f"the TURN path reconciles (callers: {callers})")

print("5. the door SEEDS THE CAST — it does not write a birth-persona")

# THE LOAD-BEARING CLAIM of ADR-614 D1, driven rather than asserted in prose.
# If naming a colleague at the door wrote `lane_meta["agent"]`, ADR-558 D3's
# dual-authority bug would return: the cast would say one thing and the scalar
# another, which is exactly the CastBar defect D3 records.
import asyncio  # noqa: E402
import os  # noqa: E402

os.environ.setdefault("MODEL_ROUTER_ENABLED", "true")
os.environ.setdefault("LANES_ENABLED", "true")
import routes.lanes as L  # noqa: E402
import services.conversation_cast as CC  # noqa: E402
import services.lane_runner as LR  # noqa: E402

_WRITES: list[dict] = []
_ROW: dict = {}
CC.add_participant = lambda conv, **kw: _WRITES.append(kw)
LR.lane_model_availability = lambda m: (True, None)  # no provider key in CI


class _Auth:
    user_id = "u-1"
    workspace_id = "w-1"
    principal_id = "u-1"

    class client:  # noqa: N801
        @staticmethod
        def table(_n):
            class Q:
                def select(s, *a, **k): return s
                def eq(s, *a, **k): return s
                def like(s, *a, **k): return s
                def limit(s, *a, **k): return s
                def order(s, *a, **k): return s
                def insert(s, row, *a, **k): _ROW.update(row); return s

                def execute(s):
                    class R:
                        data = [{"id": "lane-1", "workspace_id": "w-1", **_ROW}]
                    return R()
            return Q()


try:
    asyncio.run(L.create_lane(L.CreateLaneRequest(agent="editor"), _Auth()))
except Exception:  # noqa: BLE001 — the fake DB ends the handler; the writes stand
    pass

_kinds = [(w.get("member_kind"), w.get("agent_slug")) for w in _WRITES]
_assert(("human", None) in _kinds, f"the creator is seeded into the cast ({_kinds})")
_assert(("agent", "editor") in _kinds,
        f"the NAMED COLLEAGUE is seeded as a cast row ({_kinds})")
_lm = (_ROW.get("context_metadata") or {}).get("lane") or {}
_assert("agent" not in _lm,
        f"NO birth-persona scalar is written to lane_meta (ADR-558 D3 intact): {_lm}")
_assert(_lm.get("model") == "anthropic/claude-sonnet-5",
        f"the being's own engine is persisted as the lane's fact ({_lm.get('model')})")

print()
if FAILURES:
    print(f"ADR-614 gate RED — {len(FAILURES)} failing:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print("ADR-614 gate GREEN")
