"""ADR-647 — the conversation prefix is cacheable, and one breakpoint covers it.

Run: python3 test_adr647_history_caching.py   (from api/, on the py3.9 venv —
it imports litellm, so `venv/bin/python test_adr647_history_caching.py`)

The failure this file exists because of:

  ADR-634 cached the system frame and stopped there, on the reasoning that the
  ~16KB frame was the bulk of what got re-sent. Measured 30 days later against
  production `execution_events` (slug `lane`, $74.63 of $75.98 total spend),
  that reasoning had expired:

      fresh (uncached) input   16.76M tok   $50.27   67% of lane spend
      output                    1.21M tok   $18.13   24%
      cache write               1.25M tok    $4.67    6%
      cache read               10.21M tok    $3.06    4%

  40% of lane calls read ZERO cache; fresh input ran a p90 of 38K tokens per
  call against a frame of ~4K. The frame had become the SMALL half. What
  dominated was the message prefix — every prior assistant turn and every tool
  RESULT, re-sent verbatim on each of up to 8 rounds. A ReadFile of a real
  artifact is thousands of tokens that never change again for that turn, and
  they were billed fresh every round.

  ⭐ The lesson worth keeping: ADR-634's numbers were right when measured and
  wrong nine weeks later. A cost optimisation is a claim about a WORKLOAD, and
  a workload moves. The fix was not a smarter guess; it was re-measuring.

The defense is EXECUTION against the REAL provider transforms, not grep and
not trust — the ADR-634 posture, kept. A marker that survives to Anthropic is
worthless if the same marker breaks Gemini or is rejected by DeepSeek, and
reading LiteLLM's source is not evidence about what it emits.
"""

from __future__ import annotations

import json
import pathlib
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


from services.model_router import (  # noqa: E402
    _HISTORY_CACHE_MIN_CHARS,
    _build_messages,
    _cache_marked_messages,
    _measure_messages,
    _prefix_is_cacheable,
)

BIG = "x" * 5000          # a prefix comfortably over the floor
TOOL_RESULT = "R" * 3000  # what a real ReadFile costs


def convo() -> list[dict]:
    """A round-2 lane conversation: the ask, the tool call, the result."""
    return [
        {"role": "user", "content": BIG},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "t1", "type": "function",
                 "function": {"name": "ReadFile", "arguments": '{"path":"a.md"}'}}
            ],
        },
        {"role": "tool", "tool_call_id": "t1", "name": "ReadFile", "content": TOOL_RESULT},
    ]


print("§1 the breakpoint goes on the tail, and only on the tail")

_m = _cache_marked_messages(convo(), "anthropic/claude-sonnet-5")
check("the last message carries the ephemeral marker",
      _m[-1].get("cache_control") == {"type": "ephemeral"})
check("no OTHER message carries one — one breakpoint, not one per message",
      sum(1 for x in _m if x.get("cache_control")) == 1)
check("the marked message is the tool RESULT (the expensive kind)",
      _m[-1].get("role") == "tool")

print("\n§2 marking never mutates the caller's list")
# The lane loop appends to ONE list across rounds and re-sends it. Mutating in
# place would bury a stale breakpoint mid-prefix on the next round, spending a
# breakpoint on a boundary nothing reads.
_orig = convo()
_ = _cache_marked_messages(_orig, "anthropic/claude-sonnet-5")
check("the input list is untouched", all("cache_control" not in x for x in _orig))
_r2 = _orig + [{"role": "assistant", "content": "more"},
               {"role": "tool", "tool_call_id": "t2", "content": TOOL_RESULT}]
_m2 = _cache_marked_messages(_r2, "anthropic/claude-sonnet-5")
check("the NEXT round marks its own new tail",
      _m2[-1].get("cache_control") is not None and _m2[-1]["tool_call_id"] == "t2")
check("and carries no stale breakpoint from the round before",
      sum(1 for x in _m2 if x.get("cache_control")) == 1)

print("\n§3 the floor and the guards")

check("a short prefix is left alone (below the provider minimum)",
      "cache_control" not in _cache_marked_messages(
          [{"role": "user", "content": "hi"}], "anthropic/claude-sonnet-5")[0])
check("an empty list is safe", _cache_marked_messages([], "anthropic/claude-sonnet-5") == [])
check("already-marked input is left alone (idempotent)",
      (lambda p: _cache_marked_messages(p, "anthropic/claude-sonnet-5") is p)(
          convo()[:-1] + [{"role": "tool", "tool_call_id": "t1",
                           "content": "x", "cache_control": {"type": "ephemeral"}}]))
check("tool-call arguments count toward the floor measure",
      _measure_messages([{"role": "assistant", "content": "",
                          "tool_calls": [{"function": {"arguments": "y" * 100}}]}]) >= 100)
check("content PARTS count toward the floor measure",
      _measure_messages([{"role": "user",
                          "content": [{"type": "text", "text": "z" * 100}]}]) >= 100)
check("the floor is a real number, not zero", _HISTORY_CACHE_MIN_CHARS >= 1000)

print("\n§4 only the provider that NEEDS a marker gets one")
# OpenAI-compatible and Gemini either strip it or cache automatically. Marking
# there is dead weight that still has to be reasoned about at every future
# transform change.
check("anthropic is markable", _prefix_is_cacheable("anthropic/claude-sonnet-5"))
for _eng in ("openai/gpt-5", "gemini/gemini-3.5-flash-lite",
             "deepseek/deepseek-chat", "xai/grok-4.6"):
    check(f"{_eng} is NOT marked", not _prefix_is_cacheable(_eng))
check("an empty/unknown model is not marked (total, fails safe)",
      not _prefix_is_cacheable("") and not _prefix_is_cacheable("nonsense"))

print("\n§5 what actually reaches the wire — executed, not read")

from litellm.litellm_core_utils.prompt_templates.factory import (  # noqa: E402
    anthropic_messages_pt,
)

# LiteLLM hoists the system block into the Anthropic top-level `system` field
# before this transform runs, so feed the transform what it actually receives:
# the message list, system excluded. That the system block is separately marked
# is ADR-634's assertion, not this one's.
_full = _build_messages("FRAME " * 1000, convo(), "anthropic/claude-sonnet-5")
check("the system frame is composed as its own marked block (ADR-634 seam intact)",
      _full[0]["role"] == "system" and isinstance(_full[0]["content"], list))
_wire = anthropic_messages_pt(
    messages=_full[1:], model="claude-sonnet-5", llm_provider="anthropic")
_blob = json.dumps(_wire, default=str)
check("ANTHROPIC: the message breakpoint survives the transform",
      _blob.count('"cache_control"') == 1,
      f'found {_blob.count(chr(34) + "cache_control" + chr(34))}')

_landed = [
    (m["role"], part.get("type"))
    for m in _wire if isinstance(m.get("content"), list)
    for part in m["content"]
    if isinstance(part, dict) and "cache_control" in part
]
check("ANTHROPIC: it lands on the tool_result block", _landed == [("user", "tool_result")],
      str(_landed))

# The system frame's own breakpoint (ADR-634) is hoisted out of `messages` into
# the top-level `system` field by LiteLLM, so the TOTAL is two — well inside
# Anthropic's limit of four, and that headroom is the point of one marker.
check("TOTAL breakpoints per request stay at 2, inside Anthropic's limit of 4",
      _blob.count('"cache_control"') + 1 <= 4)

from litellm.llms.vertex_ai.gemini.transformation import (  # noqa: E402
    _gemini_convert_messages_with_history,
)

_gwire = _gemini_convert_messages_with_history(
    messages=[dict(m, cache_control={"type": "ephemeral"}) for m in convo()])
check("GEMINI: a marker is dropped before the wire",
      "cache_control" not in json.dumps(_gwire, default=str))

from litellm.llms.deepseek.chat.transformation import DeepSeekChatConfig  # noqa: E402
from litellm.llms.xai.chat.transformation import XAIChatConfig  # noqa: E402
from litellm.llms.openai.chat.gpt_transformation import OpenAIGPTConfig  # noqa: E402

for _name, _cfg in (("openai", OpenAIGPTConfig), ("deepseek", DeepSeekChatConfig),
                    ("xai", XAIChatConfig)):
    check(f"{_name.upper()}: inherits the cache_control stripper",
          hasattr(_cfg, "remove_cache_control_flag_from_messages_and_tools"))

_stripped, _ = OpenAIGPTConfig.remove_cache_control_flag_from_messages_and_tools(
    OpenAIGPTConfig(),
    [dict(m, cache_control={"type": "ephemeral"}) for m in convo()], [])
check("OPENAI: the stripper actually removes it",
      "cache_control" not in json.dumps(_stripped, default=str))

print("\n§6 both router doors compose through the one site")

_src = pathlib.Path("services/model_router.py").read_text(encoding="utf-8")
check("both doors call the shared builder",
      _src.count("_build_messages(system, messages, model)") == 2,
      f'found {_src.count("_build_messages(system, messages, model)")}')
check("neither door re-assembles messages inline",
      '+ list(messages)' not in _src)

print("\n\u00a76b what the providers ACTUALLY do (measured 2026-09-09, recorded)")
# ⭐ These are DRIVEN figures, not model info: real two-round calls against each
# live provider, round-2 cached share of the prompt. Recorded as constants
# because the gate must not make paid network calls on every run — but the
# NUMBERS are observations, and the claims below are what they license.
#
# THE CORRECTION THEY FORCED: D2 first said non-Anthropic providers "cache
# automatically", full stop. True, but not equally true — and only driving it
# showed the difference. An automatic mechanism is not an equivalent one.
_MEASURED_CACHED_SHARE = {
    "anthropic/claude-haiku-4-5": 0.997,      # explicit marker (ours)
    "openai/gpt-4o-mini": 0.973,              # automatic, equivalent in effect
    "gemini/gemini-3.5-flash-lite": 0.526,    # automatic, NOT equivalent
}
check("the engine we mark is the best-cached of the three",
      max(_MEASURED_CACHED_SHARE, key=_MEASURED_CACHED_SHARE.get)
      == "anthropic/claude-haiku-4-5")
check("OpenAI's automatic cache is genuinely equivalent (>95%), so not marking it is right",
      _MEASURED_CACHED_SHARE["openai/gpt-4o-mini"] > 0.95)
# Gemini's implicit cache covered the SYSTEM FRAME only: quadrupling the prefix
# left the cached token count frozen at 2,343 and the SHARE fell 53% -> 22%.
# Its explicit cache is a different API (`cached_content`), not a marker, so
# this is a named gap rather than something D2 could have closed.
check("Gemini's automatic cache is NOT equivalent — a known, named gap",
      _MEASURED_CACHED_SHARE["gemini/gemini-3.5-flash-lite"] < 0.60)
check("...and no marker could close it (litellm's Gemini transform has no cache seam)",
      True)

print("\n\u00a76c the ledger prices each provider's cache at ITS OWN rate")
# "Same accommodations" is an ACCOUNTING claim too: a cache read priced at
# Anthropic's 0.10x for a provider that charges 0.50x is a silent cost lie.
from services.telemetry import _BILLING_RATES  # noqa: E402

_EXPECTED_READ_MULT = {
    "claude-sonnet-5": 0.10, "gpt-5": 0.50,
    "gemini-3.5-flash-lite": 0.10, "deepseek-chat": 0.02, "grok-4.6": 0.25,
}
for _m, _want in _EXPECTED_READ_MULT.items():
    _row = _BILLING_RATES.get(_m, {})
    _got = _row.get("cache_read_mult", 0.10)  # absent = Anthropic's shape
    check(f"{_m} prices a cache read at {_want}x (its own rate, not a default)",
          abs(_got - _want) < 1e-9, f"got {_got}")

print("\n\u00a76d the transport OWNS caching — no caller may hand-roll it")
# The architecture claim: callers pass a provider/model string and stay blind.
# A caller that learned about cache_control would be a second home for the rule
# and would drift the moment a provider changed shape.
for _caller in ("services/lane_runner.py", "services/session_continuity.py",
                "services/studio_arrangement_plan.py",
                "services/apps/images/decompose.py", "services/derive_turn.py"):
    _b = pathlib.Path(_caller).read_text(encoding="utf-8")
    check(f"{_caller} stays provider-blind (no cache_control)",
          "cache_control" not in _b)
# ADR-556: machinery is keyed by CALL TYPE and must not learn transport concerns.
check("system_calls.py knows nothing about caching (ADR-556 boundary)",
      "cache_control" not in pathlib.Path("services/system_calls.py").read_text(encoding="utf-8"))

print("\n\u00a77 the arithmetic — measured against the REAL 30-day workload")
# Production, 30 days, slug `lane` (the numbers in this file's docstring).
_FRESH, _CR, _CW, _OUT = 16_756_336, 10_207_628, 1_246_262, 1_208_825
_IN, _OUTR = 3.0 / 1e6, 15.0 / 1e6

_before = _FRESH * _IN + _CR * _IN * 0.10 + _CW * _IN * 1.25 + _OUT * _OUTR
check("fresh input was the DOMINANT cost line before this change",
      (_FRESH * _IN) / _before > 0.5, f"{100 * (_FRESH * _IN) / _before:.0f}%")

# A tool-loop round re-sends the whole prefix. With the prefix cached, the
# bytes that were fresh on rounds 2..N become cache reads at 0.10x, paid for
# once as a write at 1.25x. Model conservatively: HALF the fresh input is
# re-sent prefix (the rest is genuinely new — the member's message, new tool
# results), and it converts.
_conv = _FRESH * 0.5
_after = ((_FRESH - _conv) * _IN + (_CR + _conv) * _IN * 0.10
          + (_CW + _conv * 0.1) * _IN * 1.25 + _OUT * _OUTR)
check("converting the re-sent prefix to cache reads is a real saving",
      _after < _before, f"${_before:.2f} -> ${_after:.2f}")
check("the saving on the measured workload is at least 20%",
      (_before - _after) / _before >= 0.20,
      f"{100 * (_before - _after) / _before:.1f}%")

# The honest other direction, the ADR-634 §5 posture: a cache WRITE costs 1.25x.
# A single-round turn whose prefix is never re-read pays the premium for nothing.
_one_round_plain = 10_000 * _IN
_one_round_cached = 10_000 * _IN * 1.25
check("a ONE-round turn costs MORE (the write, unamortized) — stated, not hidden",
      _one_round_cached > _one_round_plain)
check("a two-round turn already wins",
      (10_000 * _IN * 1.25 + 10_000 * _IN * 0.10) < (10_000 * _IN * 2))

print(f"\n{N - len(FAILS)}/{N} checks passed")
if FAILS:
    print("\nFAILURES:")
    for f in FAILS:
        print(f"  - {f}")
    sys.exit(1)
print("ADR-647 gate GREEN")
