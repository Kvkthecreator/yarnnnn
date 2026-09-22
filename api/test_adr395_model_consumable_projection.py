"""
ADR-395 — the model-consumable projection: upload intake conformance.

Drives the REAL upload intake logic (process_document → ExtractTextFromBlob →
path/content_url/embed-eligibility), mocking only at the DB/storage boundary
(write_revision + _embed_workspace_file + storage). This is the gate the prior
coverage lacked: test_adr331 mocks process_document entirely, so it exercised the
batch envelope but NOTHING of ADR-395's raw+derive core. The two assertions that
would have caught the shipped defects:

  • the raw lands at inbound/uploads/{slug}.{ext} with content_url
    (not a derived .md masquerading as the upload);
  • the derived .extracted.md projection is EMBED-ELIGIBLE + RECALL-REACHABLE
    (Defect 2 — the projection was landing in a lane recall could not see).

Plus: the download route resolves storage_path from content_url for new-shape
rows (Defect 1), and the derive-registry verdicts are correct.
"""

import asyncio
import io
from pathlib import Path
from unittest.mock import patch

import pytest

#: The api/ root — the amendment-1 source checks read from here (ADR-395 am.1).
ROOT = Path(__file__).resolve().parent


# ── DB/storage boundary mocks ──────────────────────────────────────────────


class _RecordingClient:
    """A workspace_files-shaped client. Only .table(...).select(...).like(...)
    .execute() is exercised by the code under test (the _unique_raw_path existence
    probe); everything else routes through the patched write_revision. It reads
    from the SAME `store` the write recorder populates, so a second upload sees
    the first upload's rows (mirrors the single DB that backs both in prod)."""

    def __init__(self, store):
        self.store = store  # path -> row (shared with the write recorder)

    def table(self, _name):
        self._like = None
        return self

    def select(self, *_a, **_k):
        return self

    def eq(self, _col, _val):
        return self

    def like(self, col, pattern):
        self._like = (col, pattern)
        return self

    def limit(self, _n):
        return self

    def execute(self):
        matched = []
        if self._like:
            _, pattern = self._like
            stem = pattern.split("%", 1)[0]
            matched = [{"path": p} for p in self.store if p.startswith(stem)]
        return type("R", (), {"data": matched})()


def _make_write_recorder(store):
    """A write_revision stand-in recording (path -> {content, content_url,
    authored_by, ...}). Returns a fake revision id.

    2026-07-22 — `content` made OPTIONAL and `content_bytes` accepted, mirroring
    the real `write_revision` (authored_substrate.py: both are Optional). The
    stub had `content` as a REQUIRED keyword-only arg, which was true when this
    gate was written but stopped being true at ADR-427 Phase 2/3: a binary
    upload now writes its raw through the CAS as `content_bytes=` with no
    `content`, so every call raised TypeError ("missing 1 required keyword-only
    argument: 'content'") and 5 tests failed on the STUB, not on the pipeline.
    A test double that is stricter than the real function tests nothing but
    itself. `content_bytes` is recorded so a binary write is still observable
    (the caption + content_url assertions are what these tests actually check).
    """
    def _write(db_client=None, *, user_id, path, content=None, content_bytes=None,
               authored_by, message, lifecycle=None, content_type=None,
               content_url=None, **_k):
        store[path] = {
            "content": content,
            "content_bytes": content_bytes,
            "authored_by": authored_by,
            "content_url": content_url,
            "content_type": content_type,
            "lifecycle": lifecycle,
            "message": message,
        }
        return "rev-" + str(len(store))
    return _write


# ── The end-to-end upload path ─────────────────────────────────────────────


def _run_upload(store, embeds, *, filename, file_type, text_body):
    """Drive the REAL process_document with write_revision + embed mocked at the
    boundary. Returns process_document's result dict."""
    from services import documents

    async def _fake_extract(_bytes, _ft):
        return (text_body, len(text_body.split("\n")))

    async def _fake_embed(_client, _uid, path, _content):
        embeds.append(path)

    client = _RecordingClient(store)

    # Patch write_revision in BOTH modules that import it (documents writes the
    # raw; the ExtractTextFromBlob primitive writes the projection).
    with patch.object(documents, "extract_text", _fake_extract), \
         patch("services.authored_substrate.write_revision", _make_write_recorder(store)), \
         patch("services.primitives.workspace._embed_workspace_file", _fake_embed):
        result = asyncio.run(documents.process_document(
            document_id="doc-1",
            file_content=b"x" * 500,
            file_type=file_type,
            filename=filename,
            file_size=500,
            storage_path=f"user-1234/doc-1/original.{file_type}",
            user_id="user-1234",
            db_client=client,
        ))
    return result


def test_upload_lands_raw_in_inbound_uploads_as_versioned_bytes():
    """Piece A: the RAW blob lands at inbound/uploads/{slug}.{ext}
    as a VERSIONED BINARY revision — NOT a derived .md, NOT under the legacy
    uploads/ root.

    REWRITTEN 2026-07-22 (was `..._with_content_url`). This asserted the pre-
    ADR-427 representation: a caption string in `content` ("Uploaded file: …")
    plus a stored `content_url` pointing at an un-versioned bucket copy. ADR-427
    Phase 3 replaced BOTH — the bytes now enter the content-addressed store
    behind the storage seam (attributed, parent-pointered, revertible), the type
    is derived at the door, and serving URLs are MINTED AT READ. documents.py
    says it outright at the call site: "No un-versioned bucket copy, no stored
    content_url." So the old assertions did not describe a regression; they
    described a superseded design, and could never pass again.

    What is asserted now is the live contract — bytes retained, no caption, no
    stored URL, operator-attributed.
    """
    store, embeds = {}, []
    body = "Acme quarterly brief.\n" + ("Revenue grew. " * 40)
    result = _run_upload(store, embeds, filename="acme-brief.pdf", file_type="pdf", text_body=body)

    assert result["success"] is True, result
    raw_path = result["raw_path"]
    assert raw_path == "/workspace/inbound/uploads/acme-brief.pdf", raw_path
    raw = store[raw_path]
    # The raw is BYTES in the CAS (ADR-427 Phase 3) — not a caption + pointer.
    assert raw["content_bytes"], f"raw must carry bytes, got {raw!r}"
    assert raw["content"] is None, f"no caption string on a binary raw: {raw['content']!r}"
    assert raw["content_url"] is None, (
        "serving URLs are minted at READ, never stored on the revision (ADR-427 D4)"
    )
    assert raw["authored_by"] == "operator"  # the raw is the operator's


def test_upload_derives_projection_citing_the_raw():
    """Piece B: a co-located .extracted.md projection is written, citing the raw
    via a `derived_from:` first line, attributed system:extract."""
    store, embeds = {}, []
    body = "Acme quarterly brief.\n" + ("Revenue grew. " * 40)
    result = _run_upload(store, embeds, filename="acme-brief.pdf", file_type="pdf", text_body=body)

    proj_path = result["projection_path"]
    assert proj_path == "/workspace/inbound/uploads/acme-brief.extracted.md", proj_path
    proj = store[proj_path]
    # DP32 citation is the first line so trace/_extract_derived_from_list walks it.
    assert proj["content"].splitlines()[0] == "derived_from: /workspace/inbound/uploads/acme-brief.pdf", proj["content"][:120]
    assert proj["authored_by"] == "system:extract", proj  # mechanical, not the operator


def test_projection_is_embed_eligible_and_recall_reachable():
    """Defect 2 (the regression guard): the projection lands in a lane that is
    BOTH embed-eligible AND inside the QueryKnowledge default search surface. If
    this fails, an uploaded document's text is invisible to recall."""
    from services.primitives.embed import is_embed_eligible, is_searchable_root

    store, embeds = {}, []
    body = "Acme quarterly brief.\n" + ("Revenue grew. " * 40)
    result = _run_upload(store, embeds, filename="acme-brief.pdf", file_type="pdf", text_body=body)
    proj_path = result["projection_path"]

    eligible, reason = is_embed_eligible(proj_path, store[proj_path]["content"])
    assert eligible, f"projection must be embed-eligible, got: {reason}"
    assert is_searchable_root(proj_path), "projection must be in the QueryKnowledge search surface"


def test_upload_defers_the_embed_off_the_request():
    """The embed is DEFERRED (ADR-395/ADR-325): process_document does NOT embed
    inline (no paid OpenAI call on the request path), but reports embed_pending so
    the route schedules it as a BackgroundTask. This is the over-reach correction —
    the projection is BM25-searchable immediately; the embed enrichment catches up."""
    store, embeds = {}, []
    body = "Acme quarterly brief.\n" + ("Revenue grew. " * 40)
    result = _run_upload(store, embeds, filename="acme-brief.pdf", file_type="pdf", text_body=body)

    # No inline embed happened on the request path (the whole point of deferral).
    assert embeds == [], f"embed must be deferred, not inline; embeds={embeds}"
    # But an embed IS owed — the route will schedule it (text projection is eligible).
    assert result.get("embed_pending") is True, "process_document must flag embed_pending for the route to defer"


def test_deferred_embed_helper_embeds_the_projection():
    """The route's BackgroundTask helper reads the projection back and embeds it —
    proving the deferred path actually completes the enrichment (just off-request)."""
    from unittest.mock import patch
    from routes import documents as route_docs

    proj_path = "/workspace/inbound/uploads/acme-brief.extracted.md"
    proj_content = "derived_from: /x\n\n# acme\n" + ("Revenue grew. " * 40)
    embedded = []

    class _Svc:
        def table(self, _n):
            self._sel = None
            return self
        def select(self, *_a, **_k):
            return self
        def eq(self, *_a, **_k):
            return self
        def limit(self, _n):
            return self
        def execute(self):
            return type("R", (), {"data": [{"content": proj_content}]})()

    async def _fake_embed(_c, uid, path, _content):
        embedded.append((uid, path))

    # _embed_projection_deferred imports get_service_client from services.supabase
    # inside the function body, so patch it at the source module.
    with patch("services.supabase.get_service_client", lambda: _Svc()), \
         patch("services.primitives.workspace._embed_workspace_file", _fake_embed):
        asyncio.run(route_docs._embed_projection_deferred("user-1234", proj_path))

    assert embedded == [("user-1234", proj_path)], f"deferred helper must embed the projection; got {embedded}"


def test_second_upload_same_name_does_not_clobber():
    """_unique_raw_path: re-uploading the same filename yields a -2 sibling for
    both the raw and its projection (they stay co-located + collision-free)."""
    store, embeds = {}, []
    body = "Distinct content.\n" + ("word " * 60)
    r1 = _run_upload(store, embeds, filename="dup.pdf", file_type="pdf", text_body=body)
    r2 = _run_upload(store, embeds, filename="dup.pdf", file_type="pdf", text_body=body)

    assert r1["raw_path"] == "/workspace/inbound/uploads/dup.pdf"
    assert r2["raw_path"] == "/workspace/inbound/uploads/dup-2.pdf", r2["raw_path"]
    assert r2["projection_path"] == "/workspace/inbound/uploads/dup-2.extracted.md"


# ── The derive-registry verdicts (ADR-395 D2 / DP34) ───────────────────────


@pytest.mark.parametrize("ft,expected", [
    ("pdf", "text"), ("docx", "text"), ("txt", "text"), ("md", "text"), ("csv", "text"),
    ("html", "text"),  # ADR-530 D1
    # ADR-395 am.1 D10 — xlsx/pptx LEAVE the deferred set (openpyxl / python-pptx,
    # in-process; no sandbox). These two lines were `deferred` before the amendment.
    ("xlsx", "text"), ("pptx", "text"),
    ("png", "passthrough"), ("jpg", "passthrough"),
    ("zip", "deferred"), ("mp3", "deferred"),
    # ADR-395 am.2 D17 — `doc` LEAVES the text family: python-docx cannot open
    # an OLE `.doc`, so it only ever reached the marker while the registry
    # claimed it readable. D18 — the Hancom pair joins.
    ("doc", "deferred"), ("hwp", "text"), ("hwpx", "text"),
    ("wat-is-this", "deferred"),  # unknown = retained-not-consumable, never a break
    (None, "deferred"),
])
def test_registry_strategy_verdicts(ft, expected):
    from services.file_formats import registry_strategy
    assert registry_strategy(ft) == expected


def test_passthrough_writes_no_projection():
    """An image is already model-consumable — the derive writes no projection."""
    from services.primitives.extract_text_from_blob import handle_extract_text_from_blob

    class _Auth:
        user_id = "u"
        client = object()
        caller_identity = "system:extract"

    out = asyncio.run(handle_extract_text_from_blob(_Auth(), {
        "raw_path": "/workspace/inbound/uploads/logo.png",
        "write_to": "/workspace/inbound/uploads/logo.extracted.md",
        "file_type": "png",
        "text": "irrelevant",
    }))
    assert out["success"] is True and out["strategy"] == "passthrough"
    assert out["projection_path"] is None


# ── Download route (Defect 1) ──────────────────────────────────────────────


def test_download_resolves_storage_path_from_content_url():
    """Defect 1: the download route resolves storage_path from a NEW-shape row's
    content_url (no frontmatter), and legacy frontmatter rows still work."""
    from routes.documents import _storage_path_from_content_url

    # New shape: content_url carries the url-encoded key.
    assert _storage_path_from_content_url(
        "/api/documents/blob?storage_path=user-1234%2Fdoc-1%2Foriginal.pdf"
    ) == "user-1234/doc-1/original.pdf"
    # Non-blob (output-gateway absolute URL) → None → falls through to frontmatter.
    assert _storage_path_from_content_url("https://cdn.example.com/report.pdf") is None
    assert _storage_path_from_content_url("") is None
    assert _storage_path_from_content_url(None) is None


# ── Projection hiding (Files UX): narrow + symmetric (2026-07-02) ───────────


import pytest as _pytest


@_pytest.mark.parametrize("path,hidden", [
    # The co-located upload projection → hidden (plumbing).
    # BOTH lane shapes are asserted: the ADR-555 amendment dropped the inert
    # `{principal}/` sublane from NEW uploads, and the ~67 rows already written
    # under `operator/` keep resolving. The rule keys on the derive EDGE and the
    # `inbound/uploads/` prefix, so neither shape may drift.
    ("/workspace/inbound/uploads/acme.extracted.md", True),
    ("workspace/inbound/uploads/acme.extracted.md", True),  # no leading slash
    ("/workspace/inbound/uploads/operator/acme.extracted.md", True),  # pre-amendment row
    ("workspace/inbound/uploads/operator/acme.extracted.md", True),
    ("/workspace/inbound/uploads/chat/acme.extracted.md", True),  # the chat shelf
    # The raw upload → shown (the user's file).
    ("/workspace/inbound/uploads/acme.pdf", False),
    ("/workspace/inbound/uploads/operator/acme.pdf", False),  # pre-amendment row
    # A user's own prose .md → shown (never hidden).
    ("/workspace/uploads/legacy.md", False),
    ("/workspace/operation/report.md", False),
    # An .extracted.md OUTSIDE the upload lane → shown (symmetry: not our plumbing).
    ("/workspace/operation/notes.extracted.md", False),
    # MCP raw lane → shown (different lane, not an upload projection).
    ("/workspace/inbound/mcp/chatgpt/x.md", False),
])
def test_is_upload_projection_is_narrow_and_symmetric(path, hidden):
    """The hide predicate must match ONLY inbound/uploads/**.extracted.md — so a
    pure-text upload (no projection) and any user file are NEVER hidden. This is
    the seamless/reversible guard: a bug here would hide user files or leak
    plumbing into the tree."""
    from services.documents import is_upload_projection
    assert is_upload_projection(path) is hidden


# ═══════════════════════════════════════════════════════════════════════════
# ADR-395 Amendment 1 (2026-09-21) — the door opens, and nothing is dropped
# ═══════════════════════════════════════════════════════════════════════════


def test_am1_d8_no_format_allowlist_survives_at_the_intake_door():
    """D8 — `_DOC_MIMES` is DELETED, and acceptance is conformance to public.data.

    A widened allowlist is the same defect with a longer list, so this asserts
    the NAME is gone rather than that it contains more entries. Reads the source
    with comments stripped: the amendment's own comment names `_DOC_MIMES` to
    explain the deletion, and a substring check would match that prose (the
    ADR-588 lesson — a gate assertion can match its own comment).
    """
    import re
    src = (ROOT / "routes" / "documents.py").read_text(encoding="utf-8")
    code = "\n".join(
        re.sub(r"#.*$", "", line) for line in src.splitlines()
    )
    assert "_DOC_MIMES" not in code, "the format allowlist is back"
    assert 'conforms_to(mime, "public.data")' in code, \
        "the intake verdict no longer asks the public.data question"


def test_am1_d8_intake_verdict_accepts_every_format():
    """D8 driven — the verdict itself, over formats that were refused before."""
    from routes.documents import _intake_verdict

    # xlsx/pptx were rejected by _DOC_MIMES; the zip magic is what they carry.
    zip_magic = b"PK\x03\x04" + b"\x00" * 20
    for name, expect_ft in [
        ("q3.xlsx", "xlsx"), ("deck.pptx", "pptx"), ("brief.docx", "docx"),
    ]:
        mime, ft, is_media = _intake_verdict(name, zip_magic)
        assert mime is not None, f"{name} refused at the door"
        assert ft == expect_ft, (name, ft)
        assert is_media is False

    # A format nobody has ever registered still lands (retained, not consumable),
    # and keeps its own extension. TRUE binary bytes: `b"\x00\x01\x02\x03"` is
    # valid utf-8 (control chars), so it exercises the utf-8 fallback rather than
    # the binary one — the weak fixture that hid this during implementation.
    for head in (b"\xff\xd8\xab\xcd\x00\x91", b"8BPS\x00\x01\x00\x00"):
        mime, ft, is_media = _intake_verdict("model.sketch", head)
        assert mime is not None, "an unknown format is refused — the door is not open"
        assert ft == "sketch", (
            "the derived MIME beat the extension — an unsignatured head that "
            "decodes as utf-8 would send binary bytes to the TEXT extractor"
        )


def test_am1_d9_deferred_write_marks_rather_than_logs():
    """D9 — a retained-not-consumable file gets a MARKER file citing its raw.

    The pre-amendment branch returned after a log line, so an agent saw a file
    it could not open with no explanation anywhere it could read.
    """
    from services.primitives.extract_text_from_blob import handle_extract_text_from_blob

    written = {}

    def _fake_write(db, *, user_id, path, content=None, **kw):
        written["path"] = path
        written["content"] = content
        written["derived_from"] = kw.get("derived_from")
        written["kind"] = kw.get("revision_kind")
        return {"id": "rev1"}

    class _Auth:
        user_id = "u"
        client = object()
        caller_identity = "system:extract"

    import services.authored_substrate as sub
    with patch.object(sub, "write_revision", _fake_write):
        out = asyncio.run(handle_extract_text_from_blob(_Auth(), {
            "raw_path": "/workspace/inbound/uploads/archive.zip",
            "write_to": "/workspace/inbound/uploads/archive.extracted.md",
            "file_type": "zip",
            "source_filename": "archive.zip",
            "embed": False,
        }))

    assert out["success"] is True
    assert out["strategy"] == "deferred"
    assert out["projection_path"] == "/workspace/inbound/uploads/archive.extracted.md", \
        "the deferred branch wrote no marker — the anti-silent-drop clause is only a log line"
    assert written["derived_from"] == ["/workspace/inbound/uploads/archive.zip"], \
        "the marker does not cite its raw"
    assert written["kind"] == "derivation"
    body = written["content"]
    assert "derived_from: /workspace/inbound/uploads/archive.zip" in body
    assert "NOTE:" in body and "retained in full" in body
    # Never fabricate: the marker states the gap, it does not invent contents.
    assert "zip" in body.lower()


def test_am1_d9_empty_extraction_marks_instead_of_failing_the_upload():
    """D9 — a text-family file that yields no text still lands, and says so.

    The scanned-PDF case. Before the amendment a 50-char floor in
    `process_document` returned success:False and the BYTES NEVER LANDED.
    """
    from services.primitives.extract_text_from_blob import handle_extract_text_from_blob

    written = {}

    def _fake_write(db, *, user_id, path, content=None, **kw):
        written["content"] = content
        return {"id": "rev1"}

    class _Auth:
        user_id = "u"
        client = object()
        caller_identity = "system:extract"

    import services.authored_substrate as sub
    with patch.object(sub, "write_revision", _fake_write):
        out = asyncio.run(handle_extract_text_from_blob(_Auth(), {
            "raw_path": "/workspace/inbound/uploads/scan.pdf",
            "write_to": "/workspace/inbound/uploads/scan.extracted.md",
            "text": "   \n  ",          # extractor found nothing
            "file_type": "pdf",
            "source_filename": "scan.pdf",
            "embed": False,
        }))

    assert out["success"] is True, "an unreadable PDF failed the upload"
    assert out["strategy"] == "deferred"
    assert "No text could be read" in written["content"], \
        "the empty-extraction marker does not distinguish itself from an unknown format"


def test_am1_d9_the_rejection_floor_is_gone_from_process_document():
    """D9 — the 50-char floor that failed the whole upload no longer exists."""
    import re
    src = (ROOT / "services" / "documents.py").read_text(encoding="utf-8")
    code = "\n".join(re.sub(r"#.*$", "", line) for line in src.splitlines())
    assert "No text could be extracted from document" not in code, \
        "the extraction floor still rejects the upload"
    assert "registry_strategy(file_type)" in code, \
        "process_document no longer asks the registry what is owed"


def test_am1_d10_docx_extraction_keeps_tables_and_headers():
    """D10 — the repaired docx extractor, DRIVEN over a real table-bearing file.

    The pre-amendment extractor walked `doc.paragraphs` only and returned just
    "Intro paragraph." for this document: the table and the header were dropped
    with no error and no log line. A contract or spec sheet is mostly tables, so
    this was live data loss that read as a successful upload.
    """
    docx = pytest.importorskip("docx")
    from services.documents import extract_text

    d = docx.Document()
    d.add_paragraph("Intro paragraph.")
    t = d.add_table(rows=2, cols=2)
    t.cell(0, 0).text = "Term"
    t.cell(0, 1).text = "Value"
    t.cell(1, 0).text = "Payment"
    t.cell(1, 1).text = "Net 30"
    d.add_paragraph("Closing paragraph.")
    d.sections[0].header.paragraphs[0].text = "ACME CONFIDENTIAL"
    buf = io.BytesIO()
    d.save(buf)

    text, blocks = asyncio.run(extract_text(buf.getvalue(), "docx"))

    assert "Net 30" in text, "the table was dropped — the am.1 D10 data loss is back"
    assert "Term\tValue" in text, "table rows are not tab-separated"
    assert "ACME CONFIDENTIAL" in text, "the header was dropped"
    assert "Intro paragraph." in text and "Closing paragraph." in text
    # Document order: the table sits BETWEEN the two paragraphs, and only the
    # body's XML child order records that.
    assert text.index("Intro paragraph.") < text.index("Net 30") < text.index("Closing paragraph.")
    assert blocks >= 4


def test_am1_d10_xlsx_extraction_reads_every_sheet():
    """D10 — xlsx joins the text family, driven over a real workbook."""
    openpyxl = pytest.importorskip("openpyxl")
    from services.documents import extract_text

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Q3"
    ws.append(["Region", "Revenue"])
    ws.append(["EMEA", 1200])
    wb.create_sheet("Notes").append(["renewal risk"])
    buf = io.BytesIO()
    wb.save(buf)

    text, sheets = asyncio.run(extract_text(buf.getvalue(), "xlsx"))

    assert "## Q3" in text and "## Notes" in text, "a sheet is missing"
    assert "EMEA\t1200" in text, "rows are not tab-separated"
    assert "renewal risk" in text, "the second sheet was dropped"
    assert sheets == 2


def test_am1_d10_pptx_extraction_reads_slides_and_notes():
    """D10 — pptx joins the text family, with speaker notes kept."""
    pptx = pytest.importorskip("pptx")
    from services.documents import extract_text

    prs = pptx.Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Roadmap"
    slide.placeholders[1].text = "Ship intake"
    slide.notes_slide.notes_text_frame.text = "Do not promise dates"
    buf = io.BytesIO()
    prs.save(buf)

    text, slides = asyncio.run(extract_text(buf.getvalue(), "pptx"))

    assert "## Slide 1" in text
    assert "Roadmap" in text and "Ship intake" in text
    assert "Speaker notes: Do not promise dates" in text, \
        "speaker notes dropped — the argument the slide only gestures at"
    assert slides == 1


def test_am1_d8_zip_expansion_no_longer_filters_on_the_parser_table():
    """D8 — a .xlsx inside a .zip is expanded, and a nested archive is not.

    `_expand_zip` filtered entries on `_MIME_EXTS.values()` — the EXTRACTOR
    table doing duty as a gate, so an office file inside an envelope was
    dropped without a word.
    """
    import zipfile
    from routes.documents import _expand_zip

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("sheet.xlsx", b"PK\x03\x04payload")
        zf.writestr("deck.pptx", b"PK\x03\x04payload")
        zf.writestr("notes.md", b"# hi")
        zf.writestr("model.sketch", b"\x00\x01")
        zf.writestr("nested.zip", b"PK\x03\x04nested")
        zf.writestr("__MACOSX/._x", b"junk")
        zf.writestr(".hidden", b"junk")

    names = [n for n, _ in _expand_zip(buf.getvalue())]

    assert "sheet.xlsx" in names and "deck.pptx" in names, \
        "office files inside a .zip are still filtered out"
    assert "model.sketch" in names, "an unknown format inside a .zip is dropped"
    assert "notes.md" in names
    assert "nested.zip" not in names, "a nested archive was expanded recursively"
    assert not any(n.startswith(".") for n in names)


# ── am.1 D11 — a member can tell "not readable" from "read fine" ────────────


@pytest.mark.parametrize("path,ct,projection,expected", [
    # A real projection carries the file's own words.
    ("/w/q3.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
     "derived_from: /w/q3.xlsx\n\n# q3.xlsx\n\n## Q3\n\nEMEA\t1200", "read"),
    ("/w/deck.pptx", None, "derived_from: /w/deck.pptx\n\n# deck.pptx\n\n## Slide 1\n\nRoadmap", "read"),
    ("/w/brief.docx", None, "derived_from: /w/brief.docx\n\n# brief.docx\n\nTerms follow.", "read"),
    # A D9 MARKER is not a projection, however much it looks like one.
    ("/w/design.sketch", "application/octet-stream",
     "derived_from: /w/design.sketch\n\n# design.sketch\n\nNOTE: This is a sketch file. It is retained in full…",
     "unread"),
    ("/w/scan.pdf", None,
     "derived_from: /w/scan.pdf\n\n# scan.pdf\n\nNOTE: No text could be read from this pdf file…",
     "unread"),
    # Native — the file IS its own content, so nothing is owed or missing.
    ("/w/photo.png", "image/png", None, "native"),
    ("/w/clip.mp4", "video/mp4", None, "native"),
    ("/w/notes.md", "text/markdown", None, "native"),
])
def test_am1_d11_readable_state_separates_the_three_cases(path, ct, projection, expected):
    """D11 — `read` / `unread` / `native`, the member's question not the viewer's.

    The viewer asks "can I DRAW this"; both a .sketch and an .xlsx answer no.
    The member asks "does my agent know what is in it", and those two answer
    oppositely. This is that second question.
    """
    from services.documents import readable_state
    got = readable_state(
        path, content_type=ct, projection_content=projection,
        has_projection=projection is not None,
    )
    assert got == expected, f"{path} → {got}, expected {expected}"


def test_am1_d11_no_projection_is_unread_not_read():
    """D11 — the conservative default. Claiming readability we do not have is
    the failure that matters; the reverse is merely modest."""
    from services.documents import readable_state
    assert readable_state("/w/mystery.bin", content_type="application/octet-stream") == "unread"
    assert readable_state("/w/q3.xlsx", has_projection=False) == "unread"


def test_am1_d11_marker_and_projection_are_told_apart_by_the_writers_token():
    """D11 — the discriminator matches what `_deferred_note` actually emits.

    A gate that invents its own marker text would pass while the real writer
    drifted. This asserts the REAL note, produced by the real function.
    """
    from services.documents import readable_state
    from services.primitives.extract_text_from_blob import _deferred_note

    for had_strategy in (True, False):
        note = _deferred_note("xlsx", had_strategy=had_strategy)
        body = f"derived_from: /w/a.xlsx\n\n# a.xlsx\n\n{note}\n"
        assert readable_state("/w/a.xlsx", projection_content=body) == "unread", \
            f"a real marker (had_strategy={had_strategy}) was read as a projection"


def test_am1_d11_the_client_never_re_derives_the_rule():
    """D11 — the verdict is the SERVER's, like `access` (ADR-643 D3).

    A second copy of `registry_strategy` in TypeScript is the split that let the
    upload door and the derive-registry disagree in the first place (§8.1), so
    the FE must consume `file.readable` and never compute it.
    """
    import re
    web = ROOT.parent / "web"
    viewer = (web / "components" / "workspace" / "viewers" / "index.tsx").read_text(encoding="utf-8")
    code = re.sub(r"//.*$", "", viewer, flags=re.MULTILINE)
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)

    assert "file.readable" in code, "the viewer does not read the served verdict"
    # The FE must not rebuild the registry: no format list deciding readability.
    for spelling in ("'xlsx'", '"xlsx"', "'pptx'", '"pptx"'):
        assert spelling not in code, \
            f"the viewer names {spelling} — the derive-registry is being re-derived client-side"


def test_am1_d11_the_route_decorates_the_read():
    """D11 — the decoration is wired, and degrades to None rather than a 500."""
    import re
    src = (ROOT / "routes" / "workspace.py").read_text(encoding="utf-8")
    code = "\n".join(re.sub(r"#.*$", "", line) for line in src.splitlines())
    # Pin the MECHANISM, not the call's spelling: D12 widened the decoration to
    # return three fields, so an exact-call assertion would fail on a correct
    # change (the ADR-658 am.4 lesson — a gate that pins prose loses an argument
    # with the product).
    assert "_readable_fields(auth, row[" in code, "the file read is not decorated"
    assert "def _readable_or_none(" in code
    assert '"readable": verdict' in code, "the decoration no longer carries the verdict"
    # A decoration that can 500 a read is worse than no decoration.
    helper = code.split("def _readable_or_none(", 1)[1].split("\ndef ", 1)[0]
    assert "except Exception" in helper and "return None" in helper, \
        "the decoration does not degrade to None on failure"


# ── am.1 D12/D13 — the terminal shows the words, and offers the door ────────


def test_am1_d12_projection_header_is_stripped_from_the_preview():
    """D12 — the member sees the file's words, not the substrate's plumbing.

    A projection opens with `derived_from:` + a `# <filename>` title, both
    written for the reference edge (ADR-448) and both noise to a member looking
    at that very file.
    """
    from routes.workspace import _strip_projection_header

    body = (
        "derived_from: /workspace/inbound/uploads/q3.xlsx\n\n"
        "# q3.xlsx\n\n"
        "## Q3 Forecast\n\nRegion\tRevenue\nEMEA\t1200\n"
    )
    out = _strip_projection_header(body)
    assert not out.startswith("derived_from"), "the reference edge leaked into the preview"
    assert "# q3.xlsx" not in out, "the filename title is repeated at the member"
    assert out.startswith("## Q3 Forecast"), out[:40]
    assert "EMEA\t1200" in out, "the content was eaten with the header"


def test_am1_d12_a_heading_inside_the_body_survives():
    """D12 — the stripper stops at the first real line, it does not filter.

    A `#` heading LOWER in a document is content. Dropping every `# ` line
    would quietly delete a deck's slide titles.
    """
    from routes.workspace import _strip_projection_header

    body = (
        "derived_from: /w/deck.pptx\n\n# deck.pptx\n\n"
        "## Slide 1\n\nRoadmap\n\n# A Heading In The Deck\n\nmore\n"
    )
    out = _strip_projection_header(body)
    assert "# A Heading In The Deck" in out, "a heading inside the body was stripped"


def test_am1_d12_preview_is_bounded_and_says_when_it_is_cut():
    """D12 — a 200-page PDF's projection must not inflate every file read."""
    from routes.workspace import _PROJECTION_PREVIEW_CHARS, _strip_projection_header

    assert 500 <= _PROJECTION_PREVIEW_CHARS <= 20000, \
        f"the preview bound is not a preview: {_PROJECTION_PREVIEW_CHARS}"
    # The stripper itself must not truncate — bounding is the caller's job, so
    # the two concerns stay separable.
    long_body = "derived_from: /w/a.pdf\n\n# a.pdf\n\n" + ("word " * 20000)
    assert len(_strip_projection_header(long_body)) > _PROJECTION_PREVIEW_CHARS


def test_am1_d12_only_a_read_file_carries_a_preview():
    """D12 — `unread` carries none (its NOTE is already the sentence shown),
    and `native` carries none (the file is its own preview). Serving a marker's
    text as a 'preview' would print the same fact twice."""
    import re
    src = (ROOT / "routes" / "workspace.py").read_text(encoding="utf-8")
    code = "\n".join(re.sub(r"#.*$", "", line) for line in src.splitlines())
    helper = code.split("def _readable_or_none(", 1)[1].split("\ndef ", 1)[0]
    assert 'if verdict != "read":' in helper, \
        "the preview is not gated on the `read` verdict"
    assert "_strip_projection_header(" in helper


def test_am1_d13_the_terminal_offers_the_download_it_names():
    """D13 — the panel that says "open or download this file" now has a door.

    Download lived ONLY in the Files right-click menu and Properties, neither
    reachable from this panel: advice without an affordance.
    """
    import re
    web = ROOT.parent / "web"
    src = (web / "components" / "workspace" / "viewers" / "index.tsx").read_text(encoding="utf-8")
    code = re.sub(r"//.*$", "", src, flags=re.MULTILINE)
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)

    terminal = code.split("export const DownloadTerminal", 1)[1]
    assert "resolveDownload(" in terminal, "the terminal offers no download"
    # ONE resolver: rebuilding the href here is the exact defect
    # `lib/workspace/download.ts` exists to fix (it silently returned null for
    # all 39 live binaries).
    assert "blobUrl(" not in terminal, \
        "the terminal rebuilds the download instead of using the one resolver"
    assert "revokeObjectURL" in terminal, "minted object URLs are never revoked"


def test_am1_d13_needsblob_is_gone_and_stays_gone():
    """D13 cleanup — a field every row had to keep correct and nothing read."""
    web = ROOT.parent / "web"
    src = (web / "lib" / "file-types" / "apps.tsx").read_text(encoding="utf-8")
    import re
    code = re.sub(r"//.*$", "", src, flags=re.MULTILINE)
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    assert "needsBlob" not in code, "the dead registry field is back"


# ═══════════════════════════════════════════════════════════════════════════
# ADR-395 Amendment 2 (2026-09-23) — the format harness
# ═══════════════════════════════════════════════════════════════════════════


def _code(path: Path) -> str:
    """Python source with `#` comments stripped — so an arm cannot match the
    comment that explains a deletion (the ADR-588 lesson)."""
    import re
    return "\n".join(re.sub(r"#.*$", "", line) for line in path.read_text(encoding="utf-8").splitlines())


def test_am2_d14_the_superseded_format_tables_are_gone():
    """D14 — ONE table. The five hand-kept copies are DELETED, not aliased.

    Asserted on the live modules (an attribute that exists is a second home,
    however it was spelled), not on source text: a rename that EXTENDS a name
    satisfies a substring check.
    """
    import importlib

    gone = {
        "services.primitives.extract_text_from_blob": (
            "_TEXT_FORMATS", "_PASSTHROUGH_FORMATS", "_DEFERRED_FORMATS"),
        "services.content_types": ("_ZIP_EXT_MIMES",),
        "services.machine_projection": ("_BINARY_TEXT_FAMILY",),
        "services.documents": ("IMAGE_TYPES", "upload_mime"),
        "routes.documents": ("_MIME_EXTS",),
    }
    for module, names in gone.items():
        mod = importlib.import_module(module)
        for name in names:
            assert not hasattr(mod, name), f"{module}.{name} is back — a second format table"
    # The primitive READS the registry; it does not export a copy of it.
    from services.primitives import extract_text_from_blob as prim
    assert "registry_strategy" not in prim.__all__


def test_am2_d14_no_office_extension_literal_outside_the_registry():
    """D14 — a format name in a string literal anywhere else is a second table.

    Scans every service and route for a quoted office/Hancom extension in CODE
    (comments stripped). The registry is the one place a format is named.
    """
    import re
    # Bare "doc" is omitted: it is an ordinary word elsewhere (a design-system
    # file class), and D17 is asserted on the registry itself below.
    pat = re.compile(r"""['"]\.?(docx|xlsx|pptx|hwpx|hwp)['"]""")
    registry = ROOT / "services" / "file_formats.py"
    hits = []
    for top in (ROOT / "services", ROOT / "routes"):
        for path in top.rglob("*.py"):
            if path == registry:
                continue
            for n, line in enumerate(_code(path).splitlines(), 1):
                if pat.search(line):
                    hits.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()[:90]}")
    assert not hits, "format names outside the registry:\n" + "\n".join(hits)


def test_am2_d14_every_row_is_one_mime_one_base_one_home():
    """D14 driven — the MIME and conformance tables are DERIVED from the rows.

    For every declared extension: the path derives to the row's MIME, a zip
    container with the PK signature derives to its own MIME (not application/
    zip), and the MIME conforms to the row's base.
    """
    from services.content_types import conforms_to, derive_content_type
    from services.file_formats import FORMATS, format_for

    seen = set()
    for fmt in FORMATS:
        for ext in fmt.exts:
            assert ext not in seen, f".{ext} is declared twice"
            seen.add(ext)
            assert format_for(ext) is fmt and format_for(f".{ext.upper()}") is fmt
            assert derive_content_type(f"/w/a.{ext}") == fmt.mime, ext
            assert conforms_to(fmt.mime, fmt.base), (ext, fmt.mime, fmt.base)
            assert fmt.projection in ("text", "passthrough", "deferred"), ext
            if fmt.extractor is not None:
                assert fmt.projection == "text", f".{ext} has a parser but is not read"
    # Zip containers are named HERE, independently of the rows' own flag: an
    # arm conditioned on `fmt.zip_container` stays green when the flag is lost
    # (found by falsifying it). With the PK signature in hand, each must still
    # derive to its own MIME rather than application/zip.
    head = b"PK\x03\x04" + b"\x00" * 20
    for ext in ("docx", "xlsx", "pptx", "hwpx"):
        assert derive_content_type(f"/w/a.{ext}", head) == format_for(ext).mime, \
            f".{ext} with a zip signature derived to a generic archive"


def test_am2_d14_extract_text_dispatches_through_the_row():
    """D14 — the parser table IS the registry: `extract_text` names no format.

    An if-chain over extensions was the second copy that let `doc` reach
    python-docx (which cannot open it). Checked on the function's AST, so a
    comment or docstring cannot satisfy or break it.
    """
    import ast
    from services.file_formats import FORMATS

    tree = ast.parse((ROOT / "services" / "documents.py").read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.AsyncFunctionDef) and n.name == "extract_text")
    names = {ext for f in FORMATS for ext in f.exts} | {"doc"}
    literals = {
        n.value for n in ast.walk(fn)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in names
    }
    assert not literals, f"extract_text re-derives formats: {sorted(literals)}"
    assert any(isinstance(n, ast.Attribute) and n.attr == "extractor" for n in ast.walk(fn)), \
        "extract_text does not read the row's extractor"


def test_am2_d17_doc_is_not_claimed_readable():
    """D17 — the one-line truth fix. `.doc` is an OLE file python-docx cannot
    open: listing it as `text` sent every `.doc` to a parser that always failed
    and then to the marker, while the registry said it was readable."""
    from services.file_formats import format_for, is_binary_text_family, registry_strategy

    assert format_for("doc") is None
    assert registry_strategy("doc") == "deferred"
    assert not is_binary_text_family("doc")
    for ft in ("pdf", "docx", "xlsx", "pptx", "hwp", "hwpx"):
        assert is_binary_text_family(ft), f"{ft} left the binary text family"
    for ft in ("md", "txt", "csv", "html", "png", "zip"):
        assert not is_binary_text_family(ft), ft


# ── D15 — the view kind is served; the client's guess is held in parity ─────


def test_am2_d15_office_formats_declare_their_view_kinds():
    from services.file_formats import served_capabilities

    assert served_capabilities("/w/q3.xlsx")["view"] == "spreadsheet"
    assert served_capabilities("/w/brief.docx")["view"] == "wordprocessing"
    assert served_capabilities("/w/deck.pptx")["view"] == "presentation"
    # Undeclared → None: the server has no opinion, and says so.
    assert served_capabilities("/w/model.sketch") == {"view": None, "export_as": []}


def test_am2_d15_d16_the_file_read_serves_the_format_fields():
    """D15/D16 — wired into THE file read, and degrading to None, never a 500.

    Anchored on the FileResponse construction inside `get_file`, not on the
    whole file — the same helper name could appear at another mount.
    """
    src = _code(ROOT / "routes" / "workspace.py")
    ctor = src.split("return FileResponse(", 1)[1].split("\n        )", 1)[0]
    assert '_format_fields(row["path"], row.get("content"))' in ctor, \
        "the file read does not carry view/export_as"
    helper = src.split("def _format_fields(", 1)[1].split("\ndef ", 1)[0]
    assert "served_capabilities(" in helper, "the route re-derives instead of reading the registry"
    assert "except Exception" in helper and '"view": None' in helper, \
        "the format decoration can break a read"
    from routes.workspace import FileResponse
    assert {"view", "export_as"} <= set(FileResponse.model_fields)


_PARITY_PROBE = r"""
// `node -e`: argv[1] is the first argument after the script.
const { transform } = require(process.argv[1]);
const fs = require('fs'); const path = require('path');
const load = (file, req) => {
  const m = { exports: {} };
  new Function('module', 'exports', 'require',
    transform(fs.readFileSync(file, 'utf8'), { transforms: ['typescript', 'imports'] }).code
  )(m, m.exports, req);
  return m.exports;
};
const web = process.argv[2];
const _load = (spec) => {
  if (!spec.startsWith('@/')) return {};
  const base = path.join(web, spec.slice(2));
  const file = ['.ts', '.tsx', '/index.ts'].map((e) => base + e).find((f) => fs.existsSync(f));
  return file ? load(file, _load) : {};
};
const mod = load(path.join(web, 'lib/file-types/index.ts'), _load);
const rows = JSON.parse(process.argv[3]);
const out = { mismatches: [], served_wins: [], unknown_served_falls_back: null };
for (const [ext, view] of rows) {
  const guess = mod.resolveViewerApplication(`/w/a.${ext}`);
  if (guess !== view) out.mismatches.push([ext, view, guess]);
  // The served value beats a contradicting content type.
  const won = mod.resolveViewerApplication(`/w/a.${ext}`, 'application/octet-stream', view);
  if (won !== view) out.served_wins.push([ext, view, won]);
}
out.unknown_served_falls_back =
  mod.resolveViewerApplication('/w/a.pdf', undefined, 'no-such-kind') === 'pdf';
out.served_overrides_extension =
  mod.resolveViewerApplication('/w/a.bin', undefined, 'spreadsheet') === 'spreadsheet';
console.log(JSON.stringify(out));
"""


def _sucrase() -> str:
    web = ROOT.parent / "web"
    direct = web / "node_modules" / "sucrase"
    if direct.exists():
        return str(direct)
    store = sorted((web / "node_modules" / ".pnpm").glob("sucrase@*/node_modules/sucrase"))
    return str(store[-1]) if store else str(direct)


def test_am2_d15_the_client_guess_matches_the_server_for_every_declared_format():
    """D15 — EXECUTED parity: the client's pre-fetch extension cache must give
    the answer the fetch returns, for every extension the registry declares.

    A mirrored table drifts (the ADR-658 am.5 lesson), and the symptom here
    would be a file that draws one way in a tree row and another once opened.
    The TS is transpiled and CALLED — never grepped.
    """
    import json
    import shutil
    import subprocess
    from services.file_formats import FORMATS

    if not shutil.which("node"):
        pytest.fail("node is not installed — the parity arm cannot run (a gate that cannot run reports nothing)")
    rows = [[ext, f.view] for f in FORMATS for ext in f.exts]
    proc = subprocess.run(
        ["node", "-e", _PARITY_PROBE, _sucrase(), str(ROOT.parent / "web"), json.dumps(rows)],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-800:]
    out = json.loads(proc.stdout)
    assert not out["mismatches"], f"client fallback disagrees with the registry: {out['mismatches']}"
    assert not out["served_wins"], f"a served view lost to the content type: {out['served_wins']}"
    assert out["unknown_served_falls_back"], "an unknown served kind was trusted"
    assert out["served_overrides_extension"], "the served view does not win"


def test_am2_d15_the_renderer_mount_passes_the_served_view():
    """D15 — FileBody is THE dispatcher (ADR-436); it must hand over `file.view`."""
    import re
    web = ROOT.parent / "web"
    src = (web / "components" / "workspace" / "FileBody.tsx").read_text(encoding="utf-8")
    code = re.sub(r"//.*$", "", src, flags=re.MULTILINE)
    assert "resolveApp(file.path, file.content_type, file.view)" in code, \
        "FileBody ignores the server's view kind"
    types = (web / "types" / "index.ts").read_text(encoding="utf-8")
    body = types.split("export interface WorkspaceFile {", 1)[1].split("\n}", 1)[0]
    assert "view?: string | null;" in body and "export_as?: ExportTarget[] | null;" in body


# ── D16 — export targets, per file ──────────────────────────────────────────


def test_am2_d16_export_targets_are_per_file():
    from services.file_formats import export_targets

    assert export_targets("/w/notes.md") == ["docx"]
    assert export_targets("/w/data.csv") == ["xlsx"]
    deck = '<html data-template="deck"><body></body></html>'
    post = '<html data-template="post"><body></body></html>'
    assert export_targets("/w/deck.html", deck) == ["docx", "pptx"]
    assert export_targets("/w/post.html", post) == ["docx"], "a blog post was offered as a deck"
    assert export_targets("/w/bare.html", "<p>no type</p>") == ["docx"]
    assert export_targets("/w/q3.xlsx") == [] and export_targets("/w/x.sketch") == []


def test_am2_d16_every_target_lands_readable():
    """D16 — what the writer produces must be a format yarnnn reads back.

    A target the registry cannot extract would mint a file that immediately
    takes the "cannot read" marker: an export that leaves the agent blind.
    """
    from services.file_formats import FORMATS, format_for

    for fmt in FORMATS:
        for target in fmt.export_as:
            row = format_for(target.to)
            assert row is not None and row.projection == "text" and row.extractor, \
                f".{fmt.exts[0]} → .{target.to}, which yarnnn cannot read back"


# ── D18 — the Hancom pair, driven over files built here ─────────────────────


_HWPX_SECTION = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE hs:sec [<!ENTITY leak SYSTEM "file:///etc/hosts">]>
<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"
        xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:p><hp:run><hp:t>{title}</hp:t></hp:run></hp:p>
  <hp:p>
    <hp:run><hp:t>본문 첫 줄<hp:tab/>이어서</hp:t></hp:run>
    <hp:run><hp:tbl><hp:tr>
      <hp:tc><hp:subList><hp:p><hp:run><hp:t>항목</hp:t></hp:run></hp:p></hp:subList></hp:tc>
      <hp:tc><hp:subList><hp:p><hp:run><hp:t>금액</hp:t></hp:run></hp:p></hp:subList></hp:tc>
    </hp:tr><hp:tr>
      <hp:tc><hp:subList><hp:p><hp:run><hp:t>인건비</hp:t></hp:run></hp:p></hp:subList></hp:tc>
      <hp:tc><hp:subList><hp:p><hp:run><hp:t>1,200</hp:t></hp:run></hp:p></hp:subList></hp:tc>
    </hp:tr></hp:tbl></hp:run>
  </hp:p>
  <hp:p><hp:run><hp:t>&leak;</hp:t></hp:run></hp:p>
</hs:sec>"""


def _hwpx(sections: dict) -> bytes:
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("mimetype", "application/hwp+zip")
        zf.writestr("Contents/header.xml", "<hh:head xmlns:hh='x'><hh:t>NOT BODY</hh:t></hh:head>")
        for name, title in sections.items():
            zf.writestr(f"Contents/{name}.xml", _HWPX_SECTION.format(title=title))
    return buf.getvalue()


def test_am2_d18_hwpx_reads_paragraphs_tables_and_section_order():
    from services.documents import extract_text

    text, sections = asyncio.run(extract_text(
        _hwpx({"section10": "열번째 구역", "section2": "두번째 구역"}), "hwpx"))
    assert sections == 2
    assert text.index("두번째 구역") < text.index("열번째 구역"), \
        "sections read in string order (section10 before section2)"
    assert "본문 첫 줄" in text and "이어서" in text
    assert "항목\t금액" in text and "인건비\t1,200" in text, "the table was not read as rows"
    assert text.count("인건비") == 2, "a table cell was printed twice (once per section is right)"
    assert "NOT BODY" not in text, "a non-body part was read as content"
    assert "localhost" not in text, "an external entity was resolved — XXE"


def _cfb(streams: dict) -> bytes:
    """A minimal OLE compound file (v3, 512-byte sectors) — enough for olefile.

    Every stream is padded to >= 4096 bytes so it lives in the regular FAT
    (the mini-stream is not needed for a fixture). `streams` maps a path
    tuple → bytes; one storage level is supported, which is what HWP uses.
    """
    import struct
    SECT, END, FREE, FATSECT, NOSTREAM = 512, 0xFFFFFFFE, 0xFFFFFFFF, 0xFFFFFFFD, 0xFFFFFFFF
    datas, entries = [], []  # entries: (name, type, child, left, right, start, size)
    entries.append(["Root Entry", 5, NOSTREAM, NOSTREAM, NOSTREAM, END, 0])
    storages = {}
    next_sector = 2
    for path, data in streams.items():
        if len(path) == 2 and path[0] not in storages:
            storages[path[0]] = len(entries)
            entries.append([path[0], 1, NOSTREAM, NOSTREAM, NOSTREAM, 0, 0])
        padded = data + b"\x00" * (max(4096, -(-len(data) // SECT) * SECT) - len(data))
        idx = len(entries)
        entries.append([path[-1], 2, NOSTREAM, NOSTREAM, NOSTREAM, next_sector, len(padded)])
        datas.append((next_sector, padded))
        next_sector += len(padded) // SECT
        parent = entries[storages[path[0]]] if len(path) == 2 else entries[0]
        if parent[2] == NOSTREAM:
            parent[2] = idx
        else:  # chain as right siblings of the parent's first child
            sib = parent[2]
            while entries[sib][4] != NOSTREAM:
                sib = entries[sib][4]
            entries[sib][4] = idx
    # storages hang off the root, as right siblings too
    for sidx in storages.values():
        root = entries[0]
        if root[2] == NOSTREAM:
            root[2] = sidx
        else:
            sib = root[2]
            while entries[sib][4] != NOSTREAM:
                sib = entries[sib][4]
            entries[sib][4] = sidx
    fat = [FREE] * 128
    fat[0], fat[1] = FATSECT, END
    for start, padded in datas:
        n = len(padded) // SECT
        for k in range(n):
            fat[start + k] = start + k + 1 if k < n - 1 else END
    header = bytearray(512)
    header[0:8] = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    struct.pack_into("<HHHHH", header, 24, 0x3E, 3, 0xFFFE, 9, 6)
    struct.pack_into("<IIIIIIII", header, 44, 1, 1, 0, 0x1000, END, 0, END, 0)
    struct.pack_into("<I", header, 76, 0)
    for i in range(1, 109):
        struct.pack_into("<I", header, 76 + 4 * i, FREE)
    dirs = bytearray()
    for name, typ, child, left, right, start, size in entries:
        e = bytearray(128)
        raw = name.encode("utf-16-le")
        e[0:len(raw)] = raw
        struct.pack_into("<HBB", e, 64, len(raw) + 2, typ, 1)
        struct.pack_into("<III", e, 68, left, right, child)
        struct.pack_into("<II", e, 116, start, size)
        dirs += e
    dirs += b"\x00" * (SECT - len(dirs) % SECT if len(dirs) % SECT else 0)
    assert len(dirs) == SECT, "fixture supports one directory sector"
    body = bytearray(struct.pack("<128I", *fat)) + dirs
    for _, padded in datas:
        body += padded
    return bytes(header) + bytes(body)


def _hwp_record(tag: int, payload: bytes) -> bytes:
    import struct
    if len(payload) >= 0xFFF:
        return struct.pack("<II", tag | (0xFFF << 20), len(payload)) + payload
    return struct.pack("<I", tag | (len(payload) << 20)) + payload


def _hwp_units(*parts) -> bytes:
    """UTF-16LE text, with ints as raw control units."""
    out = bytearray()
    for p in parts:
        out += p.encode("utf-16-le") if isinstance(p, str) else p.to_bytes(2, "little")
    return bytes(out)


def _hwp(*, compressed: bool, password: bool = False) -> bytes:
    import zlib
    table_ctrl = [11, *[ord(c) for c in " lbt"], 0x4141, 0x4242, 11]  # 8 units, junk payload ≥ 32
    tab_ctrl = [9, 0x5858, 0x5959, 0x5A5A, 0x5A5A, 0x5A5A, 0x5A5A, 9]
    long_para = "가" * 2100  # > 4095 bytes → the extended-size record header
    section = b"".join([
        _hwp_record(66, b"\x00" * 22),                               # PARA_HEADER (ignored)
        _hwp_record(67, _hwp_units("사업계획서 ", *tab_ctrl, "요약", *table_ctrl, 13)),
        _hwp_record(67, _hwp_units("셀 내용", 13)),                   # a table cell's paragraph
        _hwp_record(68, b"\x01\x02\x03\x04"),                        # PARA_CHAR_SHAPE (ignored)
        _hwp_record(67, _hwp_units(long_para, 13)),
    ])
    if compressed:
        c = zlib.compressobj(9, zlib.DEFLATED, -15)
        section = c.compress(section) + c.flush()
    flags = (1 if compressed else 0) | (2 if password else 0)
    file_header = b"HWP Document File".ljust(32, b"\x00") + bytes([0, 3, 0, 5]) + flags.to_bytes(4, "little")
    return _cfb({("FileHeader",): file_header.ljust(256, b"\x00"),
                 ("BodyText", "Section0"): section})


@pytest.mark.parametrize("compressed", [True, False])
def test_am2_d18_hwp5_reads_paragraph_text_and_skips_controls(compressed):
    pytest.importorskip("olefile")
    from services.documents import extract_text

    text, sections = asyncio.run(extract_text(_hwp(compressed=compressed), "hwp"))
    assert sections == 1
    assert "사업계획서" in text and "요약" in text and "셀 내용" in text
    assert "\t" in text, "the tab control was not kept as a tab"
    for junk in ("XX", "YY", "AA", "BB", "lbt"):
        assert junk not in text, f"a control's payload leaked into the text ({junk})"
    assert "가" * 2100 in text, "the extended-size record header was misread"


def test_am2_d18_a_locked_hwp_reads_empty_and_takes_the_marker():
    """D18 — a password-protected HWP has no readable body. Empty, not garbage:
    the upload then takes the am.1 D9 marker instead of a projection of noise."""
    pytest.importorskip("olefile")
    from services.documents import extract_text

    assert asyncio.run(extract_text(_hwp(compressed=True, password=True), "hwp")) == ("", 0)
    assert asyncio.run(extract_text(b"not an ole file", "hwp")) == ("", 0)


def test_am2_d18_olefile_reaches_both_services():
    """D18 — both Render services install from api/requirements.txt."""
    import re
    reqs = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert re.search(r"^olefile\b", reqs, re.MULTILINE), "olefile is not a declared dependency"
