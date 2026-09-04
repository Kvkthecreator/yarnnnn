"""ADR-637 §7 — the A/B the gate cannot run.

`test_adr637_register.py` proves the register clause is COMPOSED. It cannot
prove it WORKS. ADR-365's whole lesson is that this distinction is where prompt
work goes wrong: its first directive was ratified, shipped, and then FALSIFIED
by a controlled A/B (2.72 vs 2.60 jargon per 1000 chars — noise).

So this runs the same experiment on the surface that now does the talking:
ARM A = the live lane frame (clause present)
ARM B = the identical frame with the clause stripped

Both arms get the same IMAGES-shaped task — the operator's own screenshot: an
agent that has just moved things on an artboard, reporting back. Scored by
COUNTING the leak markers measured in production, which is deterministic and
needs no judge: raw tool names, `data-*` grammar, block ids, coordinate keys.

⚠️ A count is a proxy. ADR-365 §Eval learned that word-frequency scoring can
miss a real effect (D2 scored as noise on frequency and 365b later scored +49-79%
on an LLM judge over STRUCTURE). So a null result here is NOT proof the clause
does nothing — it is proof the clause does not move THIS metric. Report both.

Run: cd api && python3 scripts/operator/probe_adr637_register_ab.py [trials]
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

API = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(API))

for _line in (API / ".env").read_text().splitlines():
    if _line.strip() and not _line.strip().startswith("#") and "=" in _line:
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

from services.workspace_paths import PARTICIPANT_REGISTER  # noqa: E402

#: The task, shaped exactly like the operator's screenshot: the agent has just
#: finished an artboard pass and is reporting it. The TOOL RESULT deliberately
#: hands it the internal grammar — that is the real condition, and the whole
#: question is whether the clause stops it echoing it back.
TASK = """The member asked you to "fix the hierarchy — the headline is fighting the photo".
You have finished. This is what you changed in the file:

  <h1 data-block="heading" data-block-id="b3" data-y="66" data-z="5"
      style="font-size:108px">  (was data-y="58", font-size:96px)
  <p data-block="prose" data-block-id="b4" data-y="86" data-z="5"
      data-opacity="62">        (was data-y="82", data-opacity="72")
  <div data-block="media" data-block-id="b1" data-z="1">   (unchanged)

You called ReadFile once and EditFile twice. The artboard is 1080x1080.

Reply to the member now."""

FRAME = """You are Designer, working inside a YARNNN workspace as Kevin's hands.
You author one artifact: a stack of layers on an artboard. Blocks carry
data-block="<kind>" and a stable data-block-id; placement rides measures
(data-x/data-y/data-z) and emphasis rides tokens (data-opacity, data-blend).
Patch with EditFile; never rewrite what the member authored.
{register_section}"""

REGISTER_SECTION = f"\n## Talking to Kevin\n{PARTICIPANT_REGISTER}\n"

LEAKS = {
    "tool name": r"\b(EditFile|WriteFile|ReadFile|ListFiles|SearchFiles)\b",
    "data-* grammar": r"data-(block|arrange|area|template|ref|opacity|blend|[xyz])\b",
    "block id": r"\bb\d+\b|data-block-id",
    "coordinate key": r"`?\b[xyz]:\s?\d|\bdata-[xyz]=",
}


def score(text: str) -> dict:
    out = {k: len(re.findall(p, text, re.I)) for k, p in LEAKS.items()}
    out["TOTAL"] = sum(out.values())
    out["words"] = len(text.split())
    return out


async def run(trials: int = 4) -> None:
    from services.model_router import route_completion

    print("=" * 72)
    print("ADR-637 §7 — register A/B (ARM A = clause present, ARM B = stripped)")
    print(f"{trials} trials/arm · leak markers counted, not judged")
    print("=" * 72)

    arms = {
        "A (clause)": FRAME.format(register_section=REGISTER_SECTION),
        "B (stripped)": FRAME.format(register_section=""),
    }
    totals: dict[str, list[dict]] = {a: [] for a in arms}

    for arm, system in arms.items():
        for i in range(trials):
            try:
                resp = await route_completion(
                    model="anthropic/claude-sonnet-5",
                    messages=[{"role": "user", "content": TASK}],
                    system=system,
                    max_tokens=700,
                )
                text = resp.text
            except Exception as exc:  # noqa: BLE001
                print(f"  [{arm}] trial {i+1} FAILED: {exc}")
                continue
            s = score(text)
            totals[arm].append(s)
            print(f"  [{arm}] trial {i+1}: leaks={s['TOTAL']:3}  words={s['words']:4}"
                  f"  ({', '.join(f'{k}={v}' for k, v in s.items() if k not in ('TOTAL','words') and v)})")
            if i == 0:
                print(f"      first 220 chars: {text[:220]!r}")

    print("\n" + "=" * 72)
    for arm, rows in totals.items():
        if not rows:
            print(f"  {arm}: no data")
            continue
        n = len(rows)
        print(f"  {arm}: mean leaks={sum(r['TOTAL'] for r in rows)/n:5.2f}"
              f"  mean words={sum(r['words'] for r in rows)/n:6.1f}"
              f"  clean replies={sum(1 for r in rows if r['TOTAL']==0)}/{n}")
    print("=" * 72)
    print("A null result falsifies the METRIC, not necessarily the clause — see"
          " the docstring and ADR-365's own D2-vs-365b history.")


if __name__ == "__main__":
    import asyncio

    os.environ.setdefault("MODEL_ROUTER_ENABLED", "true")
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 4))
