"""Gate — the lane artifact contract (2026-07-09, the chat artifact card).

A lane's WriteFile/EditFile lands an attributed revision in the shared commons
(ADR-411: "the transcript is private; the work lands in files"). Before this
change the member saw only the VERB NAME in a footer — `gemini-2.5-pro ·
WriteFile…` — never the file. The stream now carries the produced PATH so the
chat surface can mount the same viewer the Files surface uses.

What this gate pins:

  1. `artifact_path_from` is a PURE function of (verb, result). It is the only
     place the path is derived, and it derives it from the primitive's RESULT
     (which `handle_write_file` has normalized) rather than from the model's
     arguments (which it has not).
  2. Only WRITE verbs produce artifacts. ReadFile / ListFiles / SearchFiles
     also return a `path` — a card for a read would be a lie about what the
     lane did.
  3. A FAILED write produces nothing. The member never gets a card for a file
     that isn't there.
  4. The three collaborating layers agree on the wire name `artifacts`
     (runner → route SSE + persisted metadata → FE).

Run:  cd api && python -m pytest test_lane_artifacts.py -q
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from services.lane_runner import (  # noqa: E402
    LANE_ARTIFACT_VERBS,
    LANE_TOOL_NAMES,
    artifact_path_from,
)

_OK_WRITE = {"success": True, "scope": "workspace", "path": "/workspace/operation/reports/q3.md", "mode": "write"}


# ---------------------------------------------------------------------------
# 1 + 2 — the verb gate
# ---------------------------------------------------------------------------

def test_write_verbs_produce_the_path():
    for verb in ("WriteFile", "EditFile"):
        assert artifact_path_from(verb, _OK_WRITE) == "/workspace/operation/reports/q3.md"


def test_read_verbs_produce_nothing_even_though_they_return_a_path():
    # ReadFile/ListFiles/SearchFiles legitimately echo a path. A card for a
    # read would misreport what the lane did to the commons.
    for verb in ("ReadFile", "SearchFiles", "ListFiles"):
        assert artifact_path_from(verb, _OK_WRITE) is None


def test_artifact_verbs_are_a_strict_subset_of_the_lane_surface():
    assert set(LANE_ARTIFACT_VERBS) < set(LANE_TOOL_NAMES)


def test_a_tool_off_the_lane_surface_produces_nothing():
    assert artifact_path_from("DispatchSpecialist", _OK_WRITE) is None


# ---------------------------------------------------------------------------
# 3 — failure and malformed results are silent
# ---------------------------------------------------------------------------

def test_failed_write_produces_nothing():
    assert artifact_path_from("WriteFile", {"success": False, "error": "empty_content_blocked"}) is None


def test_gate_rejected_write_produces_nothing():
    # The permission gate (ADR-307/320) returns a failure dict, not a raise.
    assert artifact_path_from("WriteFile", {"success": False, "error": "path_locked"}) is None


def test_missing_or_empty_path_produces_nothing():
    assert artifact_path_from("WriteFile", {"success": True}) is None
    assert artifact_path_from("WriteFile", {"success": True, "path": ""}) is None
    assert artifact_path_from("WriteFile", {"success": True, "path": None}) is None


def test_non_dict_result_produces_nothing():
    for bad in (None, "written", 42, ["/workspace/x.md"]):
        assert artifact_path_from("WriteFile", bad) is None


def test_the_path_comes_from_the_result_not_the_arguments():
    # `handle_write_file` normalizes `workspace/…` / `/workspace/…` and returns
    # the canonical absolute form. Whatever the model asked for is irrelevant.
    result = {"success": True, "path": "/workspace/operation/notes.md"}
    assert artifact_path_from("WriteFile", result) == "/workspace/operation/notes.md"


# ---------------------------------------------------------------------------
# 4 — the three layers agree on the wire name
# ---------------------------------------------------------------------------

_API = pathlib.Path(__file__).parent
_WEB = _API.parent / "web"


def test_runner_emits_the_artifact_event_and_the_done_key():
    src = (_API / "services" / "lane_runner.py").read_text()
    assert 'yield ("artifact", {"path": produced, "verb": name})' in src
    assert '"artifacts": artifacts,' in src


def test_route_forwards_the_frame_and_persists_the_metadata():
    src = (_API / "routes" / "lanes.py").read_text()
    assert 'elif kind == "artifact":' in src
    assert 'yield sse({"artifact": payload})' in src
    # persisted on the assistant row so a reloaded lane keeps its cards
    assert '"artifacts": artifacts,' in src


def test_frontend_reads_the_same_wire_names():
    client = (_WEB / "lib" / "api" / "client.ts").read_text()
    assert "onArtifact" in client
    assert "evt.artifact" in client
    assert "evt.artifacts" in client

    panel = (_WEB / "components" / "chat-surface" / "LanePanel.tsx").read_text()
    assert "ArtifactCard" in panel
    assert "onArtifact" in panel
    # the reply is markdown now, not raw text
    assert "MarkdownRenderer" in panel


# ---------------------------------------------------------------------------
# 5 — Singular Implementation: one viewer, two mounts
# ---------------------------------------------------------------------------

def test_the_file_body_is_the_only_kind_switch():
    """`FileBody` is THE renderer. No mount may re-derive the viewer kind and
    branch on it — that is how the `.mp4`-renders-as-text bug would come back,
    in two places instead of one."""
    body = _WEB / "components" / "workspace" / "FileBody.tsx"
    assert body.exists(), "FileBody is the one shared viewer"

    mounts = [
        _WEB / "components" / "workspace" / "ContentViewer.tsx",
        _WEB / "components" / "chat-surface" / "ArtifactCard.tsx",
    ]
    for mount in mounts:
        src = mount.read_text()
        assert "FileBody" in src, f"{mount.name} must mount the shared viewer"
        # A mount may LABEL a type (describeViewerApplication); it may not
        # RESOLVE one and switch on it.
        assert "resolveViewerApplication" not in src, (
            f"{mount.name} resolves the viewer kind itself — dispatch belongs in FileBody"
        )


def test_the_type_table_has_a_binary_terminal_and_media_nodes():
    src = (_WEB / "lib" / "file-types" / "index.ts").read_text()
    for kind in ("'video'", "'audio'"):
        assert kind in src, f"the type table must know {kind}"
    # The terminal is DERIVED from text-ness, not an enumerated allowlist.
    assert "isTextualContentType" in src
    assert "if (t && !isTextualContentType(t)) return 'download';" in src
