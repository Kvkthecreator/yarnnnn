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
  (c) adding FireInvocation back into FREDDIE_PRIMITIVES (violates
      ADR-296 v2 D3 — Reviewer does not self-invoke)
  (d) removing ManageHook or Schedule from FREDDIE_PRIMITIVES (violates
      Trigger-authoring authority per Derived Principle 18)
  (e) shrinking or expanding DEFAULT_FREDDIE_WRITE_LOCKS beyond the
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


# Executor-self-model phrases — the action-grammar contradiction class.
# These collapse the Reviewer-directs / runtime-executes separation that
# FOUNDATIONS Axiom 1 §4 + Axiom 2 mandate, and were the root cause of the
# 2026-05-29 confabulation (the Reviewer narrated "I attempted the write, it
# was gated, it queued" with zero substrate-receipt — role-playing an
# executor self-model the frame had handed it). See
# docs/evaluations/2026-05-29-reviewer-action-grammar-framing-gap.md and the
# composed-coherence discipline at docs/architecture/agent-composition.md
# §3.2.2. These are the structural (Hat-A) half of the layered gate; the
# behavioral half (narrated-action-without-receipt) is the eval suite's
# confabulation cross-check (the finding's Rec-3).
BANNED_EXECUTOR_GRAMMAR = (
    "is your hands",          # "the System Agent is your hands"
    "are your hands",
    "write directly",        # executor self-model — Reviewer directs, doesn't write directly
    "the doing",             # "they delegated the deciding AND the doing"
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
    path = REPO_ROOT / "api" / "agents" / "freddie_agent.py"
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
    """Persona frame must not regress to pre-ADR-296-v2 framing.

    Post-ADR-302 D6 the frame is assembled from _PERSONA_FRAME_SECTIONS via
    resolve_persona_frame_sections(), not a monolithic _PERSONA_FRAME
    constant. Scan the live composed body (the same text that reaches the
    LLM) rather than a dead regex against a constant that no longer exists.
    """
    from agents.freddie_agent import (
        _PERSONA_FRAME_SECTIONS,
        resolve_persona_frame_sections,
    )
    frame_body = resolve_persona_frame_sections(_PERSONA_FRAME_SECTIONS)

    leaks: list[str] = []
    for phrase in BANNED_PERSONA_PHRASES:
        if phrase in frame_body:
            leaks.append(phrase)
    assert not leaks, (
        f"Banned pre-cutover phrases leaked into _PERSONA_FRAME: "
        f"{leaks}. The Reviewer is wake-fired (ADR-296 v2 D1), not "
        f"continuously running. Self-invocation was removed per D3."
    )


def test_persona_frame_action_grammar_coherence() -> None:
    """Composed-coherence gate for the action-grammar contradiction class.

    Structural (Hat-A) half of the layered gate from the 2026-05-29 finding.
    The persona frame must describe the Reviewer's agency as Axiom 1 §4 +
    Axiom 2 mandate: the Reviewer *directs*; the runtime *executes*; the
    substrate revision is the channel. It must NOT carry the executor
    self-model ("your hands", "write directly", "the doing") that produced
    the confabulation where the Reviewer narrated an inline execute-and-
    observe step it never performed.

    Paired assertion — a banned-phrase scan alone cannot catch a *removed*
    fix (a commit could delete the corrected grammar without re-adding the
    banned grammar). So we assert BOTH: executor grammar is absent AND the
    directs-not-executes grammar is present.

    The behavioral half (narrated-action-without-substrate-receipt) lives in
    the eval suite's confabulation cross-check (the finding's Rec-3) — only a
    live wake + transcript-vs-receipt read can catch behavioral regression.
    This gate catches structural regression on every commit.

    Canon: docs/architecture/agent-composition.md §3.2.2 (composed-coherence
    discipline); FOUNDATIONS Axiom 1 §4 + Axiom 2; finding at
    docs/evaluations/2026-05-29-reviewer-action-grammar-framing-gap.md.
    """
    from agents.freddie_agent import (
        _PERSONA_FRAME_SECTIONS,
        resolve_persona_frame_sections,
    )
    frame_body = resolve_persona_frame_sections(_PERSONA_FRAME_SECTIONS)
    normalized = " ".join(frame_body.lower().split())

    # (1) Executor self-model must be absent.
    leaks = [p for p in BANNED_EXECUTOR_GRAMMAR if p in normalized]
    assert not leaks, (
        f"Executor-self-model grammar leaked into the persona frame: {leaks}. "
        f"The Reviewer DIRECTS; the runtime EXECUTES; the substrate revision "
        f"is the channel (FOUNDATIONS Axiom 1 §4 + Axiom 2). This grammar "
        f"collapses that separation and reproduces the 2026-05-29 "
        f"confabulation. See agent-composition.md §3.2.2."
    )

    # (2) The directs-not-executes grammar must be present (catches a removed
    #     fix, not just an added regression). At least one phrase from each
    #     of the two load-bearing ideas must appear.
    directs_anchors = ("you direct", "the runtime is the hands", "the runtime applies it")
    channel_anchors = ("substrate revision is the channel", "the channel")
    assert any(a in normalized for a in directs_anchors), (
        "Persona frame is MISSING the directs-not-executes anchor. The frame "
        "must state that the Reviewer directs and the runtime executes (e.g. "
        "'you direct', 'the runtime is the hands'). Absence means the "
        "2026-05-29 fix was removed. See agent-composition.md §3.2.2."
    )
    assert any(a in normalized for a in channel_anchors), (
        "Persona frame is MISSING the substrate-as-channel anchor. The frame "
        "must state the substrate revision is the channel between Reviewer "
        "(directs) and runtime (executes) per Axiom 1 §4."
    )


# ---------------------------------------------------------------------------
# Test 5 — Persona frame names pace + queue-serialization explicitly
# ---------------------------------------------------------------------------

def test_persona_frame_instructs_mandate_citation() -> None:
    """Persona frame must instruct the Reviewer to cite MANDATE.md when
    MANDATE content is load-bearing in standing_intent.md reasoning. Closes
    the clause-6 strict-reading gap surfaced by the 2026-05-22 L6 Variant-F
    clause validation (FOUNDATIONS DP21)."""
    path = REPO_ROOT / "api" / "agents" / "freddie_agent.py"
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


def test_persona_frame_names_what_it_is() -> None:
    """The minimal frame must carry the Variant-F 'what you are' identity line +
    the pace/autonomy dial vocabulary (single-lane, paced).

    REWRITTEN by ADR-306 (2026-05-29 collapse). The prior version asserted the
    full cadence-trifecta prose ("Pace + Autonomy + Persona", "Cycles are
    serialized") in the frame. That substrate-pedagogy moved to
    _workspace_guide.md; the dial-by-dial explanation is no longer the frame's
    job (the model reads _pace.yaml / _autonomy.yaml from the envelope under
    their own headers). The frame keeps only the Variant-F identity line, which
    names the dials at the vocabulary level (paced, single-lane, wake-fired).
    """
    from agents.freddie_agent import (
        _PERSONA_FRAME_SECTIONS,
        resolve_persona_frame_sections,
    )
    frame = resolve_persona_frame_sections(_PERSONA_FRAME_SECTIONS)
    # The Variant-F identity sentence (FOUNDATIONS DP21) names the dials at
    # vocabulary level: paced by pace + autonomy, single-lane, wake-fired.
    assert "single-lane queue-serialized" in frame, (
        "Minimal frame missing the Variant-F 'single-lane queue-serialized' "
        "identity vocabulary. Post-collapse the frame names the dials at the "
        "identity-line level; the dial-by-dial pedagogy lives in "
        "_workspace_guide.md."
    )
    assert "paced by" in frame and "pace" in frame.lower(), (
        "Minimal frame missing the pace/autonomy dial vocabulary in the "
        "Variant-F identity line."
    )


def test_reviewer_email_tool_excluded_by_code_not_prose() -> None:
    """ADR-299 D8 Reviewer-side exclusion of platform_email_send_to_operator
    is enforced by CODE (absence from FREDDIE_PRIMITIVES), not by persona-
    frame prose.

    REWRITTEN by ADR-306 (2026-05-29 persona-frame collapse). The prior
    version of this test asserted ~5 prose clauses in the persona-frame
    teaching the operator-addressing-infrastructure framing + the by-design
    exclusion. ADR-306 collapsed the frame to principal-shift + action-grammar
    only; "code-enforced needs no prose" (the Reviewer cannot call a tool it
    doesn't have). The exclusion is the same — its enforcement is now asserted
    at the genuinely load-bearing layer (the tool surface) rather than at a
    narration of it. This is a STRONGER test: it verifies the gate, not the
    description of the gate.
    """
    from services.primitives.registry import FREDDIE_PRIMITIVES

    names = {
        (t["name"] if isinstance(t, dict) else getattr(t, "name", str(t)))
        for t in FREDDIE_PRIMITIVES
    }
    assert "platform_email_send_to_operator" not in names, (
        "platform_email_send_to_operator must NOT be in FREDDIE_PRIMITIVES "
        "(ADR-299 D8 — operator-addressing system infrastructure is excluded "
        "from the judgment-bearing Reviewer surface by design; v5 canary "
        "2026-05-25 evidence-confirmed). Post-ADR-306 this exclusion is "
        "code-enforced, not narrated in the persona-frame — the Reviewer "
        "literally cannot call a tool absent from its surface."
    )
    # No email-send tool of any shape leaks into the Reviewer surface.
    assert not any("email_send" in str(n).lower() for n in names), (
        "An email-send tool leaked into FREDDIE_PRIMITIVES. Operator-"
        "addressing email is system infrastructure (SYSTEM_INFRASTRUCTURE_TOOLS, "
        "task-bearing agents only), never the Reviewer's."
    )


# ---------------------------------------------------------------------------
# Test 6 — FREDDIE_PRIMITIVES contract holds
# ---------------------------------------------------------------------------

def test_reviewer_primitives_contract() -> None:
    """FREDDIE_PRIMITIVES matches ADR-296 v2 + ADR-258 revised commitments."""
    from services.primitives.registry import FREDDIE_PRIMITIVES

    names = {tool["name"] for tool in FREDDIE_PRIMITIVES}

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
        f"FREDDIE_PRIMITIVES missing required tools: {missing}. "
        f"These are load-bearing for Variant F structural claims #1 "
        f"and #5."
    )

    # MUST NOT be present (ADR-296 v2 D3 — Reviewer does not self-invoke)
    assert "FireInvocation" not in names, (
        "FireInvocation is back in FREDDIE_PRIMITIVES — this violates "
        "ADR-296 v2 D3 (Reviewer does not self-invoke). Cadence + "
        "standing-intent + hook-authoring are the Reviewer's trigger-"
        "authoring authority, not unit-of-work fires. FireInvocation "
        "stays in CHAT_PRIMITIVES + HEADLESS_PRIMITIVES for operator-"
        "chat manual fire only."
    )


# ---------------------------------------------------------------------------
# Test 7 — DEFAULT_FREDDIE_WRITE_LOCKS matches operator-control trifecta
# ---------------------------------------------------------------------------

# NOTE (ADR-320): test_default_reviewer_write_locks_contract DELETED.
# DEFAULT_FREDDIE_WRITE_LOCKS collapsed into the five-root CALLER_WRITE_POLICY
# (governance/ locked from the reviewer caller). The operator-control-paths-locked
# contract is now covered by test_adr320_permission_topology.py.


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
        f"fallback at freddie_agent.py:1409-1422, producing inert "
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
        test_persona_frame_action_grammar_coherence,
        test_persona_frame_instructs_mandate_citation,
        test_persona_frame_names_what_it_is,
        test_reviewer_email_tool_excluded_by_code_not_prose,
        test_reviewer_primitives_contract,
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
