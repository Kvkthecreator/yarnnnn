"""CLAUDE.md ablation ratchet (2026-07-30 pass, commit 9ae0f56).

CLAUDE.md was ablated 155K -> ~46K chars by extracting reference material to
docs/architecture/ADR-LEDGER.md + docs/database/SCHEMA-NOTES.md. The prompt
layer is held by CI ceilings (test_adr383 / test_adr323); nothing held
CLAUDE.md, and an ungated cut regrows. This gate holds the cut:

  (a) CLAUDE.md stays under a char ceiling (~50K — headroom over the 45.6K cut).
  (b) The two extraction targets exist and are non-trivial (the pointers in
      CLAUDE.md must not dangle).

Raising the ceiling requires the same evidence as adding a prompt instruction
(ADR-306 / DP22): a REPEATED observed failure that new instruction text fixes,
named in the commit that raises it. Reference material goes to the ledger or
schema notes, not here.

Run: python -m pytest api/test_claude_md_ratchet.py -q
"""
from __future__ import annotations

import os

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CLAUDE_MD_CEILING = 50_000


def test_claude_md_under_ceiling():
    size = len(open(os.path.join(_REPO, "CLAUDE.md"), encoding="utf-8").read())
    assert size <= CLAUDE_MD_CEILING, (
        f"CLAUDE.md is {size} chars (> {CLAUDE_MD_CEILING}). The 2026-07-30 ablation "
        "cut it to ~46K; instruction content stays, reference material moves to "
        "docs/architecture/ADR-LEDGER.md or docs/database/SCHEMA-NOTES.md. Raise the "
        "ceiling only for a repeated observed failure, named in the raising commit."
    )


def test_extraction_targets_exist():
    for rel, floor in [
        ("docs/architecture/ADR-LEDGER.md", 50_000),
        ("docs/database/SCHEMA-NOTES.md", 10_000),
    ]:
        path = os.path.join(_REPO, rel)
        assert os.path.exists(path), f"{rel} missing — CLAUDE.md points at it."
        assert len(open(path, encoding="utf-8").read()) >= floor, (
            f"{rel} shrank below {floor} chars — the extracted reference "
            "material must not silently evaporate."
        )
