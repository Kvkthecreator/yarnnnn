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
    ("wat-is-this", "deferred"),  # unknown = retained-not-consumable, never a break
    (None, "deferred"),
])
def test_registry_strategy_verdicts(ft, expected):
    from services.primitives.extract_text_from_blob import registry_strategy
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
