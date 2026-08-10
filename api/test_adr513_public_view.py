"""ADR-513 regression gate — the public artifact view.

The first unauthenticated read surface: the projection boundary, the lifecycle
honesty, and the rendering discipline are all pinned here. Structural checks.

Run: python3 test_adr513_public_view.py  (from api/)

Asserts:
  1. GET /s/{token} is public (no auth dependency); POST accept stays gated.
  2. Lifecycle honesty (D4, as amended by ADR-531): preview enforces status +
     expiry and sets `no-store` on every exit. `noindex` is deliberately GONE
     (ADR-531 D1) and its absence is asserted — revocation is authoritative at
     the origin and best-effort in the world, knowingly.
  3. The projection boundary (D2): the response model exposes no shared_by /
     workspace_id / share id; the walk entry is metadata-only (no content, no
     diff, no revision_id); caps exist.
  4. Middleware: "/s" left PROTECTED_PREFIXES.
  5. FE rendering (D3): the page uses ONLY the fully-locked sandbox for member
     HTML — no allow-scripts, no allow-same-origin, no dangerouslySetInnerHTML.
"""

import inspect
import re
import sys


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def _check_capability_headers_execute():
    """2c — EXECUTE GET /s/{token} and read the headers off real responses.

    A grep cannot see this defect: the strings are present in the source and the
    404/410 still ship bare. So we drive the app and assert on what the wire
    carries, for the miss (404) and the revoked (410) paths as well as the 200.
    """
    out = []
    try:
        from fastapi.testclient import TestClient
    except Exception as exc:  # noqa: BLE001
        # Say it plainly — an unrun check must never read as a passing one.
        return [_check("2c EXECUTING header gate", False,
                       f"could not import TestClient ({exc}) — check did NOT run")]

    import os
    from unittest.mock import patch

    # Boot-time env validation is not what this check is about. Supply a dummy
    # only when the real one is absent (CI/Render already sets it).
    os.environ.setdefault("INTEGRATION_ENCRYPTION_KEY",
                          "ZmFrZS1rZXktZm9yLWhlYWRlci1nYXRlLW9ubHktMDAwMDA=")

    try:
        from main import app
    except Exception as exc:  # noqa: BLE001
        return [_check("2c EXECUTING header gate", False,
                       f"could not import app ({exc}) — check did NOT run")]

    client = TestClient(app, raise_server_exceptions=False)
    # ADR-531 D1 amended D4: `noindex` is GONE from the share surface (it was
    # what blocked ChatGPT's search-index-mediated retrieval). `no-store` is the
    # half that survives and is the half that carries revocation at the origin —
    # an intermediary must never serve a revoked link from cache. Asserting
    # both directions so neither the removal nor the survivor can drift.
    want = {"cache-control": "no-store"}
    forbidden = "x-robots-tag"

    # (a) 404 — no share at that token.
    with patch("services.workspace_shares.get_share_by_token", return_value=None):
        resp = client.get("/api/s/definitely-not-a-real-token")
    out.append(_check("2c-404 status", resp.status_code == 404, str(resp.status_code)))
    for h, v in want.items():
        out.append(_check(f"2c-404 carries {h}",
                          resp.headers.get(h) == v,
                          f"got {resp.headers.get(h)!r} (want {v!r})"))
    out.append(_check(f"2c-404 does NOT carry {forbidden} (ADR-531 D1)",
                      forbidden not in resp.headers,
                      f"got {resp.headers.get(forbidden)!r}"))

    # (b) 410 — the revoked link. THE response revocation depends on.
    revoked = {"id": "s1", "token": "t", "status": "revoked", "role": "member",
               "workspace_id": "w1", "artifact_path": None, "label": None,
               "expires_at": None, "workspace_name": "W"}
    with patch("services.workspace_shares.get_share_by_token", return_value=revoked):
        resp = client.get("/api/s/revoked-token")
    out.append(_check("2c-410 status", resp.status_code == 410, str(resp.status_code)))
    for h, v in want.items():
        out.append(_check(f"2c-410 carries {h}",
                          resp.headers.get(h) == v,
                          f"got {resp.headers.get(h)!r} (want {v!r})"))
    out.append(_check(f"2c-410 does NOT carry {forbidden} (ADR-531 D1)",
                      forbidden not in resp.headers,
                      f"got {resp.headers.get(forbidden)!r}"))

    # (c) 200 — the happy path must not regress.
    active = dict(revoked, status="active")
    with patch("services.workspace_shares.get_share_by_token", return_value=active):
        resp = client.get("/api/s/active-token")
    out.append(_check("2c-200 status", resp.status_code == 200, str(resp.status_code)))
    for h, v in want.items():
        out.append(_check(f"2c-200 carries {h}",
                          resp.headers.get(h) == v,
                          f"got {resp.headers.get(h)!r} (want {v!r})"))
    out.append(_check(f"2c-200 does NOT carry {forbidden} (ADR-531 D1)",
                      forbidden not in resp.headers,
                      f"got {resp.headers.get(forbidden)!r}"))
    return out


def main():
    results = []
    from routes import shares as r

    prev_src = inspect.getsource(r.preview_share)
    accept_src = inspect.getsource(r.accept_workspace_share)

    # 1. public read, gated join
    prev_sig = str(inspect.signature(r.preview_share))
    results.append(_check(
        "1a preview has NO auth dependency",
        "UserClient" not in prev_sig and "auth" not in prev_sig))
    results.append(_check(
        "1b accept KEEPS the auth dependency",
        "auth: UserClient" in str(inspect.signature(r.accept_workspace_share))
        or "UserClient" in str(inspect.signature(r.accept_workspace_share))))

    # 2. lifecycle honesty + headers
    results.append(_check(
        "2a preview enforces status (revoked share goes dark)",
        'share["status"] != "active"' in prev_src and "410" in prev_src))
    results.append(_check(
        "2b preview enforces expiry (marks expired on read)",
        "expires_at" in prev_src and '"expired"' in prev_src))
    # 2c EXECUTES the error paths. The former grep-only version of this check
    # passed while BOTH the 404 and the 410 shipped bare: the route sets the
    # headers on the injected Response, then `raise HTTPException` discards it
    # (main.py's handler builds a fresh JSONResponse from exc.headers alone).
    # Found live 2026-08-03. A capability link that goes dark must not be
    # cacheable — that is exactly the response revocation depends on.
    results.extend(_check_capability_headers_execute())

    # 3. the projection boundary
    model_fields = set(r.SharePreviewResponse.model_fields.keys())
    forbidden = {"shared_by", "workspace_id", "id", "token"}
    results.append(_check(
        "3a response model carries no identity/internal fields",
        not (model_fields & forbidden), str(model_fields & forbidden)))
    walk_fields = set(r.WalkEntry.model_fields.keys())
    results.append(_check(
        "3b walk entries are metadata-only (who/when/what-message)",
        walk_fields == {"authored_by", "when", "change"}, str(walk_fields)))
    results.append(_check(
        "3c caps exist (content + walk)",
        isinstance(r.PUBLIC_CONTENT_CAP, int) and isinstance(r.PUBLIC_WALK_CAP, int)
        and r.PUBLIC_WALK_CAP <= 25))
    # 3d re-cut (2026-08-10): assert the INTENT — the walk select carries no
    # content/diff/blob column — not the exact spelling (the prior pin broke
    # when author_identity_uuid joined the select for the principal-display
    # resolution; that column is metadata consumed server-side, never emitted).
    import re as _re
    walk_select = _re.search(
        r'walk_rows = \(\s*svc\.table\("workspace_file_versions"\)\s*\.select\("([^"]+)"\)',
        prev_src,
    )
    sel_cols = {c.strip() for c in walk_select.group(1).split(",")} if walk_select else set()
    results.append(_check(
        "3d walk query selects metadata columns only (no content/diff/blob)",
        bool(sel_cols)
        and not (sel_cols & {"content", "diff", "blob_sha", "content_bytes"})
        and {"authored_by", "created_at", "message"} <= sel_cols))
    # The public walk renders through the ONE principal resolver (2026-08-10
    # identity pass) — raw member UUIDs / legacy emails never reach an
    # account-less viewer.
    results.append(_check(
        "3e walk emits display-resolved authors (principal_display), not raw authored_by",
        "display_for_rows" in prev_src
        and "authored_by=walk_display" in prev_src))

    # 4. middleware
    with open("../web/lib/supabase/middleware.ts", encoding="utf-8") as f:
        mw = f.read()
    results.append(_check(
        "4 '/s' removed from PROTECTED_PREFIXES",
        '"/s",' not in mw and "ADR-513" in mw))

    # 5. FE rendering discipline
    #
    # ADR-529 D3 split this surface into a server page + a client island, so
    # the discipline is asserted over BOTH files. Reading only page.tsx would
    # let the accept bounce (or a looser sandbox) move into the island and go
    # unchecked — a gate that reads one file cannot defend a two-file surface.
    with open("../web/app/s/[token]/page.tsx", encoding="utf-8") as f:
        page = f.read()
    with open("../web/app/s/[token]/ShareClient.tsx", encoding="utf-8") as f:
        island = f.read()
    surface = page + "\n" + island
    results.append(_check(
        "5a locked sandbox only (page + island)",
        'sandbox=""' in surface and "allow-scripts" not in surface
        and "allow-same-origin" not in surface))
    results.append(_check(
        "5b no inline injection of member HTML (page + island)",
        "dangerouslySetInnerHTML" not in surface))
    results.append(_check(
        "5c the 401-accept bounce preserves ?next through login",
        re.search(r"/auth/login\?next=", surface) is not None))
    # ADR-529 D3 — the read path must be SERVER-side. This is the assertion
    # that would have caught the original defect: a `"use client"` page that
    # fetches in useEffect ships `Loading…` to every non-JS reader.
    results.append(_check(
        "5d the page is a server component (no 'use client')",
        not page.lstrip().startswith('"use client"')
        and not page.lstrip().startswith("'use client'")))
    # Strip comments before asserting on CODE. The first cut of this check
    # failed on page.tsx's own doc-comment, which NAMES `useEffect` to explain
    # the defect being closed — an assertion matching its own explanation is
    # the documented trap, not a finding.
    page_code = re.sub(r"/\*.*?\*/", "", page, flags=re.DOTALL)
    page_code = re.sub(r"^\s*//.*$", "", page_code, flags=re.MULTILINE)
    results.append(_check(
        "5e the artifact is fetched server-side, not in an effect",
        "useEffect" not in page_code and "fetchSharePreview" in page_code))
    # ADR-531 D1 re-cut: the share surface is INDEXABLE on purpose (noindex was
    # what blocked ChatGPT's search-index-mediated retrieval). `follow: false`
    # survives — indexing this page must not turn a crawler loose on the links
    # inside a member's document. Asserting the exact pair so an accidental
    # revert to `index: false` is caught, not just a missing tag.
    results.append(_check(
        "5f the capability link is indexable, and does not pass link equity",
        "index: true" in page and "follow: false" in page))

    ok = all(results)
    print(f"\n{'ALL PASS' if ok else 'FAILURES'} — {sum(results)}/{len(results)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
