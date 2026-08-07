"""ADR-531 — the OAuth state carries itself, and a failure is visible.

Three defects, three gate groups:

  1. State was a process-local dict, so a callback landing in a different
     process than the authorize call failed. Gate: the state must round-trip
     across a SIMULATED PROCESS BOUNDARY (module state cleared between mint
     and verify) — the property the dict version could not satisfy.

  2. The error redirect emitted `tab=integrations`, which is not a pane the
     settings page accepts, so failures silently landed on Account. Gate: the
     error URL must name the connectors pane in the spelling the FE reads.

  3. `provider`/`status`/`error` were never read by any component. Gate: the
     settings page reads them and the section renders a banner.

Gate craft note (memory: a counting gate cannot defend a per-site invariant):
these assert BEHAVIOR through the real functions wherever possible, and fall
back to source inspection only for the FE, which has no Python-importable
surface. The FE checks anchor on the BRANCH (the param read, the prop, the
role="alert" banner), never on a copy spelling that will drift.
"""

import base64
import importlib
import json
import os
import re
import sys
from pathlib import Path

import pytest

# A Fernet-shaped key. oauth.py uses it as opaque HMAC key material, so any
# stable value works here — but keeping it Fernet-shaped keeps the fixture
# honest about what production actually supplies.
_TEST_KEY = base64.urlsafe_b64encode(b"k" * 32).decode()

REPO_ROOT = Path(__file__).resolve().parent.parent
API_ROOT = Path(__file__).resolve().parent


@pytest.fixture()
def oauth(monkeypatch):
    """Import oauth.py with a signing key present."""
    monkeypatch.setenv("INTEGRATION_ENCRYPTION_KEY", _TEST_KEY)
    monkeypatch.setenv("FRONTEND_URL", "https://yarnnn.com")
    sys.path.insert(0, str(API_ROOT))
    import integrations.core.oauth as mod

    importlib.reload(mod)
    return mod


# =============================================================================
# 1. The state carries itself
# =============================================================================

def test_state_round_trips(oauth):
    state = oauth.generate_oauth_state("user-abc", "notion", "/settings")
    user_id, provider, redirect_to = oauth.validate_oauth_state(state)
    assert (user_id, provider, redirect_to) == ("user-abc", "notion", "/settings")


def test_state_survives_a_process_boundary(oauth, monkeypatch):
    """THE defect. A state minted in one process must verify in another.

    Reloading the module discards every module-global — exactly what a redeploy
    or a second Gunicorn worker does. The dict implementation fails this; a
    signed token passes because the payload travels inside the token.
    """
    state = oauth.generate_oauth_state("user-abc", "slack", None)

    monkeypatch.setenv("INTEGRATION_ENCRYPTION_KEY", _TEST_KEY)
    import integrations.core.oauth as reloaded

    importlib.reload(reloaded)

    user_id, provider, _ = reloaded.validate_oauth_state(state)
    assert (user_id, provider) == ("user-abc", "slack")


def test_no_module_level_state_store_remains(oauth):
    """Singular implementation — the dict must be GONE, not merely unused.

    A surviving `_oauth_states` would be a second source of truth for the same
    fact, and the next edit could revive the process-local dependence.
    """
    assert not hasattr(oauth, "_oauth_states")
    source = (API_ROOT / "integrations" / "core" / "oauth.py").read_text()
    assert "_oauth_states" not in source


def test_tampered_payload_is_rejected(oauth):
    """CSRF protection is the point of state. A forged payload must not verify."""
    state = oauth.generate_oauth_state("user-abc", "notion", None)
    body, signature = state.split(".", 1)

    forged_payload = json.loads(base64.urlsafe_b64decode(body + "=="))
    forged_payload["uid"] = "attacker"
    forged_body = (
        base64.urlsafe_b64encode(
            json.dumps(forged_payload, separators=(",", ":"), sort_keys=True).encode()
        )
        .decode()
        .rstrip("=")
    )

    with pytest.raises(oauth.OAuthStateError) as exc:
        oauth.validate_oauth_state(f"{forged_body}.{signature}")
    assert exc.value.reason == "bad_signature"


def test_state_signed_with_another_secret_is_rejected(oauth, monkeypatch):
    state = oauth.generate_oauth_state("user-abc", "notion", None)

    monkeypatch.setenv(
        "INTEGRATION_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"z" * 32).decode()
    )
    import integrations.core.oauth as other

    importlib.reload(other)

    with pytest.raises(other.OAuthStateError) as exc:
        other.validate_oauth_state(state)
    assert exc.value.reason == "bad_signature"


def test_expired_state_is_rejected_with_its_own_reason(oauth, monkeypatch):
    """Expiry must be DISTINGUISHABLE from tampering — the old code could not
    tell them apart, so no log line could explain a failure."""
    state = oauth.generate_oauth_state("user-abc", "notion", None)

    real_ttl = oauth.OAUTH_STATE_TTL_SECONDS
    monkeypatch.setattr(oauth, "OAUTH_STATE_TTL_SECONDS", -1)
    try:
        with pytest.raises(oauth.OAuthStateError) as exc:
            oauth.validate_oauth_state(state)
        assert exc.value.reason == "expired"
    finally:
        monkeypatch.setattr(oauth, "OAUTH_STATE_TTL_SECONDS", real_ttl)


@pytest.mark.parametrize("bad", ["", "nodot", "a.b.c", "!!!.@@@"])
def test_malformed_states_are_rejected(oauth, bad):
    with pytest.raises(oauth.OAuthStateError) as exc:
        oauth.validate_oauth_state(bad)
    assert exc.value.reason in {"malformed", "bad_signature"}


def test_ttl_is_ten_minutes(oauth):
    assert oauth.OAUTH_STATE_TTL_SECONDS == 600


def test_state_error_is_a_valueerror(oauth):
    """The callback catches ValueError. If OAuthStateError stopped being one,
    every state failure would fall through to the generic 500 branch and lose
    its reason."""
    assert issubclass(oauth.OAuthStateError, ValueError)


def test_each_state_is_unique(oauth):
    """A nonce must actually vary — otherwise two flows share a token."""
    states = {oauth.generate_oauth_state("u", "notion", None) for _ in range(5)}
    assert len(states) == 5


# =============================================================================
# 2. The error redirect lands on a pane that exists
# =============================================================================

def test_error_redirect_targets_the_connectors_pane(oauth):
    url = oauth.get_frontend_redirect_url(False, "notion", "boom", error_reason="expired")
    assert "settings.pane=connectors" in url
    # The dead spelling must not come back.
    assert "tab=integrations" not in url


def test_error_redirect_carries_provider_status_and_reason(oauth):
    url = oauth.get_frontend_redirect_url(
        False, "notion", "state expired", error_reason="expired"
    )
    assert "provider=notion" in url
    assert "status=error" in url
    assert "error_reason=expired" in url


def test_error_pane_spelling_matches_the_frontend_whitelist(oauth):
    """The pane value in the redirect must be a pane the settings page ACCEPTS.

    This is the actual defect class: the backend named a pane the frontend had
    no case for. Read ALL_PANES out of the FE and assert membership, so the two
    sides cannot drift apart silently again.
    """
    url = oauth.get_frontend_redirect_url(False, "notion", "boom", error_reason="expired")
    pane = re.search(r"settings\.pane=([a-z-]+)", url).group(1)

    page = (
        REPO_ROOT / "web" / "app" / "(authenticated)" / "settings" / "page.tsx"
    ).read_text()
    declared = set(re.findall(r'key:\s*"([a-z-]+)"', page))
    assert pane in declared, (
        f"redirect names pane '{pane}', which the settings page does not declare "
        f"(declares: {sorted(declared)})"
    )


def test_success_redirect_is_unchanged(oauth):
    url = oauth.get_frontend_redirect_url(True, "notion", redirect_to="/settings?settings.pane=connectors")
    assert "status=connected" in url
    assert "provider=notion" in url


def test_success_redirect_defaults_to_workfloor(oauth):
    url = oauth.get_frontend_redirect_url(True, "slack")
    assert "/workfloor?" in url


# =============================================================================
# 3. The failure is visible on the surface
# =============================================================================

SETTINGS_PAGE = REPO_ROOT / "web" / "app" / "(authenticated)" / "settings" / "page.tsx"
SECTION = (
    REPO_ROOT / "web" / "components" / "settings" / "ConnectedIntegrationsSection.tsx"
)


def test_settings_page_reads_the_oauth_outcome_params():
    """Each param the API encodes must have a reader. The defect was that the
    backend built a diagnostic URL nothing consumed."""
    page = SETTINGS_PAGE.read_text()
    for param in ("provider", "status", "error", "error_reason"):
        assert f'searchParams.get("{param}")' in page, f"no reader for '{param}'"


def test_settings_page_passes_the_outcome_to_the_connectors_section():
    page = SETTINGS_PAGE.read_text()
    assert "oauthOutcome=" in page
    assert "onDismissOauthOutcome=" in page


def test_section_accepts_and_renders_the_outcome():
    section = SECTION.read_text()
    assert "oauthOutcome" in section
    # Anchor on the BRANCH (an alert region gated on the error status), not on
    # any copy string — the wording is free to change.
    assert 'role="alert"' in section
    assert 'oauthOutcome?.status === "error"' in section


def test_every_api_reason_has_operator_copy():
    """A reason the API can emit but the FE cannot describe would fall back to
    the raw sentence — which is the pre-ADR-531 behavior for that case."""
    section = SECTION.read_text()
    described = set(re.findall(r'case "([a-z_]+)":', section))

    oauth_src = (API_ROOT / "integrations" / "core" / "oauth.py").read_text()
    routes_src = (API_ROOT / "routes" / "integrations.py").read_text()
    emitted = set(re.findall(r'OAuthStateError\(\s*"([a-z_]+)"', oauth_src))
    emitted |= set(re.findall(r'error_reason="([a-z_]+)"', routes_src))

    missing = emitted - described
    assert not missing, f"API emits reasons with no operator copy: {sorted(missing)}"


def test_dismiss_clears_every_oauth_param():
    """A dismissed banner must not return on reload. All four params go."""
    page = SETTINGS_PAGE.read_text()
    match = re.search(r"\[([^\]]*?)\]\.forEach\(\(k\) => next\.delete\(k\)\)", page)
    assert match, "no param-clearing loop found"
    cleared = set(re.findall(r'"([a-z_]+)"', match.group(1)))
    assert cleared == {"provider", "status", "error", "error_reason"}


def test_callback_passes_a_reason_on_every_error_branch():
    """Three error exits in the callback; each must name a reason, or its
    failure degrades to the undiagnosable default."""
    routes = (API_ROOT / "routes" / "integrations.py").read_text()
    start = routes.index("async def oauth_callback")
    # Scope to the function's REAL end (the next top-level def / section rule),
    # never a fixed character window — a window that truncates mid-call reports
    # a defect in code that is fine.
    rest = routes[start:]
    end = re.search(r"\n# =+\n|\n@router\.", rest)
    body = rest[: end.start()] if end else rest

    # Split at each error-redirect call and inspect the segment that follows,
    # up to the closing of the RedirectResponse. Extracting by the BRANCH
    # (`False` as the success arg) rather than by a balanced-paren expression
    # keeps the check honest when a call gains a nested call like getattr().
    segments = body.split("get_frontend_redirect_url(")
    error_segments = [
        seg for seg in segments[1:] if re.match(r"\s*False\b", seg)
    ]
    assert len(error_segments) == 3, (
        f"expected 3 error redirects in oauth_callback, found {len(error_segments)}"
    )
    for seg in error_segments:
        # The call's own argument list ends at the first line that closes it
        # back at the `url=` indent level. Taking a generous window and cutting
        # at the following `except`/`return` keeps nested calls intact.
        head = re.split(r"\n\s{,8}(?:except|return|@router|async def)\b", seg)[0]
        assert "error_reason=" in head, f"error redirect without a reason: {head[:200]}"
