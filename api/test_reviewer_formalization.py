"""Regression gate — Reviewer formalization (Variant F / FOUNDATIONS DP21).

The Reviewer's framing across code, prompts, and canon must align with
the canonical formalization sentence (FOUNDATIONS Derived Principle 21):

    The Reviewer is a full-substrate-authoring persona-bearing judgment
    seat — filesystem-native, single-lane queue-serialized, wake-fired,
    paced by operator-declared pace + autonomy, driven by operator-
    authored mandate.

This gate fails CI when a future commit drifts away from any of the
seven structural claims by:

  (a) introducing banned pre-cutover framing into the persona frame
      ("continuously running", "self-invoke", "background process",
      "self-pacing process")
  (b) removing the canonical formalization anchor from the persona frame,
      FOUNDATIONS, or GLOSSARY
  (c) adding FireInvocation back into REVIEWER_PRIMITIVES (violates
      ADR-296 v2 D3 — Reviewer does not self-invoke)
  (d) removing ManageHook or Schedule from REVIEWER_PRIMITIVES (violates
      Trigger-authoring authority per Derived Principle 18)
  (e) shrinking or expanding DEFAULT_REVIEWER_WRITE_LOCKS beyond the
      operator-control trifecta (Pace + Autonomy + token budget +
      preferences)
  (f) shipping a judgment-mode hook or recurrence prompt in
      alpha-{author,trader} bundles that does not bind verdict-emission
      structurally to ReturnVerdict (regression-source for the canary v3
      text-only-fallback symptom)

Audit folder: docs/evaluations/2026-05-22-043009-reviewer-formalization-audit/

Run via:
    python -m pytest api/test_reviewer_formalization.py -v

Or as a standalone script:
    python api/test_reviewer_formalization.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "api"))


# ---------------------------------------------------------------------------
# Variant F canonical sentence + anchors
# ---------------------------------------------------------------------------

VARIANT_F = (
    "full-substrate-authoring persona-bearing judgment seat — "
    "filesystem-native, single-lane queue-serialized, wake-fired, "
    "paced by operator-declared pace + autonomy, driven by operator-"
    "authored mandate"
)

# Banned phrases that signal pre-cutover framing creeping back in.
# Any of these appearing in the persona frame indicates drift away from
# ADR-296 v2 + ADR-298. The persona frame is the highest-leverage prompt
# surface — drift here propagates to every Reviewer wake.
BANNED_PERSONA_PHRASES = (
    "continuously running",
    "continuously-running",
    "continuous loop",
    "always-on Reviewer",
    "self-invokes",
    "self-invoke ",  # trailing space avoids matching "does not self-invoke"
    "background process",
    "self-pacing process",
    "never sleeps",
)


# ---------------------------------------------------------------------------
# Test 1 — Variant F appears verbatim in FOUNDATIONS Derived Principle 21
# ---------------------------------------------------------------------------

def test_foundations_dp21_quotes_variant_f() -> None:
    """FOUNDATIONS Derived Principle 21 must quote the Variant F sentence."""
    path = REPO_ROOT / "docs" / "architecture" / "FOUNDATIONS.md"
    content = path.read_text()
    assert "21. **Reviewer formalization**" in content, (
        "FOUNDATIONS DP21 missing — Variant F anchor must live in canon "
        "as a Derived Principle (drift recommendation: re-add the "
        "principle, do not delete it). See "
        "docs/evaluations/2026-05-22-043009-reviewer-formalization-audit/"
    )
    normalized_content = " ".join(content.split())
    normalized_variant_f = " ".join(VARIANT_F.split())
    assert normalized_variant_f in normalized_content, (
        f"FOUNDATIONS does not contain the Variant F sentence "
        f"(whitespace-normalized). Expected: {normalized_variant_f!r}. "
        f"Drift recommendation: restore the canonical sentence in DP21."
    )


# ---------------------------------------------------------------------------
# Test 2 — Variant F appears verbatim in GLOSSARY Reviewer entry
# ---------------------------------------------------------------------------

def test_glossary_reviewer_entry_quotes_variant_f() -> None:
    """GLOSSARY Reviewer entry must carry the Variant F formalization."""
    path = REPO_ROOT / "docs" / "architecture" / "GLOSSARY.md"
    content = path.read_text()
    assert "Canonical formalization (FOUNDATIONS Derived Principle 21)" in content, (
        "GLOSSARY Reviewer entry missing the Canonical formalization "
        "anchor. New contributors should land on Variant F when they "
        "look up 'Reviewer'."
    )
    normalized_content = " ".join(content.split())
    normalized_variant_f = " ".join(VARIANT_F.split())
    assert normalized_variant_f in normalized_content, (
        f"GLOSSARY does not contain the Variant F sentence "
        f"(whitespace-normalized). Expected: {normalized_variant_f!r}."
    )


# ---------------------------------------------------------------------------
# Test 3 — _PERSONA_FRAME contains the Variant F header + cites DP21
# ---------------------------------------------------------------------------

def test_persona_frame_header_quotes_variant_f() -> None:
    """The Reviewer persona frame opens with the Variant F formalization."""
    path = REPO_ROOT / "api" / "agents" / "reviewer_agent.py"
    content = path.read_text()
    assert "What you are (FOUNDATIONS Derived Principle 21)" in content, (
        "_PERSONA_FRAME missing the 'What you are' formalization "
        "preamble. This is the highest-leverage prompt — the structural "
        "anchor must precede the embodiment register."
    )
    # The persona frame is multi-line for readability; normalize internal
    # whitespace before substring-matching so prose can re-wrap without
    # breaking the gate. The semantic check is "the sentence is present
    # verbatim modulo line-wrapping," not "exact character match."
    normalized_content = " ".join(content.split())
    normalized_variant_f = " ".join(VARIANT_F.split())
    assert normalized_variant_f in normalized_content, (
        f"_PERSONA_FRAME missing Variant F (whitespace-normalized). "
        f"Expected: {normalized_variant_f!r}."
    )


# ---------------------------------------------------------------------------
# Test 4 — No banned pre-cutover phrases in the persona frame
# ---------------------------------------------------------------------------

def test_persona_frame_no_banned_phrases() -> None:
    """Persona frame must not regress to pre-ADR-296-v2 framing."""
    path = REPO_ROOT / "api" / "agents" / "reviewer_agent.py"
    content = path.read_text()

    # Isolate the persona-frame body so we don't flag intentional
    # historical-reference comments elsewhere in the file.
    match = re.search(
        r'_PERSONA_FRAME\s*=\s*"""\\?\n(.*?)"""',
        content,
        re.DOTALL,
    )
    assert match, "Could not locate _PERSONA_FRAME body for scanning."
    frame_body = match.group(1)

    leaks: list[str] = []
    for phrase in BANNED_PERSONA_PHRASES:
        if phrase in frame_body:
            leaks.append(phrase)
    assert not leaks, (
        f"Banned pre-cutover phrases leaked into _PERSONA_FRAME: "
        f"{leaks}. The Reviewer is wake-fired (ADR-296 v2 D1), not "
        f"continuously running. Self-invocation was removed per D3."
    )


# ---------------------------------------------------------------------------
# Test 5 — Persona frame names pace + queue-serialization explicitly
# ---------------------------------------------------------------------------

def test_persona_frame_instructs_mandate_citation() -> None:
    """Persona frame must instruct the Reviewer to cite MANDATE.md when
    MANDATE content is load-bearing in standing_intent.md reasoning. Closes
    the clause-6 strict-reading gap surfaced by the 2026-05-22 L6 Variant-F
    clause validation (FOUNDATIONS DP21)."""
    path = REPO_ROOT / "api" / "agents" / "reviewer_agent.py"
    content = path.read_text()
    # Source-level guard: the instruction must be present in the persona
    # frame body. Doesn't enforce runtime citation (that's observational and
    # context-conditional); enforces the prompt teaches the Reviewer to do so.
    assert "When MANDATE.md content is load-bearing" in content, (
        "_PERSONA_FRAME missing MANDATE.md citation instruction in the "
        "standing_intent.md guidance section. Closes the clause-6 strict-"
        "reading caveat from L6 morning findings — the prompt must teach "
        "Reviewer to cite MANDATE.md by name when MANDATE content drives "
        "forward-looking judgment."
    )
    assert "mandate→reasoning chain" in content or "mandate-clause anchor" in content, (
        "MANDATE.md citation instruction must name WHY the citation matters "
        "(auditability of mandate→reasoning chain). Without the rationale, "
        "the instruction reads as cargo-cult prompt-padding and the Reviewer "
        "is unlikely to honor it consistently."
    )


def test_persona_frame_names_pace_and_queue() -> None:
    """Persona frame must surface the operator's Pace dial + queue-serialized model."""
    path = REPO_ROOT / "api" / "agents" / "reviewer_agent.py"
    content = path.read_text()
    assert "_pace.yaml" in content, (
        "_PERSONA_FRAME does not name _pace.yaml. Pace is the operator's "
        "Trigger-dimension dial (ADR-298 D11) and is locked from "
        "Reviewer writes — the Reviewer needs to know."
    )
    assert "Cycles are serialized" in content or "single-lane" in content, (
        "_PERSONA_FRAME does not name the single-lane queue-serialized "
        "model (ADR-298 D1+D2). The Reviewer's cram-vs-leave-for-next-"
        "cycle reasoning depends on knowing the queue holds concurrent "
        "wakes safely."
    )
    assert "Pace + Autonomy + Persona" in content, (
        "_PERSONA_FRAME does not name the operator-control trifecta "
        "(Pace + Autonomy + Persona). Variant F's claim #6 depends on "
        "the Reviewer understanding which dials the operator turns."
    )


def test_persona_frame_system_resend_wire_prose_post_adr299_discovery_note_2() -> None:
    """Persona frame must teach the system-deployed Resend wire shape for
    platform_email_send_to_operator (ADR-299 Discovery note 2, 2026-05-24).

    Two assertions:
      1. The OBSOLETE wire-gate-detection prose from Phase 3 original
         (commit 0248b56) must NOT survive. The clause taught the Reviewer
         to note substrate-vs-wire drift when the tool was absent from its
         surface; post-Discovery-note-2 the tool is ALWAYS available (no
         wire-gate), so the clause is misleading.
      2. The NEW system-deployed Resend prose MUST be present, naming
         that the tool uses the system wire (no operator-side Resend
         setup), sender defaults, and Reply-To routing.

    This guard catches any future regression that re-introduces the
    obsolete wire-gate-detection discipline OR loses the system-wire
    framing.
    """
    path = REPO_ROOT / "api" / "agents" / "reviewer_agent.py"
    content = path.read_text()

    # OBSOLETE clause from Phase 3 original (must NOT be present)
    obsolete_markers = (
        "operator's Resend connection isn't active",
        "substrate-vs-wire drift",
    )
    leaks: list[str] = []
    for marker in obsolete_markers:
        if marker in content:
            leaks.append(marker)
    assert not leaks, (
        f"Obsolete wire-gate-detection prose leaked back into _PERSONA_FRAME: "
        f"{leaks}. Post-ADR-299 Discovery note 2 (2026-05-24), the tool uses "
        f"the system-deployed Resend wire (api/jobs/email.py) — there is no "
        f"wire-gate to detect drift against. Re-introducing the obsolete "
        f"clause would teach the Reviewer to note a substrate-vs-wire drift "
        f"that the post-correction architecture never produces."
    )

    # NEW system-wire prose (MUST be present)
    assert "system-deployed Resend wire" in content, (
        "_PERSONA_FRAME missing the post-Discovery-note-2 system-wire "
        "framing. The clause must name 'system-deployed Resend wire' so "
        "the Reviewer knows platform_email_send_to_operator is always "
        "available (no operator-side Resend setup ceremony)."
    )
    assert "ADR-299 Discovery note 2" in content, (
        "_PERSONA_FRAME missing the ADR-299 Discovery note 2 citation. "
        "The system-wire framing should cite its canonical source so future "
        "readers can trace the correction shape."
    )


# ---------------------------------------------------------------------------
# Test 6 — REVIEWER_PRIMITIVES contract holds
# ---------------------------------------------------------------------------

def test_reviewer_primitives_contract() -> None:
    """REVIEWER_PRIMITIVES matches ADR-296 v2 + ADR-258 revised commitments."""
    from services.primitives.registry import REVIEWER_PRIMITIVES

    names = {tool["name"] for tool in REVIEWER_PRIMITIVES}

    # MUST be present (Variant F claim #5 + ADR-296 v2 D2/D3)
    required = {
        "Schedule",        # cadence authority (ADR-261 D4)
        "ManageHook",      # substrate-event interest (ADR-296 v2 D2)
        "WriteFile",       # full-substrate-authoring (lock-gated)
        "ProposeAction",   # direction primitive (ADR-258)
        "DispatchSpecialist",  # ADR-261 D7
        "Clarify",         # conversation surface
    }
    missing = required - names
    assert not missing, (
        f"REVIEWER_PRIMITIVES missing required tools: {missing}. "
        f"These are load-bearing for Variant F structural claims #1 "
        f"and #5."
    )

    # MUST NOT be present (ADR-296 v2 D3 — Reviewer does not self-invoke)
    assert "FireInvocation" not in names, (
        "FireInvocation is back in REVIEWER_PRIMITIVES — this violates "
        "ADR-296 v2 D3 (Reviewer does not self-invoke). Cadence + "
        "standing-intent + hook-authoring are the Reviewer's trigger-"
        "authoring authority, not unit-of-work fires. FireInvocation "
        "stays in CHAT_PRIMITIVES + HEADLESS_PRIMITIVES for operator-"
        "chat manual fire only."
    )


# ---------------------------------------------------------------------------
# Test 7 — DEFAULT_REVIEWER_WRITE_LOCKS matches operator-control trifecta
# ---------------------------------------------------------------------------

def test_default_reviewer_write_locks_contract() -> None:
    """DEFAULT_REVIEWER_WRITE_LOCKS contains exactly the 5 operator-control paths."""
    from services.workspace_paths import (
        DEFAULT_REVIEWER_WRITE_LOCKS,
        SHARED_AUTONOMY_PATH,
        SHARED_AUTONOMY_YAML_PATH,
        SHARED_TOKEN_BUDGET_PATH,
        SHARED_PREFERENCES_PATH,
        SHARED_PACE_PATH,
    )

    expected = {
        SHARED_AUTONOMY_PATH,        # Mechanism-dimension dial (ADR-293)
        SHARED_AUTONOMY_YAML_PATH,   # Mechanism-dimension dial (machine-parsed)
        SHARED_TOKEN_BUDGET_PATH,    # compute-resource ceiling (ADR-293)
        SHARED_PREFERENCES_PATH,     # operator deliverable cadence (ADR-275 D6)
        SHARED_PACE_PATH,            # Trigger-dimension dial (ADR-298 Phase 4)
    }
    actual = set(DEFAULT_REVIEWER_WRITE_LOCKS)

    assert actual == expected, (
        f"DEFAULT_REVIEWER_WRITE_LOCKS drifted from the operator-control "
        f"trifecta. Expected: {expected}. Got: {actual}. "
        f"Diff added: {actual - expected}. "
        f"Diff removed: {expected - actual}. "
        f"Variant F claim #6 (paced by operator-declared pace + autonomy) "
        f"depends on these 5 paths being operator-only."
    )


# ---------------------------------------------------------------------------
# Test 8 — All judgment-mode prompts in alpha-{author,trader} bind ReturnVerdict
# ---------------------------------------------------------------------------

# Bundles whose judgment prompts must bind ReturnVerdict structurally.
# Add new bundles to this list as they ship judgment-mode recurrences.
JUDGMENT_PROMPT_FILES = (
    ("alpha-author", "_hooks.yaml"),
    ("alpha-author", "_recurrences.yaml"),
    ("alpha-trader", "_recurrences.yaml"),
)


def _load_judgment_prompts(bundle: str, filename: str) -> list[tuple[str, str]]:
    """Return (slug, prompt) pairs for every judgment-mode entry."""
    path = (
        REPO_ROOT / "docs" / "programs" / bundle
        / "reference-workspace" / filename
    )
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        return []

    # _hooks.yaml has 'hooks:'; _recurrences.yaml has 'recurrences:'.
    entries = data.get("hooks") or data.get("recurrences") or []
    out: list[tuple[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        # Mechanical-mode recurrences don't wake the Reviewer — skip them.
        if entry.get("mode") == "mechanical":
            continue
        # Paused entries are inactive — skip.
        if entry.get("paused") is True:
            continue
        slug = entry.get("slug") or "<unknown>"
        prompt = entry.get("prompt") or ""
        if prompt.strip():
            out.append((slug, prompt))
    return out


def test_judgment_prompts_bind_return_verdict() -> None:
    """Every judgment-mode prompt structurally binds verdict-emission to ReturnVerdict."""
    failures: list[str] = []
    for bundle, filename in JUDGMENT_PROMPT_FILES:
        for slug, prompt in _load_judgment_prompts(bundle, filename):
            if "ReturnVerdict(" not in prompt:
                failures.append(f"{bundle}/{filename}::{slug}")

    assert not failures, (
        "Judgment-mode prompts missing structural ReturnVerdict binding: "
        f"{failures}. Drift recommendation: every prompt that asks the "
        f"Reviewer to decide must name ReturnVerdict(...) explicitly. "
        f"Prose-only verdict requests fall through to the text-only "
        f"fallback at reviewer_agent.py:1409-1422, producing inert "
        f"stand_down with no substrate write — the canary v3 root cause. "
        f"See docs/evaluations/2026-05-22-043009-reviewer-formalization-audit/findings.md §L5."
    )


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_foundations_dp21_quotes_variant_f,
        test_glossary_reviewer_entry_quotes_variant_f,
        test_persona_frame_header_quotes_variant_f,
        test_persona_frame_no_banned_phrases,
        test_persona_frame_instructs_mandate_citation,
        test_persona_frame_names_pace_and_queue,
        test_persona_frame_system_resend_wire_prose_post_adr299_discovery_note_2,
        test_reviewer_primitives_contract,
        test_default_reviewer_write_locks_contract,
        test_judgment_prompts_bind_return_verdict,
    ]
    failures: list[str] = []
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except AssertionError as exc:
            failures.append(f"  FAIL  {fn.__name__}\n         {exc}")
            print(f"  FAIL  {fn.__name__}")
            print(f"         {exc}")
    print()
    print(f"{len(tests) - len(failures)}/{len(tests)} tests passed")
    if failures:
        sys.exit(1)
