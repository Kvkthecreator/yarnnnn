"""ADR-350 gate — the Standing band (settled-state render of the standing obligation).

ADR-350 is FE-only (render of substrate the Reviewer already produces — no new
primitive/schema/table, ADR-344 §7). The web package has no JS test runner, so
the load-bearing FE invariants are guarded here by source-assertion (the same
pattern as the ADR-351 FE guards), with `tsc --noEmit` as the companion type
gate run in web/.

Invariants:
  1. StandingBand exists and is mounted in the Notifications "To do" (resolve)
     pane, above QueueBody.
  2. It RENDERS substrate, never authors it: reads the expected-output contract
     (reusing the stable ADR-348 hook) + persona/standing_intent.md prose. It
     contains NO write to standing_intent.md (region discipline, ADR-320).
  3. standing_intent.md is rendered as PROSE AS-IS — no field-parsing of that
     free-form file (forward-compatible with posture-layer reshaping).
  4. The standing-intent path mirrors the backend constant
     (PERSONA_STANDING_INTENT_PATH = persona/standing_intent.md).
  5. Framing obeys ADR-345 witness reframe — the band never calls a standing
     item "blocked".

Run: pytest test_adr350_standing_band.py -q
"""
from __future__ import annotations

import os

_WEB = os.path.join(os.path.dirname(__file__), "..", "web")


def _read_web(rel: str) -> str:
    with open(os.path.join(_WEB, rel), encoding="utf-8") as fh:
        return fh.read()


def test_standing_band_component_exists():
    src = _read_web("components/queue/StandingBand.tsx")
    assert "export function StandingBand" in src


def test_standing_band_mounted_in_resolve_pane_above_queue():
    page = _read_web("app/(authenticated)/notifications/page.tsx")
    assert "StandingBand" in page
    # mounted above QueueBody in the resolve pane
    assert page.index("<StandingBand />") < page.index("<QueueBody />")


def test_band_reuses_expected_output_hook_not_a_new_parser():
    src = _read_web("components/queue/StandingBand.tsx")
    # Read-1 reuses the stable ADR-348 contract hook + summary formatter
    assert "useExpectedOutput" in src
    assert "formatExpectedOutputSummary" in src


def test_band_renders_standing_intent_as_prose_no_field_parsing():
    src = _read_web("components/queue/StandingBand.tsx")
    # prose render via the shared MarkdownRenderer
    assert "MarkdownRenderer" in src
    # forward-compatibility guard: no field-extraction regex/parse of the
    # free-form standing_intent.md (the file has no schema). If a future change
    # introduces structured parsing of that file, this bites — revisit the ADR.
    assert ".match(" not in src, "StandingBand must not field-parse standing_intent.md"
    assert "gap_type" not in src, "no structured shortfall field — prose as-is"


def test_band_does_not_write_persona_substrate():
    """Region discipline (ADR-320): the band READS persona-region prose; the
    operator never writes standing_intent.md from here."""
    src = _read_web("components/queue/StandingBand.tsx")
    assert "writeShape" not in src
    assert "writeFile" not in src
    assert "setContract" not in src  # even the contract is read-only in the band


def test_standing_intent_path_mirrors_backend_constant():
    consts = _read_web("components/queue/standing-band.constants.ts")
    assert "persona/standing_intent.md" in consts
    # backend source of truth
    with open(os.path.join(os.path.dirname(__file__), "services", "workspace_paths.py"), encoding="utf-8") as fh:
        py = fh.read()
    assert 'PERSONA_STANDING_INTENT_PATH = "persona/standing_intent.md"' in py


def test_band_framing_is_witness_not_blocked():
    """ADR-345 autonomy-as-witness: a standing item is surfaced for decision,
    never framed as the agent being blocked."""
    src = _read_web("components/queue/StandingBand.tsx")
    lower = src.lower()
    assert "blocked" not in lower
    assert "stuck" not in lower
    assert "waiting for permission" not in lower


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
