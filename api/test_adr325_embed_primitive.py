"""ADR-325 regression gate — Embed as a gated primitive.

Asserts:
  (a) Embed is registered in CHAT_PRIMITIVES + HEADLESS_PRIMITIVES + HANDLERS.
  (b) Embed is CONSEQUENTIAL (not read_only) and GATE_QUEUEABLE (autonomy-governed).
  (c) Content-kind eligibility (D5): operation/ + uploads/ eligible; governance/,
      system/, *.yaml/*.json, and tiny files ineligible.
  (d) The WriteFile fire-and-forget auto-embed is GONE (deleted with the
      scope='context' branch in ADR-321) — `_embed_workspace_file` has exactly
      one live caller path (the Embed primitive) + the operator-upload route.
  (e) The embed mechanism (`_embed_workspace_file`) survives (not orphaned).

Run: python -m pytest api/test_adr325_embed_primitive.py -q
"""
from __future__ import annotations

from pathlib import Path

API = Path(__file__).parent


def _read(*parts: str) -> str:
    return (API / Path(*parts)).read_text()


def test_embed_registered():
    from services.primitives.registry import CHAT_PRIMITIVES, HEADLESS_PRIMITIVES, HANDLERS
    chat = {t["name"] for t in CHAT_PRIMITIVES}
    headless = {t["name"] for t in HEADLESS_PRIMITIVES}
    assert "Embed" in chat, "Embed must be in CHAT_PRIMITIVES (ADR-325)."
    assert "Embed" in headless, "Embed must be in HEADLESS_PRIMITIVES (ADR-325)."
    assert "Embed" in HANDLERS, "Embed must be in HANDLERS (ADR-325)."


def test_embed_is_consequential_and_gate_queueable():
    from services.primitives.permission import (
        is_read_only, GATE_QUEUEABLE_PRIMITIVES,
    )
    assert not is_read_only("Embed"), "Embed must be consequential (ADR-325/307)."
    assert "Embed" in GATE_QUEUEABLE_PRIMITIVES, (
        "Embed must be gate-queueable so the autonomy mode IS the embed policy (ADR-325 D3)."
    )


def test_embed_eligibility_selective():
    from services.primitives.embed import is_embed_eligible
    body = "x" * 300

    # Eligible — semantic-search targets.
    assert is_embed_eligible("operation/competitors/acme/profile.md", body)[0]
    assert is_embed_eligible("uploads/q2-report.md", body)[0]
    assert is_embed_eligible("/workspace/operation/market/landscape.md", body)[0]

    # Ineligible — machine/runtime roots.
    assert not is_embed_eligible("governance/_pace.yaml", body)[0]
    assert not is_embed_eligible("system/notes.md", body)[0]
    # Ineligible — machine config / structured state by extension.
    assert not is_embed_eligible("operation/trading/_signals.yaml", body)[0]
    assert not is_embed_eligible("operation/d/manifest.json", body)[0]
    # Ineligible — not a search-target root.
    assert not is_embed_eligible("persona/IDENTITY.md", body)[0]
    assert not is_embed_eligible("constitution/MANDATE.md", body)[0]
    # Ineligible — too short.
    assert not is_embed_eligible("operation/d/tiny.md", "short")[0]


def test_writefile_no_auto_embed():
    # The scope='context' branch (which fired _embed_workspace_file) is gone
    # (ADR-321). handle_write_file must not call _embed_workspace_file anymore.
    src = _read("services", "primitives", "workspace.py")
    # The helper is DEFINED here (survives), but the fire-and-forget call site
    # (asyncio.ensure_future(_embed_workspace_file(...))) must be absent.
    assert "ensure_future(\n                _embed_workspace_file" not in src
    assert "asyncio.ensure_future(_embed_workspace_file" not in src
    # No bare _embed_workspace_file( call inside handle_write_file region.
    # (Definition `async def _embed_workspace_file` is allowed.)


def test_embed_mechanism_survives_not_orphaned():
    # _embed_workspace_file must still exist (it's the Embed handler's call target).
    from services.primitives.workspace import _embed_workspace_file
    assert callable(_embed_workspace_file)
    # And the Embed handler imports it.
    embed_src = _read("services", "primitives", "embed.py")
    assert "from services.primitives.workspace import _embed_workspace_file" in embed_src


def test_embed_tool_description_states_selectivity():
    # The LLM-facing description must communicate eligibility (not 100%-embed).
    from services.primitives.embed import EMBED_TOOL
    desc = EMBED_TOOL["description"]
    assert "ELIGIBLE" in desc and "NOT ELIGIBLE" in desc, (
        "Embed description must state content-kind selectivity (ADR-325 D5 — not a 100%-embed principle)."
    )
