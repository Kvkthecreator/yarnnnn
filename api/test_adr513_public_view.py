"""ADR-513 regression gate — the public artifact view.

The first unauthenticated read surface: the projection boundary, the lifecycle
honesty, and the rendering discipline are all pinned here. Structural checks.

Run: python3 test_adr513_public_view.py  (from api/)

Asserts:
  1. GET /s/{token} is public (no auth dependency); POST accept stays gated.
  2. Lifecycle honesty (D4): preview enforces status + expiry; no-store +
     noindex headers set.
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
    results.append(_check(
        "2c no-store + noindex headers",
        '"Cache-Control"' in prev_src and "no-store" in prev_src
        and '"X-Robots-Tag"' in prev_src and "noindex" in prev_src))

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
    results.append(_check(
        "3d walk query selects metadata columns only (no content/diff)",
        '"authored_by, created_at, message"' in prev_src))

    # 4. middleware
    with open("../web/lib/supabase/middleware.ts", encoding="utf-8") as f:
        mw = f.read()
    results.append(_check(
        "4 '/s' removed from PROTECTED_PREFIXES",
        '"/s",' not in mw and "ADR-513" in mw))

    # 5. FE rendering discipline
    with open("../web/app/s/[token]/page.tsx", encoding="utf-8") as f:
        page = f.read()
    results.append(_check(
        "5a locked sandbox only",
        'sandbox=""' in page and "allow-scripts" not in page
        and "allow-same-origin" not in page))
    results.append(_check(
        "5b no inline injection of member HTML",
        "dangerouslySetInnerHTML" not in page))
    results.append(_check(
        "5c the 401-accept bounce preserves ?next through login",
        re.search(r"/auth/login\?next=", page) is not None))

    ok = all(results)
    print(f"\n{'ALL PASS' if ok else 'FAILURES'} — {sum(results)}/{len(results)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
