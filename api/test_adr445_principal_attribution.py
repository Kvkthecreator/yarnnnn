"""ADR-373/445 gate — every COSTED telemetry site attributes its principal.

WHY (the audit finding, 2026-07-21): `execution_events.principal_id` was stamped
at 11 of 34 `record_execution_event` call sites. The other 23 wrote NULL — not a
user_id fallback, an UNATTRIBUTED row. Two consequences:

  1. `spend_by_principal` (the Usage pane's "who used it") understated real spend,
     with the workspace's largest cost source — the recurrence/wake lane — landing
     entirely in the NULL bucket.
  2. `check_member_cap` sums `spend_by_principal` filtered by principal, so a
     member's draw through any unstamped path was invisible to their own cap.

THE CARVE THIS GATE ENFORCES: a site must stamp `principal_id` iff it records
COST (input_tokens/output_tokens/cost_usd). A zero-cost mechanical row (a capture
tick, a foreign READ, an embed) may stay unattributed — it draws nothing from the
pool, so it cannot distort a rollup or a cap. Those are listed in
ZERO_COST_ALLOWLIST with a reason each, so the deferral is DECLARED rather than
silent (an unlisted new site fails).

Modelled on `test_adr296_wake_source_populated.py`'s structural walk — the
technique that, applied here, would have caught all 23 mechanically.

Usage:
    cd api
    python test_adr445_principal_attribution.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PASSED = 0
FAILED = 0

# Sites that record NO cost. Each may stay unattributed; the reason is declared so
# the deferral is a decision, not an oversight. A costed site may never be listed.
ZERO_COST_ALLOWLIST: dict[str, str] = {
    "services/capture/lane.py": "capture lane — mechanical, zero tokens, and DORMANT behind CONNECTOR_CAPTURE_ENABLED (ADR-404)",
    "services/foreign_read.py": "foreign READ — mode='mechanical', zero tokens; a read draws nothing from the pool (ADR-396 free-reads carve)",
    "services/primitives/embed.py": "embed — mechanical; the embedding COGS is absorbed by base, not metered (ADR-396)",
    "services/wake.py": "wake.py's non-cost rows (failure/skip/stand-down paths) record no tokens; its one COSTED site is asserted explicitly below",
    "services/anthropic.py": "shared client helper — not itself a metered invocation",
    "services/platform_limits.py": "the ledger reader, not a writer of costed rows",
    "services/telemetry.py": "the recorder's own module (definition + docs)",
    "services/session_continuity.py": "stamped already; listed for completeness",
}

# The costed sites this session stamped — asserted individually so a regression
# names the exact file rather than only moving a count.
COSTED_SITES = [
    ("services/wake.py", "the recurrence/wake judgment lane (largest cost source)"),
    ("services/primitives/dispatch_specialist.py", "specialist sub-LLM calls"),
    ("services/primitives/web_search.py", "web search"),
    ("services/harvest.py", "harvest"),
    ("services/context_inference.py", "identity/brand authoring"),
    ("services/recurrence_prompt_inference.py", "back-office prompt inference"),
    # Found BY this gate, not by the audit walk — it postdated the manual count.
    # Exactly what a structural check is for.
    ("services/images/compose.py", "image generation (cost_override_usd)"),
]

COST_MARKERS = ("input_tokens", "output_tokens", "cost_override_usd")


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        print(f"  ✓ {label}")
        PASSED += 1
    else:
        print(f"  ✗ {label}{(' — ' + detail) if detail else ''}")
        FAILED += 1


def _calls(src: str) -> list[str]:
    """Every record_execution_event(...) call body, parenthesis-balanced.

    Skips the definition and PROSE mentions (a comment or docstring naming the
    function, e.g. "via the canonical record_execution_event() path") — those are
    documentation, not call sites, and flagging them would train the next editor
    to delete accurate comments to appease the gate.
    """
    out = []
    for m in re.finditer(r"record_execution_event\(", src):
        # Skip the definition itself.
        if "def record_execution_event" in src[max(0, m.start() - 40):m.start()]:
            continue
        # Skip mentions inside a comment line.
        line_start = src.rfind("\n", 0, m.start()) + 1
        if "#" in src[line_start:m.start()]:
            continue
        i, depth = m.end(), 1
        while i < len(src) and depth:
            depth += (src[i] == "(") - (src[i] == ")")
            i += 1
        out.append(src[m.start():i])
    return out


def _iter_sources():
    for base in ("services", "routes"):
        for p in Path(base).rglob("*.py"):
            yield p


def test_every_costed_site_is_attributed() -> None:
    print("\n[carve] a site that records COST must stamp principal_id")
    offenders: list[str] = []
    costed_total = 0
    for p in _iter_sources():
        src = p.read_text()
        for body in _calls(src):
            costed = any(k in body for k in COST_MARKERS)
            if not costed:
                continue
            costed_total += 1
            if "principal_id" not in body:
                offenders.append(str(p))
    check(f"all {costed_total} costed telemetry sites carry principal_id",
          not offenders,
          f"unattributed costed sites: {sorted(set(offenders))}")


def test_named_costed_sites_stamp() -> None:
    print("\n[sites] each costed site fixed this session still stamps")
    for rel, why in COSTED_SITES:
        src = Path(rel).read_text()
        costed = [b for b in _calls(src) if any(k in b for k in COST_MARKERS)]
        ok = bool(costed) and all("principal_id" in b for b in costed)
        check(f"{rel} ({why})", ok,
              f"{len(costed)} costed call(s); "
              f"{sum('principal_id' in b for b in costed)} stamped")


def test_zero_cost_deferrals_are_declared() -> None:
    print("\n[deferrals] every unattributed site is on the declared allowlist")
    undeclared: list[str] = []
    for p in _iter_sources():
        src = p.read_text()
        for body in _calls(src):
            if "principal_id" in body:
                continue
            if any(k in body for k in COST_MARKERS):
                continue  # caught by the carve test above
            rel = str(p)
            if rel not in ZERO_COST_ALLOWLIST:
                undeclared.append(rel)
    check("no undeclared unattributed sites", not undeclared,
          f"add to ZERO_COST_ALLOWLIST with a reason (or stamp them): "
          f"{sorted(set(undeclared))}")


def test_allowlist_holds_no_costed_site() -> None:
    print("\n[integrity] the allowlist cannot hide a costed site")
    violations = []
    for rel in ZERO_COST_ALLOWLIST:
        p = Path(rel)
        if not p.exists():
            continue
        for body in _calls(p.read_text()):
            if any(k in body for k in COST_MARKERS) and "principal_id" not in body:
                violations.append(rel)
    check("no allowlisted file carries an unattributed COSTED call", not violations,
          f"{sorted(set(violations))} — a costed site may never be deferred")


def test_resolver_is_the_canonical_path() -> None:
    print("\n[canon] auth-bearing sites resolve via resolve_principal_id")
    for rel in ("services/primitives/web_search.py",
                "services/primitives/dispatch_specialist.py",
                "services/harvest.py"):
        src = Path(rel).read_text()
        check(f"{rel} uses resolve_principal_id", "resolve_principal_id" in src,
              "the uniform ADR-373 D2 abstraction, not a hand-rolled id")


def main() -> int:
    print("=" * 74)
    print("ADR-373/445 — per-principal attribution on the one cost ledger")
    print("=" * 74)
    test_every_costed_site_is_attributed()
    test_named_costed_sites_stamp()
    test_zero_cost_deferrals_are_declared()
    test_allowlist_holds_no_costed_site()
    test_resolver_is_the_canonical_path()
    print("\n" + "=" * 74)
    print(f"  {PASSED} passed, {FAILED} failed")
    print("=" * 74)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
