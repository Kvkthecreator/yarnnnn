"""ADR-574 §2b follow-on — a read VIEW is not the file, and cannot be saved as one.

The elision fix (2026-08-28) made reading a Studio artifact correct and writing
it hazardous. `open` drops the machine-composed stylesheets so authored content
fits the first page; the resulting view is ~31KB short of the file. Every
machine-readable field said otherwise — `truncated: false` and
`content_chars == len(content)` is the signature a caller uses for "I hold the
whole file" — while the only honest description lived in `explanation`, prose,
for a human. A whole-file save of that view deletes the kernel sheet and the
skin, with no error and a revision log recording the caller's intended edit.

Holds:
  §1 the payload distinguishes the VIEW from the FILE
  §2 the write door REFUSES a view, and intent cannot override content
  §3 an ordinary file is unaffected (the guard must not over-refuse)

Script-style (python3, from api/).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
sys.path.insert(0, str(API))

PASS = 0
FAIL = 0


def check(label: str, ok, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}" + (f" — {detail}" if detail else ""))


from services.machine_projection import (  # noqa: E402
    carries_elision_marker,
    elide_presentation_css,
)

_KERNEL = '<style data-kernel="true">' + ("a{b:c}" * 900) + "</style>"
_SKIN = '<style data-skin="true">' + ("d{e:f}" * 300) + "</style>"
_AUTHORED = "<body><h1>Real content</h1></body>"
_FILE = _KERNEL + _SKIN + _AUTHORED

# ═════════════════════════════════════════════════════════════════════════════
print("§1 the marker is the unforgeable trace of a view")
# ═════════════════════════════════════════════════════════════════════════════

_view, _n = elide_presentation_css(_FILE)
check("1a eliding is detectable afterwards", carries_elision_marker(_view))
check("1b the FILE itself is not flagged (no false positive)",
      not carries_elision_marker(_FILE))
check("1c authored bytes survive the view", "Real content" in _view)
check("1d the view really is shorter than the file",
      len(_view) < len(_FILE) and _n > 0, f"elided={_n}")
# ⭐ The detector must not key on the exact character count — that varies per
# artifact, and pinning it would make the guard pass on every OTHER deck.
_other, _ = elide_presentation_css(
    '<style data-kernel="true">' + ("z{y:x}" * 40) + "</style>" + _AUTHORED
)
check("1e detection is count-independent (works on any artifact)",
      carries_elision_marker(_other))
# A file with no marked sheets is returned untouched — elision is not a
# rewrite, so an unmarked artifact must be byte-identical.
_plain, _pn = elide_presentation_css("<body><p>plain</p></body>")
check("1f an unmarked file is untouched",
      _plain == "<body><p>plain</p></body>" and _pn == 0)

# ═════════════════════════════════════════════════════════════════════════════
print("§2 the write door refuses a view; intent cannot override content")
# ═════════════════════════════════════════════════════════════════════════════

import services.mcp_composition as mc  # noqa: E402
from types import SimpleNamespace  # noqa: E402


class _Client:
    """A workspace holding exactly one artifact, whose stored bytes include the
    stylesheets. Enough for the save door to find a head and size it."""

    def __init__(self):
        self._t = None

    def table(self, n):
        self._t = n
        return self

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def execute(self):
        # ⚠️ The save door resolves its HEAD from `workspace_file_versions`,
        # not `workspace_files`. A double that answers only the latter leaves
        # `head` None, every head-gated guard is skipped, and the test reaches
        # the write and fails with `write_failed` — passing or failing for
        # reasons that have nothing to do with the guard. Answering both is
        # what makes §2 observe the branch it names.
        if self._t == "workspace_file_versions":
            return SimpleNamespace(data=[{
                "id": "rev-1", "path": "/workspace/ops/deck.html",
                "blob_sha": "deadbeef", "created_at": "2026-08-28T00:00:00Z",
                "authored_by": "member:u-1",
            }])
        if self._t == "workspace_files":
            return SimpleNamespace(data=[{
                "content": _FILE, "content_bytes": len(_FILE),
                "path": "/workspace/ops/deck.html", "updated_at": "2026-08-28T00:00:00Z",
            }])
        return SimpleNamespace(data=[])


_auth = SimpleNamespace(client=_Client(), user_id="u-1", workspace_id="ws-1",
                        caller_identity="yarnnn:mcp:test", headless=False)


def _save(content, **kw):
    return asyncio.new_event_loop().run_until_complete(
        mc.compose_save(_auth, "ops/deck.html", content, **kw)
    )


_r = _save(_view, confirm_full_replace=True)
# ⭐⭐⭐ THE LOAD-BEARING ROW. `confirm_full_replace` states INTENT ("I mean to
# replace the whole file"); the marker states a fact about the CONTENT (it is
# missing bytes the caller never saw). Intent cannot confirm a mistake, so the
# strongest override in the API must still fail here.
check("2a a view is refused EVEN with confirm_full_replace",
      _r.get("success") is False and _r.get("error") == "elided_content_save",
      f"got success={_r.get('success')} error={_r.get('error')}")
check("2b the refusal names `edit` as the remedy that works",
      "edit" in (_r.get("message") or "").lower())

# ⭐ Ordering matters: this check must precede the SIZE guard, because paging
# can satisfy the size guard and can never satisfy this one. If size ran first,
# a caller would be told to page — and would come back with an elided view
# again, having followed the instructions.
_r2 = _save(_view)
check("2c the view refusal beats the size guard (paging cannot fix it)",
      _r2.get("error") == "elided_content_save",
      f"got {_r2.get('error')}")

# ═════════════════════════════════════════════════════════════════════════════
print("§3 the guard does not over-refuse")
# ═════════════════════════════════════════════════════════════════════════════

# Authored content that merely MENTIONS stylesheets is not a view. The guard
# keys on the marker's own sentence, so ordinary prose about CSS saves fine.
_prose = "<body><p>We elided the stylesheet from the design doc.</p></body>"
check("3a prose mentioning stylesheets is not mistaken for a view",
      not carries_elision_marker(_prose))

_src = (API / "services" / "mcp_composition.py").read_text()
# The payload must carry BOTH numbers. One number cannot answer both "how much
# is left to read" and "is this the file".
check("3b `open` serves stored_chars beside content_chars",
      '"stored_chars"' in _src and '"content_chars"' in _src)
check("3c `open` serves complete_for_write", '"complete_for_write"' in _src)
# ⭐ It must be computed from BOTH halves. `not truncated` alone was the old
# lie; `elided == 0` alone would call a truncated read complete.
check("3d complete_for_write requires un-truncated AND un-elided",
      "(not truncated) and elided == 0" in _src)
# The stale remedy: the size guard used to promise paging to `truncated: false`
# yields a saveable read. After elision it does not.
check("3e the size guard's remedy names complete_for_write, not truncated",
      "until complete_for_write is true" in _src)

_schema = (API / "mcp_server" / "server.py").read_text()
check("3f the tool schema documents the view/file split",
      "stored_chars" in _schema and "complete_for_write" in _schema)
check("3g the schema no longer calls content_chars the file's full length",
      "`content_chars` is the\n    file's full length" not in _schema)

print()
print(f"{PASS}/{PASS + FAIL} view-is-not-the-file assertions pass")
sys.exit(1 if FAIL else 0)
