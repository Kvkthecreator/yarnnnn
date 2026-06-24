"""ADR-365b validation — does a STRUCTURE directive make the Reviewer's
composed documents read like a human wrote them?

The first ADR-365 attempt (probe_adr365_register_ab_local.py) tested a vague
"write plainly" directive and scored JARGON WORD-FREQUENCY — the wrong proxy.
It found the directive inert. But the real problem (the operator's screenshot)
is STRUCTURAL: the Reviewer's standing_intent/judgment_log lead with process
("I read the workspace state…"), backtrack semantically ("firing and failing
predictably on empty substrate"), and drop raw codenames (corpus-coherence-
check, cadence-drift). CC's communication canon optimizes exactly those:
inverted pyramid, expand codenames, flowing prose.

This probe (a) tests a SHARPER directive — concrete bad→good examples targeting
STRUCTURE, not a vague "be plain" — and (b) scores the RIGHT things via an LLM
JUDGE (a regex can't tell "leads with the takeaway"). Same isolation discipline
as before: no live workspace, one variable (the directive present vs absent),
same empty-author wake envelope, multiple trials.

  ARM A (treatment): the structure directive present in the frame.
  ARM B (control):   the same frame, directive absent.

Each arm composes a real standing_intent. An LLM judge scores both on three
CC dimensions (0-10 each): leads-with-takeaway, codenames-expanded, flowing-
prose. PASS if ARM A scores materially higher (the directive moves structure).

Usage:
  cd /Users/macbook/yarnnn && api/venv/bin/python -m api.scripts.operator.probe_adr365b_composed_prose_ab_local
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_API_ROOT = _THIS_DIR.parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))
REPO_ROOT = _THIS_DIR.parents[2]

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_API_ROOT / ".env")
load_dotenv(_API_ROOT / ".env.alpha-ops")


# The candidate directive — STRUCTURE-targeted, with concrete bad→good examples
# (the vague version lacked these). This is what would land in _compute_minimal_frame
# if the probe validates it.
STRUCTURE_DIRECTIVE = """

**The documents you write are read by the operator — write them so a person who
never read your files can pick them up cold.** Three rules, with the failure each
fixes:
- Lead with the takeaway, not your process. NOT "I read the workspace state: 36
  days post-bootstrap, full framework, zero corpus" → "There's nothing to review
  yet — no pieces written, everything set up and ready."
- Expand or drop codenames. The operator doesn't know `corpus-coherence-check` or
  `cadence-drift` → "the scheduled checks run on time but have nothing to look at."
- Flowing sentences read once. NOT "recurrences firing and failing on empty
  substrate" → "the checks run on schedule but have nothing to review yet."
Your reasoning keeps its vocabulary; the documents you leave the operator do not."""


# The empty-author wake envelope — the screenshot scenario.
def _envelope() -> str:
    return """\
## Wake context

A scheduled check just ran: `corpus-coherence-check` (daily). Its prompt:
"Audit the published corpus for coherence against the voice and editorial
principles; flag any drift."

## MANDATE — why this operation exists

Publish a recurring essay series in the author's voice. The floor: no slop, no
unverified claims, every piece on-thesis. Expected output: ~2 essays/month.

## principles.md — Your framework

(Rules of judgment for corpus coherence, voice match, anti-slop, citation
verifiability. Omitted here for the probe.)

## IDENTITY — who you are

A meticulous editor with the author's voice. Skeptical, independent, plain.

## Workspace state

- Framework: complete (voice, editorial, entity, MANDATE, principles authored).
- Corpus: ZERO pieces published or in-draft.
- Recent scheduled-check fires: corpus-coherence-check (4 fires, 4 no-ops —
  nothing to audit), outcome-reconciliation (14 fires, 14 no-ops).

## What you were watching for last cycle (standing_intent.md)

(empty — first substantive cycle)

---

Everything you need is inline above. Do NOT call ReadFile. This cycle, write
your forward intent to `/workspace/persona/standing_intent.md` via WriteFile —
what you're watching for and why, given the current state — then call
ReturnVerdict to close.
"""


async def _compose(arm: str, system_text: str) -> dict:
    """One model call → the composed standing_intent text."""
    from services.anthropic import chat_completion_with_tools
    from agents.reviewer_agent import RETURN_VERDICT_TOOL, _HAIKU

    write_tool = {
        "name": "WriteFile",
        "description": "Write a file to the workspace (path + content).",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    }
    resp = await chat_completion_with_tools(
        model=_HAIKU,
        system=[{"type": "text", "text": system_text}],
        messages=[{"role": "user", "content": _envelope()}],
        tools=[RETURN_VERDICT_TOOL, write_tool],
        max_tokens=1500,
        tool_choice={"type": "any"},
    )
    si = ""
    for tu in (resp.tool_uses or []):
        if tu.name == "WriteFile":
            si = (tu.input or {}).get("content", "")
            break
    return {"arm": arm, "standing_intent": si}


JUDGE_PROMPT = """You are scoring how READABLE a document is for a non-technical \
business operator who has NOT read the system's internal docs. Score the document \
on three dimensions, each 0-10 (10 = best):

1. leads_with_takeaway: Does the FIRST sentence tell the operator what it MEANS \
for them (e.g. "there's nothing to review yet"), rather than narrating the \
agent's process ("I read the workspace state…") or starting with mechanism?

2. codenames_expanded: Are internal codenames/jargon (corpus-coherence-check, \
cadence-drift, recurrence, substrate, the pre-ship hook, principles.md) either \
AVOIDED or EXPANDED into plain words? 10 = no raw codenames a layperson couldn't \
parse; 0 = dense with unexplained internal terms.

3. flowing_prose: Does it read in flowing, linear sentences a person reads ONCE \
without re-parsing — versus notation-dense, fragmented, or semantically \
backtracking ("firing and failing predictably on empty substrate")?

Return ONLY a JSON object: {"leads_with_takeaway": N, "codenames_expanded": N, \
"flowing_prose": N, "one_line_why": "…"}

Document to score:
---
%s
---"""


async def _judge(text: str) -> dict:
    from services.anthropic import chat_completion_with_tools
    from agents.reviewer_agent import _SONNET  # stronger model judges

    resp = await chat_completion_with_tools(
        model=_SONNET,
        system="You are a precise document-readability judge. Output only JSON.",
        messages=[{"role": "user", "content": JUDGE_PROMPT % (text[:2500] or "(empty)")}],
        tools=[],
        max_tokens=400,
    )
    raw = (resp.text or "").strip()
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return {"leads_with_takeaway": 0, "codenames_expanded": 0, "flowing_prose": 0, "one_line_why": "judge-parse-failed"}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {"leads_with_takeaway": 0, "codenames_expanded": 0, "flowing_prose": 0, "one_line_why": "judge-json-failed"}


async def main() -> int:
    from agents.reviewer_agent import _compute_minimal_frame
    from agents.cockpit_awareness import build_cockpit_section

    base = _compute_minimal_frame() + "\n\n" + build_cockpit_section()
    system_A = base + STRUCTURE_DIRECTIVE   # treatment
    system_B = base                          # control

    TRIALS = 4
    print(f"[adr365b] composing {TRIALS} trials/arm (structure directive present vs absent)…\n")
    compose_tasks = []
    for i in range(TRIALS):
        compose_tasks.append(_compose(f"A.{i}", system_A))
        compose_tasks.append(_compose(f"B.{i}", system_B))
    composed = await asyncio.gather(*compose_tasks)

    # Judge each composed document.
    judged = await asyncio.gather(*[_judge(c["standing_intent"]) for c in composed])
    for c, j in zip(composed, judged):
        c["score"] = j

    arms_a = [c for c in composed if c["arm"].startswith("A")]
    arms_b = [c for c in composed if c["arm"].startswith("B")]

    def _avg(rs, dim):
        vals = [r["score"].get(dim, 0) for r in rs]
        return round(sum(vals) / max(len(vals), 1), 2)

    # Show one representative sample per arm.
    for label, sample in (("A (directive ON)", arms_a[0]), ("B (directive OFF)", arms_b[0])):
        print("=" * 72)
        print(f"ARM {label} — sample standing_intent + score {sample['score']}")
        for line in (sample["standing_intent"] or "(empty)").splitlines():
            print(f"   {line}")
        print()

    print("=" * 72)
    dims = ["leads_with_takeaway", "codenames_expanded", "flowing_prose"]
    a_tot = b_tot = 0.0
    for d in dims:
        a, b = _avg(arms_a, d), _avg(arms_b, d)
        a_tot += a; b_tot += b
        print(f"  {d:22s}  A(on)={a:5.2f}   B(off)={b:5.2f}   Δ={a-b:+.2f}")
    a_tot, b_tot = round(a_tot, 2), round(b_tot, 2)
    print(f"  {'TOTAL (max 30)':22s}  A(on)={a_tot:5.2f}   B(off)={b_tot:5.2f}   Δ={a_tot-b_tot:+.2f}")

    print("=" * 72)
    if b_tot > 0 and a_tot >= b_tot * 1.20:
        print(f"✅ PASS — the structure directive raised readability {b_tot}→{a_tot}/30 "
              f"(+{round(100*(a_tot-b_tot)/b_tot)}%). Worth shipping (operator-first).")
        return 0
    if a_tot - b_tot >= 3.0:
        print(f"✅ PASS (absolute) — directive added {a_tot-b_tot:+.1f} points on a 30-scale. Ship it.")
        return 0
    if abs(a_tot - b_tot) < 2.0:
        print(f"➖ INCONCLUSIVE — within noise (A={a_tot} vs B={b_tot}). Even a STRUCTURE "
              f"directive with examples doesn't move composed prose at this tier. The lever "
              f"is likely a post-compose plain-English PROJECTION (ADR-340 'compose few'), "
              f"not a frame directive — a separate, larger change.")
        return 1
    print(f"❌ COUNTER — directive made it worse (A={a_tot} < B={b_tot}). Inspect samples.")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
