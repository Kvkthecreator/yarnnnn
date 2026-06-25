"""Window-cap LRU-recede gate (ADR-369 follow-on, 2026-06-25).

The pre-369 window cap (ADR-297 D15.3) REFUSED a navigation when 8 windows were
open ("You have 8 windows open. Close one before opening X") — the one move
ADR-340 DP29 forbids: a primary act is never blocked. This gate locks in the
reshape to LRU RECEDE — opening past the cap auto-closes the least-recently-used
window and proceeds; navigation is never refused, and the blocking toast is gone.

FE-only — no schema, primitive, backend, or Render-service change. The web
package has no JS test runner, so the load-bearing invariants are guarded here by
source-assertion (the same pattern as the ADR-350/367/369 FE guards), with
`tsc --noEmit` as the companion type gate run in web/.

Invariants:
  1. The cap constant survives as a PERF ceiling (not deleted) and its doc names
     the LRU/recede semantic, not refusal.
  2. foregroundWindowGrade no longer REFUSES at the cap — the `setCapHit(slug);
     return false;` refusal path is gone; the cap branch now evicts an LRU victim
     via closeSurfaceWrite.
  3. The victim is the lowest-z OPEN window EXCLUDING the foregrounded one (z is
     the recency signal — the operator never loses what they're looking at).
  4. The `capHit` / `clearCapHit` refusal plumbing is fully removed (hook state,
     interface, and the TopBar toast) — Singular Implementation, no dead path.
  5. The blocking toast string ("windows open. Close one before opening") is gone
     from the TopBar.

Run: pytest test_window_cap_lru_recede.py -q
"""
from __future__ import annotations

import os

_WEB = os.path.join(os.path.dirname(__file__), "..", "web")


def _read_web(rel: str) -> str:
    with open(os.path.join(_WEB, rel), encoding="utf-8") as fh:
        return fh.read()


def test_cap_constant_survives_as_perf_ceiling():
    src = _read_web("lib/shell/surface-preferences.ts")
    assert "export const MAX_OPEN_WINDOWS" in src, (
        "the cap constant stays — it's a perf ceiling on mounted windows."
    )
    # its doc names the new LRU/recede meaning, not refusal
    lower = src.lower()
    assert "recede" in lower or "lru" in lower, (
        "MAX_OPEN_WINDOWS doc must name the LRU/recede semantic."
    )


def test_foreground_no_longer_refuses_at_cap():
    src = _read_web("lib/shell/useSurfacePreferences.tsx")
    # the refusal path is gone
    assert "setCapHit(slug)" not in src, (
        "the cap must not REFUSE the open (setCapHit + return false is the "
        "pre-369 refusal path — ADR-340 DP29 forbids blocking a primary act)."
    )
    # the cap branch still exists, but now evicts via the close write helper
    assert "open.length >= MAX_OPEN_WINDOWS" in src, "the cap branch survives."
    assert "closeSurfaceWrite(userId, victim)" in src, (
        "at the cap, foregroundWindowGrade must recede the LRU victim via "
        "closeSurfaceWrite, not refuse."
    )


def test_victim_is_lowest_z_excluding_foregrounded():
    src = _read_web("lib/shell/useSurfacePreferences.tsx")
    # the victim is selected over the OPEN set, excluding the foregrounded one
    assert "s !== foregrounded" in src, (
        "the LRU victim must exclude the foregrounded window — the operator "
        "never loses what they're looking at."
    )
    # z is the recency signal used to pick the oldest
    assert "const victim" in src
    assert "?.z ?? 0" in src, (
        "the victim is chosen by lowest z (the recency signal — every "
        "foreground bumps z)."
    )


def test_caphit_plumbing_fully_removed():
    """Singular Implementation: no dead refusal plumbing left behind."""
    hook = _read_web("lib/shell/useSurfacePreferences.tsx")
    assert "capHit" not in hook, "the capHit hook state/interface must be gone."
    assert "clearCapHit" not in hook, "clearCapHit must be gone."

    top = _read_web("components/shell/chrome/TopBarSurface.tsx")
    assert "capHit" not in top, "TopBar must not consume capHit."
    assert "clearCapHit" not in top, "TopBar must not consume clearCapHit."


def test_blocking_toast_removed():
    top = _read_web("components/shell/chrome/TopBarSurface.tsx")
    assert "windows open. Close one before opening" not in top, (
        "the blocking cap toast must be removed — opening recedes, never blocks."
    )


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
