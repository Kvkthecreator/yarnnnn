"""
One-shot: bring every Studio artifact up to the current kernel contract.

Context (2026-08-07, following b7c1927): the deck slide's BOX moved out of the
layout skin and into the kernel as `--stage-w`/`--stage-h`, on the explicit
reasoning that "the kernel is the layer that retrofits, so decks that ALREADY
EXIST get it." That is true of the MECHANISM but not of the TIMING: the retrofit
rides the next mechanical op per artifact (`ensureKernelStyle` in artifactOps.ts,
`ensure_kernel_style_in_html` server-side). An artifact nobody edits sits at its
old version indefinitely.

So at v14 ship time every deck in production was still v11/v13, carrying only
the baked `width: min(100%, 62rem)` the move was meant to replace — a CONTAINER
read. The viewer had meanwhile stopped restating 992 and started ASKING the
document (`readStageSize`), so the geometry the FE now reads did not exist in
any file. The operator saw slides clipped to visual emptiness in the navigator.

This applies the retrofit NOW, as an attributed revision, so the file actually
carries the box the viewer reads. It is version-generic — it targets whatever
`STUDIO_KERNEL_CSS_VERSION` currently is, so it remains the correct backfill for
the next kernel bump too.

Difference from `studio_artifact_kernel_upgrade.py` (2026-07-20, ADR-466/471):
that script is scoped to one hardcoded USER_ID and also seeds template
representatives. This one is workspace-wide and does nothing but the retrofit —
ADR-373 re-keyed substrate to workspace_id, and a per-user backfill can no
longer see every artifact.

Attribution: `system:studio-kernel-retrofit` — a mechanical version bump, not an
authored edit. Every write goes through `write_revision`, so each retrofit is a
normal parent-pointered revision the operator can inspect or revert (ADR-209).

Not ADR-numbered on purpose: this is not one ADR's migration but the standing
answer to "the kernel bumped and existing artifacts have not caught up." It
targets whatever `STUDIO_KERNEL_CSS_VERSION` currently is, so it is re-runnable
at every future bump rather than being superseded by one.

Usage:
    cd api
    python -m scripts.oneshot.backfill_studio_kernel_version            # dry run
    python -m scripts.oneshot.backfill_studio_kernel_version --execute  # apply
"""

from __future__ import annotations

import argparse
import logging
import re

logging.basicConfig(level=logging.WARNING)

RETROFIT_AUTHOR = "system:studio-kernel-retrofit"
RETROFIT_MESSAGE = (
    "Studio kernel retrofit: bring the artifact's kernel style element to the "
    "current version so the stage geometry the viewer reads (--stage-w/"
    "--stage-h) exists in the file. Mechanical — no authored content touched."
)

_KERNEL_VERSION_RX = re.compile(r'data-kernel="true"[^>]*data-kernel-v="(\d+)"')

#: PostgREST caps an unbounded select; artifacts are few but page anyway so a
#: growing workspace does not silently truncate the backfill (the ADR-533 §13
#: lesson: a cap that is never logged reads as "covered everything").
_PAGE = 500


def _fetch_artifacts(client) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        page = (
            client.table("workspace_files")
            .select("id, path, content, user_id, workspace_id")
            .like("path", "%.html")
            .order("path")
            .range(offset, offset + _PAGE - 1)
            .execute()
        ).data or []
        rows.extend(page)
        if len(page) < _PAGE:
            break
        offset += _PAGE
    return rows


def main(execute: bool) -> int:
    from services.authored_substrate import write_revision
    from services.studio import (
        STUDIO_KERNEL_CSS_VERSION,
        ensure_kernel_style_in_html,
    )
    from services.supabase import get_service_client

    client = get_service_client()
    rows = _fetch_artifacts(client)

    print(f"kernel target: v{STUDIO_KERNEL_CSS_VERSION} — {len(rows)} artifact(s)")

    retrofit = 0
    already = 0
    noop = 0
    failed = 0

    for row in rows:
        path = row["path"]
        content = row.get("content") or ""
        m = _KERNEL_VERSION_RX.search(content)
        have = int(m.group(1)) if m else None

        if have == STUDIO_KERNEL_CSS_VERSION:
            already += 1
            continue

        fresh = ensure_kernel_style_in_html(content)
        if fresh == content:
            # No </head> (not a full-document artifact) — legitimately skipped.
            noop += 1
            print(f"  skip      v{have}  {path} (not a full document)")
            continue

        if not execute:
            print(f"  DRY RUN   v{have} -> v{STUDIO_KERNEL_CSS_VERSION}  {path}")
            retrofit += 1
            continue

        # user_id is required by write_revision for attribution; every artifact
        # row carries one (verified before writing this script). Skip loudly
        # rather than guess if that ever stops being true.
        user_id = row.get("user_id")
        if not user_id:
            failed += 1
            print(f"  FAILED    {path} — no user_id to attribute the revision to")
            continue

        try:
            rev = write_revision(
                client,
                user_id=user_id,
                path=path,
                content=fresh,
                authored_by=RETROFIT_AUTHOR,
                message=RETROFIT_MESSAGE,
                summary="Kernel style element upgraded to the current version",
            )
        except Exception as exc:  # noqa: BLE001 — report, don't abort the sweep
            failed += 1
            print(f"  FAILED    {path} — {exc}")
            continue

        retrofit += 1
        print(f"  retrofit  v{have} -> v{STUDIO_KERNEL_CSS_VERSION}  {path}  rev={rev}")

    verb = "would retrofit" if not execute else "retrofitted"
    print(
        f"\n{verb}: {retrofit} · already current: {already} · "
        f"not a document: {noop} · failed: {failed}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    raise SystemExit(main(args.execute))
