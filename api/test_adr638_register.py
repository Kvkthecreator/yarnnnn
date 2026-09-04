"""ADR-638 — the agent speaks the member's language, not ours.

WHAT THIS GATE IS FOR
ADR-365 ratified "register follows consumer" and 365b VALIDATED a structural
directive at +49-79% operator readability. It lived in the steward's frame and
died with it (ADR-632); the lane frame that replaced it carried none, so 120
consecutive live replies leaked raw tool names (11), `data-*` grammar (6),
block ids (3) and stage coordinates (1 — the operator's screenshot).

This gate holds the restored clause in place. It asserts the clause is
COMPOSED into every lane frame, that it keeps the shape the A/B validated
(concrete failures, not "write plainly"), and that the two adjacent
precedents — `toolLabels.ts` and the filesystem-model translation — are still
standing, since this rule is meaningless without them.

⚠️ WHAT IT CANNOT ASSERT: that the directive WORKS. Only an A/B can, and
ADR-638 §7 records that as owed. A gate proving composition must never be
read as proving effect.

Run: cd api && python3 test_adr638_register.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

API = Path(__file__).parent
WEB = API.parent / "web"

_passed = 0
_failed = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"  ok   {label}")
    else:
        _failed += 1
        print(f"  FAIL {label}" + (f" — {detail}" if detail else ""))


# ---------------------------------------------------------------------------
# [1] The clause exists, is a participant clause, and is COMPOSED
# ---------------------------------------------------------------------------
def test_clause_is_composed() -> None:
    print("\n[1] the register clause is a participant clause, composed into the frame")
    from services.lane_runner import _CONVENTIONS_FRAME
    from services.workspace_paths import PARTICIPANT_REGISTER

    check("PARTICIPANT_REGISTER is non-empty", bool(PARTICIPANT_REGISTER.strip()))
    # Its home is beside the siblings it belongs with (ADR-533 D1) — a clause
    # authored in `lane_runner` would be unreachable by any second surface.
    wp = (API / "services" / "workspace_paths.py").read_text()
    check(
        "authored in workspace_paths beside the other participant clauses",
        "PARTICIPANT_REGISTER = " in wp,
    )
    check(
        "the frame reserves a slot for it",
        "{register}" in _CONVENTIONS_FRAME,
        "a clause that exists but is never composed is a comment",
    )
    lr = (API / "services" / "lane_runner.py").read_text()
    check(
        "…and the slot is actually filled at composition",
        "register=PARTICIPANT_REGISTER" in lr,
    )


# ---------------------------------------------------------------------------
# [2] The clause reaches a REAL composed frame (not just the template)
# ---------------------------------------------------------------------------
def test_clause_reaches_the_composed_frame() -> None:
    print("\n[2] the clause survives into the composed text an agent actually reads")
    from services.lane_runner import _CONVENTIONS_FRAME
    from services.workspace_paths import PARTICIPANT_REGISTER

    # Render the scaffold the way composition does, with every other slot blank.
    slots = set(re.findall(r"\{([a-z_]+)\}", _CONVENTIONS_FRAME))
    filled = _CONVENTIONS_FRAME.format(
        **{s: (PARTICIPANT_REGISTER if s == "register" else "") for s in slots}
    )
    check("the composed frame carries the clause verbatim", PARTICIPANT_REGISTER in filled)
    check(
        "…under a heading that names the reader",
        re.search(r"##\s+Talking to", filled) is not None,
        "an unlabelled clause reads as one more rule about files",
    )


# ---------------------------------------------------------------------------
# [3] The SHAPE the A/B validated — concrete failures, not "write plainly"
# ---------------------------------------------------------------------------
def test_clause_keeps_the_validated_shape() -> None:
    print("\n[3] the clause names concrete failures (the falsified arm must not return)")
    from services.workspace_paths import PARTICIPANT_REGISTER

    t = PARTICIPANT_REGISTER
    # ADR-365's FIRST attempt was a vague directive and a controlled A/B
    # falsified it (2.72 vs 2.60 jargon/1k — noise). 365b's win came from
    # naming the bad->good failure per rule. These assertions pin THAT shape.
    check(
        "it shows a concrete bad example, not just an instruction",
        "never" in t.lower() and ("y:" in t or "z:" in t),
        "a rule without its failure is the arm that was measured not to work",
    )
    check(
        "it names the leaking vocabularies explicitly",
        all(w in t for w in ("data-block", "ReadFile")),
        "the leak measured in production was tool names + data-* grammar",
    )
    check(
        "it forbids the leak in the REPLY while allowing it in the FILE",
        "in the file" in t and "in the reply" in t,
        "ADR-365 D5 — a forward-reasoning surface stays free; only the address "
        "is constrained. A rule that banned the grammar outright would break "
        "authoring itself.",
    )
    check(
        "it carries the lead-with-the-result rule (the Claude Code Concise lever)",
        "Lead with" in t,
    )
    check(
        "…and refuses narration preamble (measured: a plan concatenated with its own result)",
        "narration" in t.lower() or "about to do" in t,
    )
    check(
        "it names the member's nouns",
        sum(w in t for w in ("slides", "pages", "layers", "images", "posts")) >= 4,
    )
    # Anti-vagueness ratchet: the failure mode is a future edit softening this
    # into a platitude. A platitude has no examples and no forbidden terms.
    check(
        "the clause is not a platitude (it would fail every check above at once)",
        len(t) > 300,
        f"{len(t)} chars — too short to carry the examples the A/B needed",
    )


# ---------------------------------------------------------------------------
# [4] The frame stays ablated (DP22 / ADR-306) — a clause is not a licence
# ---------------------------------------------------------------------------
def test_frame_stays_under_its_ceiling() -> None:
    print("\n[4] the frame is ablated, not accreted (DP22)")
    from services.lane_runner import _CONVENTIONS_FRAME
    from services.workspace_paths import PARTICIPANT_REGISTER

    scaffold = re.sub(r"\{[a-z_]+\}", "", _CONVENTIONS_FRAME)
    # The SAME ceiling test_adr632 §5 holds. Asserted here too because this ADR
    # is the one that adds text: a ceiling checked only in another file is one
    # this change could quietly blow.
    check(
        f"conventions scaffold still under 900 ({len(scaffold)})",
        len(scaffold) <= 900,
        "ADR-306: raising a ceiling needs the same evidence as adding an "
        "instruction, named in the raising commit",
    )
    check(
        f"the clause itself is frame-sized, not pedagogy ({len(PARTICIPANT_REGISTER)} chars)",
        len(PARTICIPANT_REGISTER) <= 1200,
        "ADR-365 §3.1 — the frame carries the CONTRACT; worked exposition "
        "belongs in bundle guidance, not here",
    )


# ---------------------------------------------------------------------------
# [5] The two precedents this rule depends on are still standing
# ---------------------------------------------------------------------------
def test_the_adjacent_translations_hold() -> None:
    print("\n[5] the tool-name and path translations still stand")
    labels = (WEB / "components" / "chat-surface" / "toolLabels.ts").read_text()
    check("toolLabels still translates the file verbs", "ReadFile" in labels and "read a file" in labels)
    check(
        "…and still refuses 'your computer' for the workspace",
        "your workspace" in labels,
        "the place is the commons; 'on your computer' is a marketing-honesty "
        "defect in the transcript itself",
    )
    from services.workspace_paths import PARTICIPANT_FILESYSTEM_MODEL

    check(
        "the filesystem model still TELLS the member's names",
        "Documents" in PARTICIPANT_FILESYSTEM_MODEL
        and "Downloads" in PARTICIPANT_FILESYSTEM_MODEL,
    )
    check(
        "…and does not leak the kernel's own roots to the reader",
        "operation/" not in PARTICIPANT_FILESYSTEM_MODEL,
        "the substrate says operation/; the member is told Documents",
    )


# ---------------------------------------------------------------------------
# [6] D2 — lanes only; the connector's host owns its own voice
# ---------------------------------------------------------------------------
def test_connector_does_not_carry_it() -> None:
    print("\n[6] the connector composes mechanics, not our conversational register")
    srv = (API / "mcp_server" / "server.py").read_text()
    check(
        "the connector still composes the workspace-mechanics clauses",
        "PARTICIPANT_FILESYSTEM_MODEL" in srv and "PARTICIPANT_FORMAT_DISCIPLINE" in srv,
    )
    check(
        "…and does NOT carry the register clause (ADR-638 D2)",
        "PARTICIPANT_REGISTER" not in srv,
        "that reader sits in someone else's client, whose host owns its voice; "
        "shipping ours would be yarnnn dictating tone to Claude Desktop",
    )


if __name__ == "__main__":
    print("=" * 70)
    print("ADR-638 — the agent speaks the member's language, not ours")
    print("=" * 70)
    test_clause_is_composed()
    test_clause_reaches_the_composed_frame()
    test_clause_keeps_the_validated_shape()
    test_frame_stays_under_its_ceiling()
    test_the_adjacent_translations_hold()
    test_connector_does_not_carry_it()
    print("\n" + "=" * 70)
    print(f"  {_passed} passed, {_failed} failed")
    print("=" * 70)
    sys.exit(1 if _failed else 0)
