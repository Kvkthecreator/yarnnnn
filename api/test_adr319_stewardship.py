"""Regression gate — ADR-319 Stewardship of Intent against Ground Truth (2026-06-05).

Sustainability mechanism for FOUNDATIONS Derived Principle 24: every ACTIVE
program's reviewer substrate must declare the ownership posture (not the old
defensive faithful-executor framing), and the R&R partition must hold (the
posture's rules live in principles.md per agent-composition §3.2.1 — NOT
duplicated into the persona-frame or MANDATE, which would recreate the dual-
context divergence the §3.2.2 composed-coherence finding warned about).

This is the "not one-off" property the operator asked for: a future program
that ships a reviewer principles.md MUST carry the Stewardship posture, or this
gate goes red — the audit is mechanical, not a per-program prose re-read.

Run: .venv/bin/python api/test_adr319_stewardship.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROGRAMS = REPO / "docs" / "programs"

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")


def _manifest_status(slug: str) -> str:
    m = PROGRAMS / slug / "MANIFEST.yaml"
    if not m.exists():
        return "absent"
    for line in m.read_text().splitlines():
        if line.startswith("status:"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def _active_programs() -> list[str]:
    return [
        p.name for p in PROGRAMS.iterdir()
        if p.is_dir() and _manifest_status(p.name) == "active"
    ]


active = _active_programs()
check("at least one active program exists", len(active) > 0, str(active))
print(f"  (active programs: {', '.join(active)})\n")

# The DP24 posture markers a conforming principles.md §Stewardship must carry.
# Program-agnostic: each program names its own ground-truth flavor, but the
# OWNERSHIP + TWO-ALTITUDE + GROUND-TRUTH-NOT-PRESSURE invariant is universal.
OWNERSHIP_MARKERS = ["own", "two altitude"]              # ownership, not delegation
PRESSURE_MARKER = "pressure never"                        # the safety invariant
ADR_CITE = "319"                                          # cites the canon

for slug in active:
    # ADR-320 topological cut moved review/ → persona/ (the seat's reasoning files).
    principles = PROGRAMS / slug / "reference-workspace" / "persona" / "principles.md"
    check(f"[{slug}] principles.md exists", principles.exists(), str(principles))
    if not principles.exists():
        continue
    text = principles.read_text()
    low = text.lower()

    # (1) The Stewardship posture is present (header renamed from the old
    #     defensive "Self-Improvement Posture" — singular implementation).
    check(
        f"[{slug}] declares Stewardship posture (not the old 'Self-Improvement Posture')",
        "stewardship" in low and "## self-improvement posture" not in low,
        "found old 'Self-Improvement Posture' header" if "## self-improvement posture" in low else "no 'stewardship' marker",
    )

    # (2) Ownership framing (not delegate/faithful-executor).
    check(
        f"[{slug}] carries ownership framing (owns + two altitudes)",
        all(m in low for m in OWNERSHIP_MARKERS),
        f"missing one of {OWNERSHIP_MARKERS}",
    )

    # (3) The ground-truth-not-pressure invariant (the safety spine).
    check(
        f"[{slug}] declares the ground-truth-not-pressure invariant",
        PRESSURE_MARKER in low,
        f"missing '{PRESSURE_MARKER}'",
    )

    # (4) Cites the canon (ADR-319 / DP24).
    check(
        f"[{slug}] cites ADR-319 / Derived Principle 24",
        ADR_CITE in text,
        "no ADR-319 citation",
    )

    # (5) The old defensive markers are GONE (posture inverted, not appended).
    #     "epistemic deference" + "bulldoze" were the defensive framing.
    check(
        f"[{slug}] old defensive framing removed (no 'epistemic deference' / 'bulldoze')",
        "epistemic deference" not in low and "bulldoze" not in low,
        "stale defensive framing still present",
    )

    # (6) R&R partition — thresholds stay INLINE in principles.md (ADR-305:
    #     the LLM is their consumer), not hoisted into a dead yaml block.
    #     We assert the evidence-pattern thresholds are still here (the rules
    #     of judgment live in this one home, not split into a parallel surface).
    check(
        f"[{slug}] evidence thresholds remain inline (rules-of-judgment single home)",
        "evidence" in low and ("threshold" in low or "pattern" in low),
        "evidence/threshold language missing — may have been wrongly hoisted",
    )

# (7) R&R no-duplication — the persona-frame must NOT carry the stewardship
#     rules (DP22 minimal frame: principal-shift + action-grammar only).
#     Duplication here is the dual-context trap that produced divergent behavior.
frame = REPO / "api" / "agents" / "freddie_agent.py"
if frame.exists():
    ftext = frame.read_text().lower()
    check(
        "persona-frame does NOT duplicate the stewardship rules (DP22 minimal frame)",
        "stewardship of expectancy" not in ftext and "ground truth moves the mandate" not in ftext,
        "persona-frame carries stewardship prose — R&R violation (belongs in principles.md)",
    )

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
