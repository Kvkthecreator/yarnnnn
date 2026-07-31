"""Eval-suite manifest gate — the 2026-07-31 eval-layer audit.

The suite layer sat one commit deep from 2026-07-03 through four canon waves
(ADR-366, ADR-393, ADR-402/403, ADR-414); at audit time ZERO of nine suites
could fire through run_eval_suite.py — eight refused at pre-flight on stale
`requires:` paths, and the CURRENT suite crashed on a persona slug that was
never in the registry, plus an unsupported `absent_or_empty:` operator that
silently inverted to must-be-present. None of that was mechanical-checkable
until now. This gate makes the mechanically checkable half permanent:

  1. Every manifest parses, is schema v3, carries the required fields, and
     declares a machine-readable `status: current | dormant | superseded`.
  2. Every persona slug resolves in docs/alpha/personas.yaml — the exact
     crash class of the un-runnable CURRENT suite.
  3. Every referenced scenario file exists.
  4. Every `requires:` assertion uses a SUPPORTED operator key-set — the
     exact silent-inversion class of `absent_or_empty:`. Mirrors
     services/operator_proxy/scenarios.py::check_preconditions, which now
     also rejects unknown operators loudly at runtime; this gate catches
     them before any session tries to fire.
  5. `status: current` suites must not assert the ADR-366-migrated
     `governance/_preferences.yaml` / `governance/_expected_output.yaml`
     spellings (moved to `contract/`).
  6. SESSION-TEMPLATE.md carries no v2 `Read kind` field.

What this gate deliberately does NOT check: whether a dormant suite's thesis
is still true (a MIND question — EVAL-SUITE-DISCIPLINE §0), or whether a
`requires:` path exists on a live workspace (that is check_preconditions'
runtime job, S2).

Run: python -m pytest api/test_eval_suite_gate.py -q
"""
from __future__ import annotations

import os
import re

import yaml

_API = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_API)
SUITES_DIR = os.path.join(_REPO, "docs", "evaluations", "eval-suites")
SCENARIOS_DIR = os.path.join(_REPO, "docs", "evaluations", "scenarios")
PERSONAS_YAML = os.path.join(_REPO, "docs", "alpha", "personas.yaml")

VALID_STATUS = {"current", "dormant", "superseded"}

#: The suite kinds the registry recognizes. `thesis` = Suite B, fired by
#: run_eval_suite.py against a persona workspace. `browser` = the E2E
#: human-parity lane (VERIFICATION.md): a click-pass manifest driven by a
#: BROWSER principal, NOT by the LLM runner — run_eval_suite.py refuses it
#: (VALID_SUITE_KINDS stays {"thesis"}), which is the point: the two lanes
#: have different firing instruments and must not be confusable.
VALID_SUITE_KINDS = {"thesis", "browser"}

#: Fields every browser manifest must carry. `principals` names WHICH logged-in
#: principals the pass is run as (the owner/member pair is the instrument);
#: `steps` is the click-path. `thesis` is required for BOTH kinds — a suite
#: without a declared criterion is a snapshot, not an eval (README rule 1).
BROWSER_REQUIRED = ("eval_suite", "suite_kind", "thesis", "principals", "steps")

# Mirror of check_preconditions' supported assertion forms (keys beyond `path`).
SUPPORTED_OPERATOR_SETS = (
    set(),                    # bare {path} -> present
    {"absent"},
    {"field", "equals"},
    {"contains"},
    {"not_contains"},
)
MIGRATED_PATHS = {
    "/workspace/governance/_preferences.yaml": "contract/_preferences.yaml (ADR-366)",
    "/workspace/governance/_expected_output.yaml": "contract/_expected_output.yaml (ADR-366)",
}


def _suite_files() -> list[str]:
    return sorted(
        f for f in os.listdir(SUITES_DIR)
        if f.endswith(".yaml") and not f.endswith(".criterion.md")
    )


def _persona_slugs() -> set[str]:
    src = open(PERSONAS_YAML, encoding="utf-8").read()
    return set(re.findall(r"^\s*-\s*slug:\s*([A-Za-z0-9_-]+)", src, re.M))


def _check_browser_suite(fname: str, raw: dict) -> list[str]:
    """Mechanical checks for a `suite_kind: browser` click-pass manifest.

    The invariant this gate exists to defend (VERIFICATION.md E2E lane, and the
    2026-07-31 closed-loop direction): **a browser pass without a substrate
    receipt is narrative.** A step that changes state must name BOTH what the
    DOM shows and what the substrate proves — so the gate enumerates the
    state-changing steps and asserts a receipt PER SITE. A counting gate cannot
    defend a per-site invariant (the ADR-495 lesson), so this checks each step
    by name and reports the specific step that is missing its receipt.
    """
    problems: list[str] = []
    for req in BROWSER_REQUIRED:
        if req not in raw:
            problems.append(f"{fname}: missing required field {req!r} (browser suite)")

    principals = raw.get("principals")
    if not isinstance(principals, list) or not principals:
        problems.append(
            f"{fname}: `principals` must be a non-empty list naming the logged-in "
            "principals the pass runs as (e.g. the owner/member pair)")

    steps = raw.get("steps")
    if not isinstance(steps, list) or not steps:
        problems.append(f"{fname}: `steps` must be a non-empty list")
        return problems

    seen: set[str] = set()
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            problems.append(f"{fname}: steps[{i}] is not a mapping")
            continue
        slug = step.get("step")
        if not slug:
            problems.append(f"{fname}: steps[{i}] missing `step` slug")
        elif slug in seen:
            problems.append(f"{fname}: duplicate step slug {slug!r}")
        else:
            seen.add(slug)
        label = slug or f"steps[{i}]"

        if not step.get("expect_dom"):
            problems.append(
                f"{fname}: step {label!r} has no `expect_dom` — every step must "
                "name what the operator should SEE, or the pass is unfalsifiable")

        # THE PER-SITE INVARIANT: a state-changing step needs a receipt.
        if step.get("mutates"):
            if not step.get("receipt"):
                problems.append(
                    f"{fname}: step {label!r} sets `mutates: true` but carries no "
                    "`receipt:` — a state-changing click without a substrate "
                    "receipt is narrative (VERIFICATION.md E2E exit criteria)")
            if not step.get("restore"):
                problems.append(
                    f"{fname}: step {label!r} mutates but declares no `restore:` — "
                    "deliberate writes on live substrate must be reversible "
                    "(the d5b9029b read-mostly guardrail)")
    return problems


def _check_suite(fname: str, raw: dict, persona_slugs: set[str]) -> list[str]:
    """All mechanical problems for one parsed manifest. Pure — falsifiable."""
    problems: list[str] = []

    kind = raw.get("suite_kind")
    if kind is not None and kind not in VALID_SUITE_KINDS:
        problems.append(
            f"{fname}: suite_kind={kind!r} — must be one of "
            f"{sorted(VALID_SUITE_KINDS)}")

    status = raw.get("status")
    if status not in VALID_STATUS:
        problems.append(
            f"{fname}: status={status!r} — must be one of {sorted(VALID_STATUS)} "
            "(machine-readable status is how the runner refuses superseded suites)")

    # Browser suites have a DIFFERENT required shape (no persona/scenario —
    # they are driven by a browser principal, not the LLM runner).
    if kind == "browser":
        return problems + _check_browser_suite(fname, raw)

    for req in ("eval_suite", "suite_kind", "persona", "thesis", "evals"):
        if req not in raw:
            problems.append(f"{fname}: missing required field {req!r}")
    if int(raw.get("eval_suite_schema_version", 0)) != 3:
        problems.append(f"{fname}: not schema v3")
    persona = raw.get("persona")
    if persona and persona not in persona_slugs:
        problems.append(
            f"{fname}: persona {persona!r} not in docs/alpha/personas.yaml "
            f"{sorted(persona_slugs)} — the runner raises at from_persona")
    for i, ev in enumerate(raw.get("evals") or []):
        scenario = ev.get("scenario")
        if scenario and not os.path.exists(
                os.path.join(_REPO, "docs", "evaluations", scenario)):
            problems.append(f"{fname}: evals[{i}] scenario missing: {scenario}")
        for j, assertion in enumerate(ev.get("requires") or []):
            ops = set(assertion.keys()) - {"path"}
            if ops not in SUPPORTED_OPERATOR_SETS:
                problems.append(
                    f"{fname}: evals[{i}].requires[{j}] unsupported operator "
                    f"key-set {sorted(ops)} — check_preconditions supports "
                    "absent | field+equals | contains | not_contains | bare path")
            if status == "current":
                p = assertion.get("path", "")
                if p in MIGRATED_PATHS:
                    problems.append(
                        f"{fname}: evals[{i}].requires[{j}] asserts migrated "
                        f"path {p} — now {MIGRATED_PATHS[p]}")
    return problems


def test_all_suite_manifests_mechanically_sound():
    persona_slugs = _persona_slugs()
    assert persona_slugs, "no persona slugs parsed from personas.yaml"
    problems: list[str] = []
    for fname in _suite_files():
        raw = yaml.safe_load(open(os.path.join(SUITES_DIR, fname), encoding="utf-8"))
        if not isinstance(raw, dict):
            problems.append(f"{fname}: does not parse to a dict")
            continue
        problems += _check_suite(fname, raw, persona_slugs)
    assert not problems, (
        "Eval-suite manifests failed the mechanical gate:\n  "
        + "\n  ".join(problems)
    )


def test_exactly_one_current_suite_and_it_is_the_declared_one():
    """The registry's CURRENT designation is singular and named. If a second
    suite goes current, or the current one changes, this test forces the
    change to be deliberate (update here + README in the same commit)."""
    current = []
    for fname in _suite_files():
        raw = yaml.safe_load(open(os.path.join(SUITES_DIR, fname), encoding="utf-8"))
        # Browser suites are a SEPARATE lane with a separate firing instrument
        # (a browser principal, not run_eval_suite.py). The "exactly one current"
        # rule governs the LLM-runner registry; a current browser manifest does
        # not contend for that slot.
        if not isinstance(raw, dict) or raw.get("suite_kind") == "browser":
            continue
        if raw.get("status") == "current":
            current.append(fname)
    assert current == ["freddie-bare-workspace-steward.yaml"], (
        f"current suites = {current}; expected exactly "
        "['freddie-bare-workspace-steward.yaml']. Going current requires the "
        "suite to pass live pre-flight — update this assertion + the README "
        "registry deliberately in the same commit."
    )


def test_llm_runner_refuses_browser_suites():
    """The two lanes must not be confusable at the firing instrument.

    A `suite_kind: browser` manifest describes a CLICK path for a human/browser
    principal; run_eval_suite.py fires LLM wakes against a persona workspace. If
    the runner ever accepted `browser`, it would try to fire a click-pass as a
    wake — silently producing a thesis read of a suite that has no scenario. The
    registry gate recognizes the kind; the runner must still reject it.
    """
    src = open(
        os.path.join(_API, "scripts", "operator", "run_eval_suite.py"),
        encoding="utf-8",
    ).read()
    m = re.search(r"^VALID_SUITE_KINDS\s*=\s*\{([^}]*)\}", src, re.M)
    assert m, "run_eval_suite.py no longer declares VALID_SUITE_KINDS"
    kinds = {k.strip().strip("\"'") for k in m.group(1).split(",") if k.strip()}
    assert "browser" not in kinds, (
        "run_eval_suite.py accepts suite_kind 'browser' — the browser lane is "
        "driven by a browser principal (VERIFICATION.md E2E lane), not by the "
        "LLM runner. Keep VALID_SUITE_KINDS = {'thesis'}."
    )


def test_browser_manifests_declare_a_receipt_for_every_mutating_step():
    """The per-site invariant, asserted over the real manifests + falsified.

    Enumerate every browser manifest's mutating steps, assert each names a
    receipt — and prove the check BITES by running it against a synthetic
    manifest whose mutating step has none (a counting gate cannot defend a
    per-site invariant; this one is falsified in-place).
    """
    browser_files = []
    for fname in _suite_files():
        raw = yaml.safe_load(open(os.path.join(SUITES_DIR, fname), encoding="utf-8"))
        if isinstance(raw, dict) and raw.get("suite_kind") == "browser":
            browser_files.append((fname, raw))
    assert browser_files, (
        "no `suite_kind: browser` manifests found — the E2E lane's click-pass "
        "criteria are the deliverable this gate exists to hold"
    )

    problems: list[str] = []
    mutating_seen = 0
    for fname, raw in browser_files:
        for step in raw.get("steps") or []:
            if isinstance(step, dict) and step.get("mutates"):
                mutating_seen += 1
        problems += _check_browser_suite(fname, raw)
    assert not problems, "Browser manifests failed the gate:\n  " + "\n  ".join(problems)
    assert mutating_seen, (
        "no mutating steps across the browser manifests — a settings sign-off "
        "that never exercises a verb proves only that pages render"
    )

    # FALSIFIER: the same checker must REJECT a receipt-less mutating step.
    bad = {
        "eval_suite": "synthetic", "suite_kind": "browser", "thesis": "x",
        "principals": ["owner"],
        "steps": [{"step": "s1", "expect_dom": "something", "mutates": True}],
    }
    caught = _check_browser_suite("synthetic.yaml", bad)
    assert any("receipt" in p for p in caught), (
        "the receipt check does not bite — it would pass a mutating step with "
        "no substrate receipt, which is the exact narrative-not-evidence failure"
    )


def test_session_template_is_v3():
    tmpl = open(os.path.join(SUITES_DIR, "SESSION-TEMPLATE.md"), encoding="utf-8").read()
    assert "**Read kind**" not in tmpl, (
        "SESSION-TEMPLATE.md emits the v2 `Read kind` field the v3 rework "
        "deleted — the template lagged a schema version for eight weeks."
    )
