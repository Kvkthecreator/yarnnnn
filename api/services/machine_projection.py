"""The model-consumable projection of a file — ADR-530 / Derived Principle 34.

DP34: *substrate crosses into a model only as text or image, never as the raw
container.* This module is the **one seam** every consumer calls to get a file's
machine-readable form. It adds no principle — DP34 and the ADR-395 derive-registry
already ruled; this is the conformance surface they implied.

**Why it exists** (the live defect, 2026-08-06): the public share view served
`workspace_files.content` verbatim. For a `.md` file that is already text and
looked correct; for an `.html` artifact the content is markup that renders in a
locked iframe and is opaque to every non-browser reader; for a PDF/XLSX/ZIP the
raw bytes were emitted into a `<pre>`. The kind was decided by a filename suffix
test (`endswith('.html') else 'text'`), which asserts that everything not-HTML
IS text — DP34's diagnostic test failing verbatim.

**The one seam (ADR-530 D6)**: callers ask `project_for_machine(...)` and receive
a verdict; they never sniff a suffix and never extract inline. Today the
projection is computed on read. The named scaling step is a *stored* projection —
a derived substrate object carrying `derived_from` (DP32/ADR-395's own pattern),
computed at write, cacheable and revision-pinnable. Because every caller goes
through this function, that becomes a swap inside it rather than a rewrite of
each consumer.

**Extraction is NOT sanitization (ADR-530 D2 — load-bearing).** There is no HTML
sanitizer in this codebase (ADR-513 §1) and this does not become one. The output
is *text*, inserted only as text — never as markup, never into `innerHTML`, never
into a `srcDoc`. A missed edge case here degrades legibility, never safety. The
human rendering path is unchanged and still goes exclusively through
`<iframe sandbox="">`; nothing in this module licenses inlining.
"""

from __future__ import annotations

import html as _html
import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

#: Elements whose *content* is never document prose. Dropped whole — body and all.
_NON_PROSE_ELEMENTS = ("script", "style", "template", "noscript", "svg", "head")

#: Elements that imply a line break when flattened to text.
_BLOCK_ELEMENTS = (
    "p", "div", "section", "article", "header", "footer", "main", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "br", "hr",
    "blockquote", "pre", "figure", "figcaption", "table", "thead", "tbody",
)

#: Registry `text`-family formats whose RAW form is binary. They get a text
#: projection at UPLOAD time (`services.documents.extract_text`, byte-oriented);
#: a content-column read cannot produce one, so this boundary marks them rather
#: than emitting `%PDF-1.4 …` and calling it text (DP34).
_BINARY_TEXT_FAMILY = {"pdf", "docx", "doc"}

_BLOCK_RX = re.compile(
    r"</?(?:" + "|".join(_BLOCK_ELEMENTS) + r")\b[^>]*>", re.IGNORECASE
)
_TAG_RX = re.compile(r"<[^>]+>")
_COMMENT_RX = re.compile(r"<!--.*?-->", re.DOTALL)
_DOCTYPE_RX = re.compile(r"<!doctype[^>]*>", re.IGNORECASE)


@dataclass(frozen=True)
class Projection:
    """What a machine may read of a file.

    strategy: 'text' | 'passthrough' | 'deferred' — the derive-registry verdict.
    text:     the model-consumable text, when strategy == 'text'. None otherwise.
    note:     the honest, human-readable reason when there is no text. DP34's
              anti-silent-drop clause: a format with no strategy is a KNOWN GAP,
              legibly marked — never dropped, never fabricated.
    """

    strategy: str
    text: Optional[str] = None
    note: Optional[str] = None

    @property
    def is_readable(self) -> bool:
        return self.strategy == "text" and bool(self.text)


def file_type_of(path: str) -> str:
    """The extension the derive-registry dispatches on. Never a kind decision —
    the registry decides; this only reads the suffix off the path."""
    leaf = (path or "").rsplit("/", 1)[-1]
    return leaf.rsplit(".", 1)[-1].lower() if "." in leaf else ""


def extract_text_from_html(markup: str) -> str:
    """Flatten HTML markup to its readable prose (ADR-530 D2).

    Extraction, not sanitization: `<script>`/`<style>` BODIES are dropped
    (they are not prose), comments and the doctype go, block elements become
    newlines, remaining tags are removed, and entities are unescaped. The result
    is text and is only ever inserted as text.
    """
    if not markup:
        return ""
    out = _COMMENT_RX.sub(" ", markup)
    out = _DOCTYPE_RX.sub(" ", out)
    # Drop non-prose elements INCLUDING their content — a stylesheet's body is
    # not the document, and `_TAG_RX` alone would leave the CSS text behind.
    for tag in _NON_PROSE_ELEMENTS:
        out = re.sub(
            rf"<{tag}\b[^>]*>.*?</{tag}\s*>", " ", out, flags=re.DOTALL | re.IGNORECASE
        )
        # An unclosed/self-closed form of the same element.
        out = re.sub(rf"<{tag}\b[^>]*/?>", " ", out, flags=re.IGNORECASE)
    out = _BLOCK_RX.sub("\n", out)
    out = _TAG_RX.sub(" ", out)
    out = _html.unescape(out)
    # Collapse horizontal runs, keep paragraph breaks.
    out = re.sub(r"[ \t\r\f\v]+", " ", out)
    out = re.sub(r" *\n *", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


#: The MARKED presentation elements (ADR-449 D2 skin / ADR-453 D2 kernel). Both
#: are machine-composed and re-stamped on every write, so neither can carry a
#: byte a member authored. The UNMARKED layout `<style>` is deliberately absent:
#: it is baked once at `build_skeleton` and never retrofitted, making it the one
#: sheet that could hold a per-artifact edit. Mirrors of `_KERNEL_ELEMENT_RX`
#: (authoring) and `_SKIN_ELEMENT_RX` (design_systems) — matched by their MARK,
#: never by size or position, so a moved or re-versioned element still matches.
_MARKED_STYLE_RX = re.compile(
    r'<style\s+[^>]*data-(?:kernel|skin)="true"[^>]*>.*?</style>',
    re.DOTALL | re.IGNORECASE,
)

#: Left in place of an elided sheet, so a reader sees that a presentation layer
#: was REMOVED rather than that the artifact never had one.
_ELIDED_NOTE = '<!-- {n} chars of machine-composed stylesheet elided for reading -->'


def elide_presentation_css(markup: str) -> tuple[str, int]:
    """Drop the machine-composed stylesheets from markup read AS MARKUP.

    The second projection a machine can need. `extract_text_from_html` answers
    "what does this document SAY" and destroys every tag to do it — right for a
    share view or an index, wrong for a caller that must hand the content back
    through `edit`/`save`, where a `find` string has to match the stored bytes.
    This keeps the artifact editable and removes only the layers no one authored.

    The live defect (ADR-574 §2b, measured 2026-08-28): a Studio deck inlines a
    ~31KB kernel sheet plus a skin ahead of `<body>`, so an MCP `open` capped at
    24,000 chars returned CSS and ZERO authored content — under `success: true,
    found: true`. `deck.html` reached its first slide at char 39,118, 15,118 past
    the cap. Eliding the marked sheets brings the body inside the first window.

    Returns `(markup, chars_elided)`. **Read path only** — never a write door,
    or the ADR-453 D2 retrofit contract would be silently undone on the next save.
    """
    if not markup or "<style" not in markup:
        return markup or "", 0
    elided = 0

    def _sub(m: "re.Match") -> str:
        nonlocal elided
        n = len(m.group(0))
        elided += n
        return _ELIDED_NOTE.format(n=f"{n:,}")

    return _MARKED_STYLE_RX.sub(_sub, markup), elided


def project_for_machine(
    *,
    path: str,
    content: Optional[str],
    file_type: Optional[str] = None,
) -> Projection:
    """The ONE seam: a file's model-consumable projection (ADR-530 D6).

    `file_type` defaults to the path's extension. The verdict comes from the
    ADR-395 derive-registry (`registry_strategy`) — never from a call-site
    suffix test, which is the defect this replaces.
    """
    from services.primitives.extract_text_from_blob import registry_strategy

    ft = (file_type or file_type_of(path)).lower().lstrip(".")
    strategy = registry_strategy(ft)

    if strategy == "passthrough":
        # DP34: an image is already model-consumable — it needs no TEXT
        # projection, and fabricating one would be a lie. Its delivery over the
        # public boundary is named-deferred (ADR-530 D7), so v1 marks it.
        return Projection(
            strategy="passthrough",
            note="This is an image — open it in yarnnn to view it.",
        )

    if strategy != "text":
        # The anti-silent-drop clause. A format with no registered strategy is a
        # KNOWN GAP, said out loud — never a wall of raw bytes (which is what
        # this boundary used to emit).
        return Projection(
            strategy="deferred",
            note="This file type can't be previewed yet — open it in yarnnn to view it.",
        )

    if content is None:
        return Projection(
            strategy="deferred",
            note="This file has no readable content yet.",
        )

    # The binary members of the text family (pdf/docx/doc) reach their text
    # projection through `services.documents.extract_text`, which operates on
    # BYTES at upload time. THIS path receives `workspace_files.content` — already
    # text — so a binary body arriving here has no meaningful text form. Emitting
    # it would be the exact DP34 violation this module exists to close (raw
    # container handed over and assumed readable: `%PDF-1.4 …`). Mark it instead.
    if ft in _BINARY_TEXT_FAMILY:
        return Projection(
            strategy="deferred",
            note="This file type can't be previewed yet — open it in yarnnn to view it.",
        )

    # `text` family. HTML needs flattening; the rest are already prose.
    if ft in {"html", "htm"}:
        text = extract_text_from_html(content)
        if not text:
            return Projection(
                strategy="deferred",
                note="This document has no readable text yet.",
            )
        return Projection(strategy="text", text=text)

    return Projection(strategy="text", text=content)


__all__ = [
    "Projection",
    "project_for_machine",
    "extract_text_from_html",
    "file_type_of",
]
