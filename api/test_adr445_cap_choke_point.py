"""ADR-445 §9 closure gate — the draw gate binds at EVERY costed member entry.

The debt this closes (found by the 2026-07-21 audit, deferred as a design
question): the per-member cap bound at exactly ONE call site (routes/feed.py)
while lanes, studio, and images drew the pool with no gate at all — several
with no balance check either. "The cap bounds one conversation surface, not a
member."

The design taken (ADR-491 Phase 3): ONE helper —
`platform_limits.check_draw(client, user_id, workspace_id=, principal_id=)` —
is the single implementation of hard-stop + per-member cap, and every costed,
member-attributed entry calls it before launching model work. The wake lane is
deliberately NOT covered: standing work attributes to the owner (radar/
recurrence convention), and the owner is never capped; wake keeps its own
check_balance.

Behavioural where it matters ([[feedback_config_gate_is_not_evidence]]):
  1. check_draw() itself, against fake clients — exhausted pool blocks with
     'balance_exhausted'; a capped member blocks with 'member_capped'; an
     uncapped principal with balance passes.
  2. The call-site walk — each named entry file calls check_draw (saw-N, so a
     regression names the file), and feed.py no longer runs the two gates
     separately (Singular Implementation).

Usage:
    cd api
    python3 test_adr445_cap_choke_point.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

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


def main() -> int:
    sys.path.insert(0, str(Path(__file__).parent))
    root = Path(__file__).parent

    # ── 1. check_draw behaviour ──────────────────────────────────────────────
    print("\n[behaviour] check_draw — one gate, two checks")
    import services.platform_limits as pl

    # Monkeypatch the two parts so the composition is what's under test (each
    # part has its own behavioural gate: test_adr490 for balance reads,
    # test_adr445_member_caps_scope for the cap).
    orig_balance, orig_effective = pl.check_balance, pl.get_effective_balance
    import services.member_caps as mc
    orig_cap = mc.check_member_cap
    try:
        # Pool exhausted → balance_exhausted, cap never consulted.
        pl.check_balance = lambda c, u: (False, 0.0)
        cap_calls = []
        mc.check_member_cap = lambda *a, **k: cap_calls.append(1) or (True, None, 0.0)
        ok, reason, detail = pl.check_draw(None, "u1", principal_id="m1")
        check("exhausted pool → blocked with 'balance_exhausted'",
              ok is False and reason == "balance_exhausted")
        check("balance detail carried", detail.get("balance_usd") == 0.0)
        check("cap not consulted once the pool blocks", not cap_calls)

        # Pool ok, member at cap → member_capped with the cap figures.
        pl.check_balance = lambda c, u: (True, 42.0)
        mc.check_member_cap = lambda *a, **k: (False, 5.0, 5.25)
        ok, reason, detail = pl.check_draw(None, "u1", principal_id="m1")
        check("capped member → blocked with 'member_capped'",
              ok is False and reason == "member_capped")
        check("cap detail carried",
              detail.get("cap_usd") == 5.0 and detail.get("spent_usd") == 5.25)

        # Pool ok, uncapped → allowed.
        mc.check_member_cap = lambda *a, **k: (True, None, 1.0)
        ok, reason, detail = pl.check_draw(None, "u1", principal_id="m1")
        check("uncapped principal with balance → allowed",
              ok is True and reason is None and detail == {})
    finally:
        pl.check_balance = orig_balance
        pl.get_effective_balance = orig_effective
        mc.check_member_cap = orig_cap

    # The real check_member_cap wiring: check_draw passes principal + workspace
    # through (the two args whose omission made the cap inert pre-audit).
    src_pl = (root / "services" / "platform_limits.py").read_text()
    m = re.search(r"def check_draw[\s\S]*?return True, None, \{\}", src_pl)
    check("check_draw threads workspace_id + principal_id to the cap",
          m is not None and "workspace_id=workspace_id" in m.group(0)
          and "principal_id" in m.group(0))

    # ── 2. The call-site walk — every costed member entry gates ──────────────
    print("\n[coverage] every costed member-facing entry calls check_draw")
    ENTRIES = [
        ("routes/feed.py", "the addressed steward turn"),
        ("routes/lanes.py", "lane turns + regenerate (via _turn_stream_response)"),
        ("routes/studio.py", "the arrangement plan (costed judgment)"),
        ("routes/images.py", "compose (planning + per-image engine cost)"),
    ]
    for rel, why in ENTRIES:
        src = (root / rel).read_text()
        n = len(re.findall(r"check_draw\(", src))
        check(f"{rel} gates with check_draw ({why})", n >= 1, "no check_draw call")

    # lanes gates ONCE, at the turn core — and that is the invariant worth
    # asserting: every metered path in the file funnels through the one site
    # (streaming + regenerate both reach it via _turn_stream_response). ADR-506
    # deleted the second site with the `settle` verb, so "gates at both" would
    # now be a gate defending a path that no longer exists; what must never
    # happen is a metered path added AROUND this one.
    lanes_src = (root / "routes/lanes.py").read_text()
    check("lanes.py gates the turn core (the file's one metered choke point)",
          len(re.findall(r"check_draw\(", lanes_src)) >= 1)

    # Singular Implementation: feed.py runs the ONE gate, not the two parts.
    feed_src = (root / "routes/feed.py").read_text()
    check("feed.py no longer imports check_member_cap directly",
          "check_member_cap" not in feed_src)
    check("feed.py no longer calls check_balance directly",
          "check_balance(" not in feed_src)
    check("feed.py preserves both SSE payload shapes",
          "balance_exhausted" in feed_src and "member_cap_reached" in feed_src)

    # The wake lane deliberately keeps its own balance check (owner-attributed,
    # never capped) — assert it did NOT get swept into the member gate.
    wake_src = (root / "services/wake.py").read_text()
    check("wake keeps check_balance (owner-attributed; caps don't apply)",
          "check_balance(" in wake_src and "check_draw(" not in wake_src)

    print(f"\n{'='*60}\nADR-445 §9 choke-point gate: {PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
