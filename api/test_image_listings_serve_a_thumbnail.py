"""An image in a LISTING serves a thumbnail, not a format glyph (2026-08-27).

THE DEFECT THIS GATE EXISTS FOR
===============================
Every image in the Files surface rendered as a generic green glyph while its
bytes sat healthy in the CAS. Operator-observed twice — first in a folder view,
then in Recents after the bytes were confirmed intact.

Nothing was broken in the renderer. `FileTile.Preview` draws a real thumbnail
whenever `thumb.content_url` is set, and it had done so since 2026-07-02. The
listings simply never fed it:

  - `workspace_files.content_url` is NULL for every CAS-backed binary BY
    CONTRACT (ADR-427 D4: the serving capability is MINTED AT READ, never
    stored). Forwarding that column therefore forwards NULL, forever.
  - The per-file door (`GET /workspace/file`) already minted. The LISTINGS —
    which are where files are actually looked at — did not.

So the surface said "this file has no preview" about a 900KB PNG. That is the
ADR-373 D6 incorrect-success shape in the read path: an affordance ABSENT
rather than refused, which reads to the operator as "the product can't do this."

WHAT THIS GATE PINS
===================
Not the mint itself (an implementation detail that may move) but the SEAM that
kept failing: a listing that carries images must (a) select the column the mint
keys on, (b) actually call the mint, and (c) carry BOTH fields the tile needs
through to its response shape. Half of that wiring is worse than none — it
looks done and draws nothing.

Run directly: `python3 test_image_listings_serve_a_thumbnail.py` from `api/`.
"""

import re
import sys
from pathlib import Path

_API = Path(__file__).resolve().parent
_passed = True


def check(label: str, cond: bool, detail: str = "") -> None:
    global _passed
    print(f"  {'ok  ' if cond else 'FAIL'} {label}" + (f"  [{detail}]" if detail and not cond else ""))
    if not cond:
        _passed = False


def code_only(src: str) -> str:
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    src = re.sub(r"'''[\s\S]*?'''", "", src)
    return re.sub(r"(^|\s)#[^\n]*", " ", src)


_src = code_only((_API / "routes" / "workspace.py").read_text())

print("\n── the mint exists and is the ONE implementation ──")

_mint = re.search(r"def mint_thumb_urls\(.*?(?=\ndef )", _src, re.DOTALL)
check("mint_thumb_urls is readable", _mint is not None)
if _mint:
    body = _mint.group(0)
    check(
        "it mints rather than forwarding the stored column",
        "mint_serving_url" in body,
    )
    # ADR-427 D4 again: a STORED capability is the thing the contract forbids.
    check(
        "[FALSIFIER] it is BATCHED, never one query per row",
        ".in_(" in body and body.count("mint_serving_url") == 1,
        "an N+1 mint across a 500-row subtree is a real cost on every load",
    )
    # Restricted to what a tile can draw. A listing of PDFs must mint nothing.
    check(
        "[FALSIFIER] only IMAGE rows are minted",
        'startswith("image/")' in body,
    )
    # A preview is enrichment; it must never be able to fail the listing.
    # Asserted on the EXCEPT BLOCK ITSELF, not on "the words appear somewhere in
    # the function". The loose form passed vacuously against a real `raise`,
    # because an earlier `return {}` (the no-images short-circuit) satisfied it.
    # Matched against RAW source, not the comment-stripped copy: stripping the
    # trailing `# noqa` comment off the `except` line collapses the line
    # structure this regex depends on, and the check went red against correct
    # code. Comment-stripping protects against prose SATISFYING a check; here
    # the risk runs the other way.
    _raw_mint = re.search(
        r"def mint_thumb_urls\(.*?(?=\ndef )",
        (_API / "routes" / "workspace.py").read_text(),
        re.DOTALL,
    )
    # Anchored on the LINE END, not on `:\n`. The `except` line here ends in a
    # `# noqa` comment, so the colon is mid-line and `[^\n]*:` (greedy) ate it —
    # the pattern could never match and the check went red against correct code.
    # `(?:\n|$)` on the last line because the handler is the function's final
    # statement.
    _handler = re.search(
        r"except Exception[^\n]*\n((?:[ \t]+[^\n]*(?:\n|$))+)", _raw_mint.group(0)
    ) if _raw_mint else None
    check(
        "[FALSIFIER] a mint failure degrades to the glyph, never raises",
        _handler is not None
        and "return {}" in _handler.group(1)
        and "raise" not in _handler.group(1),
    )

print("\n── BOTH listings feed the tile (the per-file door already did) ──")

# The two listings that draw tiles. Each must select the key, call the mint, and
# emit the url. Asserted per-listing because either one alone leaves half the
# surface glyphed — which is exactly the state the operator met twice.
for label, anchor in (
    ("Recents", r"async def get_recent_revisions\(.*?(?=\n@router|\ndef |\Z)"),
    ("the folder tree", r"async def get_workspace_tree\(.*?(?=\n@router|\ndef |\Z)"),
):
    m = re.search(anchor, _src, re.DOTALL)
    check(f"{label}: handler is readable", m is not None)
    if not m:
        continue
    body = m.group(0)
    check(
        f"{label}: selects head_version_id (the mint keys on it)",
        "head_version_id" in body,
        "without it the mint has nothing to resolve and silently returns {}",
    )
    check(
        f"{label} [FALSIFIER]: actually CALLS the mint",
        "mint_thumb_urls(" in body,
        "the renderer was always complete — this call is the whole fix",
    )

print("\n── the tile needs BOTH fields, so both must survive to the response ──")

# The tile picks its lane by content_type and draws from content_url. Serving
# one without the other leaves the thumbnail unreachable while LOOKING wired.
# ANCHORED INSIDE _build_tree, not on a bare `files.append({`. The loose
# pattern matched `synthesis_files.append({` 2700 lines earlier — an unrelated
# block that carries neither field — so the assertion went red against code
# that was correct. A slice-scoped assertion has to be scoped to the slice it
# means, or it reports on the wrong region with total confidence.
_builder = re.search(r"def _build_tree\(.*?(?=\ndef |\Z)", _src, re.DOTALL)
_tree_node = (
    re.search(r"\n        files\.append\(\{(.*?)\}\)", _builder.group(0), re.DOTALL)
    if _builder
    else None
)
check("the tree's file node is readable", _tree_node is not None)
if _tree_node:
    node = _tree_node.group(1)
    check(
        "[FALSIFIER] the tree's file node carries content_url AND content_type",
        '"content_url"' in node and '"content_type"' in node,
        "one without the other renders nothing but reads as done",
    )

# Recents' response model must expose the field at all.
_model = re.search(r"class RecentRevision\(.*?(?=\nclass )", _src, re.DOTALL)
check(
    "[FALSIFIER] the Recents response model exposes content_url + content_type",
    _model is not None
    and "content_url" in _model.group(0)
    and "content_type" in _model.group(0),
)

print("\n" + ("thumbnail-listing gate GREEN" if _passed else "thumbnail-listing gate RED"))
sys.exit(0 if _passed else 1)
