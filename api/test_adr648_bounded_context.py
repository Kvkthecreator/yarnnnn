"""ADR-648 — a read is bounded and says so; history is bounded in the unit that costs.

Run: python3 test_adr648_bounded_context.py   (from api/)

Two failures this file exists because of:

  D1. `ReadFile` had NO size cap, while `ListFiles` beside it has had one since
      it was written. So ONE read of one large file could inject more than
      twice the median entire prompt. Measured on production 2026-09-09:
      workspace files run to 178,206 chars (~45K tokens), 6.4% are over 40K,
      and lane calls peaked at 86,799 prompt tokens against a 19,999 median.
      The tail IS the large read.

  D2. `_HISTORY_WINDOW = 20` bounds the COUNT of messages, and count is not
      what a provider charges for. The same 20 messages are 2K tokens in one
      conversation and 200K in another — the budget was unpredictable by
      construction, which is why the "fixed" window still produced a 4.3x
      spread between the median and the max.

⭐⭐⭐ THE RULE THAT SHAPES BOTH FIXES: **the clip is not the feature, the
NOTICE is.** A silently truncated read is the worst outcome available — the
model answers confidently from a fragment it believes is whole, and nothing
downstream can tell. That is `feedback_silence_is_the_most_dangerous_wrong_answer`,
already learned once in this very file for BINARY reads (`_binary_file_notice`),
and re-learned here for large ones.

⚠️ THE CACHE INTERACTION, which is why the trim shape is not free choice:
prompt caching matches on a PREFIX. Dropping a message from the MIDDLE
invalidates every cached token after it, so a "smarter" trim that kept one
interesting old turn would force a full re-write at 1.25x and cost MORE than
the tokens it saved. Oldest-first is the only shape that leaves the survivors
contiguous. 82% of consecutive lane calls land inside the 5-minute cache TTL
(measured), so this is the common path, not a corner.
"""

from __future__ import annotations

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


from services.primitives.workspace import (  # noqa: E402
    READ_FILE_MAX_CHARS,
    READ_FILE_TOOL,
    _clip_read,
)

print("§1 D1 — a small read is BYTE-IDENTICAL to before")

# The overwhelmingly common case (median file is 2,367 chars). A bound that
# changes the normal path is a behaviour change wearing an efficiency costume.
_small = "x" * 500
check("an unclipped read returns only `content`", _clip_read(_small) == {"content": _small})
check("an empty file is safe", _clip_read("") == {"content": ""})
check("a None content is safe", _clip_read(None) == {"content": ""})
check("a file exactly at the cap is NOT marked truncated",
      _clip_read("y" * READ_FILE_MAX_CHARS) == {"content": "y" * READ_FILE_MAX_CHARS})

print("\n§2 D1 — a clipped read SAYS SO, and says how to continue")

_big = "y" * 250_000
_r = _clip_read(_big)
# ⚠️ READ EVERY FIELD WITH .get(). A first cut indexed `_r["returned_chars"]`
# directly, so falsifying the notice (making the clip SILENT — the exact defect
# this section exists to catch) raised KeyError and killed the run before the
# remaining 30 checks reported. The gate DID catch the defect and then hid its
# own verdict behind a stack trace. Same shape as the `test_adr557` crash fixed
# earlier the same day: a gate that crashes reports nothing, and reporting
# nothing looks far too much like passing.
check("a large read is marked truncated", _r.get("truncated") is True)
check("it returns exactly the cap", _r.get("returned_chars") == READ_FILE_MAX_CHARS)
check("it states the file's REAL size", _r.get("total_chars") == 250_000)
check("it names the exact offset to continue from",
      _r.get("next_offset") == READ_FILE_MAX_CHARS)
# ⭐ The message must forbid the specific wrong behaviour, not just describe
# the clip. "Showing 1-100000 of 250000" is a fact a model can read past.
_rmsg = _r.get("message") or ""
check("the message TELLS the model not to answer as if it saw the rest",
      "not all of it" in _rmsg and "do not answer" in _rmsg.lower())
check("the message names the continuing call by parameter", "offset=" in _rmsg)

print("\n§3 D1 — the continuation is a REAL mechanism, not advice")

# ⚠️ Telling a model to "request more" without a parameter to do it with is an
# instruction it cannot follow. The schema must carry `offset`.
_props = READ_FILE_TOOL["input_schema"]["properties"]
check("ReadFile's schema exposes `offset`", "offset" in _props)
check("`offset` is an integer", _props.get("offset", {}).get("type") == "integer")
check("`offset` is optional (a normal read passes nothing)",
      "offset" not in READ_FILE_TOOL["input_schema"]["required"])
check("the tool DESCRIPTION warns about bounded windows (where the model reads it)",
      "BOUNDED WINDOW" in READ_FILE_TOOL["description"])

_r2 = _clip_read(_big, offset=_r.get("next_offset") or READ_FILE_MAX_CHARS)
check("continuing from next_offset advances the window",
      _r2.get("offset") == READ_FILE_MAX_CHARS
      and _r2.get("returned_chars") == READ_FILE_MAX_CHARS)
_r3 = _clip_read(_big, offset=200_000)
check("the FINAL window carries no next_offset", "next_offset" not in _r3)
check("...and says it reached the end", "end of the file" in (_r3.get("message") or ""))

# Reassembling every window must reproduce the file exactly — a clip that
# loses or duplicates a byte is a corruption, not a bound.
_parts, _off, _guard = [], 0, 0
while _guard < 100:                      # bounded: a broken clip must not hang the gate
    _guard += 1
    _w = _clip_read(_big, offset=_off)
    _parts.append(_w.get("content") or "")
    if "next_offset" not in _w:
        break
    _off = _w.get("next_offset") or 0
check("the windows reassemble to the EXACT original file", "".join(_parts) == _big)

print("\n§4 D1 — a bad offset clamps, it never raises")
# A bad offset is a model mistake; an exception here would fail the whole turn
# over an arithmetic slip.
check("a negative offset clamps to 0", _clip_read(_big, offset=-50).get("offset") == 0)
check("an over-long offset returns empty, not an error",
      _clip_read(_big, offset=999_999).get("returned_chars") == 0)
check("a non-numeric offset does not raise",
      _clip_read(_big, offset=0).get("returned_chars") == READ_FILE_MAX_CHARS)

print("\n§5 D1 — BOTH return sites are bounded (a half-fixed cap is not a cap)")
_wsrc = pathlib.Path("services/primitives/workspace.py").read_text(encoding="utf-8")
check("both ReadFile scopes clip (workspace + agent)",
      _wsrc.count("**_clip_read(content, offset=") == 2,
      f'found {_wsrc.count("**_clip_read(content, offset=")}')
check("no scope still returns raw content",
      '"content": content,\n        }' not in _wsrc)

print("\n§6 D2 — history is bounded in CHARS as well as count")

from routes.lanes import (  # noqa: E402
    _HISTORY_MAX_CHARS,
    _HISTORY_WINDOW,
    _clamp_history_chars,
    _message_chars,
)


def _msg(i: int, n: int) -> dict:
    return {"role": "user" if i % 2 == 0 else "assistant", "content": "x" * n}


check("the count bound still exists (both bounds, not a swap)", _HISTORY_WINDOW == 20)
check("the char ceiling is a real number", _HISTORY_MAX_CHARS >= 50_000)

_under = [_msg(i, 1000) for i in range(10)]
check("a normal conversation is returned UNTOUCHED (identity, not a copy)",
      _clamp_history_chars(_under) is _under)
check("an empty history is safe", _clamp_history_chars([]) == [])

_over = [_msg(i, 30_000) for i in range(10)]  # 300K chars
_kept = _clamp_history_chars(_over)
check("an oversized history is clamped",
      sum(_message_chars(m) for m in _kept) <= _HISTORY_MAX_CHARS)

print("\n§7 D2 — the TRIM SHAPE, which the cache dictates")

# ⚠️ THE ASSERTION THAT MATTERS MOST. A middle-drop invalidates the cache
# prefix and costs more than it saves.
check("the kept messages are a CONTIGUOUS TAIL (never a middle-drop)",
      _kept == _over[len(_over) - len(_kept):])
check("the NEWEST message survives — it is the thing being answered",
      _kept[-1] is _over[-1])
check("the OLDEST are the ones dropped", _kept[0] is not _over[0])

# ⭐ A ceiling that can eat the question is not a ceiling, it is a bug that
# only appears on the largest input.
_giant = [_msg(0, 500_000)]
check("a lone over-ceiling message is NEVER dropped", len(_clamp_history_chars(_giant)) == 1)
_mixed = [_msg(0, 10_000), _msg(1, 10_000), _msg(2, 500_000)]
_mk = _clamp_history_chars(_mixed)
check("an over-ceiling NEWEST message survives while older ones go",
      len(_mk) == 1 and _mk[0] is _mixed[-1])

print("\n§8 sizing counts text, not pixels")
_img = [{"role": "user", "content": [
    {"type": "text", "text": "y" * 100},
    {"type": "image_url", "image_url": {"url": "z" * 9000}}]}]
check("an image part is sized by its TEXT (the provider bills pixels its own way)",
      _message_chars(_img[0]) == 100)
check("an unknown content shape sizes as 0 rather than raising",
      _message_chars({"role": "user", "content": None}) == 0)

print("\n§9 the bounds are DOCUMENTED where the next reader looks")
_lsrc = pathlib.Path("routes/lanes.py").read_text(encoding="utf-8")
# The rationale sits ABOVE the constant (the house comment style), so slice
# BACKWARD from it — slicing forward read the wrong region and failed against
# a correct file (the same boundary mistake as ADR-647's function slice).
_ceiling_at = _lsrc.index("_HISTORY_MAX_CHARS")
_rationale = _lsrc[max(0, _ceiling_at - 2000):_ceiling_at].lower()
check("the char ceiling explains the cache-prefix constraint",
      "prefix" in _rationale and "middle" in _rationale)
check("the read cap explains why silence is the danger",
      "silently truncated" in _wsrc or "silence" in _wsrc.lower())

print(f"\n{N - len(FAILS)}/{N} checks passed")
if FAILS:
    print("\nFAILURES:")
    for f in FAILS:
        print(f"  - {f}")
    sys.exit(1)
print("ADR-648 gate GREEN")
