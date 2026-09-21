#!/usr/bin/env python3
"""Gate — one Unicode spelling for a path, at every door it enters through.

    python3 test_nfc_one_unicode_spelling.py

## What this defends

A non-Latin name has two byte forms that render IDENTICALLY. `한` is either one
composed syllable (NFC, 3 bytes) or three combining jamo (NFD, 9 bytes), and
nothing compares them equal — not Python, not Postgres
(`'한글' = normalize('한글', NFD)` is false), not git, which stores path bytes
verbatim.

macOS decomposes filenames. So a Korean file uploaded from Finder arrives NFD
while the same name typed in the browser arrives NFC, and the two address
different files. Measured on production 2026-09-21: of four Hangul paths in
`workspace_files`, **two were NFC (authored in-app) and two NFD (uploaded)**,
and each was findable ONLY in the form it was stored in.

`path` is the substrate's binding unit (ADR-373), the single-writer unit
(ADR-286) and the revision-chain key (ADR-209). Two spellings of one name are
therefore two identities, two revision chains, and a file an agent can be told
about but cannot open. This is a key-integrity gate, not a display one.

## Why the checks are shaped this way

- The doors are asserted by DRIVING the real functions over a Hangul pair, never
  by grepping for `normalize` — a call can be present and on the wrong side of a
  return, and `services/documents.py::_filename_to_slug` is the proof: it kept
  `\\w` (which MATCHES Hangul in Python) and passed every existing check while
  writing two spellings into `path`.
- ASCII is asserted UNCHANGED, because the cheapest wrong fix here is one that
  quietly rewrites every Latin path in the system.
- Normalization is asserted to happen at the DOORS ONLY. Normalizing when
  READING an already-stored path would make the two legacy NFD rows unfindable
  by their own stored spelling — a migration's job, not a resolver's.
- The refusals are re-asserted, because a normalization inserted at the wrong
  point in `parse_file_reference` could fold a traversal into an accepted name.

The TS twin (`web/lib/interop/fileHandle.ts::parseFileReference`) is held by
`test_adr587_handle_grammar_parity.py`, which DRIVES both implementations over
one table under node. ⚠️ That gate's TS half was DEAD from 2026-09-17 (ee5f6f0)
until 2026-09-21: a `Readonly<Record<…>>` annotation defeated its type-stripper,
node refused the module, and the parity half silently stopped running while the
gate still reported a count. Repaired in the same commit as this file.
"""

import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

_passed = 0
_failed = 0


def check(label: str, ok: bool, detail: str = "") -> bool:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"  ok   {label}")
    else:
        _failed += 1
        print(f"  FAIL {label}" + (f" — {detail}" if detail else ""))
    return ok


def nfd(s: str) -> str:
    return unicodedata.normalize("NFD", s)


def is_nfc(s: str) -> bool:
    return s == unicodedata.normalize("NFC", s)


print("NFC — one Unicode spelling for a path, at every door")
print()

# --- the helper ------------------------------------------------------------
print("The helper")
from services.naming import nfc  # noqa: E402

check("nfc() folds NFD to NFC", nfc(nfd("한국어")) == "한국어")
check("nfc() is idempotent", nfc(nfc(nfd("한국어"))) == nfc(nfd("한국어")))
check("nfc() leaves ASCII untouched", nfc("operation/gtm.md") == "operation/gtm.md")
check("nfc() tolerates empty/None-ish", nfc("") == "" and nfc(None) == "")  # type: ignore[arg-type]

# --- door 1: the interop chokepoint ---------------------------------------
print()
print("Door 1 — parse_file_reference (ADR-588 D2, the one interop chokepoint)")
from services.mcp_composition import parse_file_reference  # noqa: E402

KO = "operation/한국어-커넥터-테스트.md"
check(
    "the two spellings of one Korean path resolve identically",
    parse_file_reference(KO) == parse_file_reference(nfd(KO)),
    f"{parse_file_reference(KO)!r} != {parse_file_reference(nfd(KO))!r}",
)
check(
    "the resolved path is NFC, whichever form arrived",
    is_nfc(parse_file_reference(nfd(KO)) or ""),
)
check(
    "every accepted spelling agrees (bare / absolute / yarnnn:// handle)",
    len({
        parse_file_reference(nfd(KO)),
        parse_file_reference(nfd("/workspace/" + KO)),
        parse_file_reference(nfd("yarnnn://workspace/" + KO)),
    }) == 1,
)
check(
    "a told-name home still resolves under NFD (ADR-588 D2 survives)",
    parse_file_reference(nfd("Documents/한국어.md")) == nfc("operation/한국어.md"),
)

# ASCII must be a no-op — the cheapest wrong fix rewrites every Latin path.
_ascii = {
    "operation/gtm.md": "operation/gtm.md",
    "/workspace/a/b.md": "a/b.md",
    "yarnnn://workspace/a/b.md": "a/b.md",
    "Documents/x.md": "operation/x.md",
}
check(
    "ASCII paths are unchanged (a no-op for every Latin path)",
    all(parse_file_reference(k) == v for k, v in _ascii.items()),
    "; ".join(f"{k}->{parse_file_reference(k)}" for k in _ascii),
)

# Normalization must not fold a refusal into an accepted name.
_refusals = ["", "   ", "../x.md", "operation/../../etc", "https://evil.example/x"]
check(
    "the refusals still refuse",
    all(parse_file_reference(r) is None for r in _refusals),
    "; ".join(f"{r!r}->{parse_file_reference(r)!r}" for r in _refusals),
)
check(
    "a traversal spelled in NFD is still refused",
    parse_file_reference(nfd("한국어/../../etc")) is None,
)

# --- door 2: the upload slug ----------------------------------------------
print()
print("Door 2 — the upload filename slug (where the two live NFD rows came from)")
from services.documents import _filename_to_slug  # noqa: E402

UP = "배출증-출력.pdf"
check(
    "a Finder upload and a typed name produce ONE slug",
    _filename_to_slug(UP) == _filename_to_slug(nfd(UP)),
    f"{_filename_to_slug(UP)!r} != {_filename_to_slug(nfd(UP))!r}",
)
check(
    "the slug is NFC",
    is_nfc(_filename_to_slug(nfd(UP))),
)
check(
    "an ASCII filename slugs exactly as before",
    _filename_to_slug("Acme Brief v2.pdf") == "acme-brief-v2",
    _filename_to_slug("Acme Brief v2.pdf"),
)

# --- the read path stays untouched ----------------------------------------
print()
print("Reads are NOT normalized — a legacy NFD row stays findable by its own name")
import inspect  # noqa: E402

from services import workspace as _ws  # noqa: E402

_read_src = inspect.getsource(_ws)
check(
    "services/workspace.py does not normalize on read",
    "unicodedata" not in _read_src and ".normalize(" not in _read_src,
    "a read-side fold would orphan the two legacy NFD rows",
)

# --- the TS twin is actually driven ---------------------------------------
print()
print("The TS twin is driven, not assumed (ADR-587 parity)")
_parity = Path(__file__).resolve().parent / "test_adr587_handle_grammar_parity.py"
_psrc = _parity.read_text()
check(
    "the parity gate's type-stripper handles a generic annotation",
    "Readonly<" in _psrc and "the TS half of a PARITY gate silently" in _psrc,
    "without this the TS module fails to execute and parity is unverified",
)
check(
    "the TS twin normalizes too",
    "normalize('NFC')" in (Path(__file__).resolve().parent.parent
                           / "web/lib/interop/fileHandle.ts").read_text(),
)

print()
print(f"  {_passed} passed, {_failed} failed")
if _failed:
    print()
    print("✗ a path can enter the substrate in two Unicode spellings")
    sys.exit(1)
print()
print("✓ one Unicode spelling at every door")
