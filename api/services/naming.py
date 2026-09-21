"""Naming — the ONE place a member's typed name becomes a path segment.

ADR-469. The rule this module encodes is the split ADR-459 D2 could not make
while the folder had to carry the name:

  • The PATH is an identity key — ASCII, lowercase, collision-free, machine
    facing. `(workspace_id, path)` is the substrate's binding unit (ADR-373),
    the single-writer unit (ADR-286), and the revision-chain key (ADR-209). It
    must be injective; it does not have to be readable.
  • The NAME is a fact the artifact carries — its own `<title>`, unicode and
    exact (`services/authoring.py::extract_title`). It must be readable; it does
    not have to be unique.

Neither impersonates the other. Before this split, one lossy `[^a-z0-9]+` slug
tried to be both, and under a name with no Latin characters it stopped being
injective: four distinct Korean names all produced `untitled`, so distinct
documents collided on one path. See
`docs/analysis/what-a-thing-is-called-vs-how-its-stored-2026-07-20.md`.

Why the transliteration stays deliberately dumb: a slug that tried to romanize
(`한글` → `hangeul`) would be guessing, and guessing wrong is worse here than
being opaque — the key is not read by anyone. `untitled` is an honest key.
Only its COLLISIONS needed fixing, not its unreadability.

Scope: this names things a MEMBER reads. Internal identifier derivation
(`mcp_composition._slugify` for entity matching, `routes/lanes.py` for agent
slugs) is a different job with different constraints and is deliberately NOT
routed through here.
"""

from __future__ import annotations

import re
import unicodedata

#: Cap on a generated path segment. Long enough to stay readable for Latin
#: names, short enough to keep paths sane.
MAX_SLUG_LEN = 48

#: The honest key for a name that romanizes to nothing (a fully non-Latin
#: name). Never shown to a member — the artifact's <title> is what they read.
FALLBACK_SLUG = "untitled"


def nfc(text: str) -> str:
    """Normalize a path or a path segment to Unicode NFC. The ONE spelling.

    A non-Latin name has two byte forms that render identically. `한` is either
    one composed syllable (NFC, 3 bytes) or three combining jamo (NFD, 9 bytes),
    and nothing compares them equal — not Python, not Postgres
    (`'한글' = normalize('한글', NFD)` is false), not git.

    macOS decomposes filenames, so a Korean file uploaded from Finder arrives
    NFD while the same name typed in the browser arrives NFC. Measured on
    production 2026-09-21: of four Hangul paths in `workspace_files`, two were
    NFC (authored in-app) and two NFD (uploaded), and each was findable ONLY in
    the form it was stored in. `path` is the substrate's binding unit
    (ADR-373), the single-writer unit (ADR-286) and the revision-chain key
    (ADR-209) — so two spellings of one name are two identities, two revision
    chains, and a file an agent is told about but cannot open.

    NFC is the target because it is what the web produces and what the W3C
    specifies for identifiers; normalizing toward it moves the rarer form.

    Applied at the DOORS a path enters through, never at the read of an already
    stored path: normalizing on read would make a legacy NFD row unfindable by
    its own stored spelling. The doors are the upload slug
    (`services/documents.py::_filename_to_slug`) and the interop chokepoint
    (`services/mcp_composition.py::parse_file_reference`), whose TypeScript
    twin `web/lib/interop/fileHandle.ts::parseFileReference` does the same.

    Pure and total — safe for a gate to call. ASCII is returned unchanged, so
    this is a no-op for every Latin path in the system.
    """
    return unicodedata.normalize("NFC", text or "")


def path_slug(name: str) -> str:
    """A member's typed name → an ASCII path segment (the identity key).

    `IR deck v3` → `ir-deck-v3`. `한글 문서` → `untitled`. `Émile` → `emile`
    (accents fold to their base letter rather than being deleted, so `café`
    reads `cafe` instead of the old `caf`).

    NOT injective on its own — `path_slug` is a key CANDIDATE. Uniqueness is
    the caller's job via `disambiguate`, because only the caller knows what
    already exists.
    """
    # NFKD splits an accented letter into base + combining mark, so dropping
    # the marks folds `é`→`e` instead of deleting the whole character.
    folded = unicodedata.normalize("NFKD", name or "")
    ascii_only = folded.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)[:MAX_SLUG_LEN].strip("-")
    return slug or FALLBACK_SLUG


def disambiguate(slug: str, taken: set[str] | frozenset[str]) -> str:
    """Make `slug` unique against `taken` by suffixing `-2`, `-3`, …

    This is what makes the fallback safe: a member working entirely in Korean
    gets `untitled`, `untitled-2`, `untitled-3` — distinct keys, each reading
    back as the name they actually typed. Without it their second document
    would collide on the first's path.

    The suffix respects MAX_SLUG_LEN by trimming the stem, so a long name plus
    a suffix can never exceed the cap.
    """
    if slug not in taken:
        return slug
    n = 2
    while True:
        suffix = f"-{n}"
        stem = slug[: MAX_SLUG_LEN - len(suffix)].strip("-") or FALLBACK_SLUG
        candidate = f"{stem}{suffix}"
        if candidate not in taken:
            return candidate
        n += 1
