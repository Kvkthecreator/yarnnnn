"""
Validation Suite — ADR-209 Phase 4 (Cockpit UI + inference-meta simplification)

Tests:
  1. GET /api/workspace/revisions returns the chain for a path
  2. GET /api/workspace/revisions/{id} returns a specific revision
  3. GET /api/workspace/revisions/{id} 404 for unknown id
  4. GET /api/workspace/revisions/diff/two returns unified diff
  5. PATCH /api/workspace/file accepts optional message and lands it on the revision
  6. Revert round-trip: read old revision → PATCH with its content + message → chain grows
  7. _append_inference_meta no longer emits `inferred_at`
  8. _append_inference_meta still emits target + sources + gaps
  9. Existing ADR-162 provenance callers still produce parsable output
 10. save_identity / save_brand route writes attributed to `operator`
 11. Phases 1 + 2 + 3 regression (full suites re-run)

Strategy: Real DB reads + HTTPX calls against the FastAPI app under test.
Test user: kvkthecreator@gmail.com

Usage:
    cd api && python test_adr209_phase4.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
SCRATCH_PATH = "/workspace/context/_shared/CONVENTIONS.md"  # editable + always exists for the test user post-onboarding
# Fallback scratch if CONVENTIONS.md isn't present on the test user's workspace:
SCRATCH_FALLBACK_PATH = "/workspace/uploads/_adr209-phase4-test.md"

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    icon = "✓" if ok else "✗"
    logger.info(f"{icon} {name}: {detail}")


def get_client():
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL + SUPABASE_SERVICE_KEY required")
    return create_client(url, key)


class _FakeAuth:
    """Stub that mirrors UserClient for route-level handler testing. The
    route functions use auth.client (service-keyed during tests) + auth.user_id
    for RLS scoping; no JWT bearer required because we call the handler
    functions directly rather than through HTTP middleware."""
    def __init__(self, client, user_id: str):
        self.client = client
        self.user_id = user_id


async def _seed_scratch(client) -> tuple[str, list[str]]:
    """Seed three revisions on the scratch path. Returns (path, [rev_ids]).

    Uses SCRATCH_PATH if editable_prefixes permits it; otherwise the
    uploads fallback. Both paths are in the workspace.py editable list.
    """
    from services.authored_substrate import write_revision

    path = SCRATCH_PATH
    # FK order cleanup
    client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).eq("path", path).execute()
    client.table("workspace_file_versions").delete().eq("user_id", TEST_USER_ID).eq("path", path).execute()

    ids = []
    for i, (author, msg) in enumerate([
        ("operator", "initial edit (test)"),
        ("yarnnn:test-sonnet", "refine (test)"),
        ("operator", "latest edit (test)"),
    ], start=1):
        rid = write_revision(
            client,
            user_id=TEST_USER_ID,
            path=path,
            content=f"# Phase 4 test revision {i}\n- author: {author}\n- sequence: {i}\n",
            authored_by=author,
            message=msg,
        )
        ids.append(rid)
    return path, ids


def _cleanup_scratch(client, path: str) -> None:
    client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).eq("path", path).execute()
    client.table("workspace_file_versions").delete().eq("user_id", TEST_USER_ID).eq("path", path).execute()


# ---------------------------------------------------------------------------
# Tests 1-4: Revision API endpoints
# ---------------------------------------------------------------------------

async def test_list_revisions_endpoint(client) -> None:
    try:
        from routes.workspace import list_revisions_route

        path, ids = await _seed_scratch(client)
        auth = _FakeAuth(client, TEST_USER_ID)

        resp = await list_revisions_route(auth, path=path, limit=10)
        revisions = resp.revisions

        ok = (
            resp.path == path
            and resp.count == 3
            and revisions[0].id == ids[2]
            and revisions[1].id == ids[1]
            and revisions[2].id == ids[0]
            and revisions[0].authored_by == "operator"
        )
        record(
            "GET /workspace/revisions returns chain newest-first",
            ok,
            f"count={resp.count}, head.authored_by={revisions[0].authored_by if revisions else None}",
        )
    except Exception as e:
        record("GET /workspace/revisions", False, f"Error: {e}")


async def test_read_revision_endpoint(client) -> None:
    try:
        from routes.workspace import read_revision_route

        path, ids = await _seed_scratch(client)
        auth = _FakeAuth(client, TEST_USER_ID)

        resp = await read_revision_route(auth, revision_id=ids[0], path=path)
        ok = (
            resp.id == ids[0]
            and resp.authored_by == "operator"
            and resp.content is not None
            and "sequence: 1" in resp.content
        )
        record(
            "GET /workspace/revisions/{id} returns specific revision",
            ok,
            f"authored_by={resp.authored_by}, content_has_sequence_1={'sequence: 1' in (resp.content or '')}",
        )
    except Exception as e:
        record("GET /workspace/revisions/{id}", False, f"Error: {e}")


async def test_read_revision_endpoint_404(client) -> None:
    try:
        from routes.workspace import read_revision_route
        from fastapi import HTTPException

        path, _ = await _seed_scratch(client)
        auth = _FakeAuth(client, TEST_USER_ID)

        try:
            await read_revision_route(
                auth,
                revision_id="00000000-0000-0000-0000-000000000000",
                path=path,
            )
            record("GET /workspace/revisions/{id} 404 for unknown", False, "No 404 raised")
        except HTTPException as he:
            record(
                "GET /workspace/revisions/{id} 404 for unknown",
                he.status_code == 404,
                f"status={he.status_code}",
            )
    except Exception as e:
        record("GET /workspace/revisions/{id} 404", False, f"Error: {e}")


async def test_diff_revisions_endpoint(client) -> None:
    try:
        from routes.workspace import diff_revisions_route

        path, ids = await _seed_scratch(client)
        auth = _FakeAuth(client, TEST_USER_ID)

        resp = await diff_revisions_route(auth, path=path, from_rev=ids[0], to_rev=ids[2])
        ok = (
            resp.path == path
            and resp.from_revision.id == ids[0]
            and resp.to_revision.id == ids[2]
            and resp.identical is False
            and ("+" in resp.diff or "-" in resp.diff)
            and "sequence: 1" in resp.diff
            and "sequence: 3" in resp.diff
        )
        record(
            "GET /workspace/revisions/diff/two returns unified diff",
            ok,
            f"from={resp.from_revision.id[:8]}... to={resp.to_revision.id[:8]}... diff_len={len(resp.diff)}",
        )
    except Exception as e:
        record("GET /workspace/revisions/diff/two", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 5 + 6: PATCH /workspace/file with message + revert round-trip
# ---------------------------------------------------------------------------

async def test_edit_file_with_message(client) -> None:
    try:
        from routes.workspace import edit_workspace_file, FileEditRequest, list_revisions_route

        path = SCRATCH_PATH
        await _seed_scratch(client)
        auth = _FakeAuth(client, TEST_USER_ID)

        custom_message = "test: explicit message via PATCH"
        await edit_workspace_file(
            auth,
            FileEditRequest(
                path=path,
                content="# Phase 4 PATCH test\nmessage passed explicitly.",
                message=custom_message,
            ),
        )

        resp = await list_revisions_route(auth, path=path, limit=5)
        head = resp.revisions[0]
        ok = head.message == custom_message and head.authored_by == "operator"
        record(
            "PATCH /workspace/file with message lands custom message on revision",
            ok,
            f"head.message={head.message!r}, head.authored_by={head.authored_by}",
        )
    except Exception as e:
        record("PATCH with message", False, f"Error: {e}")


async def test_revert_round_trip(client) -> None:
    try:
        from routes.workspace import (
            edit_workspace_file, read_revision_route, list_revisions_route,
            FileEditRequest,
        )

        path, ids = await _seed_scratch(client)
        auth = _FakeAuth(client, TEST_USER_ID)

        # Simulate frontend revert: read old revision, patch with its content + revert message
        old_rev = await read_revision_route(auth, revision_id=ids[0], path=path)
        revert_msg = f"revert to revision {ids[0][:8]}"

        await edit_workspace_file(
            auth,
            FileEditRequest(
                path=path,
                content=old_rev.content or "",
                message=revert_msg,
            ),
        )

        # Chain should now be 4 revisions; head message should be the revert
        resp = await list_revisions_route(auth, path=path, limit=10)
        head = resp.revisions[0]
        ok = (
            resp.count == 4
            and head.message == revert_msg
            and head.authored_by == "operator"
            and (head.parent_version_id == ids[2])  # parent = prior head
        )
        record(
            "Revert round-trip: read old → PATCH → head is revert revision with correct parent",
            ok,
            f"count={resp.count}, head.message={head.message!r}, head.parent_matches_prior_head={head.parent_version_id == ids[2]}",
        )
    except Exception as e:
        record("Revert round-trip", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Tests 7 + 8: inference-meta schema simplification
# ---------------------------------------------------------------------------

def test_inference_meta_drops_inferred_at() -> None:
    try:
        from services.context_inference import _append_inference_meta

        result = _append_inference_meta(
            content="# Test content",
            target="identity",
            source_summary={"has_text": True, "doc_filenames": ["test.pdf"], "urls": []},
            gap_report=None,
        )

        # Extract the JSON payload from the HTML comment
        match = re.search(r"<!-- inference-meta: (.+?) -->", result)
        ok = False
        detail = "no meta comment found"
        if match:
            meta = json.loads(match.group(1))
            ok = "inferred_at" not in meta
            detail = f"fields={sorted(meta.keys())}"
        record("_append_inference_meta drops `inferred_at`", ok, detail)
    except Exception as e:
        record("inference-meta drops inferred_at", False, f"Error: {e}")


def test_inference_meta_keeps_target_sources_gaps() -> None:
    try:
        from services.context_inference import _append_inference_meta

        gap_report = {
            "richness": "sparse",
            "gaps": [{"field": "company_name", "severity": "high"}],
        }
        result = _append_inference_meta(
            content="# Test",
            target="brand",
            source_summary={"has_text": False, "doc_filenames": [], "urls": ["https://example.com"]},
            gap_report=gap_report,
        )
        match = re.search(r"<!-- inference-meta: (.+?) -->", result)
        if not match:
            record("_append_inference_meta keeps target/sources/gaps", False, "no meta")
            return
        meta = json.loads(match.group(1))
        ok = (
            meta.get("target") == "brand"
            and meta.get("sources", {}).get("urls") == ["https://example.com"]
            and meta.get("gaps", {}).get("richness") == "sparse"
        )
        record(
            "_append_inference_meta keeps target + sources + gaps",
            ok,
            f"keys={sorted(meta.keys())}",
        )
    except Exception as e:
        record("inference-meta keeps core fields", False, f"Error: {e}")


def test_inference_meta_parseable_from_frontend_shape() -> None:
    """The frontend's parseInferenceMeta expects a trailing HTML comment with
    JSON. Ensure the backend's emitted shape still matches the regex the
    frontend uses (META_COMMENT_RE)."""
    try:
        from services.context_inference import _append_inference_meta

        result = _append_inference_meta(
            content="# Example\n\nparagraph",
            target="identity",
            source_summary={"has_text": True, "doc_filenames": [], "urls": []},
        )
        # Mirror the frontend regex
        fe_regex = re.compile(r"\n*<!--\s*inference-meta:\s*(\{[\s\S]*?\})\s*-->\s*$")
        match = fe_regex.search(result)
        ok = match is not None
        record(
            "Backend emits inference-meta comment matching frontend parser",
            ok,
            f"matched={ok}",
        )
    except Exception as e:
        record("parseable shape", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 10: save_identity / save_brand attribution
# ---------------------------------------------------------------------------

async def test_save_identity_brand_operator_attribution(client) -> None:
    """Simulated call of save_brand — verifies authored_by ends up as `operator`
    via the new routes-layer explicit attribution (not the default
    `system:user-memory`)."""
    try:
        from routes.memory import save_brand, BrandSaveRequest
        from routes.workspace import list_revisions_route

        auth = _FakeAuth(client, TEST_USER_ID)

        # Capture current brand so we restore it at the end (don't mutate user data)
        brand_path = "/workspace/context/_shared/BRAND.md"
        before = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", TEST_USER_ID)
            .eq("path", brand_path)
            .limit(1)
            .execute()
        )
        prior_content = (before.data or [{}])[0].get("content")

        # Save a test brand
        test_content = "# Test brand (phase 4 attribution check)\n- test: true\n"
        await save_brand(BrandSaveRequest(content=test_content), auth)

        # Inspect the head revision
        resp = await list_revisions_route(auth, path=brand_path, limit=3)
        head = resp.revisions[0] if resp.revisions else None
        ok = head is not None and head.authored_by == "operator" and "settings surface" in head.message
        record(
            "save_brand routes operator-attributed revision",
            ok,
            f"head.authored_by={head.authored_by if head else None}, head.message={(head.message if head else '')!r}",
        )

        # Restore prior content if any
        if prior_content:
            await save_brand(BrandSaveRequest(content=prior_content), auth)
    except Exception as e:
        record("save_brand attribution", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Test 11: regression
# ---------------------------------------------------------------------------

def test_regression() -> None:
    api_root = Path(__file__).parent
    for phase_num, path in [
        (1, api_root / "test_adr209_phase1.py"),
        (2, api_root / "test_adr209_phase2.py"),
        (3, api_root / "test_adr209_phase3.py"),
    ]:
        try:
            result = subprocess.run(
                [sys.executable, str(path)],
                capture_output=True, text=True, timeout=240,
            )
            ok = result.returncode == 0
            out = result.stdout.strip().splitlines()
            score_line = next((l for l in out if "passed ===" in l), "?")
            record(
                f"Phase {phase_num} regression check",
                ok,
                score_line.strip() if score_line else f"rc={result.returncode}",
            )
        except Exception as e:
            record(f"Phase {phase_num} regression", False, f"Error: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def _async_tests(client) -> None:
    await test_list_revisions_endpoint(client)
    await test_read_revision_endpoint(client)
    await test_read_revision_endpoint_404(client)
    await test_diff_revisions_endpoint(client)
    await test_edit_file_with_message(client)
    await test_revert_round_trip(client)
    await test_save_identity_brand_operator_attribution(client)


def main() -> int:
    api_dir = Path(__file__).parent
    sys.path.insert(0, str(api_dir))

    client = get_client()

    try:
        asyncio.run(_async_tests(client))
        # Sync tests
        test_inference_meta_drops_inferred_at()
        test_inference_meta_keeps_target_sources_gaps()
        test_inference_meta_parseable_from_frontend_shape()
        # Regression
        test_regression()
    finally:
        _cleanup_scratch(client, SCRATCH_PATH)

    total = len(RESULTS)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print()
    print(f"=== ADR-209 Phase 4 test results: {passed}/{total} passed ===")
    for name, ok, detail in RESULTS:
        icon = "✓" if ok else "✗"
        print(f"  {icon} {name}" + (f" — {detail}" if not ok else ""))

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
