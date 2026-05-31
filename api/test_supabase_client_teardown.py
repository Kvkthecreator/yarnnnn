"""Regression guard for the 2026-06-01 yarnnn-api OOM.

Root cause: ``get_user_client`` constructed a fresh Supabase ``Client`` per
authenticated request (including the always-on frontend polls every ~60s).
Each client's ``postgrest`` wraps an ``httpx.Client`` connection pool that was
never closed, so pools accumulated over the process lifetime — a slow RSS
creep (~5 MB/hr) that eventually crossed the 512 MB starter-plan ceiling and
triggered the OOM kill.

Fix (services/supabase.py): ``get_user_client`` is now a generator dependency
that (a) disables gotrue auto-refresh / session persistence and (b) closes the
per-request postgrest connection pool in a ``finally`` block.

These tests assert both properties hold so the leak cannot silently return.
"""
from __future__ import annotations

import inspect
import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "anon-placeholder")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "service-placeholder")

import httpx  # noqa: E402

from services.supabase import (  # noqa: E402
    AuthenticatedClient,
    get_user_client,
)

# A syntactically-valid JWT with payload {"sub": "...", "email": "..."}.
# header.payload.signature — only the payload is decoded (no verification).
_FAKE_JWT = (
    "eyJhbGciOiJIUzI1NiJ9."
    # {"sub":"user-123","email":"t@example.com"}
    "eyJzdWIiOiJ1c2VyLTEyMyIsImVtYWlsIjoidEBleGFtcGxlLmNvbSJ9."
    "sig"
)


def test_get_user_client_is_a_generator_dependency():
    """It must yield (so FastAPI runs the finally teardown), not return."""
    assert inspect.isgeneratorfunction(get_user_client)


def test_get_user_client_closes_pool_on_teardown():
    """Driving the dependency the way FastAPI does must close the postgrest pool."""
    gen = get_user_client(authorization=f"Bearer {_FAKE_JWT}")
    auth = next(gen)

    assert isinstance(auth, AuthenticatedClient)
    assert auth.user_id == "user-123"
    assert auth.email == "t@example.com"

    session = auth.client.postgrest.session
    assert isinstance(session, httpx.Client)
    assert session.is_closed is False, "pool should be open during the request"

    # FastAPI advances the generator past the yield after the response.
    try:
        next(gen)
    except StopIteration:
        pass

    assert session.is_closed is True, "pool must be closed on teardown (the leak fix)"


def test_get_user_client_disables_auto_refresh_timer():
    """No gotrue auto-refresh: defends against an orphaned threading.Timer."""
    gen = get_user_client(authorization=f"Bearer {_FAKE_JWT}")
    auth = next(gen)
    try:
        opts = auth.client.options
        assert opts.auto_refresh_token is False
        assert opts.persist_session is False
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    test_get_user_client_is_a_generator_dependency()
    test_get_user_client_closes_pool_on_teardown()
    test_get_user_client_disables_auto_refresh_timer()
    print("PASS: 3/3 — supabase client teardown guards hold")
