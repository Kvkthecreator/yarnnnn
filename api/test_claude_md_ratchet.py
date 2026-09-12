"""CLAUDE.md ablation ratchet.

2026-07-30 (9ae0f56): 155K -> ~46K chars by extracting reference material to
docs/architecture/ADR-LEDGER.md + docs/database/SCHEMA-NOTES.md.
2026-09-12: 50.7K -> 16360 chars — the per-ADR ⭐ rows (already in the ledger),
the archived-seat sections and the stale pointers were cut; the file is
instruction-only. The ceiling ratchets DOWN with each cut; an ungated cut regrows.

  (a) CLAUDE.md stays under the char ceiling.
  (b) The two extraction targets exist and are non-trivial.
  (c) Every repo path CLAUDE.md cites exists — a pointer that dangles is a
      reference sweep nobody ran (invocation-and-narrative.md was cited as
      canonical for weeks after it moved to previous_versions/).

Raising the ceiling requires the same evidence as adding a prompt instruction
(ADR-306 / DP22): a REPEATED observed failure that new instruction text fixes,
named in the commit that raises it. Reference material goes to the ledger or
schema notes, not here.

Run: python3 -m pytest api/test_claude_md_ratchet.py -q
"""
from __future__ import annotations

import os
import re

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CLAUDE_MD = os.path.join(_REPO, "CLAUDE.md")

CLAUDE_MD_CEILING = 19000

_PREFIX = r"(?:docs|api|web|scripts|supabase|\.claude)/"
_CITED = re.compile(r"`(" + _PREFIX + r"[^`\s]+)`|\]\((" + _PREFIX + r"[^)\s]+)\)")


def _cited_paths(text: str) -> list[str]:
    out = []
    for m in _CITED.finditer(text):
        raw = (m.group(1) or m.group(2)).split("::")[0].split("#")[0]
        if any(ch in raw for ch in "*{}"):
            continue  # a pattern, not a path
        out.append(raw)
    return sorted(set(out))


def test_claude_md_under_ceiling():
    size = len(open(_CLAUDE_MD, encoding="utf-8").read())
    assert size <= CLAUDE_MD_CEILING, (
        f"CLAUDE.md is {size} chars (> {CLAUDE_MD_CEILING}). Instruction content stays; "
        "reference material moves to docs/architecture/ADR-LEDGER.md or docs/database/SCHEMA-NOTES.md. "
        "Raise the ceiling only for a repeated observed failure, named in the raising commit."
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


def test_cited_paths_exist():
    cited = _cited_paths(open(_CLAUDE_MD, encoding="utf-8").read())
    assert len(cited) >= 40, f"only {len(cited)} cited paths found — the regex stopped matching, not the file"
    missing = [p for p in cited if not os.path.exists(os.path.join(_REPO, p))]
    assert not missing, (
        "CLAUDE.md cites paths that do not exist — fix the pointer or delete the row: "
        + ", ".join(missing)
    )
