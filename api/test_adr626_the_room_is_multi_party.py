"""ADR-626 — the room is multi-party, and the agent can see who is in it.

Script-style (py3.9-safe): `python3 test_adr626_the_room_is_multi_party.py`.

WHAT THIS GATE HOLDS
  1. The tag appears ONLY when it disambiguates — on BOTH axes, independently.
  2. `_fetch_history` is DRIVEN over a fake transcript, not grepped: the whole
     defect was a function that selected authorship and dropped it, so a grep
     for the field name would have passed over the broken code.
  3. `role` is never rewritten — tagging is additive.
  4. The responder tags ITSELF when tagging is on.
  5. `visibility_floor` answers for an agent slug (the species-blindness its
     docstring claimed but never had).
  6. The cast-label enricher is reached on the TURN path.

FALSIFICATION: every ADR-626 check was run against the pre-change tree and
went red for the stated reason.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

failures = []


def check(label, cond, detail=""):
    if cond:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}" + (f" — {detail}" if detail else ""))
        failures.append(label)


# ---------------------------------------------------------------------------
print("\n§1 — the tag is a function of the ROOM, on two independent axes")
# ---------------------------------------------------------------------------
from routes.lanes import _speaker_tags, _speaker_label  # noqa: E402

H = {"member_kind": "human", "principal_id": "u1"}
H2 = {"member_kind": "human", "principal_id": "u2"}
A = {"member_kind": "agent", "agent_slug": "editor"}
A2 = {"member_kind": "agent", "agent_slug": "supervisor"}

check("solo room (1 human, 1 agent) tags NOTHING", _speaker_tags([H, A]) == (False, False),
      "the common case must stay byte-identical")
check("2 humans tags HUMANS only", _speaker_tags([H, H2, A]) == (True, False))
check("2 agents tags AGENTS only", _speaker_tags([H, A, A2]) == (False, True))
check("2 of each tags BOTH", _speaker_tags([H, H2, A, A2]) == (True, True))
check("an empty cast tags nothing", _speaker_tags([]) == (False, False))
check("a None cast tags nothing (never raises)", _speaker_tags(None) == (False, False))

# The axes must be INDEPENDENT — a 3-human 1-agent room must not tag the agent.
check("three humans + one agent still tags agents NOT at all",
      _speaker_tags([H, H2, {"member_kind": "human", "principal_id": "u3"}, A]) == (True, False))

# ---------------------------------------------------------------------------
print("\n§2 — _speaker_label reads the metadata the FE already renders")
# ---------------------------------------------------------------------------
hn = {"u1": "Kevin", "u2": "Dana"}
an = {"editor": "Editor", "supervisor": "Supervisor"}

check("a human row resolves by author_principal_id",
      _speaker_label({"role": "user", "metadata": {"author_principal_id": "u2"}},
                     human_names=hn, agent_names=an) == "Dana")
check("an assistant row resolves by agent_slug",
      _speaker_label({"role": "assistant", "metadata": {"agent_slug": "supervisor"}},
                     human_names=hn, agent_names=an) == "Supervisor")
check("an unknown author resolves to None (never a wrong name)",
      _speaker_label({"role": "user", "metadata": {"author_principal_id": "ghost"}},
                     human_names=hn, agent_names=an) is None)
check("a missing metadata dict is survivable",
      _speaker_label({"role": "user"}, human_names=hn, agent_names=an) is None)
check("a null metadata is survivable",
      _speaker_label({"role": "user", "metadata": None},
                     human_names=hn, agent_names=an) is None)

# ---------------------------------------------------------------------------
print("\n§3 — _fetch_history DRIVEN: the transcript carries its speakers")
# ---------------------------------------------------------------------------
# Driven, not grepped. The defect was a function that SELECTED authorship and
# then dropped it — `grep author_principal_id routes/lanes.py` passed over the
# broken code for months, because the string was in the select clause.
import routes.lanes as L  # noqa: E402

ROWS = [
    {"role": "user", "content": "what do you both think?", "sequence_number": 1,
     "metadata": {"author_principal_id": "u1"}},
    {"role": "assistant", "content": "the deck reads well.", "sequence_number": 2,
     "metadata": {"agent_slug": "editor"}},
    {"role": "user", "content": "agreed", "sequence_number": 3,
     "metadata": {"author_principal_id": "u2"}},
    {"role": "assistant", "content": "cadence is weekly.", "sequence_number": 4,
     "metadata": {"agent_slug": "supervisor"}},
]


class _Q:
    def __init__(self, rows): self._rows = rows
    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def gte(self, *a, **k): return self
    def lt(self, *a, **k): return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def execute(self):
        class R: data = list(reversed(self._rows))
        return R()


class _Client:
    def __init__(self, rows): self._rows = rows
    def table(self, *_a, **_k): return _Q(self._rows)


class _Auth:
    def __init__(self, rows):
        self.client = _Client(rows)
        self.user_id = "u1"


def _run(cast, rows=ROWS, monkey_names=True):
    """Call the REAL _fetch_history with the label resolvers stubbed.

    BOTH modules are stubbed, deliberately: the function imports
    `resolve_member_names` AND `get_service_client`, and stubbing only the
    first left the second reaching for real credentials, throwing, and taking
    the best-effort degrade path — which made this gate report the human axis
    as broken when it was correct. (Found by exactly that false red.) The
    degrade path itself is asserted separately below.
    """
    import types
    saved = {k: sys.modules.get(k) for k in
             ("services.principal_display", "services.supabase")}
    if monkey_names:
        pd = types.ModuleType("services.principal_display")
        pd.resolve_member_names = lambda _c, ids: {"u1": "Kevin", "u2": "Dana"}
        sys.modules["services.principal_display"] = pd
        sb = types.ModuleType("services.supabase")
        sb.get_service_client = lambda: object()
        sys.modules["services.supabase"] = sb
    try:
        return L._fetch_history(_Auth(rows), "lane-1", cast=cast)
    finally:
        for k, v in saved.items():
            if v is not None:
                sys.modules[k] = v
            else:
                sys.modules.pop(k, None)


# (a) the SOLO room — byte-identical to the pre-ADR-626 shape.
solo = _run([H, A])
check("solo room: content is untouched",
      [m["content"] for m in solo] == [r["content"] for r in ROWS],
      f"got {[m['content'] for m in solo]}")

# (b) multi-human: user turns tagged, assistant turns NOT.
mh = _run([H, H2, A])
check("multi-human: human turns carry the person's name",
      mh[0]["content"] == "Kevin: what do you both think?" and mh[2]["content"] == "Dana: agreed",
      f"got {[m['content'] for m in mh]}")
check("multi-human: assistant turns stay untagged",
      mh[1]["content"] == "the deck reads well.",
      "the agent axis must not move with the human axis")

# (c) multi-agent: assistant turns tagged, user turns NOT.
ma = _run([H, A, A2])
check("multi-agent: each agent's turn carries its name",
      ma[1]["content"] == "Editor: the deck reads well."
      and ma[3]["content"] == "Supervisor: cadence is weekly.",
      f"got {[m['content'] for m in ma]}")
check("multi-agent: human turns stay untagged", ma[0]["content"] == "what do you both think?")
check("multi-agent: the RESPONDER tags itself too",
      ma[1]["content"].startswith("Editor: "),
      "a transcript naming only the others implies the untagged turns are mine")

# (d) roles are never rewritten.
both = _run([H, H2, A, A2])
check("role is never rewritten — tagging is additive",
      [m["role"] for m in both] == [r["role"] for r in ROWS],
      f"got {[m['role'] for m in both]}")

# (e) an unresolvable author is left untagged, not labelled "unknown".
GHOST = [{"role": "user", "content": "hi", "sequence_number": 1,
          "metadata": {"author_principal_id": "nobody"}}]
gh = _run([H, H2, A], rows=GHOST)
check("an unresolvable author is left UNTAGGED, never guessed",
      gh[0]["content"] == "hi", f"got {gh[0]['content']!r}")

# (f) the RESOLVER ITSELF failing must degrade, never raise. Run with no stub
# at all, so `get_service_client()` reaches for credentials this process does
# not have — the real shape of an admin-API outage on the turn path.
degraded = _run([H, H2, A], monkey_names=False)
check("a label-resolver failure degrades to untagged, never raises",
      [m["content"] for m in degraded] == [r["content"] for r in ROWS],
      "a turn must never fail over a display name")

# ---------------------------------------------------------------------------
print("\n§4 — visibility_floor is species-blind FOR REAL (ADR-626 D3)")
# ---------------------------------------------------------------------------
import inspect  # noqa: E402
from services.conversation_cast import visibility_floor  # noqa: E402

_sig = inspect.signature(visibility_floor)
check("visibility_floor accepts an agent_slug selector", "agent_slug" in _sig.parameters,
      "its docstring claimed species-blindness while only passing principal_id")
check("principal_id stays POSITIONAL (the existing human call site is unchanged)",
      _sig.parameters["principal_id"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD)

_src = inspect.getsource(visibility_floor)
check("it routes the slug to find_participant's agent_slug",
      "agent_slug=agent_slug" in _src)
check("exactly one selector is required",
      "give exactly one of" in _src)

# The turn path must actually CALL it for the responder, and take the MAX.
_lanes_src = open(os.path.join(os.path.dirname(__file__), "routes/lanes.py")).read()
check("the turn path asks the RESPONDER's window",
      "visibility_floor(lane_id, agent_slug=responder)" in _lanes_src,
      "the primitive existing is not the same as it being invoked")
check("the clamp takes the MAX, never the agent's alone",
      "max(_floor, int(_agent_floor))" in _lanes_src,
      "a human's floor is an authorization boundary an agent must not widen")

# ---------------------------------------------------------------------------
print("\n§5 — the cast section gets its people (ADR-626 D2)")
# ---------------------------------------------------------------------------
check("the turn path enriches cast labels",
      "enrich_cast_labels(cast)" in _lanes_src,
      "the enricher existed with ONE caller: the mentions WRITE path")

# It must be in its OWN try — folding it into the cast read would let a label
# failure zero the roster, the responder and the window.
_after = _lanes_src[_lanes_src.index("cast = list_participants(lane_id)"):]
_after = _after[:_after.index("enrich_cast_labels(cast)")]
check("the enricher sits OUTSIDE the cast-read try block",
      _after.count("except Exception") >= 1,
      "a cosmetic label fault must not become a lost cast")

# And `_fetch_history` must receive the cast, or the tags can never fire.
check("the cast reaches _fetch_history", "cast=cast," in _lanes_src,
      "without it `_speaker_tags` always sees None and nothing is ever tagged")

# ---------------------------------------------------------------------------
print("\n§6 — the headless-dispatch stack is DELETED (ADR-626 D4.b)")
# ---------------------------------------------------------------------------
# This section used to assert the module was DORMANT. ADR-626 D4.b deleted it:
# role-keyed dispatch ("who does this work?" answered by a role ON A BEING) is
# the shape ADR-596→610 dismantled, and capability lives at the APP instead.
# The absent-assertions are the stronger form of the dormancy ones.
import importlib  # noqa: E402
from services.primitives import registry as _R  # noqa: E402


def _gone(mod):
    try:
        importlib.import_module(mod)
        return False
    except ImportError:
        return True


check("primitives/dispatch_specialist.py is DELETED",
      _gone("services.primitives.dispatch_specialist"),
      "re-adding it re-opens role-keyed dispatch — argue with this gate")

for _sym in ("HeadlessAuth", "get_headless_tools_for_agent", "create_headless_executor"):
    check(f"registry no longer exports {_sym}", not hasattr(_R, _sym),
          "the whole headless-dispatch stack went together")

_names = lambda rows: {t["name"] for t in rows}  # noqa: E731
for _roster, _rows in (
    ("HANDLERS", None),
    ("CHAT_PRIMITIVES", _R.CHAT_PRIMITIVES),
    ("HEADLESS_PRIMITIVES", _R.HEADLESS_PRIMITIVES),
    ("FREDDIE_PRIMITIVES", _R.FREDDIE_PRIMITIVES),
    ("PRIMITIVES", _R.PRIMITIVES),
):
    _present = ("DispatchSpecialist" in _R.HANDLERS if _rows is None
                else "DispatchSpecialist" in _names(_rows))
    check(f"DispatchSpecialist absent from {_roster}", not _present)

# ⭐ The `specialist:` ATTRIBUTION PREFIX must SURVIVE the deletion. A prefix is
# a vocabulary; the class that stamped it was a mechanism. ADR-577 D1.a's
# credential guard keys on this prefix, so losing it would silently open the
# owner-token fallthrough that ADR refuses.
from services.platform_credentials import is_agent_caller  # noqa: E402


class _AgentAuth:
    def __init__(self, ci):
        self.caller_identity, self.headless = ci, True


for _identity in ("specialist:researcher", "specialist:unknown"):
    check(f"`{_identity}` still reads as an agent caller (ADR-577 D1.a)",
          is_agent_caller(_AgentAuth(_identity)),
          "the prefix outlived the class that stamped it — it must keep working")

# The live mechanism D4.b names must exist, or the ADR points at a ghost.
from services.derive_turn import run_bounded_derive_turn  # noqa: E402
check("the live bounded-turn mechanism exists (run_bounded_derive_turn)",
      callable(run_bounded_derive_turn))

# ---------------------------------------------------------------------------
print("\n" + "=" * 68)
if failures:
    print(f"RED — {len(failures)} failing assertion(s):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("GREEN — ADR-626 holds.")
