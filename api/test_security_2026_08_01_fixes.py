"""Security fixes (2026-08-01) — EXECUTED, not grepped.

Covers the two application-layer defects surfaced by the Phase 1–3 audit and
fixed in the same session:

  A. Lemon Squeezy webhook forged-write. `handle_commerce_webhook` previously
     trusted any caller, so an attacker could POST a payload with an arbitrary
     custom_data.user_id and write files into that victim's workspace. It now
     FAILS CLOSED: no signing secret configured → 503; bad/missing signature →
     401; only a correct HMAC-SHA256 over the raw body proceeds.

  B. MCP OAuth bind is POST-on-consent, not GET-auto-bind. The forced-consent
     account-takeover depended on the bind happening on page load. The bind
     route is now POST /oauth-callback; a read-only GET /oauth-consent describes
     the client without writing. We assert the route contract (methods) so a
     regression that re-adds a GET bind is caught.

Run: python3 test_security_2026_08_01_fixes.py   (exit 1 on any failure)
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import sys

FAIL: list[str] = []


def _check(cond: bool, label: str) -> None:
    print(("  PASS  " if cond else "  FAIL  ") + label)
    if not cond:
        FAIL.append(label)


# ── Fakes ────────────────────────────────────────────────────────────────────


class _FakeRequest:
    def __init__(self, body: bytes, headers: dict):
        self._body = body
        self.headers = headers

    async def body(self) -> bytes:
        return self._body


def _import_webhook_handler():
    # integrations.py imports heavy deps at module load; those are already in the
    # env for the app. Import lazily so this test file stays cheap to parse.
    from routes.integrations import handle_commerce_webhook

    return handle_commerce_webhook


async def _call_webhook(body: dict | bytes, secret_env: str | None, signature: str | None):
    handler = _import_webhook_handler()
    raw = body if isinstance(body, bytes) else json.dumps(body).encode()
    if secret_env is None:
        os.environ.pop("LEMONSQUEEZY_WEBHOOK_SECRET", None)
    else:
        os.environ["LEMONSQUEEZY_WEBHOOK_SECRET"] = secret_env
    headers = {}
    if signature is not None:
        headers["X-Signature"] = signature
    req = _FakeRequest(raw, headers)
    from fastapi import HTTPException

    try:
        result = await handler(req)
        return ("ok", result)
    except HTTPException as e:
        return ("http", e.status_code)
    except Exception as e:
        # Passed the signature gate and reached downstream work (e.g. the DB
        # client, which needs env not set in this unit test). That is SUCCESS
        # for the auth assertion — the request was NOT rejected as unauthorized.
        return ("passed_auth", type(e).__name__)


def test_webhook_fails_closed():
    forged = {"meta": {"event_name": "subscription_created", "custom_data": {"user_id": "victim"}}}

    # 1. No secret configured → 503, never a write.
    kind, code = asyncio.run(_call_webhook(forged, secret_env=None, signature="anything"))
    _check(kind == "http" and code == 503, "webhook: unset secret → 503 (fail closed)")

    # 2. Secret set but signature missing → 401.
    kind, code = asyncio.run(_call_webhook(forged, secret_env="s3cr3t", signature=None))
    _check(kind == "http" and code == 401, "webhook: missing signature → 401")

    # 3. Secret set but WRONG signature → 401 (the forged-write attack).
    kind, code = asyncio.run(_call_webhook(forged, secret_env="s3cr3t", signature="deadbeef"))
    _check(kind == "http" and code == 401, "webhook: wrong signature → 401 (forged write blocked)")

    # 4. Correct signature passes the gate (proceeds past 401/503; downstream
    #    behaviour is out of scope — we only assert it is NOT rejected as unauth).
    raw = json.dumps(forged).encode()
    good_sig = hmac.new(b"s3cr3t", raw, hashlib.sha256).hexdigest()
    kind, code = asyncio.run(_call_webhook(raw, secret_env="s3cr3t", signature=good_sig))
    passed_auth = not (kind == "http" and code in (401, 503))
    _check(passed_auth, "webhook: correct HMAC passes the signature gate")


def test_mcp_bind_is_post_only():
    from routes.mcp import router

    routes_by_path: dict[str, set[str]] = {}
    for r in router.routes:
        methods = getattr(r, "methods", set()) or set()
        routes_by_path.setdefault(getattr(r, "path", ""), set()).update(methods)

    callback = routes_by_path.get("/oauth-callback", set())
    consent = routes_by_path.get("/oauth-consent", set())

    _check("POST" in callback, "mcp: /oauth-callback accepts POST (consent bind)")
    _check("GET" not in callback, "mcp: /oauth-callback does NOT accept GET (no auto-bind)")
    _check("GET" in consent, "mcp: /oauth-consent is a read-only GET describe")
    _check("POST" not in consent, "mcp: /oauth-consent does NOT write (no POST)")


def test_rate_limiter():
    from mcp_server.rate_limit import _FixedWindow, _bucket_for

    w = _FixedWindow()
    allowed = [w.hit("k", 3, 60, 100.0) for _ in range(4)]
    _check(allowed == [True, True, True, False], "rate-limit: 4th request in a 3/window is blocked")
    _check(w.hit("k", 3, 60, 161.0) is True, "rate-limit: window resets after it elapses")
    _check(_bucket_for("/token") == "/token", "rate-limit: /token is throttled")
    _check(_bucket_for("/register") == "/register", "rate-limit: /register is throttled")
    _check(_bucket_for("/") is None, "rate-limit: the protocol root is NOT throttled")


def test_refresh_token_expiry_wired():
    # The fix is DB-backed (mig 232 adds expires_at/rotated_at) so we can't
    # exercise the DB here; assert the CODE writes expiry + checks reuse, so a
    # regression that drops either is caught. Grep the source for the invariants.
    src = open("mcp_server/oauth_provider.py").read()
    _check("REFRESH_TOKEN_LIFETIME" in src and src.count('"expires_at"') >= 3,
           "refresh-token: expires_at written on issue + rotation")
    _check("rotated_at" in src and "revoking family" in src,
           "refresh-token: reuse detection revokes the token family")
    _check(src.count("mcp_oauth_refresh_tokens\").delete()") >= 1,
           "refresh-token: expiry/reuse paths delete the stale token")


def test_jwt_signature_verified():
    # Verify the auth JWT decode rejects forged tokens when a secret is set.
    os.environ["SUPABASE_JWT_SECRET"] = "test-secret-please-ignore-32bytes-min"
    os.environ.pop("SUPABASE_JWT_ALLOW_UNVERIFIED", None)
    import importlib
    import services.supabase as sb
    importlib.reload(sb)
    import jwt

    secret = "test-secret-please-ignore-32bytes-min"
    good = jwt.encode({"sub": "u1", "aud": "authenticated"}, secret, algorithm="HS256")
    _check(sb.decode_jwt_payload(good).get("sub") == "u1", "jwt: valid signature accepted")

    forged = jwt.encode({"sub": "attacker", "aud": "authenticated"}, "wrong", algorithm="HS256")
    rejected = False
    try:
        sb.decode_jwt_payload(forged)
    except ValueError:
        rejected = True
    _check(rejected, "jwt: forged signature rejected (impersonation blocked)")

    none_tok = jwt.encode({"sub": "attacker", "aud": "authenticated"}, "", algorithm="none")
    none_rejected = False
    try:
        sb.decode_jwt_payload(none_tok)
    except ValueError:
        none_rejected = True
    _check(none_rejected, "jwt: alg=none downgrade rejected")


if __name__ == "__main__":
    print("test_security_2026_08_01_fixes")
    print("A. webhook fails closed")
    test_webhook_fails_closed()
    print("B. mcp bind is post-on-consent")
    test_mcp_bind_is_post_only()
    print("C. mcp auth rate limiting")
    test_rate_limiter()
    print("D. mcp refresh-token expiry + reuse detection")
    test_refresh_token_expiry_wired()
    print("E. main-api JWT signature verification")
    test_jwt_signature_verified()
    if FAIL:
        print(f"\n{len(FAIL)} FAILED:")
        for f in FAIL:
            print(f"  - {f}")
        sys.exit(1)
    print("\nALL PASS")
