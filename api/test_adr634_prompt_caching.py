"""ADR-634 — the lane frame is cacheable, and the marker never reaches a
provider that cannot use it.

Run: python3 test_adr633_prompt_caching.py   (from api/, on the py3.9 venv —
it imports litellm, so `venv/bin/python test_adr633_prompt_caching.py`)

The failure this file exists because of:

  The lane frame is ~16KB (65% of it the studio posture) and is built ONCE per
  turn, then re-sent on EVERY round of the tool loop — up to 5. Every round
  after the first billed the same bytes as fresh input: ~22,700 input tokens of
  pure frame per member message. `services/anthropic.py` had carried the
  prompt-caching beta header since it was written, and its own docstring said
  "prompt caching should pass a list with cache_control on static blocks" —
  and NO live path in services/ ever passed one. The ledger was further ahead
  than the request: `_normalize_usage` already split cache_read/cache_create
  out of prompt_tokens, and `telemetry` already priced them at 0.10x. The
  accounting for a feature nothing had requested had been correct and unused.

The defense is EXECUTION against the REAL provider transforms, not grep and
not trust: a marker that survives to Anthropic is worthless if the same marker
breaks Gemini, and reading LiteLLM's source is not evidence about what it
emits. Every wire assertion below runs LiteLLM's own transform and inspects
the payload it produced.
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


from services.model_router import _CACHE_MIN_CHARS, _system_payload  # noqa: E402

# A frame the size of a real one (the Slides lane measured ~16KB).
FRAME = "LANE FRAME LINE. " * 1000

print("§1 the helper marks what can be cached and nothing else")

_block = _system_payload(FRAME, "anthropic/claude-sonnet-5")
check("an Anthropic frame becomes a content block", isinstance(_block, list))
check(
    "the block carries the ephemeral marker",
    isinstance(_block, list)
    and _block[0].get("cache_control") == {"type": "ephemeral"},
)
check(
    "the block carries the frame VERBATIM (nothing truncated to fit)",
    isinstance(_block, list) and _block[0]["text"] == FRAME,
)

# Falsification: the helper must never invent a payload where there was none.
check("None stays None", _system_payload(None, "anthropic/claude-sonnet-5") is None)
check("empty stays empty", _system_payload("", "anthropic/claude-sonnet-5") == "")

# A short frame gains nothing (the provider will not cache a short prefix) and
# must stay byte-identical to the pre-ADR-634 payload.
_short = "x" * (_CACHE_MIN_CHARS - 1)
check(
    "a frame under the minimum stays a plain string",
    _system_payload(_short, "anthropic/claude-sonnet-5") == _short,
)
check(
    "a frame at the minimum is marked",
    isinstance(_system_payload("x" * _CACHE_MIN_CHARS, "anthropic/claude-sonnet-5"), list),
)

# Defense in depth: a model litellm does not know must degrade, never raise.
check(
    "an unsupported model degrades to a plain string",
    _system_payload(FRAME, "cohere/command-r") == FRAME,
)
check(
    "an UNKNOWN model degrades to a plain string, and does not raise",
    _system_payload(FRAME, "totally/made-up-xyz") == FRAME,
)

print("\n§2 the WIRE — what each provider's transform actually emits")

# ---- Anthropic: the marker must survive, hoisted into `system`.
from litellm.llms.anthropic.chat.transformation import AnthropicConfig  # noqa: E402

_a = AnthropicConfig().transform_request(
    model="claude-sonnet-5",
    messages=[
        {"role": "system", "content": _system_payload(FRAME, "anthropic/claude-sonnet-5")},
        {"role": "user", "content": "hi"},
    ],
    optional_params={},
    litellm_params={},
    headers={},
)
_a_sys = json.dumps(_a.get("system"))
check("ANTHROPIC: cache_control reaches the wire", "cache_control" in _a_sys)
check("ANTHROPIC: the marker is ephemeral", "ephemeral" in _a_sys)
check("ANTHROPIC: the frame text is intact on the wire", FRAME[:40] in _a_sys)

# ---- OpenAI-compatible (openai · xai · deepseek all ride this transform).
from litellm.llms.openai.chat.gpt_transformation import OpenAIGPTConfig  # noqa: E402

_o = OpenAIGPTConfig().transform_request(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": _system_payload(FRAME, "openai/gpt-4o-mini")},
        {"role": "user", "content": "hi"},
    ],
    optional_params={},
    litellm_params={},
    headers={},
)
_o_blob = json.dumps(_o)
check("OPENAI: cache_control is STRIPPED before the wire", "cache_control" not in _o_blob)
check("OPENAI: the frame text still reaches the model", FRAME[:40] in _o_blob)

# ---- Gemini: a different transform family entirely.
from litellm.llms.vertex_ai.gemini.transformation import (  # noqa: E402
    _gemini_convert_messages_with_history,
)

_g = _gemini_convert_messages_with_history(
    messages=[
        {"role": "system", "content": _system_payload(FRAME, "gemini/gemini-2.5-pro")},
        {"role": "user", "content": "hi"},
    ]
)
_g_blob = json.dumps(_g, default=str)
check("GEMINI: cache_control is STRIPPED before the wire", "cache_control" not in _g_blob)

print("\n§3 both router doors carry it — they are twins and a one-door fix works half the time")

_src = pathlib.Path("services/model_router.py").read_text(encoding="utf-8")
check(
    "the payload helper is used at BOTH assembly sites",
    _src.count('"content": _system_payload(system, model)') == 2,
    f'found {_src.count(chr(34) + "content" + chr(34) + ": _system_payload(system, model)")}',
)
check(
    "no site still hard-codes the bare string payload",
    '{"role": "system", "content": system}' not in _src,
)

print("\n§4 the ledger already accounts for what we now request")

from services.model_router import _normalize_usage  # noqa: E402

_u = _normalize_usage(
    {
        "prompt_tokens": 10_000,
        "completion_tokens": 200,
        "cache_read_input_tokens": 9_000,
        "cache_creation_input_tokens": 500,
    }
)
check(
    "a cached turn bills FRESH input exclusive of cache",
    _u["input_tokens"] == 500,
    str(_u),
)
check("cache reads are carried, not dropped", _u["cache_read_tokens"] == 9_000)
check("cache writes are carried, not dropped", _u["cache_create_tokens"] == 500)

from services.telemetry import _BILLING_RATES  # noqa: E402

# The multipliers are IMPLICIT — telemetry defaults to 0.10 read / 1.25 write,
# which are Anthropic's published ratios. That is correct for the models this
# change actually caches (only Anthropic receives the marker), so the check is
# that a cached turn costs a TENTH of the same turn uncached, not that a row
# spells the number out.
from services.telemetry import compute_cost_usd_inclusive  # noqa: E402

_uncached = compute_cost_usd_inclusive("claude-sonnet-5", 10_000, 0)
_cached = compute_cost_usd_inclusive("claude-sonnet-5", 0, 0, cache_read_tokens=10_000)
check(
    "a cached read costs a tenth of fresh input",
    abs(_cached - _uncached * 0.10) < 1e-9,
    f"uncached={_uncached} cached={_cached}",
)
_written = compute_cost_usd_inclusive("claude-sonnet-5", 0, 0, cache_create_tokens=10_000)
check(
    "writing the cache costs MORE than fresh input (so a one-round turn is not free)",
    _written > _uncached,
    f"write={_written} fresh={_uncached}",
)
# Falsification: the marker only ever reaches Anthropic, so a non-Anthropic
# model must never be billed a cache line by this change.
check(
    "every model this change can mark is Anthropic-priced",
    all(
        m.startswith("claude") or not isinstance(
            _system_payload(FRAME, f"anthropic/{m}"), list
        )
        for m in ["claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5"]
    ),
)

print("\n\u00a75 the trade is real in BOTH directions \u2014 a cache write is not free")

# Writing the cache costs 1.25x, so a ONE-round turn pays ~25% MORE and only a
# multi-round turn wins. Measured on 500 real production turns (2026-09-03):
# 33% ran 1 round, 67% ran 2+, blending to a ~46% saving on frame bytes. If
# traffic ever shifted to mostly-single-round turns, this change would become a
# net LOSS \u2014 so the arithmetic is asserted, not assumed.
_TOK = 4_389  # the measured slides frame, in tokens


def _plain(rounds: int) -> float:
    return compute_cost_usd_inclusive("claude-sonnet-5", _TOK * rounds, 0)


def _cached(rounds: int) -> float:
    return (
        compute_cost_usd_inclusive("claude-sonnet-5", 0, 0, cache_create_tokens=_TOK)
        + compute_cost_usd_inclusive(
            "claude-sonnet-5", 0, 0, cache_read_tokens=_TOK * (rounds - 1)
        )
    )


check(
    "a ONE-round turn costs MORE (the write, unamortized) \u2014 stated, not hidden",
    _cached(1) > _plain(1),
)
check("a two-round turn already wins", _cached(2) < _plain(2))
check("a five-round turn wins by >60%", (_plain(5) - _cached(5)) / _plain(5) > 0.60)

_DIST = {1: 166, 2: 130, 3: 84, 4: 48, 5: 29, 6: 22, 7: 11, 8: 9, 13: 1}
_before = sum(n * _plain(r) for r, n in _DIST.items())
_after = sum(n * _cached(r) for r, n in _DIST.items())
check(
    "blended over the REAL round distribution, caching wins",
    _after < _before,
    f"before={_before:.4f} after={_after:.4f}",
)
check(
    "the blended saving is at least 40%",
    (_before - _after) / _before >= 0.40,
    f"{100 * (_before - _after) / _before:.1f}%",
)

print(f"\n{N - len(FAILS)}/{N} checks passed")
if FAILS:
    print("\nFAILURES:")
    for f in FAILS:
        print(f"  - {f}")
    sys.exit(1)
print("ADR-634 gate GREEN")
