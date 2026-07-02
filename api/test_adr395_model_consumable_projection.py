"""
ADR-395 — the model-consumable projection: upload intake conformance.

Drives the REAL upload intake logic (process_document → ExtractTextFromBlob →
path/content_url/embed-eligibility), mocking only at the DB/storage boundary
(write_revision + _embed_workspace_file + storage). This is the gate the prior
coverage lacked: test_adr331 mocks process_document entirely, so it exercised the
batch envelope but NOTHING of ADR-395's raw+derive core. The two assertions that
would have caught the shipped defects:

  • the raw lands at inbound/uploads/{principal}/{slug}.{ext} with content_url
    (not a derived .md masquerading as the upload);
  • the derived .extracted.md projection is EMBED-ELIGIBLE + RECALL-REACHABLE
    (Defect 2 — the projection was landing in a lane recall could not see).

Plus: the download route resolves storage_path from content_url for new-shape
rows (Defect 1), and the derive-registry verdicts are correct.
"""

import asyncio
from unittest.mock import patch

import pytest


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
    authored_by, ...}). Returns a fake revision id."""
    def _write(db_client=None, *, user_id, path, content, authored_by, message,
               lifecycle=None, content_type=None, content_url=None, **_k):
        store[path] = {
            "content": content,
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


def test_upload_lands_raw_in_inbound_uploads_with_content_url():
    """Piece A: the RAW blob lands at inbound/uploads/{principal}/{slug}.{ext}
    carrying content_url — NOT a derived .md, NOT under the legacy uploads/ root."""
    store, embeds = {}, []
    body = "Acme quarterly brief.\n" + ("Revenue grew. " * 40)
    result = _run_upload(store, embeds, filename="acme-brief.pdf", file_type="pdf", text_body=body)

    assert result["success"] is True, result
    raw_path = result["raw_path"]
    assert raw_path == "/workspace/inbound/uploads/operator/acme-brief.pdf", raw_path
    raw = store[raw_path]
    # content_url is the stable /blob endpoint; content is a caption, not text.
    assert raw["content_url"] == "/api/documents/blob?storage_path=user-1234%2Fdoc-1%2Foriginal.pdf", raw
    assert raw["content"].startswith("Uploaded file:"), raw["content"]
    assert raw["authored_by"] == "operator"  # the raw is the operator's


def test_upload_derives_projection_citing_the_raw():
    """Piece B: a co-located .extracted.md projection is written, citing the raw
    via a `derived_from:` first line, attributed system:extract."""
    store, embeds = {}, []
    body = "Acme quarterly brief.\n" + ("Revenue grew. " * 40)
    result = _run_upload(store, embeds, filename="acme-brief.pdf", file_type="pdf", text_body=body)

    proj_path = result["projection_path"]
    assert proj_path == "/workspace/inbound/uploads/operator/acme-brief.extracted.md", proj_path
    proj = store[proj_path]
    # DP32 citation is the first line so trace/_extract_derived_from_list walks it.
    assert proj["content"].splitlines()[0] == "derived_from: /workspace/inbound/uploads/operator/acme-brief.pdf", proj["content"][:120]
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

    proj_path = "/workspace/inbound/uploads/operator/acme-brief.extracted.md"
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

    assert r1["raw_path"] == "/workspace/inbound/uploads/operator/dup.pdf"
    assert r2["raw_path"] == "/workspace/inbound/uploads/operator/dup-2.pdf", r2["raw_path"]
    assert r2["projection_path"] == "/workspace/inbound/uploads/operator/dup-2.extracted.md"


# ── The derive-registry verdicts (ADR-395 D2 / DP34) ───────────────────────


@pytest.mark.parametrize("ft,expected", [
    ("pdf", "text"), ("docx", "text"), ("txt", "text"), ("md", "text"), ("csv", "text"),
    ("png", "passthrough"), ("jpg", "passthrough"),
    ("xlsx", "deferred"), ("pptx", "deferred"), ("zip", "deferred"), ("mp3", "deferred"),
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
        "raw_path": "/workspace/inbound/uploads/operator/logo.png",
        "write_to": "/workspace/inbound/uploads/operator/logo.extracted.md",
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
    ("/workspace/inbound/uploads/operator/acme.extracted.md", True),
    ("workspace/inbound/uploads/operator/acme.extracted.md", True),  # no leading slash
    # The raw upload → shown (the user's file).
    ("/workspace/inbound/uploads/operator/acme.pdf", False),
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
