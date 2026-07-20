"""
One-shot: bring every Studio artifact in the operator's workspace up to the
current kernel contract, and seed the missing template representatives.

Context (2026-07-20, ADR-466 P8–P11 + ADR-471): the operator is live-testing
the Studio's object chrome in production, and stale artifacts (kernel v8/v10,
or no kernel style element at all) made it impossible to tell a feature bug
from a legacy-file artifact. The kernel retrofit normally rides the next
mechanical op per artifact (`ensure_kernel_style_in_html`); this applies it
NOW, as an attributed revision, so every artifact renders under one contract.

Also seeds one representative artifact per template the workspace lacks
(article, page) so every layout mode has a production test subject.

Attribution: retrofits land as `system:studio-kernel-retrofit` (a mechanical
version bump, not an authored edit); seeds land as `operator` mirroring the
New-flow route (created on the operator's explicit request).

Usage:
    cd api
    python -m scripts.oneshot.studio_artifact_kernel_upgrade            # dry run
    python -m scripts.oneshot.studio_artifact_kernel_upgrade --execute  # apply
"""

from __future__ import annotations

import argparse
import logging
import re

logging.basicConfig(level=logging.WARNING)

USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"  # kvkthecreator@gmail.com

RETROFIT_AUTHOR = "system:studio-kernel-retrofit"
RETROFIT_MESSAGE = (
    "Studio kernel retrofit (ADR-466/471): bring the artifact's kernel style "
    "element to the current version so the object chrome renders under one "
    "contract. Mechanical — no authored content touched."
)

#: Template representatives to seed when absent: slug -> (path, display name).
SEEDS = {
    "article": ("/workspace/operation/test-article/article.html", "Test article"),
    "page": ("/workspace/operation/test-page/page.html", "Test page"),
}

_KERNEL_VERSION_RX = re.compile(r'data-kernel="true"[^>]*data-kernel-v="(\d+)"')


def main(execute: bool) -> int:
    from services.authored_substrate import write_revision
    from services.studio import (
        STUDIO_KERNEL_CSS_VERSION,
        STUDIO_LAYOUTS,
        STUDIO_TEMPLATES,
        ensure_kernel_style_in_html,
        set_artifact_title,
    )
    from services.supabase import get_service_client

    client = get_service_client()

    rows = (
        client.table("workspace_files")
        .select("id, path, content, workspace_id")
        .eq("user_id", USER_ID)
        .like("path", "%.html")
        .execute()
    ).data or []

    print(f"kernel target: v{STUDIO_KERNEL_CSS_VERSION} — {len(rows)} artifact(s)")

    # ── 1. Retrofit stale kernels ────────────────────────────────────────
    for row in sorted(rows, key=lambda r: r["path"]):
        content = row.get("content") or ""
        m = _KERNEL_VERSION_RX.search(content)
        have = int(m.group(1)) if m else None
        if have == STUDIO_KERNEL_CSS_VERSION:
            print(f"  ok        v{have}  {row['path']}")
            continue
        fresh = ensure_kernel_style_in_html(content)
        if fresh == content:
            print(f"  unchanged v{have}  {row['path']} (retrofit was a no-op?)")
            continue
        if not execute:
            print(f"  DRY RUN would retrofit v{have} -> v{STUDIO_KERNEL_CSS_VERSION}  {row['path']}")
            continue
        rev = write_revision(
            client,
            user_id=USER_ID,
            path=row["path"],
            content=fresh,
            authored_by=RETROFIT_AUTHOR,
            message=RETROFIT_MESSAGE,
            summary="Kernel style element upgraded to the current version",
        )
        print(f"  retrofit  v{have} -> v{STUDIO_KERNEL_CSS_VERSION}  {row['path']}  rev={rev}")

    # ── 2. Seed missing template representatives ─────────────────────────
    have_templates = set()
    for row in rows:
        tm = re.search(r'data-template="([a-z-]+)"', row.get("content") or "")
        if tm:
            have_templates.add(tm.group(1))
    print(f"templates present: {sorted(have_templates)}")

    for slug, (path, name) in SEEDS.items():
        if slug in have_templates:
            print(f"  ok        {slug} already represented")
            continue
        if any(r["path"] == path for r in rows):
            print(f"  ok        {path} already exists")
            continue
        template = STUDIO_TEMPLATES[slug]
        layout = STUDIO_LAYOUTS.get(slug)
        is_flow = bool(layout and layout["mode"] == "flow")
        content = set_artifact_title(template["skeleton"], name, set_h1=is_flow)
        if not execute:
            print(f"  DRY RUN would seed {slug} at {path}")
            continue
        rev = write_revision(
            client,
            user_id=USER_ID,
            path=path,
            content=content,
            authored_by="operator",
            author_identity_uuid=USER_ID,
            message=f"Studio: create from template '{slug}' (test representative, operator-requested)",
            summary=f"New {template['label'].lower()} created as the {slug} test representative",
        )
        print(f"  seeded    {slug} at {path}  rev={rev}")

    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    raise SystemExit(main(args.execute))
