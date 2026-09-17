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
    # ADR-568 D3: the surface is the five file verbs PLUS the declared extras,
    # and an artifact verb may now live in either half (`GenerateImage` is an
    # extra). The invariant is "every artifact verb is on the surface" — it was
    # written against LANE_TOOL_NAMES only because every artifact verb happened
    # to be a file verb at the time.
    from services.lane_runner import lane_tool_names

    assert set(LANE_ARTIFACT_VERBS) < set(lane_tool_names())


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


# ---------------------------------------------------------------------------
# 6 — the PENDING artifact: the shape arrives before the file (2026-09-17)
#
# `pending_artifact_from` is `artifact_path_from`'s weaker sibling: it reads
# the ARGUMENTS and means "asked for", where the other reads the RESULT and
# means "landed". The whole of its correctness is that the two never get
# confused, so this section pins the difference rather than the function.
# ---------------------------------------------------------------------------

def _strip_comments(src: str) -> str:
    """Source with `#` comments and docstring bodies removed.

    ⚠️ Load-bearing, and learned the hard way three times: `inspect.getsource`
    and `read_text` both return COMMENTS, so a substring check can pass against
    prose that merely DESCRIBES the thing it is meant to prove — including a
    comment explaining why the code was removed. Every source assertion below
    runs on this.
    """
    out, in_doc, doc_q = [], False, ""
    for line in src.splitlines():
        stripped = line.strip()
        if in_doc:
            if doc_q in stripped:
                in_doc = False
            continue
        for q in ('"""', "'''"):
            if stripped.startswith(q):
                if not (stripped.endswith(q) and len(stripped) > len(q) * 2 - 1):
                    in_doc, doc_q = True, q
                stripped = ""
                break
        if not stripped or stripped.startswith("#"):
            continue
        out.append(line.split("  #")[0])
    return "\n".join(out)


def test_pending_reads_the_arguments_where_the_card_reads_the_result():
    from services.lane_runner import pending_artifact_from

    # The SAME call: arguments say where it is going, the result says where it
    # landed. Both must be derivable, independently, from their own source.
    args = {"path": "operation/reports/q3.md"}
    assert pending_artifact_from("WriteFile", args) == {
        "path": "/workspace/operation/reports/q3.md", "verb": "WriteFile",
    }
    assert artifact_path_from("WriteFile", args) is None, (
        "a pending path must never satisfy the LANDED derivation — that is the "
        "whole distinction, and it is what keeps a card off a failed write"
    )


def test_pending_normalizes_to_the_form_the_landed_card_carries():
    """The three spellings the model uses must converge on ONE path.

    If they do not, the pending card and the real card key differently and the
    member gets TWO cards for one write — the defect this normalization exists
    to prevent.
    """
    from services.lane_runner import pending_artifact_from

    landed = artifact_path_from("WriteFile", _OK_WRITE)
    for spelling in (
        "/workspace/operation/reports/q3.md",
        "workspace/operation/reports/q3.md",
        "operation/reports/q3.md",
    ):
        assert pending_artifact_from("WriteFile", {"path": spelling})["path"] == landed


def test_pending_is_silent_for_every_verb_that_makes_no_file():
    from services.lane_runner import pending_artifact_from

    # Reads echo a path; a delete names one that is about to STOP existing.
    for verb in ("ReadFile", "ListFiles", "SearchFiles", "DeleteFile", "DeleteFolder"):
        assert pending_artifact_from(verb, {"path": "a/b.md"}) is None


def test_pending_never_cards_a_prompt():
    """`GenerateImage`'s subject is its PROMPT — free text, not an address.

    Excluded BY ARGUMENT NAME, never by sniffing the string: a "looks like a
    path" heuristic rejected `toplevel.md` (a legal root write) while passing a
    one-word prompt.
    """
    from services.lane_runner import pending_artifact_from

    for prompt in ("a red bicycle at dusk", "sunset", "q3.md"):
        assert pending_artifact_from("GenerateImage", {"prompt": prompt}) is None
    # ...and the legal root write the heuristic used to reject:
    assert pending_artifact_from("WriteFile", {"path": "toplevel.md"}) == {
        "path": "/workspace/toplevel.md", "verb": "WriteFile",
    }


def test_pending_exposes_only_the_address_argument():
    """Never the raw argument dict — `content` must not reach the wire."""
    from services.lane_runner import pending_artifact_from

    out = pending_artifact_from(
        "WriteFile", {"path": "a/b.md", "content": "SECRET-BYTES"},
    )
    assert "SECRET-BYTES" not in str(out)
    assert set(out) == {"path", "verb"}


def test_pending_handles_malformed_arguments():
    from services.lane_runner import pending_artifact_from

    for bad in (None, "a/b.md", 42, ["a/b.md"]):
        assert pending_artifact_from("WriteFile", bad) is None
    for empty in ({}, {"path": ""}, {"path": "   "}, {"path": None}):
        assert pending_artifact_from("WriteFile", empty) is None


def test_the_pending_frame_is_emitted_and_forwarded_but_never_persisted():
    runner = _strip_comments((_API / "services" / "lane_runner.py").read_text())
    assert 'yield ("artifact_pending", _pending)' in runner
    # ⚠️ The pending path must NOT join `artifacts` — that list is what the
    # route persists, and persisting a provisional path is how a card for a
    # file that never landed would survive a reload.
    assert "artifacts.append(_pending" not in runner

    route = _strip_comments((_API / "routes" / "lanes.py").read_text())
    assert 'elif kind == "artifact_pending":' in route
    assert 'yield sse({"artifact_pending": payload})' in route
    pend = route.split('elif kind == "artifact_pending":')[1].split("elif kind ==")[0]
    assert "artifacts.append" not in pend, "the pending frame must not touch the persisted list"


def test_the_frontend_settles_the_pending_card_and_drops_what_never_landed():
    client = _strip_comments((_WEB / "lib" / "api" / "client.ts").read_text())
    assert "onArtifactPending" in client
    assert "evt.artifact_pending" in client

    panel = _strip_comments((_WEB / "components" / "chat-surface" / "LanePanel.tsx").read_text())
    assert "onArtifactPending" in panel
    assert "pending: true" in panel, "the pending card must be marked as such"
    # The drop at turn end: a card still pending when `done` arrives never
    # landed, and must not survive into the settled transcript.
    assert "const landed =" in panel and "f.path === a.path" in panel

    card = _strip_comments((_WEB / "components" / "chat-surface" / "ArtifactCard.tsx").read_text())
    assert "if (pending) {" in card, "the card must short-circuit before any load/Open branch"


# ---------------------------------------------------------------------------
# 7 — one tool frame, not two (2026-09-17)
#
# A bare `{"tool": name}` string rode beside `{"tool_step": {...}}` for readers
# deployed before the subject seam. Both halves shipped in the SAME commit
# (4e9df71, 2026-08-25), so the window it guarded never existed and no reader
# ever took the arm — it was a duplicated payload on every tool call.
# ---------------------------------------------------------------------------

def test_the_route_emits_one_tool_frame():
    route = _strip_comments((_API / "routes" / "lanes.py").read_text())
    assert '"tool_step": {' in route
    assert '"tool": payload["name"]' not in route, (
        "the bare tool string is deleted — one frame carries the step"
    )


def test_the_client_has_no_bare_tool_arm():
    client = _strip_comments((_WEB / "lib" / "api" / "client.ts").read_text())
    assert "evt.tool_step" in client
    assert 'typeof evt.tool === "string"' not in client, (
        "a compat arm for a producer that does not exist is dead code"
    )


def test_the_error_frame_keeps_the_structure_the_runner_built():
    """ADR-647 D8 carries the provider's own words; a flattened string loses
    the code the client needs to branch on."""
    route = _strip_comments((_API / "routes" / "lanes.py").read_text())
    assert '"code": payload.get("error")' in route
    assert 'errored = f"{payload.get(\'error\')}: {payload.get(\'message\')}"' in route, (
        "the LEDGER keeps the flat form — only the wire gains structure"
    )

    client = _strip_comments((_WEB / "lib" / "api" / "client.ts").read_text())
    assert 'evt.error && typeof evt.error === "object"' in client
    assert 'typeof evt.error === "string"' not in client, (
        "both producers emit the object; a string arm would be dead on arrival"
    )


def test_the_catch_all_does_not_leak_an_exception_to_the_member():
    """This arm catches our OWN bugs too. `name 'req' is not defined` in a chat
    bubble tells a member nothing and leaks internals; the ledger keeps it."""
    route = _strip_comments((_API / "routes" / "lanes.py").read_text())
    # ⚠️ Anchor on the STREAM's catch-all, not on "the last `except Exception`
    # in the file" — `lanes.py` has several and the archive handler's is last.
    # A gate that reads the wrong block is green against code it never saw.
    assert "logger.exception(" in route
    tail = route.split('logger.exception("[LANE stream] turn failed')[1]
    tail = tail.split("persist_reply(stopped=False)")[0]
    assert 'yield sse({"error": errored})' not in tail
    assert '"code": "turn_failed"' in tail
    assert "errored = str(exc)" in tail, "the ledger still records the real fault"
