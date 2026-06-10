"""ADR-331 — Setup-as-Rendering: the /setup Sequence surface + harvest.

Regression gate for the three-phase ADR-331 implementation:

  Phase 1 (D1, D2) — `/setup` is a kernel atomic surface, Sequence archetype,
                     os-config register, owns no substrate (substrate_paths
                     == []); the sequence archetype is registered in both the
                     Python ARCHETYPES tuple and the TS Archetype union.
  Phase 2 (D3, D4) — harvest is an ordinary attributed invocation: the
                     `agent:harvest` author string validates against the
                     existing is_valid_author taxonomy (no new author prefix);
                     the metadata-only dry-run endpoint performs no writes.
  Phase 3 (D5)     — /documents/upload accepts a file list + .zip expansion,
                     writing N attributed /workspace/uploads/*.md rows from
                     one call.

Pure-Python / pure-fs assertions where possible. No DB, no network, no LLM.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(p: Path) -> str:
    return p.read_text() if p.exists() else ""


# =============================================================================
# Phase 1 — /setup surface + sequence archetype (D1, D2)
# =============================================================================


def test_phase1_setup_registered_as_sequence_os_config():
    """D1: `setup` is in KERNEL_SURFACES with archetype=sequence,
    register=os-config, route=/setup, summon-only (default_pinned False)."""
    from services.kernel_surfaces import KERNEL_SURFACES

    setup = next((s for s in KERNEL_SURFACES if s["slug"] == "setup"), None)
    assert setup is not None, "ADR-331 D1: `setup` not registered in KERNEL_SURFACES"
    assert setup["archetype"] == "sequence", (
        f"ADR-331 D1: setup archetype must be 'sequence', got {setup['archetype']!r}"
    )
    assert setup["register"] == "os-config", (
        f"ADR-331 D1: setup register must be 'os-config', got {setup['register']!r}"
    )
    assert setup["route"] == "/setup"
    assert setup["default_pinned"] is False, "ADR-331 D1: setup is summon-only after first run"


def test_phase1_setup_owns_no_substrate():
    """D1 (load-bearing): setup is a RENDERING over api.workspace.getState();
    it owns no file. substrate_paths == [] is the no-stored-state encoding."""
    from services.kernel_surfaces import KERNEL_SURFACES

    setup = next(s for s in KERNEL_SURFACES if s["slug"] == "setup")
    assert setup["substrate_paths"] == [], (
        "ADR-331 D1: setup must own no substrate path — it reads the "
        "workspace-state composition. A non-empty substrate_paths would "
        "imply stored wizard state, which the Sequence archetype forbids."
    )


def test_phase1_sequence_archetype_in_python_tuple():
    """D1: the `sequence` archetype is registered in the Python ARCHETYPES."""
    from services.kernel_surfaces import ARCHETYPES

    assert "sequence" in ARCHETYPES, "ADR-331 D1: 'sequence' missing from ARCHETYPES"


def test_phase1_sequence_archetype_in_ts_union():
    """D1: the TS Archetype union mirrors the Python tuple — `sequence`
    must be present in web/lib/compositor/types.ts (drift = regression)."""
    ts = _read(REPO_ROOT / "web" / "lib" / "compositor" / "types.ts")
    assert "'sequence'" in ts, (
        "ADR-331 D1: 'sequence' missing from the TS Archetype union — "
        "Python ARCHETYPES and the TS union must not drift."
    )


def test_phase1_setup_page_exists():
    """D1: the /setup route page exists and renders the SetupSequence."""
    page = _read(REPO_ROOT / "web" / "app" / "(authenticated)" / "setup" / "page.tsx")
    assert page, "ADR-331 D1: /setup route page missing"
    assert "SetupSequence" in page, "ADR-331 D1: /setup page must render SetupSequence"


def test_phase1_setup_renderer_reads_getstate_no_local_state():
    """D1: the SetupSequence renderer reads api.workspace.getState() and stores
    no progress of its own (the no-wizard-state rule). We assert it calls
    getState and does NOT persist any setup/wizard/progress to an API."""
    src = _read(REPO_ROOT / "web" / "components" / "library" / "SetupSequence.tsx")
    assert src, "ADR-331 D1: SetupSequence component missing"
    assert "api.workspace.getState()" in src, (
        "ADR-331 D1: SetupSequence must derive from api.workspace.getState()"
    )
    # No persisted wizard/setup/progress writes — derivation only.
    for banned in ("saveSetup", "setWizardState", "api.setup.save", "persistProgress"):
        assert banned not in src, (
            f"ADR-331 anti-goal: SetupSequence must not persist progress ({banned})"
        )


def test_phase1_first_run_redirect_points_to_setup():
    """D2: the first-run redirect target moved to /setup?first_run=1."""
    cb = _read(REPO_ROOT / "web" / "app" / "auth" / "callback" / "page.tsx")
    assert "/setup?first_run=1" in cb, (
        "ADR-331 D2: first-run redirect must target /setup?first_run=1"
    )
    # The old /program?first_run=1 target must be gone from the redirect.
    assert "/program?first_run=1" not in cb, (
        "ADR-331 D2: stale /program?first_run=1 redirect must be removed"
    )


def test_phase1_home_cta_points_to_setup():
    """D6: the home empty-state CTA repoints from /program to /setup."""
    src = _read(REPO_ROOT / "web" / "components" / "library" / "HomeRenderer.tsx")
    assert 'href="/setup"' in src, (
        "ADR-331 D6: UnactivatedHomeCTA must point to /setup"
    )


def test_phase1_setup_is_protected_route():
    """D2: /setup is auth-gated (first-run authenticated surface)."""
    mw = _read(REPO_ROOT / "web" / "lib" / "supabase" / "middleware.ts")
    assert '"/setup"' in mw, (
        "ADR-331: /setup must be in PROTECTED_PREFIXES — it is an "
        "authenticated first-run surface."
    )


def test_phase1_rocket_icon_registered():
    """D1: the setup surface's icon_key='rocket' resolves (no Box fallback)."""
    icons = _read(REPO_ROOT / "web" / "lib" / "shell" / "surface-icons.tsx")
    assert "rocket: Rocket" in icons, (
        "ADR-331 D1: 'rocket' icon must be registered for /setup — an "
        "unregistered icon_key falls back to Box (visible inconsistency)."
    )


# =============================================================================
# Phase 2 — harvest invocation attribution (D3)
# =============================================================================


def test_phase2_agent_harvest_author_validates():
    """D3: harvest writes attributed substrate with `agent:harvest` — this
    must validate against the existing is_valid_author taxonomy (the `agent:`
    prefix is already valid; harvest adds no new author prefix)."""
    from services.authored_substrate import is_valid_author

    assert is_valid_author("agent:harvest"), (
        "ADR-331 D3: `agent:harvest` must validate against is_valid_author — "
        "harvest is an ordinary attributed invocation, no new author prefix."
    )


def test_phase2_harvest_caller_identity_is_agent_harvest():
    """D3: the harvest service attributes writes as agent:harvest (the
    caller_identity that flows to WriteFile's authored_by)."""
    from services.harvest import HARVEST_CALLER_IDENTITY

    assert HARVEST_CALLER_IDENTITY == "agent:harvest"


def test_phase2_harvest_dry_run_does_no_writes():
    """D4: the dry-run is metadata-only — no write/WriteFile/write_revision
    in the dry-run path. We assert the source never imports a write primitive
    in the dry-run function body (static guard against accidental writes)."""
    import inspect

    from services.harvest import harvest_dry_run

    src = inspect.getsource(harvest_dry_run)
    for banned in ("write_revision", "WriteFile", "handle_write_file"):
        assert banned not in src, (
            f"ADR-331 D4: harvest_dry_run must perform NO writes (found {banned!r})"
        )


def test_phase2_harvest_scope_normalization_drops_unknown_providers():
    """D4: the picker's ephemeral scope is normalized; unknown providers are
    dropped, known ones (slack/notion/github) survive with their range."""
    from services.harvest import _normalize_sources

    scope = {"sources": [
        {"provider": "slack", "id": "C1", "range_days": 30},
        {"provider": "bogus", "id": "x"},
        {"provider": "notion", "id": "p1"},
    ]}
    norm = _normalize_sources(scope)
    assert [s["provider"] for s in norm] == ["slack", "notion"]
    assert norm[0]["range_days"] == 30


def test_phase2_harvest_not_in_default_providers_or_new_primitive():
    """D3 anti-goal: harvest adds no new primitive. The harvest service uses
    execute_primitive + existing read tools; it does not register a primitive
    handler. Assert no 'harvest' handler in the primitive registry."""
    from services.primitives.registry import HANDLERS

    assert not any("harvest" in name.lower() for name in HANDLERS), (
        "ADR-331 D3: harvest must NOT register a new primitive — it's an "
        "invocation using existing read tools + WriteFile."
    )


def test_phase2_harvest_route_registered():
    """D3/D4: the /harvest/dry-run + /harvest/run endpoints are registered."""
    from routes import harvest as harvest_route

    paths = {r.path for r in harvest_route.router.routes}
    assert "/harvest/dry-run" in paths
    assert "/harvest/run" in paths


def test_phase2_changelog_entry_present():
    """Prompt-change protocol: the harvest prompt requires a CHANGELOG entry."""
    changelog = _read(REPO_ROOT / "api" / "prompts" / "CHANGELOG.md")
    assert "ADR-331 Phase 2: harvest invocation system prompt" in changelog, (
        "ADR-331 Phase 2 adds a harvest-shaped LLM prompt — CHANGELOG entry required."
    )


# =============================================================================
# Phase 3 — multi-file + .zip upload (D5)
# =============================================================================
#
# Mix of pure-logic assertions (zip expander, type resolver, single-file error
# paths — no DB) AND a real BEHAVIOR test: the route handler driven directly
# with process_document mocked, proving N files in one call → N result items
# (→ N attributed /workspace/uploads/*.md writes), .zip expansion, and
# non-transactional partial success.

import asyncio
import io
import zipfile
from unittest.mock import patch


def test_phase3_zip_expander_filters_correctly():
    """D5: .zip expands to supported entries only — dirs, hidden, macOS
    resource forks, and unsupported types are filtered; corrupt → []."""
    from routes.documents import _expand_zip

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("notes/decisions.md", "# Decisions\nWe chose X.")
        zf.writestr("readme.txt", "plain text content")
        zf.writestr("image.png", b"\x89PNG")            # unsupported
        zf.writestr(".hidden.md", "hidden")              # hidden
        zf.writestr("__MACOSX/._decisions.md", "fork")   # resource fork
        zf.writestr("sub/", "")                          # directory
    names = sorted(n for n, _ in _expand_zip(buf.getvalue()))
    assert names == ["decisions.md", "readme.txt"], names
    assert _expand_zip(b"not a zip") == []


def test_phase3_type_resolver():
    """D5: file type resolves by content-type or extension; unsupported → None."""
    from routes.documents import _resolve_file_type

    assert _resolve_file_type("application/pdf", "x") == "pdf"
    assert _resolve_file_type("", "notes.md") == "md"
    assert _resolve_file_type("", "report.docx") == "docx"
    assert _resolve_file_type("", "image.png") is None


def test_phase3_single_upload_rejects_oversize_and_unsupported_without_db():
    """D5: per-file validation (oversize, unsupported, empty) returns an error
    UploadResultItem and never touches storage/DB (the error paths are pure)."""
    from routes.documents import _process_single_upload, MAX_FILE_SIZE

    # Unsupported type — rejected before any storage call.
    r1 = asyncio.run(_process_single_upload(
        content=b"x" * 100, content_type="", filename="img.png",
        user_id="u", service=None,  # service untouched on this path
    ))
    assert r1.success is False and "Unsupported" in (r1.error or "")

    # Oversize — rejected before storage.
    r2 = asyncio.run(_process_single_upload(
        content=b"x" * (MAX_FILE_SIZE + 1), content_type="text/plain", filename="big.txt",
        user_id="u", service=None,
    ))
    assert r2.success is False and "too large" in (r2.error or "")

    # Empty — rejected before storage.
    r3 = asyncio.run(_process_single_upload(
        content=b"x", content_type="text/plain", filename="tiny.txt",
        user_id="u", service=None,
    ))
    assert r3.success is False and "empty" in (r3.error or "").lower()


# ── Behavior test fixtures ────────────────────────────────────────────────


class _FakeUploadFile:
    """Minimal UploadFile stand-in: .filename, .content_type, async .read()."""

    def __init__(self, filename, content_type, content):
        self.filename = filename
        self.content_type = content_type
        self._content = content

    async def read(self):
        return self._content


class _FakeAuth:
    def __init__(self, user_id="user-1234"):
        self.user_id = user_id
        self.client = object()


class _FakeStorageBucket:
    """Minimal Supabase storage bucket: upload() ok, remove() no-op."""

    def upload(self, *a, **k):
        return {"path": k.get("path") or (a[0] if a else "")}  # no .error → success

    def remove(self, *a, **k):
        return {}


class _FakeStorage:
    def from_(self, _bucket):
        return _FakeStorageBucket()


class _FakeService:
    """Service client whose only exercised surface here is .storage (binary
    upload). process_document is mocked, so no .table() calls reach this."""

    storage = _FakeStorage()


def _fake_process_document_factory(written_paths):
    """Returns an async process_document mock that records a distinct write per
    call (mimicking _unique_upload_path's N-files-→-N-rows guarantee) and fails
    deterministically for filenames containing 'FAIL' (to prove partial success).
    """
    counter = {"n": 0}

    async def _fake(*, filename, **kwargs):
        if "FAIL" in filename:
            return {"success": False, "error": "Processing failed (simulated)"}
        counter["n"] += 1
        slug = filename.rsplit(".", 1)[0].lower().replace(" ", "-")
        path = f"/workspace/uploads/{slug}.md"
        # Distinct path per call even on slug collision (mirror real behavior).
        if path in written_paths:
            path = f"/workspace/uploads/{slug}-{counter['n']}.md"
        written_paths.append(path)
        return {"success": True, "workspace_path": path, "word_count": 42}

    return _fake


def test_phase3_behavior_n_files_one_call_writes_n_rows():
    """D5 BEHAVIOR: N files in one call → N attributed upload rows. Drives the
    real upload_documents handler; process_document mocked at the write boundary."""
    from routes import documents

    written: list = []
    files = [
        _FakeUploadFile("decisions.md", "text/markdown", b"# Decisions\n" + b"x" * 60),
        _FakeUploadFile("notes.txt", "text/plain", b"some notes " * 10),
        _FakeUploadFile("brief.md", "text/markdown", b"# Brief\n" + b"y" * 60),
    ]
    auth = _FakeAuth()

    with patch.object(documents, "process_document", _fake_process_document_factory(written)), \
         patch.object(documents, "get_service_client", lambda: _FakeService()):
        resp = asyncio.run(documents.upload_documents(auth, files=files, project_id=None))

    assert resp.succeeded == 3, resp
    assert resp.failed == 0
    assert len(resp.results) == 3
    assert len(written) == 3, "N files must write N distinct rows"
    assert all(r.workspace_path and r.workspace_path.startswith("/workspace/uploads/") for r in resp.results)


def test_phase3_behavior_zip_expands_to_n_rows():
    """D5 BEHAVIOR: a single .zip → N rows (one per supported entry)."""
    from routes import documents

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.md", "# A\n" + "x" * 60)
        zf.writestr("b.txt", "bbb " * 30)
        zf.writestr("skip.png", b"\x89PNG")  # filtered
    zip_file = _FakeUploadFile("bundle.zip", "application/zip", buf.getvalue())

    written: list = []
    with patch.object(documents, "process_document", _fake_process_document_factory(written)), \
         patch.object(documents, "get_service_client", lambda: _FakeService()):
        resp = asyncio.run(documents.upload_documents(_FakeAuth(), files=[zip_file], project_id=None))

    assert resp.succeeded == 2, f"zip should expand to 2 supported entries, got {resp.succeeded}"
    assert len(written) == 2


def test_phase3_behavior_partial_success_non_transactional():
    """D5 BEHAVIOR: a failing file does not abort the batch — successes still
    land, failures are reported per-file (non-transactional)."""
    from routes import documents

    files = [
        _FakeUploadFile("good.md", "text/markdown", b"# Good\n" + b"x" * 60),
        _FakeUploadFile("FAIL.md", "text/markdown", b"# Bad\n" + b"x" * 60),
        _FakeUploadFile("alsogood.txt", "text/plain", b"text " * 20),
    ]
    written: list = []
    with patch.object(documents, "process_document", _fake_process_document_factory(written)), \
         patch.object(documents, "get_service_client", lambda: _FakeService()):
        resp = asyncio.run(documents.upload_documents(_FakeAuth(), files=files, project_id=None))

    assert resp.succeeded == 2, resp
    assert resp.failed == 1
    assert len(written) == 2, "successful files persist despite a sibling failure"
    failed = [r for r in resp.results if not r.success]
    assert len(failed) == 1 and failed[0].filename == "FAIL.md"


# ── Fully-real single-file path (real extract_text + real write_revision) ──


class _FakeQuery:
    """A tiny chainable Supabase query stand-in over an in-memory table.

    Supports the exact chains process_document → write_revision exercise:
      .select(...).eq(...).like(...).order(...).limit(...).execute()
      .insert(row).execute()
      .upsert(row, on_conflict=...).execute()
    """

    def __init__(self, table):
        self._t = table
        self._filters = []
        self._likes = []

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def like(self, col, pattern):
        self._likes.append((col, pattern.rstrip("%")))
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def range(self, *a, **k):
        return self

    def _matches(self, row):
        for col, val in self._filters:
            if row.get(col) != val:
                return False
        for col, prefix in self._likes:
            if not str(row.get(col, "")).startswith(prefix):
                return False
        return True

    def execute(self):
        rows = [r for r in self._t.rows if self._matches(r)]
        return type("R", (), {"data": rows})()

    def insert(self, row):
        import uuid as _u
        new = {**row, "id": str(_u.uuid4())}
        self._t.rows.append(new)
        return type("Q", (), {"execute": lambda _s=None: type("R", (), {"data": [new]})()})()

    def upsert(self, row, on_conflict=None):
        keys = (on_conflict or "").split(",") if on_conflict else []
        keys = [k.strip() for k in keys if k.strip()]
        if keys:
            for existing in self._t.rows:
                if all(existing.get(k) == row.get(k) for k in keys):
                    existing.update(row)
                    return type("Q", (), {"execute": lambda _s=None: type("R", (), {"data": [existing]})()})()
        self._t.rows.append(dict(row))
        return type("Q", (), {"execute": lambda _s=None: type("R", (), {"data": [row]})()})()


class _FakeTable:
    def __init__(self):
        self.rows = []


class _FakeDB:
    """In-memory Supabase client supporting the write_revision surface +
    storage. Used to prove the REAL attributed write lands."""

    storage = _FakeStorage()

    def __init__(self):
        self._tables = {}

    def table(self, name):
        self._tables.setdefault(name, _FakeTable())
        return _FakeQuery(self._tables[name])

    # convenience for assertions
    def rows(self, name):
        return self._tables.get(name, _FakeTable()).rows


def test_phase3_real_write_path_lands_attributed_upload_rows():
    """D5 STRONGEST RECEIPT: drive the REAL upload_documents handler with the
    REAL process_document + REAL write_revision (against an in-memory DB) and
    REAL text extraction. Two .md files in one call must produce two
    workspace_files rows under /workspace/uploads/, each with a
    workspace_file_versions revision attributed `operator`. Only the network
    embedding boundary is stubbed."""
    from routes import documents

    db = _FakeDB()
    files = [
        _FakeUploadFile("alpha.md", "text/markdown",
                        b"# Alpha\n" + b"This is real markdown content, well over fifty chars long. " * 2),
        _FakeUploadFile("beta.md", "text/markdown",
                        b"# Beta\n" + b"Another real document with plenty of extractable text content here. " * 2),
    ]

    async def _noop_embed(*a, **k):
        return None

    # _embed_workspace_file is imported lazily inside process_document from
    # services.primitives.workspace — patch it at its source module.
    with patch.object(documents, "get_service_client", lambda: db), \
         patch("services.primitives.workspace._embed_workspace_file", _noop_embed):
        resp = asyncio.run(documents.upload_documents(_FakeAuth(), files=files, project_id=None))

    assert resp.succeeded == 2, resp
    assert resp.failed == 0

    # REAL workspace_files rows landed under /workspace/uploads/.
    wf_rows = db.rows("workspace_files")
    upload_paths = sorted(r["path"] for r in wf_rows if r["path"].startswith("/workspace/uploads/"))
    assert len(upload_paths) == 2, f"expected 2 upload rows, got {upload_paths}"
    assert "/workspace/uploads/alpha.md" in upload_paths
    assert "/workspace/uploads/beta.md" in upload_paths

    # REAL revision rows, attributed operator (ADR-209 + ADR-249 Type B).
    ver_rows = db.rows("workspace_file_versions")
    upload_versions = [r for r in ver_rows if r["path"].startswith("/workspace/uploads/")]
    assert len(upload_versions) == 2
    assert all(r["authored_by"] == "operator" for r in upload_versions)


def test_phase3_behavior_empty_batch_rejected():
    """D5: a call with no supported files (e.g. only an empty/garbage zip) is a
    400, not a silent empty success."""
    from fastapi import HTTPException
    from routes import documents

    empty_zip = io.BytesIO()
    with zipfile.ZipFile(empty_zip, "w") as zf:
        zf.writestr("only.png", b"\x89PNG")  # nothing supported
    zf_file = _FakeUploadFile("empty.zip", "application/zip", empty_zip.getvalue())

    with patch.object(documents, "get_service_client", lambda: _FakeService()):
        try:
            asyncio.run(documents.upload_documents(_FakeAuth(), files=[zf_file], project_id=None))
            assert False, "expected HTTPException for no supported files"
        except HTTPException as e:
            assert e.status_code == 400


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
