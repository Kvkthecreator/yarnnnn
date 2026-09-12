"""Prompt changelog discipline (2026-09-12).

api/prompts/CHANGELOG.md had grown to 732 entries / 1.57MB, prepended by some
sessions and appended by others (three September entries sat below February's),
with nine duplicate tags and a template block buried inside the oldest entry.
The record is kept whole; its SHAPE is held here:

  (a) the live file holds the newest two calendar months, newest first, tags unique;
  (b) every `## ` heading in the live file is an entry tag;
  (c) an entry stays under ENTRY_CEILING chars — the essay belongs in the ADR;
  (d) older months are frozen in api/prompts/archive/YYYY-MM.md, each holding only
      its month, newest first, none inside the live window; the archive as a whole
      never shrinks below ARCHIVE_FLOOR chars (the record must not evaporate).

Run: python3 -m pytest api/test_prompt_changelog_discipline.py -q
"""
from __future__ import annotations

import os
import re

_API = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.join(_API, "prompts", "CHANGELOG.md")
ARCHIVE_DIR = os.path.join(_API, "prompts", "archive")

ENTRY_CEILING = 6_000
ARCHIVE_FLOOR = 1_400_000

_TAG = re.compile(r"^## \[(\d{4})\.(\d{2})\.(\d{2})\.(\d+)([a-z]?)\] - ", re.M)
_H2 = re.compile(r"^## .*$", re.M)


def _entries(path: str) -> list[tuple[tuple, str]]:
    text = open(path, encoding="utf-8").read()
    parts = _TAG.split(text)
    out = []
    for i in range(1, len(parts), 6):
        y, m, d, n, sfx, body = parts[i : i + 6]
        out.append(((int(y), int(m), int(d), int(n), sfx), body))
    return out


def _prev_month(ym: tuple[int, int]) -> tuple[int, int]:
    y, m = ym
    return (y - 1, 12) if m == 1 else (y, m - 1)


def _live_window() -> set[tuple[int, int]]:
    newest = max(k[:2] for k, _ in _entries(LIVE))
    return {newest, _prev_month(newest)}


def test_live_headings_are_tags_and_newest_first():
    text = open(LIVE, encoding="utf-8").read()
    h2 = _H2.findall(text)
    tags = _TAG.findall(text)
    assert len(h2) == len(tags), (
        f"{len(h2) - len(tags)} `## ` heading(s) in CHANGELOG.md are not entry tags "
        "([YYYY.MM.DD.N] - …); the template's home is CLAUDE.md, sub-headings use ###."
    )
    keys = [k for k, _ in _entries(LIVE)]
    assert len(keys) >= 10, f"only {len(keys)} entries parsed — the regex stopped matching, not the file"
    for a, b in zip(keys, keys[1:]):
        assert a > b, f"CHANGELOG.md is not newest-first / tags not unique at {a} -> {b}: prepend, and count N up within the day"


def test_live_holds_two_months():
    window = _live_window()
    outside = sorted({k[:2] for k, _ in _entries(LIVE)} - window)
    assert not outside, (
        f"CHANGELOG.md holds months {outside} outside its two-month window {sorted(window)}: "
        "move each such month verbatim into api/prompts/archive/YYYY-MM.md"
    )


def test_live_entries_stay_bounded():
    fat = [(k, len(b)) for k, b in _entries(LIVE) if len(b) > ENTRY_CEILING]
    assert not fat, f"entries over {ENTRY_CEILING} chars: {fat} — the essay belongs in the ADR"


def test_archive_months_are_frozen_and_whole():
    files = sorted(f for f in os.listdir(ARCHIVE_DIR) if re.fullmatch(r"\d{4}-\d{2}\.md", f))
    assert len(files) >= 6, f"archive has {len(files)} month files — the roll-out must not evaporate"
    window = _live_window()
    total = 0
    for f in files:
        ym = (int(f[:4]), int(f[5:7]))
        assert ym not in window, f"archive/{f} is inside the live window {sorted(window)}"
        entries = _entries(os.path.join(ARCHIVE_DIR, f))
        assert entries, f"archive/{f} parsed no entries"
        wrong = [k for k, _ in entries if k[:2] != ym]
        assert not wrong, f"archive/{f} holds entries from other months: {wrong[:3]}"
        for a, b in zip(entries, entries[1:]):
            assert a[0] >= b[0], f"archive/{f} not newest-first at {a[0]} -> {b[0]}"
        total += sum(len(b) for _, b in entries)
    assert total >= ARCHIVE_FLOOR, f"archive holds {total} chars (< {ARCHIVE_FLOOR}) — archived entries were dropped"
