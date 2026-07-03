"""ADR-365 validation — register-follows-consumer A/B on the prompt itself.

ADR-365 added a frame directive ("Write for the operator, not for yourself"):
operator-facing prose must drop internal vocabulary (substrate, aperture/floor,
cadence-drift, "firing on empty substrate"). This probe ISOLATES that one
variable — it does NOT touch a live workspace (no DB, no scheduler, no balance
confounds my notes flag as the source of every intermittent E2E). It composes
the REAL system prompt (frame + cockpit) and a realistic EMPTY-WORKSPACE wake
envelope (the screenshot scenario: early author workspace, empty corpus,
recurrences firing on nothing), then calls the model TWICE:

  ARM A (treatment): the live frame, D2 directive present.
  ARM B (control):   the same frame with the D2 block stripped out.

Same model, same context, one variable. Each output is the agent's actual
operator-facing prose (the verdict reasoning + any standing_intent it writes).
A mechanical jargon-scan counts internal-vocabulary hits in each arm's prose.

PASS signal: ARM A has materially FEWER jargon hits than ARM B (the directive
             changed the register). Both arms still produce a coherent verdict
             (the directive didn't break judgment).
INCONCLUSIVE: similar hit counts (directive not load-bearing at this model tier
             — a real finding, would mean ADR-365 needs sharpening).

Usage:
  cd /Users/macbook/yarnnn && api/venv/bin/python -m api.scripts.operator.probe_adr365_register_ab_local
"""

from __future__ import annotations

import asyncio
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

# Internal vocabulary the operator should NOT have to parse (ADR-365 targets).
# SPLIT into two classes (the v1 scanner conflated them, producing noise):
#
#   PURE — canon-internal plumbing words with NO operator-legible meaning. An
#   operator never needs "substrate" / "recurrence" / "wake envelope". These are
#   the unambiguous ADR-365 targets.
#
#   MIXED — words that ARE part of the agent's legitimate forward reasoning
#   (ADR-365 §D5: internal reasoning keeps its vocabulary). "floor"/"aperture"
#   are program concepts the agent reasons WITH; in a standing_intent (a
#   forward-reasoning surface read by BOTH operator and next-wake agent) they
#   are arguably fine. Counting them as jargon was the v1 confound. Tracked
#   separately, NOT summed into the pass/fail signal.
JARGON_PURE = [
    "substrate", "cadence-drift", "cadence drift", "recurrence", "recurrences",
    "judgment-mode", "judgment mode", "hard-trigger", "hard trigger",
    "wake envelope", "the envelope", "standing_intent", "principles.md",
    "mandate.md", "_voice.md", "_editorial.md", "_entities.md",
    "firing on empty", "no-op", "pre-ship",
]
JARGON_MIXED = [
    "aperture", "floor", "ground-truth", "ground truth", "axiom",
]


def _scan_terms(text: str, terms: list) -> list[tuple[str, int]]:
    low = (text or "").lower()
    hits = []
    for term in terms:
        n = len(re.findall(re.escape(term.lower()), low))
        if n:
            hits.append((term, n))
    return sorted(hits, key=lambda x: -x[1])


def _strip_d2(frame: str) -> str:
    """Remove the ADR-365 D2 block from the frame (the control arm).

    The D2 block is the paragraph that starts with the bolded
    'Write for the operator, not for yourself' header and ends at the next
    bolded header. Strips exactly that paragraph, nothing else.
    """
    pattern = re.compile(
        r"\*\*Write for the operator, not for yourself.*?(?=\n\n\*\*)",
        re.DOTALL,
    )
    stripped = pattern.sub("", frame)
    return stripped


def _build_empty_author_envelope() -> str:
    """A realistic EMPTY-WORKSPACE wake envelope — the screenshot scenario.

    Early alpha-author workspace: full framework in place (voice/editorial/
    entity/MANDATE/principles authored) but ZERO corpus pieces. A judgment-mode
    recurrence (corpus-coherence-check) just fired and found nothing to audit.
    This is exactly the state that produced the jargon-heavy standing_intent in
    the screenshot. The envelope mirrors what _build_user_message assembles, in
    the labeled-header shape the frame expects.
    """
    return """\
## Wake context

You were woken by a judgment-mode recurrence firing: `corpus-coherence-check`
(scheduled daily). Its prompt: "Audit the published corpus for coherence
against the voice and editorial principles; flag any drift."

## MANDATE — why this operation exists

Publish a recurring essay series in the author's voice. The floor: no slop, no
unverified claims, every piece on-thesis. Expected output: ~2 essays/month.

## principles.md — Your framework

(Rules of judgment for corpus coherence, voice-fingerprint match, anti-slop,
citation-verifiability. Full rules omitted here for the probe.)

## IDENTITY — who you are

A meticulous editor with the author's voice. Skeptical, independent, plain.

## Workspace state

- Framework: complete (voice, editorial, entity, MANDATE, principles authored).
- Corpus: ZERO pieces published or in-draft. `/workspace/operation/authored/`
  holds only metadata files (_voice.md, _editorial.md, _entities.md) — no
  content pieces.
- Recent recurrence fires: corpus-coherence-check (4 fires, 4 no-ops — nothing
  to audit), outcome-reconciliation (14 fires, 14 no-ops — no outcomes yet).

## What you were watching for last cycle (standing_intent.md)

(empty — first substantive cycle)

---

Everything you need is in this message — all governing files are inline above.
Do NOT call ReadFile/ListFiles; act on what is present here. This cycle:
(1) Write your forward intent to `/workspace/persona/standing_intent.md` via
    WriteFile — what you're watching for and why, given the current state.
(2) Then call ReturnVerdict to close (verdict + reasoning + confidence).
"""


async def _run_arm(arm: str, system_prompt_blocks: list, user_msg: str) -> dict:
    """One model call. Returns the agent's text + tool calls (the prose to judge)."""
    from services.anthropic import chat_completion_with_tools
    from agents.freddie_agent import RETURN_VERDICT_TOOL
    from services.model_routing import DEFAULT_ROUTES, SHAPE_ADDRESSED, SHAPE_PROPOSAL

    # Minimal tool surface for the probe: just ReturnVerdict + WriteFile, so the
    # agent can close with a verdict and optionally write standing_intent — the
    # two operator-facing prose surfaces ADR-365 governs.
    write_file_tool = {
        "name": "WriteFile",
        "description": "Write a file to the workspace (path + content).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    }

    # tool_choice=any forces a tool call THIS turn — no open-ended ReadFile
    # exploration the single-turn probe can't service. Combined with the
    # envelope's "everything is inline, do not call ReadFile", this lands the
    # agent directly on its operator-facing output (ReturnVerdict +
    # standing_intent), which is the prose ADR-365 governs.
    response = await chat_completion_with_tools(
        model=DEFAULT_ROUTES[SHAPE_ADDRESSED].model,
        system=system_prompt_blocks,
        messages=[{"role": "user", "content": user_msg}],
        tools=[RETURN_VERDICT_TOOL, write_file_tool],
        max_tokens=2000,
        tool_choice={"type": "any"},
    )

    # Extract operator-facing prose: ReturnVerdict.reasoning + any WriteFile
    # content addressed at standing_intent/reflection (operator-readable files).
    prose_parts = []
    tool_calls = []
    if (response.text or "").strip():
        prose_parts.append(("text", response.text))
    for tu in (response.tool_uses or []):
        name = tu.name
        inp = tu.input or {}
        tool_calls.append(name)
        if name == "ReturnVerdict":
            prose_parts.append(("verdict.reasoning", inp.get("reasoning", "")))
        elif name == "WriteFile":
            prose_parts.append((f"WriteFile {inp.get('path','?')}", inp.get("content", "")))

    # Separate the two surfaces: the verdict HEADLINE is purely operator-facing
    # (ADR-365's cleanest target); standing_intent is mixed (forward reasoning).
    headline = " ".join(t for l, t in prose_parts if l == "verdict.reasoning")
    si = " ".join(t for l, t in prose_parts if l.startswith("WriteFile"))
    full_prose = "\n\n".join(p[1] for p in prose_parts)

    def _rate(txt: str, terms: list) -> float:
        n = sum(c for _, c in _scan_terms(txt, terms))
        return round(1000.0 * n / max(len(txt), 1), 2)

    return {
        "arm": arm,
        "tool_calls": tool_calls,
        "prose_parts": prose_parts,
        "full_prose": full_prose,
        "prose_len": len(full_prose),
        # headline = pure operator surface
        "headline_len": len(headline),
        "headline_pure": _scan_terms(headline, JARGON_PURE),
        "headline_pure_rate": _rate(headline, JARGON_PURE),
        # standing_intent = mixed surface
        "si_len": len(si),
        "si_pure": _scan_terms(si, JARGON_PURE),
        "si_pure_rate": _rate(si, JARGON_PURE),
        "si_mixed": _scan_terms(si, JARGON_MIXED),
        # overall pure-jargon rate per 1000 chars (length-normalized)
        "pure_rate": _rate(full_prose, JARGON_PURE),
        "pure_total": sum(c for _, c in _scan_terms(full_prose, JARGON_PURE)),
    }


async def main() -> int:
    from agents.freddie_agent import _compute_minimal_frame
    from agents.cockpit_awareness import build_cockpit_section

    live_frame = _compute_minimal_frame()
    stripped_frame = _strip_d2(live_frame)

    # sanity: confirm the strip actually removed the D2 block
    d2_present_A = "Write for the operator" in live_frame
    d2_present_B = "Write for the operator" in stripped_frame
    print(f"[adr365-ab] D2 in ARM A (treatment): {d2_present_A}  |  D2 in ARM B (control): {d2_present_B}")
    if not d2_present_A or d2_present_B:
        print("[adr365-ab] FATAL: arm setup wrong — D2 must be present in A, absent in B.")
        return 2
    print(f"[adr365-ab] frame chars: A={len(live_frame)}  B={len(stripped_frame)}  (delta={len(live_frame)-len(stripped_frame)})")

    cockpit = build_cockpit_section()
    system_A = [{"type": "text", "text": live_frame + "\n\n" + cockpit}]
    system_B = [{"type": "text", "text": stripped_frame + "\n\n" + cockpit}]
    user_msg = _build_empty_author_envelope()

    # N trials per arm — single-sample LLM prose is noisy; the v1 run flipped on
    # one draw. Average the length-normalized PURE-jargon rate across trials.
    TRIALS = 4
    print(f"\n[adr365-ab] firing {TRIALS} trials/arm (D2 present vs stripped), same envelope...\n")
    tasks = []
    for i in range(TRIALS):
        tasks.append(_run_arm(f"A.{i}", system_A, user_msg))
        tasks.append(_run_arm(f"B.{i}", system_B, user_msg))
    results = await asyncio.gather(*tasks)
    arms_a = [r for r in results if r["arm"].startswith("A")]
    arms_b = [r for r in results if r["arm"].startswith("B")]

    def _avg(rs, key):
        return round(sum(r[key] for r in rs) / max(len(rs), 1), 2)

    # Print ONE representative sample per arm (the first trial) for qualitative read.
    for label, sample in (("A (D2 present)", arms_a[0]), ("B (D2 stripped)", arms_b[0])):
        print("=" * 72)
        print(f"ARM {label} — representative sample (trial 0)")
        print(f"  headline pure-jargon: {sample['headline_pure']}  rate={sample['headline_pure_rate']}/k")
        print(f"  standing_intent pure: {sample['si_pure']}  rate={sample['si_pure_rate']}/k  mixed={sample['si_mixed']}")
        for plabel, txt in sample["prose_parts"]:
            print(f"  [{plabel}]")
            for line in (txt or "").splitlines():
                print(f"    {line}")
        print()

    print("=" * 72)
    print(f"AGGREGATE over {TRIALS} trials/arm (length-normalized PURE-jargon rate per 1000 chars):")
    a_overall, b_overall = _avg(arms_a, "pure_rate"), _avg(arms_b, "pure_rate")
    a_head, b_head = _avg(arms_a, "headline_pure_rate"), _avg(arms_b, "headline_pure_rate")
    a_si, b_si = _avg(arms_a, "si_pure_rate"), _avg(arms_b, "si_pure_rate")
    print(f"  overall pure-rate:        A(D2 on)={a_overall}   B(D2 off)={b_overall}")
    print(f"  headline pure-rate:       A(D2 on)={a_head}   B(D2 off)={b_head}")
    print(f"  standing_intent pure-rate:A(D2 on)={a_si}   B(D2 off)={b_si}")
    print(f"  (raw pure totals: A avg={_avg(arms_a,'pure_total')}  B avg={_avg(arms_b,'pure_total')};  "
          f"prose len A avg={_avg(arms_a,'prose_len')}  B avg={_avg(arms_b,'prose_len')})")

    print("=" * 72)
    # The pass signal: D2 should LOWER the pure-jargon rate. Use a ≥15% relative
    # threshold to call it load-bearing (below that = noise at this sample size).
    if b_overall > 0 and a_overall <= b_overall * 0.85:
        print(f"✅ PASS — D2 lowered pure-jargon rate {b_overall}→{a_overall}/k "
              f"({round(100*(b_overall-a_overall)/b_overall)}% lower). Directive is load-bearing.")
        return 0
    if abs(a_overall - b_overall) <= max(b_overall * 0.15, 0.3):
        print(f"➖ INCONCLUSIVE — rates within noise (A={a_overall} vs B={b_overall}/k). "
              f"D2 is NOT measurably moving operator-facing register at this tier. "
              f"FINDING: the directive as written needs sharpening (concrete bad→good "
              f"examples, or a stronger imperative), OR the lever is the hard-coded "
              f"narration strings (D3, already plain) not the model's free prose.")
        return 1
    print(f"❌ COUNTER — D2 arm had HIGHER pure-jargon rate (A={a_overall} > B={b_overall}/k). "
          f"FINDING: 'write thoroughly for the operator' may license MORE explanation, "
          f"dragging in more canon. ADR-365 D2 should be re-worded toward SUPPRESSION "
          f"('name the thing, don't explain the mechanism'), not thoroughness.")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
