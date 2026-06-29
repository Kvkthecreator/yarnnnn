"""ADR-327 Phase 1 gate — _budget.yaml substrate + loader.

Covers the Phase 1 surface only (additive substrate; wake-path gates are
Phase 2):
  - services/budget.py parses default / custom / malformed correctly
  - window-floor math for monthly/weekly/daily
  - GOVERNANCE_BUDGET_PATH wired into workspace_init seed + reviewer envelope
  - the budget_yaml envelope key (renamed from pace_yaml) is present
  - the alpha-trader bundle ships _budget.yaml (not _token_budget.yaml)
  - FreddieContext carries budget_yaml (not pace_yaml)

Usage:
    cd api
    python test_adr327_phase1.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))
_REPO_ROOT = _API_ROOT.parent

try:
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
except Exception:
    pass

from services.budget import (  # noqa: E402
    Budget,
    DEFAULT_BUDGET_YAML,
    _VALID_WINDOWS,
    _window_floor_iso,
    load_budget,
)
from services.workspace_paths import GOVERNANCE_BUDGET_PATH  # noqa: E402
from services.freddie_envelope import _UNIVERSAL_ENVELOPE_DECLS  # noqa: E402

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


# ─── Fake client (returns canned workspace_files content) ────────────────────


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, content):
        self._content = content

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        if self._content is None:
            return _FakeResult([])
        return _FakeResult([{"content": self._content}])


class _FakeClient:
    def __init__(self, content):
        self._content = content

    def table(self, _name):
        return _FakeTable(self._content)


# ─── Loader ──────────────────────────────────────────────────────────────────


def test_loader_default() -> None:
    print("\n[loader] absent / blank → kernel default")
    b = load_budget(_FakeClient(None), "u" * 36)
    check("absent file → Budget", isinstance(b, Budget))
    check("default amount_usd == 50.0", b.amount_usd == 50.0, str(b.amount_usd))
    check("default window == monthly", b.window == "monthly", b.window)
    check("default per_wake_ceiling == 1.0", b.per_wake_ceiling_usd == 1.0)
    blank = load_budget(_FakeClient("   \n"), "u" * 36)
    check("blank content → default amount", blank.amount_usd == 50.0)


def test_loader_custom() -> None:
    print("\n[loader] operator-customized")
    yaml_text = (
        "budget:\n"
        "  amount_usd: 120\n"
        "  window: weekly\n"
        "per_wake_ceiling_usd: 2.5\n"
        "min_interval_between_recurrence_fires_seconds: 300\n"
        "overrides:\n"
        "  signal-evaluation:\n"
        "    min_interval_seconds: 900\n"
    )
    b = load_budget(_FakeClient(yaml_text), "u" * 36)
    check("amount_usd parsed", b.amount_usd == 120.0, str(b.amount_usd))
    check("window parsed", b.window == "weekly", b.window)
    check("per_wake_ceiling parsed", b.per_wake_ceiling_usd == 2.5)
    check("min_interval parsed", b.min_interval_between_recurrence_fires_seconds == 300)
    check("per-slug override applies", b.min_interval_for("signal-evaluation") == 900)
    check("per-slug fallback to default", b.min_interval_for("other") == 300)


def test_loader_malformed() -> None:
    print("\n[loader] malformed → safe fallback")
    b = load_budget(_FakeClient("budget: [this is not a mapping"), "u" * 36)
    check("malformed YAML → default (no raise)", b.amount_usd == 50.0)
    b2 = load_budget(_FakeClient("budget:\n  window: nonsense\n"), "u" * 36)
    check("invalid window → default monthly", b2.window == "monthly", b2.window)
    b3 = load_budget(_FakeClient("budget:\n  amount_usd: -5\n"), "u" * 36)
    check("non-positive amount → default", b3.amount_usd == 50.0)


# ─── Window-floor math ───────────────────────────────────────────────────────


def test_window_floor() -> None:
    print("\n[window] floor math")
    monthly = _window_floor_iso("monthly")
    dt = datetime.fromisoformat(monthly)
    check("monthly floor is day=1", dt.day == 1, monthly)
    check("monthly floor is midnight UTC", dt.hour == 0 and dt.minute == 0)
    daily = _window_floor_iso("daily")
    today = datetime.now(timezone.utc).date()
    check("daily floor is today", datetime.fromisoformat(daily).date() == today)
    weekly = _window_floor_iso("weekly")
    check("weekly floor is a Monday", datetime.fromisoformat(weekly).weekday() == 0, weekly)
    check("all valid windows resolve", all(_window_floor_iso(w) for w in _VALID_WINDOWS))


# ─── Wiring ──────────────────────────────────────────────────────────────────


def test_default_yaml() -> None:
    print("\n[default-yaml] DEFAULT_BUDGET_YAML shape")
    import yaml
    parsed = yaml.safe_load(DEFAULT_BUDGET_YAML)
    check("DEFAULT_BUDGET_YAML parses", isinstance(parsed, dict))
    check("has budget.amount_usd == 50", parsed.get("budget", {}).get("amount_usd") == 50.0)
    check("has budget.window == monthly", parsed.get("budget", {}).get("window") == "monthly")


def test_path_constant() -> None:
    print("\n[path] GOVERNANCE_BUDGET_PATH")
    check("path is governance/_budget.yaml", GOVERNANCE_BUDGET_PATH == "governance/_budget.yaml")


def test_envelope_key() -> None:
    print("\n[envelope] budget_yaml key (renamed from pace_yaml)")
    keys = [k for (k, _p) in _UNIVERSAL_ENVELOPE_DECLS]
    check("budget_yaml in envelope decls", "budget_yaml" in keys)
    check("pace_yaml NOT in envelope decls", "pace_yaml" not in keys)
    decl = dict(_UNIVERSAL_ENVELOPE_DECLS)
    check("budget_yaml → governance/_budget.yaml", decl.get("budget_yaml") == "governance/_budget.yaml")


def test_reviewer_context() -> None:
    print("\n[contract] FreddieContext.budget_yaml")
    from agents.occupant_contract import FreddieContext
    ann = getattr(FreddieContext, "__annotations__", {})
    check("budget_yaml in FreddieContext", "budget_yaml" in ann)
    check("pace_yaml NOT in FreddieContext", "pace_yaml" not in ann)


def test_bundle_file() -> None:
    print("\n[bundle] alpha-trader ships _budget.yaml")
    gov = _REPO_ROOT / "docs/programs/alpha-trader/reference-workspace/governance"
    check("_budget.yaml exists", (gov / "_budget.yaml").is_file())
    check("_token_budget.yaml deleted", not (gov / "_token_budget.yaml").exists())
    check("_pace.yaml absent from bundle", not (gov / "_pace.yaml").exists())
    import yaml
    raw = (gov / "_budget.yaml").read_text()
    # Strip tier frontmatter before parsing.
    body = raw
    if raw.startswith("---"):
        end = raw.find("\n---\n", 3)
        body = raw[end + 5:] if end != -1 else raw
    parsed = yaml.safe_load(body)
    check("bundle _budget.yaml has amount_usd", parsed.get("budget", {}).get("amount_usd") == 50.00)


def test_workspace_init_wiring() -> None:
    print("\n[init] workspace_init seeds _budget.yaml")
    src = (_API_ROOT / "services/workspace_init.py").read_text()
    check("imports DEFAULT_BUDGET_YAML", "DEFAULT_BUDGET_YAML" in src)
    check("imports GOVERNANCE_BUDGET_PATH", "GOVERNANCE_BUDGET_PATH" in src)
    check("no DEFAULT_TOKEN_BUDGET_YAML import", "DEFAULT_TOKEN_BUDGET_YAML" not in src)


def main() -> int:
    print("=" * 64)
    print("ADR-327 Phase 1 — _budget.yaml substrate + loader")
    print("=" * 64)
    test_loader_default()
    test_loader_custom()
    test_loader_malformed()
    test_window_floor()
    test_default_yaml()
    test_path_constant()
    test_envelope_key()
    test_reviewer_context()
    test_bundle_file()
    test_workspace_init_wiring()
    print("\n" + "=" * 64)
    print(f"  PASSED={PASSED}  FAILED={FAILED}")
    print("=" * 64)
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
