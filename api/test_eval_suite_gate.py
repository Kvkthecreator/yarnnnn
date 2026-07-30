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


def _check_suite(fname: str, raw: dict, persona_slugs: set[str]) -> list[str]:
    """All mechanical problems for one parsed manifest. Pure — falsifiable."""
    problems: list[str] = []
    for req in ("eval_suite", "suite_kind", "persona", "thesis", "evals"):
        if req not in raw:
            problems.append(f"{fname}: missing required field {req!r}")
    if int(raw.get("eval_suite_schema_version", 0)) != 3:
        problems.append(f"{fname}: not schema v3")
    status = raw.get("status")
    if status not in VALID_STATUS:
        problems.append(
            f"{fname}: status={status!r} — must be one of {sorted(VALID_STATUS)} "
            "(machine-readable status is how the runner refuses superseded suites)")
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
        if isinstance(raw, dict) and raw.get("status") == "current":
            current.append(fname)
    assert current == ["freddie-bare-workspace-steward.yaml"], (
        f"current suites = {current}; expected exactly "
        "['freddie-bare-workspace-steward.yaml']. Going current requires the "
        "suite to pass live pre-flight — update this assertion + the README "
        "registry deliberately in the same commit."
    )


def test_session_template_is_v3():
    tmpl = open(os.path.join(SUITES_DIR, "SESSION-TEMPLATE.md"), encoding="utf-8").read()
    assert "**Read kind**" not in tmpl, (
        "SESSION-TEMPLATE.md emits the v2 `Read kind` field the v3 rework "
        "deleted — the template lagged a schema version for eight weeks."
    )
