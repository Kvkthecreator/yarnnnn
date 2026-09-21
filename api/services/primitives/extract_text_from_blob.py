"""
ExtractTextFromBlob Primitive — ADR-395 Piece B (the derive-registry, entry 1)

The mechanical "make a retained raw blob model-consumable" primitive. DP34: a
model reads only a projection {text|image}, never the raw container — so a
retained upload blob (PDF/DOCX/…) needs a TEXT PROJECTION derived from it. This
primitive is that derive step: read the blob, extract text, write a searchable
projection that CITES the raw via `derived_from` (DP32), and embed it.

Zero LLM, deterministic. The FIRST entry of the derive-registry (ADR-395 D2):
MIME→strategy is `{pdf,docx,xlsx,pptx,txt,md,csv,html}→text`; image/* is already
model-consumable (pass-through, no projection needed); `{zip,audio}` and any
unrecognised format are named-deferred (retained-but-not-yet-consumable).

Trigger-agnostic (ADR-395 refined): the upload path invokes it INLINE on
arrival (a one-shot); a future cadenced caller could invoke it from the capture
lane. It never reads the clock and never fetches unless it must — the upload
caller passes the already-extracted `text` so the blob isn't re-parsed.

Surface:
  ExtractTextFromBlob(
      raw_path: str,               # the retained raw's substrate path (the cited source)
      write_to: str,               # where the derived text projection lands
      text: str = None,            # pre-extracted text (upload path passes it; else fetched)
      storage_path: str = None,    # private-bucket key to fetch+extract when `text` absent
      file_type: str = None,       # extension for the extractor when fetching
      source_filename: str = None, # for the projection's human header
  )

Attribution: `system:extract` (the derive is mechanism, not a principal —
ADR-288). The RAW is the operator's; this writes only the derived projection.

Dispatch surfaces (same policy as SyncPlatformState/CaptureConnector, ADR-264 D3):
  HEADLESS_PRIMITIVES + FREDDIE_PRIMITIVES; NOT CHAT_PRIMITIVES (operators don't
  invoke the derive directly — it runs inline on upload, or from the lane).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


# The derive-registry (ADR-395 D2), entry 1. MIME/extension → strategy. Only
# `text` is implemented in Phase 1; `passthrough` needs no projection; `deferred`
# means retained-but-not-yet-consumable (DP34 — a known gap, never a drop).
#
# ADR-530 D1: `html`/`htm` join the text family. A yarnnn artifact is very often
# HTML (the Studio authoring apps emit it), and its markup is NOT what a model
# reads — DP34. The extraction lives in `html_text.py`; see ADR-530 D2 for why
# extraction is not sanitization and never licenses inlining.
#
# ADR-395 am.1 D10: `xlsx`/`pptx` LEAVE the deferred set and join the text
# family — deterministic, in-process, no sandbox (openpyxl / python-pptx, the
# ADR-417 §2c "a library, not a service" shape). Their extractors live beside
# the pdf/docx ones in `services/documents.py`.
_TEXT_FORMATS = {"pdf", "docx", "doc", "txt", "md", "csv", "html", "htm", "xlsx", "pptx"}
_PASSTHROUGH_FORMATS = {"png", "jpg", "jpeg", "gif", "webp"}  # already model-consumable
#: Named-deferred: retained, legibly marked, never silently dropped (D3/am.1 D9).
#: NOT the gate — `registry_strategy` defers anything it does not recognise, so
#: this set is documentation of the formats we have MET and not yet read.
_DEFERRED_FORMATS = {"zip", "mp3", "wav", "m4a"}


def registry_strategy(file_type: Optional[str]) -> str:
    """The derive-registry verdict for a format (ADR-395 D2 / DP34).

    Returns 'text' | 'passthrough' | 'deferred'. A format we've never heard of
    is 'deferred' too (retained-but-not-yet-consumable — legibly a known gap,
    never silently dropped or fabricated).
    """
    ft = (file_type or "").lower().lstrip(".")
    if ft in _TEXT_FORMATS:
        return "text"
    if ft in _PASSTHROUGH_FORMATS:
        return "passthrough"
    return "deferred"


def _deferred_note(file_type: Optional[str], *, had_strategy: bool) -> str:
    """The retained-not-consumable sentence (ADR-395 am.1 D9 / ADR-530 D3).

    Says which of the two things happened, because they have different remedies:
    a format we cannot read yet may become readable; a file that yielded no text
    is likely scanned or purely visual, and the member may want to act on it.
    Never fabricates content and never guesses at what the file contains.
    """
    ft = (file_type or "").lower().lstrip(".") or "this file"
    if had_strategy:
        return (
            f"NOTE: No text could be read from this {ft} file. It is retained in full "
            f"and can be opened, downloaded and shared — but its contents are not "
            f"available to an agent. A scanned document or an image-only file reads "
            f"this way."
        )
    return (
        f"NOTE: This is a {ft} file. It is retained in full and can be opened, "
        f"downloaded and shared — but yarnnn cannot yet read its contents, so its "
        f"text is not available to an agent."
    )


EXTRACT_TEXT_FROM_BLOB_TOOL = {
    "name": "ExtractTextFromBlob",
    "description": """Derive a model-consumable TEXT projection from a retained raw blob, citing the raw (ADR-395 / DP34).

A retained upload/blob (PDF, DOCX, …) is not something a model can read — DP34:
a model reads text or images, never the raw container. This primitive derives
the text projection: extract text from the blob and write a searchable
derivation that carries `derived_from: <raw_path>` (DP32) and is embedded for
recall. Zero LLM, deterministic.

The derive-registry: {pdf,docx,xlsx,pptx,txt,md,csv,html}→text; images are
already model-consumable (pass-through); {zip,audio} and anything unrecognised
are deferred (retained-but-not-yet-consumable — marked, never a silent drop).

Typical usage — invoked INLINE by the upload path on arrival (a one-shot),
passing the already-extracted text so the blob is not re-parsed:
  ExtractTextFromBlob(
    raw_path="/workspace/inbound/uploads/acme-brief.pdf",
    write_to="/workspace/inbound/uploads/acme-brief.extracted.md",
    text="<extracted text>",
    source_filename="acme-brief.pdf",
    file_type="pdf"
  )""",
    "input_schema": {
        "type": "object",
        "properties": {
            "raw_path": {
                "type": "string",
                "description": "The retained raw blob's substrate path — cited in the projection via `derived_from`.",
            },
            "write_to": {
                "type": "string",
                "description": "Where the derived text projection lands (a sibling of the raw).",
            },
            "text": {
                "type": "string",
                "description": "Pre-extracted text (the upload path passes it to avoid re-parsing). When absent, the blob is fetched via storage_path + extracted.",
            },
            "storage_path": {
                "type": "string",
                "description": "Private-bucket key to fetch+extract when `text` is absent.",
            },
            "file_type": {
                "type": "string",
                "description": "The raw's extension (pdf/docx/…) — selects the extractor + the registry strategy.",
            },
            "source_filename": {
                "type": "string",
                "description": "Original filename, for the projection's human header.",
            },
            "embed": {
                "type": "boolean",
                "description": "Embed the projection inline (default true). The upload path passes false to defer the paid embed off the request; the projection is BM25-searchable regardless.",
            },
        },
        "required": ["raw_path", "write_to"],
    },
}


async def handle_extract_text_from_blob(auth: Any, input: dict) -> dict:
    """Execute ExtractTextFromBlob (ADR-395 Piece B).

    Returns:
      {success, projection_path, word_count, strategy, error}
    """
    user_id = getattr(auth, "user_id", None)
    db_client = getattr(auth, "client", None)
    if not user_id or not db_client:
        return {"success": False, "error": "auth_required"}

    input = input or {}
    raw_path = input.get("raw_path")
    write_to = input.get("write_to")
    text = input.get("text")
    storage_path = input.get("storage_path")
    file_type = input.get("file_type")
    source_filename = input.get("source_filename") or (raw_path or "").rsplit("/", 1)[-1]
    # embed (default True): whether to embed the projection INLINE. The upload
    # path passes False so the paid OpenAI call is DEFERRED off the synchronous
    # request (scheduled as a background task by the route) — the projection is
    # already BM25-searchable the instant it's written; the embedding is the
    # enrichment that catches up (ADR-325: embedding is enrichment, not the floor).
    embed = input.get("embed", True)

    if not raw_path or not write_to:
        return {"success": False, "error": "missing_raw_path_or_write_to"}

    strategy = registry_strategy(file_type)
    if strategy == "passthrough":
        # An image is already model-consumable — no text projection needed.
        return {"success": True, "projection_path": None, "word_count": 0, "strategy": "passthrough"}
    # ADR-395 am.1 D9 — the anti-silent-drop clause, WRITTEN rather than logged.
    #
    # `deferred` used to return here after a log line, so a retained-not-
    # consumable file left no trace an agent could read: it saw a file it could
    # not open and had no explanation. DP34 says such a file is "legibly
    # marked"; a log line is legible to no principal in the system.
    #
    # A text-family file whose extraction came back EMPTY lands in the same
    # place — a scanned PDF, a chart-only deck, a formula-only sheet. The
    # distinction that matters to a reader is not "which parser ran" but "is
    # there anything here for me", so both write the same marker.
    if strategy == "deferred" or (strategy == "text" and text is not None and not text.strip()):
        note = _deferred_note(file_type, had_strategy=(strategy == "text"))
        logger.info("[EXTRACT] %s: retained-not-consumable (%s) — marking", raw_path, file_type)
        marker = (
            f"derived_from: {raw_path}\n\n"
            f"# {source_filename}\n\n"
            f"{note}\n"
        )
        try:
            from services.authored_substrate import write_revision
            write_revision(
                db_client,
                user_id=user_id,
                path=write_to,
                content=marker,
                authored_by=getattr(auth, "caller_identity", None) or "system:extract",
                message=f"retained, not yet readable: {source_filename}",
                lifecycle="active",
                revision_kind="derivation",
                derived_from=[raw_path],
            )
        except Exception as e:  # noqa: BLE001
            # Non-fatal by design: the RAW is already landed and is the file
            # that matters. A missing marker is a missing explanation, not a
            # missing file.
            logger.warning("[EXTRACT] marker write failed for %s: %s", write_to, e)
            return {"success": True, "projection_path": None, "word_count": 0, "strategy": "deferred"}
        # No embed: a marker carries no content to rank, and embedding it would
        # put a sentence we wrote into recall as though it were the member's.
        return {
            "success": True, "projection_path": write_to, "word_count": 0,
            "strategy": "deferred", "embed_pending": False,
        }

    # strategy == "text": get the text (reuse pre-extracted, else fetch+extract).
    if not text:
        if not storage_path:
            return {"success": False, "error": "no_text_and_no_storage_path", "strategy": strategy}
        try:
            from services.documents import extract_text, DOCUMENTS_BUCKET
            blob = db_client.storage.from_(DOCUMENTS_BUCKET).download(storage_path)
            text, _ = await extract_text(blob, file_type or "txt")
        except Exception as e:  # noqa: BLE001
            logger.warning("[EXTRACT] fetch+extract failed for %s: %s", storage_path, e)
            return {"success": False, "error": f"extract_failed: {e}", "strategy": strategy}

    if not text or not text.strip():
        return {"success": False, "error": "empty_projection", "strategy": strategy}

    # Build the projection: a `derived_from` citation to the raw (DP32) + a
    # human header + the extracted body. `derived_from` first so `trace` /
    # `_extract_derived_from_list` can walk raw↔derived (ADR-376 §9 list form).
    projection = (
        f"derived_from: {raw_path}\n\n"
        f"# {source_filename}\n\n"
        f"{text}"
    )

    try:
        from services.authored_substrate import write_revision
        write_revision(
            db_client,
            user_id=user_id,
            path=write_to,
            content=projection,
            authored_by=getattr(auth, "caller_identity", None) or "system:extract",
            message=f"text projection of {source_filename}",
            lifecycle="active",
            # ADR-448: the first live derivation writer — the projection is a
            # derived act citing the raw it was made from. Explicit (belt over
            # the frontmatter lift), so the edge + kind ride the ledger.
            revision_kind="derivation",
            derived_from=[raw_path],
        )
    except Exception as e:  # noqa: BLE001
        logger.error("[EXTRACT] projection write failed for %s: %s", write_to, e)
        return {"success": False, "error": f"write_failed: {e}", "strategy": strategy}

    # Embed the projection — the text is what fuzzy recall ranks (DP34: the
    # projection is the model-consumable object). Same one embed path (ADR-325).
    # DEFERRABLE: when embed=False the caller (the upload route) schedules the
    # embed off the synchronous request; we report embed_pending so it can. The
    # projection is BM25-searchable regardless — the embed is enrichment.
    embed_pending = False
    if embed:
        try:
            from services.primitives.embed import is_embed_eligible
            from services.primitives.workspace import _embed_workspace_file
            rel = write_to.lstrip("/")
            if rel.startswith("workspace/"):
                rel = rel[len("workspace/"):]
            eligible, _reason = is_embed_eligible(rel, text)
            if eligible:
                await _embed_workspace_file(db_client, user_id, write_to, text[:2000])
        except Exception as e:  # noqa: BLE001
            logger.warning("[EXTRACT] embed failed for %s: %s", write_to, e)
    else:
        # Deferred: eligibility decides whether an embed is even owed downstream.
        from services.primitives.embed import is_embed_eligible
        rel = write_to.lstrip("/")
        if rel.startswith("workspace/"):
            rel = rel[len("workspace/"):]
        embed_pending, _reason = is_embed_eligible(rel, text)

    word_count = len(text.split())
    return {
        "success": True,
        "projection_path": write_to,
        "word_count": word_count,
        "strategy": "text",
        "embed_pending": embed_pending,
    }


__all__ = [
    "EXTRACT_TEXT_FROM_BLOB_TOOL",
    "handle_extract_text_from_blob",
    "registry_strategy",
]
