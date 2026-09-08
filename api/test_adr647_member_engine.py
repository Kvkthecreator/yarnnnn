"""ADR-647 D4/D5/D8 — the member's engine preference narrows, and a dark engine
says which kind of dark.

Run: python3 test_adr647_member_engine.py   (from api/)

Two failures this file exists because of:

  D4. Engine choice was not first-class where the spend is. A CHAT lane could
      already say "Editor, on GPT-5" (routes/lanes.py, the `chat_agent and
      model` branch), but a BOUND lane's engine was its app resident's
      hardcoded `model` field with no member input anywhere — and Studio, Text,
      Slides and Images all run bound lanes. The surface carrying 98% of lane
      spend was the one surface a member could not re-point.

  D8. `note_upstream_refusal` has stored the provider's own refusal words since
      ADR-559 and NOTHING EVER READ THEM. Every account-level refusal reached
      the member as one generic sentence, so an unfunded account and an
      exceeded quota — which call for different operator actions — were
      indistinguishable. DeepSeek has been dark on "Insufficient Balance" since
      ADR-420 and the door never said so.

⭐ The rule this file is really guarding (D5): A PREFERENCE NARROWS, IT NEVER
GRANTS. `member_state` is presentation state, deliberately member-writable and
explicitly never consulted for authorization (ADR-405 D5). If a row there could
select an engine the door refuses, a preference would be doing authorization's
job — ADR-573's lesson about the connector workspace stamp, at a new seam.
"""

from __future__ import annotations

import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

FAILS: list[str] = []
N = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global N
    N += 1
    if cond:
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label}" + (f" — {detail}" if detail else ""))
        FAILS.append(label)


# Provider keys so availability is decided by the registry, not this harness's
# environment (the ADR-559 `no_provider_key` reason would otherwise mask D5).
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
           "DEEPSEEK_API_KEY", "XAI_API_KEY"):
    os.environ.setdefault(_k, "test-key")

from services.lane_runner import (  # noqa: E402
    LANE_MODELS,
    clear_upstream_refusal,
    lane_model_availability,
    note_upstream_refusal,
    offered_lane_models,
    resolve_member_engine,
    upstream_refusal_detail,
)


class _Result:
    def __init__(self, data): self.data = data


class _Query:
    def __init__(self, data): self._d = data
    def select(self, *a): return self
    def eq(self, *a): return self
    def limit(self, n): return self
    def execute(self): return _Result(self._d)


class _Client:
    """A member_state read that returns exactly what the test stored."""
    def __init__(self, data): self._d = data
    def table(self, name): return _Query(self._d)


def _pref(value) -> object:
    return resolve_member_engine(_Client([{"value": value}]), "ws-1", "p-1")


print("§1 D4 — a stored preference resolves")

_live = next(iter(offered_lane_models()))
check("a plain model string resolves", _pref(_live) == _live)
check("the {model: ...} shape resolves too", _pref({"model": _live}) == _live)
check("no row means no preference",
      resolve_member_engine(_Client([]), "ws-1", "p-1") is None)

print("\n§2 D5 — THE PREFERENCE NARROWS, IT NEVER GRANTS")

_retired = next((m for m, v in LANE_MODELS.items() if v.get("retired")), None)
check("a RETIRED engine is refused (it left the door; the preference follows)",
      _retired is not None and _pref(_retired) is None, f"retired={_retired}")
check("an engine NOT IN THE REGISTRY AT ALL is refused",
      _pref("evil/backdoor-9") is None)
check("a bare model name with no provider prefix is refused",
      _pref("claude-sonnet-5") is None)

# The narrowing must be the CHOOSER's own two questions, so an engine that goes
# dark for any reason takes the preference with it.
_dark = "deepseek/deepseek-chat"
note_upstream_refusal(_dark, RuntimeError("Error code: 402 - Insufficient Balance"))
check("an engine the door would refuse RIGHT NOW is refused as a preference",
      _pref(_dark) is None)
clear_upstream_refusal(_dark)
check("...and is accepted again once the engine heals", _pref(_dark) == _dark)

print("\n§3 the resolver is total — a preference must never fail a turn")

check("a malformed value is refused, not raised", _pref({"nope": 1}) is None)
check("a null value is refused", _pref(None) is None)
check("an empty string is refused", _pref("   ") is None)
check("a non-string, non-dict value is refused", _pref(12345) is None)
check("no workspace resolves to no preference",
      resolve_member_engine(_Client([{"value": _live}]), None, "p-1") is None)
check("no principal resolves to no preference",
      resolve_member_engine(_Client([{"value": _live}]), "ws-1", None) is None)


class _Boom:
    def table(self, name): raise RuntimeError("db down")


check("a DB failure resolves to None (the app's default stands)",
      resolve_member_engine(_Boom(), "ws-1", "p-1") is None)

print("\n§4 D4 — the preference is a DOOR default, never a retroactive re-point")

_lanes = pathlib.Path("routes/lanes.py").read_text(encoding="utf-8")
_create = _lanes[_lanes.index("async def create_lane("):]
_create = _create[:_create.index("\n@router.")]
check("the creation door consults the preference",
      "resolve_member_engine(" in _create)
check("an explicitly named engine still wins over the preference",
      "if chat_agent and model:" in _create)

# ⚠️ THE INVARIANT WORTH THE MOST HERE. A lane's engine is what ACTUALLY ran
# and is rendered into every revision's attribution (ADR-460 D4). The turn path
# must never consult a preference, or a stored row would retroactively change
# what a past revision claims about itself.
_turn = _lanes[_lanes.index("async def lane_turn("):]
check("the TURN path never consults the preference (attribution is historical)",
      "resolve_member_engine" not in _turn)

# ⚠️ SLICE THE FUNCTION, NOT THE REST OF THE FILE. A first cut of this check
# ended each slice at the next `"\n\ndef "`, which never matches an `async def`
# — so both slices ran to EOF and swept up `__all__`, where the resolver's name
# legitimately appears. It reported two failures against correct code (the
# recorded "slice-scoped assertion reads the wrong region" lesson). Slice on
# any top-level `def`/`async def`, which is what actually ends a function.
_runner = pathlib.Path("services/lane_runner.py").read_text(encoding="utf-8")
# `__all__` also ends a function body — the LAST function in the file has
# no `def` after it, and that trailing export block is exactly where the
# resolver name legitimately lives.
_TOP_LEVEL = re.compile(r"\n\n(?:(?:async )?def |__all__)")
for _fn in ("async def run_lane_turn(", "async def run_lane_turn_stream("):
    _rest = _runner[_runner.index(_fn) + len(_fn):]
    _m = _TOP_LEVEL.search(_rest)
    _body = _rest[:_m.start()] if _m else _rest
    check(f"{_fn.split('(')[0].split()[-1]} never consults the preference",
          "resolve_member_engine" not in _body,
          f"slice was {len(_body)} chars — check the boundary, not just the result")

print("\n§5 D6/D7 — the boundaries this must not cross")

# Machinery is keyed by CALL TYPE (ADR-556) and must never be re-pointed by a
# member's preference. Structural: system_calls does not import the resolver.
_sys = pathlib.Path("services/system_calls.py").read_text(encoding="utf-8")
check("machinery (SYSTEM_CALLS) cannot reach the member preference",
      "resolve_member_engine" not in _sys and "member_state" not in _sys)

# ADR-460 D3.a: no authority-shaped field on an agent row. The preference lives
# on the MEMBER, not the agent.
_agents = pathlib.Path("services/agents_registry.py").read_text(encoding="utf-8")
check("no engine-preference field was added to the agent registry",
      "member_state" not in _agents and "resolve_member_engine" not in _agents)

print("\n§6 D8 — a dark engine says WHICH kind of dark")

from routes.lanes import _UNAVAILABLE_ENGINE_DETAIL, _refusal_suffix  # noqa: E402

check("no engine is refused before anything happens",
      upstream_refusal_detail(_dark) is None)

note_upstream_refusal(_dark, RuntimeError("Error code: 402 - Insufficient Balance"))
check("an account refusal is recorded as unavailable",
      lane_model_availability(_dark) == (False, "upstream_refused"))
check("the provider's OWN words are readable",
      "Insufficient Balance" in (upstream_refusal_detail(_dark) or ""))

_msg = _UNAVAILABLE_ENGINE_DETAIL["upstream_refused"].format(
    label=LANE_MODELS[_dark]["label"], detail=_refusal_suffix(_dark))
check("the member-facing sentence NAMES the cause, not just 'declined'",
      "Insufficient Balance" in _msg, _msg)
check("it still names the engine", LANE_MODELS[_dark]["label"] in _msg)

# EVERY template must accept {detail} or `.format(detail=...)` raises KeyError
# at the 422 — the door would 500 instead of refusing honestly.
for _reason, _tpl in _UNAVAILABLE_ENGINE_DETAIL.items():
    try:
        _tpl.format(label="X", detail="")
        _ok = True
    except (KeyError, IndexError):
        _ok = False
    check(f"the {_reason!r} template formats with detail= (no KeyError at the door)", _ok)

check("a reason we derive ourselves quotes nobody",
      _refusal_suffix("openai/gpt-5") == "")

clear_upstream_refusal(_dark)
check("a success HEALS the engine (ADR-559 D3, unchanged)",
      lane_model_availability(_dark)[0] and upstream_refusal_detail(_dark) is None)

print("\n§7 one resolver, one answer — the envelope cannot disagree with the door")

_env = _lanes[_lanes.index("def _lane_envelope("):]
_env = _env[:_env.index("\n@router.")]
check("the envelope serves the RESOLVED preference (not the raw stored row)",
      "resolve_member_engine(" in _env)
check("the envelope serves the refusal detail alongside the reason",
      "unavailable_detail" in _env and "upstream_refusal_detail(" in _env)

print("\n\u00a78 the FE consumes what the envelope serves")

# ⭐ A served field nothing reads is a claim, not a feature. Both directions:
# the server must send it AND the client must have a place to put it — the
# recorded "a negative check catches a forgotten DELETION, never an ADDITION"
# lesson, so assert the RELATION.
_web = pathlib.Path("../web").resolve()
_client = (_web / "lib/api/client.ts").read_text(encoding="utf-8")
_surface = (_web / "components/chat-surface/ChatSurface.tsx").read_text(encoding="utf-8")
_modal = (_web / "components/chat-surface/NewChatModal.tsx").read_text(encoding="utf-8")

check("the client envelope type carries default_engine", "default_engine" in _client)
check("the client envelope type carries unavailable_detail", "unavailable_detail" in _client)
check("ChatSurface passes the preference to the door",
      "defaultEngine={data?.default_engine" in _surface)
check("the door marks the preference distinctly from this browser's last-used",
      "your default" in _modal and "last used" in _modal)
check("the door renders the provider's refusal words",
      "unavailable_detail" in _modal)

print(f"\n{N - len(FAILS)}/{N} checks passed")
if FAILS:
    print("\nFAILURES:")
    for f in FAILS:
        print(f"  - {f}")
    sys.exit(1)
print("ADR-647 member-engine gate GREEN")
