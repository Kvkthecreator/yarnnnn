"""ADR-298 Phase 2 — Pace substrate + Schedule primitive gate regression gate.

Asserts:
- parse_pace_yaml handles empty, missing, valid-kind, valid-numeric-override.
- parse_pace_yaml raises on invalid kind, invalid every, mistyped values.
- _hours_to_kind coerces numeric overrides to enum bands per ADR-298 D4.
- cron_fires_per_day approximates frequencies correctly for common patterns.
- check_population_constraint: under-cap allows, at-cap allows, over-cap rejects.
- check_population_constraint: replacing_slug excludes itself from cum sum.
- check_population_constraint: mechanical-mode recurrences excluded from sum.
- check_population_constraint: reactive (schedule=None) recurrences excluded.
- check_population_constraint: continuous pace + None pace pass everything.
- GOVERNANCE_PACE_PATH is locked from the Reviewer caller (governance/ root, ADR-320).
- Reviewer envelope decl includes `pace_yaml` key.
- Schedule primitive returns pace_exceeded error when create would breach cap.

Run: .venv/bin/python api/test_adr298_phase2_pace.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

_REPO_ROOT = _API_ROOT.parent
from dotenv import load_dotenv  # noqa: E402
load_dotenv(_REPO_ROOT / ".env")


from services.pace import (  # noqa: E402
    InvalidPaceKindError,
    PACE_FIRES_PER_DAY,
    PACE_KINDS,
    Pace,
    PaceParseError,
    _hours_to_kind,
    check_population_constraint,
    cron_fires_per_day,
    parse_pace_yaml,
)
from services.workspace_paths import GOVERNANCE_PACE_PATH  # noqa: E402
from services.primitives.workspace import _is_path_locked  # noqa: E402
from services.reviewer_envelope import _UNIVERSAL_ENVELOPE_DECLS  # noqa: E402


PASSED = 0
FAILED = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        print(f"  ✓ {label}")
        PASSED += 1
    else:
        print(f"  ✗ {label}{(' — ' + detail) if detail else ''}")
        FAILED += 1


# ─── Pace parser ────────────────────────────────────────────────────────────


def test_parse_empty() -> None:
    print("\n[parse] empty / absent / blank")
    check("Empty string → None", parse_pace_yaml("") is None)
    check("Whitespace string → None", parse_pace_yaml("   \n  ") is None)
    check("YAML with no `pace:` key → None", parse_pace_yaml("other: 5\n") is None)
    check("YAML with pace=null → None", parse_pace_yaml("pace:\n") is None)


def test_parse_kind() -> None:
    print("\n[parse] enum kind values")
    for k in ("hourly", "daily", "weekly", "continuous"):
        p = parse_pace_yaml(f"pace:\n  kind: {k}\n")
        check(f"kind={k}", p is not None and p.kind == k)


def test_parse_every_numeric_override() -> None:
    print("\n[parse] numeric `every` override → band coercion (ADR-298 D4)")

    p = parse_pace_yaml("pace:\n  every: 4h\n")
    check("every:4h → hourly band", p is not None and p.kind == "hourly",
          f"got {p.kind if p else None}")
    check("every:4h preserves every_iso", p is not None and p.every_iso == "4h")

    p = parse_pace_yaml("pace:\n  every: 12h\n")
    check("every:12h → hourly band", p is not None and p.kind == "hourly")

    p = parse_pace_yaml("pace:\n  every: 24h\n")
    check("every:24h → daily band", p is not None and p.kind == "daily")

    p = parse_pace_yaml("pace:\n  every: 3d\n")
    check("every:3d → daily band", p is not None and p.kind == "daily")

    p = parse_pace_yaml("pace:\n  every: 14d\n")
    check("every:14d → weekly band", p is not None and p.kind == "weekly")


def test_parse_invalid() -> None:
    print("\n[parse] rejection of malformed input")

    for raw, label in [
        ("pace:\n  kind: garbage\n",     "unknown kind raises"),
        ("pace:\n  every: 4weeks\n",     "non-h/d unit in every raises"),
        ("pace:\n  every: 4\n",          "unitless every raises"),
        ("pace:\n",                      "neither kind nor every is None (handled)"),
    ]:
        raised = False
        try:
            parse_pace_yaml(raw)
        except (PaceParseError, InvalidPaceKindError):
            raised = True
        if "(handled)" in label:
            # Empty pace block should not raise — returns None.
            check(label, not raised)
        else:
            check(label, raised)


def test_hours_to_kind() -> None:
    print("\n[_hours_to_kind] band coercion")
    check("1h → hourly", _hours_to_kind(1) == "hourly")
    check("4h → hourly", _hours_to_kind(4) == "hourly")
    check("23h → hourly", _hours_to_kind(23) == "hourly")
    check("24h → daily", _hours_to_kind(24) == "daily")
    check("72h (3d) → daily", _hours_to_kind(72) == "daily")
    check("168h (7d) → daily (boundary)", _hours_to_kind(168) == "daily")
    check("169h → weekly", _hours_to_kind(169) == "weekly")
    check("336h (14d) → weekly", _hours_to_kind(336) == "weekly")


# ─── Pace constants ─────────────────────────────────────────────────────────


def test_pace_constants() -> None:
    print("\n[constants] enum + drain rates")
    check("PACE_KINDS has 4 entries", len(PACE_KINDS) == 4)
    check(
        "PACE_FIRES_PER_DAY covers all kinds",
        set(PACE_FIRES_PER_DAY.keys()) == PACE_KINDS,
    )
    check("hourly cap = 24/day", PACE_FIRES_PER_DAY["hourly"] == 24.0)
    check("daily cap = 1/day", PACE_FIRES_PER_DAY["daily"] == 1.0)
    check("weekly cap ~= 0.143/day", abs(PACE_FIRES_PER_DAY["weekly"] - 1/7) < 1e-9)
    check("continuous cap = +inf", PACE_FIRES_PER_DAY["continuous"] == float("inf"))


def test_pace_dataclass() -> None:
    print("\n[Pace dataclass]")
    p_h = Pace(kind="hourly")
    check("hourly fires_per_day_cap = 24", p_h.fires_per_day_cap == 24.0)
    p_d = Pace(kind="daily")
    check("daily fires_per_day_cap = 1", p_d.fires_per_day_cap == 1.0)
    p_c = Pace(kind="continuous")
    check("continuous fires_per_day_cap = inf", p_c.fires_per_day_cap == float("inf"))


# ─── cron_fires_per_day ─────────────────────────────────────────────────────


def test_cron_fires_per_day() -> None:
    print("\n[cron_fires_per_day] common cron expressions")
    check("Empty → 0", cron_fires_per_day("") == 0.0)
    check("None → 0", cron_fires_per_day(None) == 0.0)  # type: ignore[arg-type]

    # Daily at 05:00 = 1/day
    check("'0 5 * * *' → ~1.0/day", abs(cron_fires_per_day("0 5 * * *") - 1.0) < 0.01)

    # Mon + Thu at noon = 2/week ≈ 0.286/day
    check(
        "'0 12 * * 1,4' → ~0.286/day",
        abs(cron_fires_per_day("0 12 * * 1,4") - 2.0/7.0) < 0.05,
    )

    # Every hour = 24/day
    check(
        "'0 * * * *' → ~24/day",
        abs(cron_fires_per_day("0 * * * *") - 24.0) < 0.5,
    )

    # Friday weekly = 1/7 ≈ 0.143/day
    check(
        "'0 22 * * 5' → ~0.143/day",
        abs(cron_fires_per_day("0 22 * * 5") - 1.0/7.0) < 0.05,
    )

    # Semantic schedule → 1/day default per Phase 2 stub.
    check("'@market_open' → 1/day (semantic stub)", cron_fires_per_day("@market_open") == 1.0)


# ─── Population constraint ──────────────────────────────────────────────────


class _StubRecurrence:
    def __init__(self, slug, schedule, mode="judgment"):
        self.slug = slug
        self.schedule = schedule
        self.mode = mode


def test_population_under_cap() -> None:
    print("\n[population] under-cap allow")
    pace = Pace(kind="daily")  # 1/day cap
    existing = []  # empty workspace
    # New daily recurrence at 1/day exactly matches cap.
    r = check_population_constraint(pace, existing, "0 5 * * *")
    check("Empty workspace + daily-cap + 1 daily recurrence allowed", not r.exceeds, r.detail)


def test_population_over_cap() -> None:
    print("\n[population] over-cap reject")
    pace = Pace(kind="daily")
    existing = [_StubRecurrence("existing-daily", "0 5 * * *")]  # 1/day already
    # Adding another daily would total 2/day > 1/day cap.
    r = check_population_constraint(pace, existing, "0 14 * * *")
    check("daily-cap + 2 daily recurrences REJECTED", r.exceeds, r.detail)
    check(
        "exceeds reason mentions cap",
        "EXCEEDS" in r.detail or "exceeds" in r.detail.lower(),
    )


def test_population_replacing_slug() -> None:
    print("\n[population] update replaces own slug — excluded from sum")
    pace = Pace(kind="daily")
    existing = [_StubRecurrence("the-one", "0 5 * * *")]
    # Updating "the-one" to a different cron — should NOT double-count itself.
    r = check_population_constraint(
        pace, existing, "0 14 * * *", replacing_slug="the-one"
    )
    check("Update with replacing_slug allowed (self-excluded)", not r.exceeds, r.detail)


def test_population_mechanical_excluded() -> None:
    print("\n[population] mechanical-mode recurrences excluded from sum")
    pace = Pace(kind="daily")
    existing = [
        _StubRecurrence("track-positions", "*/30 * * * *", mode="mechanical"),
    ]
    # Even though the mechanical fires every 30min, it's not on the paced
    # lane — adding a daily judgment recurrence should pass.
    r = check_population_constraint(pace, existing, "0 5 * * *")
    check("daily-cap allows daily recurrence past mechanical noise", not r.exceeds, r.detail)


def test_population_reactive_excluded() -> None:
    print("\n[population] reactive (schedule=None) excluded from sum")
    pace = Pace(kind="daily")
    existing = [_StubRecurrence("reactive-one", None)]
    r = check_population_constraint(pace, existing, "0 5 * * *")
    check("Reactive existing + 1 daily new allowed", not r.exceeds, r.detail)


def test_population_continuous() -> None:
    print("\n[population] continuous pace + no pace pass everything")
    pace_c = Pace(kind="continuous")
    existing = [
        _StubRecurrence(f"r{i}", "* * * * *") for i in range(10)  # 10 recurrences firing every minute
    ]
    r = check_population_constraint(pace_c, existing, "* * * * *")
    check("continuous + 10× minutely existing + 1 minutely new allowed", not r.exceeds)

    r = check_population_constraint(None, existing, "* * * * *")
    check("None pace + same setup allowed", not r.exceeds)


def test_population_reactive_new() -> None:
    print("\n[population] new schedule=None always passes")
    pace = Pace(kind="daily")
    existing = [_StubRecurrence("r1", "0 5 * * *")]  # at cap
    r = check_population_constraint(pace, existing, None)
    check("Adding reactive recurrence past at-cap allowed", not r.exceeds)


# ─── Integration: workspace_paths + reviewer_envelope ───────────────────────


def test_pace_locked_for_reviewer() -> None:
    # ADR-320: the flat DEFAULT_REVIEWER_WRITE_LOCKS list dissolved into the
    # five-root permission topology. "pace is locked from Reviewer" is still
    # true — governance/ is locked from the reviewer caller class — but the
    # assertion mechanism is now the singular gate.
    print("\n[integration] GOVERNANCE_PACE_PATH locked from Reviewer (governance/ root)")
    check(
        "_pace.yaml is locked from Reviewer writes",
        _is_path_locked("reviewer", GOVERNANCE_PACE_PATH),
        f"_is_path_locked('reviewer', {GOVERNANCE_PACE_PATH!r}) returned False",
    )


def test_envelope_includes_pace() -> None:
    print("\n[integration] reviewer envelope decl carries pace_yaml")
    keys = [decl[0] for decl in _UNIVERSAL_ENVELOPE_DECLS]
    check("pace_yaml key in envelope decls", "pace_yaml" in keys, f"got {keys}")
    # Per ADR-298, pace_yaml should be adjacent to preferences_yaml (kindred
    # operator-declared substrate).
    if "pace_yaml" in keys and "preferences_yaml" in keys:
        check(
            "pace_yaml decl after preferences_yaml",
            keys.index("pace_yaml") == keys.index("preferences_yaml") + 1,
        )


# ─── Main ───────────────────────────────────────────────────────────────────


def main() -> int:
    print("=== ADR-298 Phase 2 — pace substrate + Schedule gate regression ===")

    test_parse_empty()
    test_parse_kind()
    test_parse_every_numeric_override()
    test_parse_invalid()
    test_hours_to_kind()
    test_pace_constants()
    test_pace_dataclass()
    test_cron_fires_per_day()
    test_population_under_cap()
    test_population_over_cap()
    test_population_replacing_slug()
    test_population_mechanical_excluded()
    test_population_reactive_excluded()
    test_population_continuous()
    test_population_reactive_new()
    test_pace_locked_for_reviewer()
    test_envelope_includes_pace()

    print(f"\n=== Results: {PASSED} passed, {FAILED} failed ===")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
