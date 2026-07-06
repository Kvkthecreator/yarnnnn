"""Regression gate for ADR-408 D3 — the steward dial inverts for substrate.

The SUBSTRATE action class (reversible workspace writes) resolves its own
per-class block (`substrate:` → `default` → {}), so the steward's file work
runs autonomous while the capital default stays manual/fail-closed. Pause +
never_auto still queue everything.

Run:
    cd api && python test_adr408_d3_steward_dial.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_PASS: list[str] = []
_FAIL: list[tuple[str, str]] = []


def _ok(name):
    _PASS.append(name); print(f"  ✓ {name}")


def _bad(name, reason):
    _FAIL.append((name, reason)); print(f"  ✗ {name}\n      {reason}")


def test_default_yaml_shape() -> None:
    from services.orchestration import DEFAULT_AUTONOMY_YAML
    import yaml
    parsed = yaml.safe_load(DEFAULT_AUTONOMY_YAML)
    if parsed.get("substrate", {}).get("delegation") == "autonomous":
        _ok("seed: substrate delegation autonomous")
    else:
        _bad("seed: substrate delegation autonomous", str(parsed.get("substrate")))
    if parsed.get("default", {}).get("delegation") == "manual":
        _ok("seed: capital default stays manual (fail-closed)")
    else:
        _bad("seed: capital default stays manual (fail-closed)", str(parsed.get("default")))
    if "yarnnn:steward-default" in DEFAULT_AUTONOMY_YAML:
        _ok("seed: steward marker preserved (program-fork overwrite eligibility)")
    else:
        _bad("seed: steward marker preserved", "marker missing")


def test_resolution() -> None:
    from services.review_policy import autonomy_for_substrate, should_auto_apply

    autonomy = {
        "default": {"delegation": "manual"},
        "substrate": {"delegation": "autonomous"},
        "domains": {},
        "paused_until": None,
        "pause_reason": None,
    }

    # Substrate class → autonomous → applies
    policy = autonomy_for_substrate(autonomy)
    allowed, reason = should_auto_apply(
        autonomy_policy=policy, action_class="substrate",
        substrate_path="/workspace/operation/notes.md",
    )
    if allowed:
        _ok("gate: substrate write applies under the D3 posture")
    else:
        _bad("gate: substrate write applies under the D3 posture", reason)

    # Capital class still resolves the default → manual → queues
    from services.review_policy import autonomy_for_domain
    cap_policy = autonomy_for_domain(autonomy, "")
    allowed, reason = should_auto_apply(
        autonomy_policy=cap_policy, action_class="capital",
        verdict="approve", estimated_cents=100,
    )
    if not allowed and "manual" in reason:
        _ok("gate: capital stays fail-closed (manual)")
    else:
        _bad("gate: capital stays fail-closed (manual)", f"allowed={allowed} {reason}")

    # No substrate block → falls back to default (pre-D3 behavior intact)
    legacy = {"default": {"delegation": "manual"}, "domains": {},
              "paused_until": None, "pause_reason": None}
    allowed, reason = should_auto_apply(
        autonomy_policy=autonomy_for_substrate(legacy), action_class="substrate",
        substrate_path="/workspace/operation/notes.md",
    )
    if not allowed and "manual" in reason:
        _ok("gate: legacy file (no substrate block) → default fallback, queues")
    else:
        _bad("gate: legacy file (no substrate block) → default fallback, queues",
             f"allowed={allowed} {reason}")

    # Pause overrides the substrate autonomy
    paused = dict(autonomy, paused_until="2999-01-01T00:00:00Z", pause_reason="test")
    allowed, reason = should_auto_apply(
        autonomy_policy=autonomy_for_substrate(paused), action_class="substrate",
        substrate_path="/workspace/operation/notes.md",
    )
    if not allowed and "paused" in reason:
        _ok("gate: pause queues substrate despite autonomous")
    else:
        _bad("gate: pause queues substrate despite autonomous", f"allowed={allowed} {reason}")

    # never_auto path-match still queues
    guarded = {
        "default": {"delegation": "manual"},
        "substrate": {"delegation": "autonomous",
                      "never_auto": ["path:operation/critical"]},
        "domains": {}, "paused_until": None, "pause_reason": None,
    }
    allowed, reason = should_auto_apply(
        autonomy_policy=autonomy_for_substrate(guarded), action_class="substrate",
        substrate_path="/workspace/operation/critical/x.md",
    )
    if not allowed:
        _ok("gate: never_auto path-match queues despite autonomous")
    else:
        _bad("gate: never_auto path-match queues despite autonomous", reason)


def test_load_autonomy_parses_substrate() -> None:
    from services.review_policy import load_autonomy
    from services.orchestration import DEFAULT_AUTONOMY_YAML

    class _Q:
        def __init__(self, rows): self._rows = rows
        def select(self, *a, **k): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def execute(self):
            class R: pass
            r = R(); r.data = self._rows
            return r

    class _C:
        def table(self, name):
            return _Q([{"content": DEFAULT_AUTONOMY_YAML}])

    out = load_autonomy(_C(), "u-1")
    if out.get("substrate", {}).get("delegation") == "autonomous":
        _ok("load: substrate block parsed from the seed")
    else:
        _bad("load: substrate block parsed from the seed", str(out))


def test_permission_wired() -> None:
    text = (ROOT / "services/primitives/permission.py").read_text()
    if "autonomy_for_substrate(autonomy)" in text and "ADR-408 D3" in text:
        _ok("permission: substrate branch resolves the per-class block")
    else:
        _bad("permission: substrate branch resolves the per-class block", "not wired")
    # Capital dispatch untouched
    disp = (ROOT / "services/review_proposal_dispatch.py").read_text()
    if 'action_class="capital"' in disp and "autonomy_for_domain" in disp:
        _ok("dispatch: capital path unchanged")
    else:
        _bad("dispatch: capital path unchanged", "capital wiring altered")


def main() -> int:
    print("ADR-408 D3 — steward dial regression")
    print("=" * 60)
    test_default_yaml_shape()
    test_resolution()
    test_load_autonomy_parses_substrate()
    test_permission_wired()
    print("=" * 60)
    print(f"{len(_PASS)} passed, {len(_FAIL)} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
