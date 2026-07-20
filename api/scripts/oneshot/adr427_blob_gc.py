"""
ADR-427 GC — sweep unreferenced blobs from the content-addressed store.

ROOTS (what is kept, forever):
  - every blob referenced by ANY workspace_file_versions.blob_sha — the whole
    revision chain, not just heads: trace + revert need history, and the FK
    from blob_sha makes referenced blobs undeletable anyway. The reference
    graph (data-ref pins, derived_from edges) cites PATHS whose revisions are
    chain rows, so it is covered by the same root set.
  - any blob younger than SAFETY_WINDOW_HOURS — closes the write_revision
    crash window (blob upserted in step 1, revision inserted in step 3).

CANDIDATES: blobs with NO referencing revision row and older than the window.
These arise from workspace purges/resets that delete workspace_file_versions
rows while the unscoped global CAS was never swept (the measured pathology:
~34.4k orphans / ~101 MB as of 2026-07-20, vs 666 total revision rows).

DRY-RUN IS THE DEFAULT. It prints the receipt (counts, sizes, age buckets,
external-vs-inline split) and deletes NOTHING. The destructive sweep runs only
with --sweep, and per the arc discipline only after operator sign-off on the
dry-run receipt.

Usage:
    cd api && python3 scripts/oneshot/adr427_blob_gc.py            # dry run
    cd api && python3 scripts/oneshot/adr427_blob_gc.py --sweep    # destructive
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

env_path = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)

SAFETY_WINDOW_HOURS = 24
# A sha256 is 64 chars; PostgREST puts `in_()` filters in the URL, so 500 of
# them is ~34KB of query string and the server answers 400 "JSON could not be
# generated" (observed 2026-07-20 on the first sweep attempt — it deleted
# nothing and died on batch 0). 100 keeps the URL near 7KB, comfortably inside
# the limit, at a negligible cost in round-trips.
BATCH = 100


def get_client():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def _orphan_query(client, select: str, count: bool = False):
    """Blobs with no referencing revision, older than the safety window.

    PostgREST has no NOT EXISTS; page through referenced shas instead (the
    referenced set is small — one per revision row) and diff client-side.
    """
    refs: set[str] = set()
    page = 0
    while True:
        rows = (
            client.table("workspace_file_versions")
            .select("blob_sha")
            .range(page * 1000, page * 1000 + 999)
            .execute()
        ).data or []
        refs.update(r["blob_sha"] for r in rows)
        if len(rows) < 1000:
            break
        page += 1
    return refs


def main() -> int:
    sweep = "--sweep" in sys.argv
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=SAFETY_WINDOW_HOURS)).isoformat()

    client = get_client()
    refs = _orphan_query(client, "sha256")
    print(f"referenced blobs (roots): {len(refs)}")

    # Walk all blobs in pages; collect orphan stats (and optionally delete).
    total = 0
    orphans = 0
    orphan_inline_bytes = 0
    orphan_external = 0
    orphan_external_bytes = 0
    young_skipped = 0
    age_buckets: dict[str, int] = {}
    to_delete: list[tuple[str, str | None]] = []  # (sha, storage_key)

    page = 0
    while True:
        rows = (
            client.table("workspace_blobs")
            .select("sha256, size_bytes, byte_size, storage_key, created_at")
            .order("created_at")
            .range(page * 1000, page * 1000 + 999)
            .execute()
        ).data or []
        for r in rows:
            total += 1
            if r["sha256"] in refs:
                continue
            if (r.get("created_at") or "") > cutoff:
                young_skipped += 1
                continue
            orphans += 1
            month = (r.get("created_at") or "")[:7]
            age_buckets[month] = age_buckets.get(month, 0) + 1
            if r.get("storage_key"):
                orphan_external += 1
                orphan_external_bytes += r.get("byte_size") or 0
            else:
                orphan_inline_bytes += r.get("size_bytes") or 0
            if sweep:
                to_delete.append((r["sha256"], r.get("storage_key")))
        if len(rows) < 1000:
            break
        page += 1

    print(f"total blobs: {total}")
    print(f"orphans (unreferenced, >{SAFETY_WINDOW_HOURS}h old): {orphans}")
    print(f"  inline text: {orphans - orphan_external} blobs, {orphan_inline_bytes/1e6:.1f} MB")
    print(f"  external (bucket): {orphan_external} blobs, {orphan_external_bytes/1e6:.1f} MB")
    print(f"young blobs skipped (safety window): {young_skipped}")
    print("orphans by creation month:")
    for m in sorted(age_buckets):
        print(f"  {m}: {age_buckets[m]}")

    if not sweep:
        print("\nDRY RUN — nothing deleted. Re-run with --sweep after sign-off.")
        return 0

    print(f"\nSWEEP: deleting {len(to_delete)} orphan blobs…")
    from services.storage_backend import CAS_BUCKET
    deleted = 0
    for i in range(0, len(to_delete), BATCH):
        chunk = to_delete[i : i + BATCH]
        keys = [k for _, k in chunk if k]
        if keys:
            try:
                client.storage.from_(CAS_BUCKET).remove(keys)
            except Exception as exc:  # noqa: BLE001
                print(f"  bucket remove failed (continuing, rows kept): {exc}")
                continue
        shas = [s for s, _ in chunk]
        try:
            client.table("workspace_blobs").delete().in_("sha256", shas).execute()
        except Exception as exc:  # noqa: BLE001
            # A referenced blob cannot be deleted (blob_sha FK is NO ACTION), so
            # a failure here is transport-shaped, not a safety breach. Report the
            # batch and keep going rather than dying mid-sweep with a traceback.
            print(f"  batch {i//BATCH} failed ({len(shas)} shas kept): {exc}")
            continue
        deleted += len(shas)
        print(f"  {deleted}/{len(to_delete)}")
    print(f"swept {deleted} blobs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
