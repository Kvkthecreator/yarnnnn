# ADR-427 GC sweep — EXECUTED receipt, 2026-07-20

Operator-approved after the [dry-run receipt](adr427-gc-dry-run-2026-07-20.md).
Harness: `api/scripts/oneshot/adr427_blob_gc.py --sweep`.

## Result

| metric | before | after |
|---|---|---|
| `workspace_blobs` rows | 34,851 | **461** |
| referenced blobs (roots) | 450 | 453 |
| orphans | 34,401 | **8** (all inside the 24h safety window) |
| `workspace_files` | 190 | 195 |
| `workspace_file_versions` | 698 | 709 |
| dangling references | — | **0** |

**Swept: 34,393 blobs (~110 MB of inline text).** Zero external/bucket blobs
were involved, so this was pure table-row deletion — no storage objects touched.

Files and revisions *grew* during the sweep (190→195, 698→709) because the
workspace stayed live. That is expected and is itself evidence the sweep was
scoped to unreachable rows only.

## Integrity verification (post-sweep)

Not inferred from the script's own output — queried independently:

- **Dangling references: 0.** No `workspace_file_versions` row points at a
  missing blob.
- **All 195 live files resolve their head content** through the blob join;
  0 heads with a missing blob.
- **Full revision history resolves, not just heads** — sampled the deepest
  chains: `_recent_execution.md` 104/104 revisions resolvable,
  `prd-for-yarnnn/document.html` 71/71, `yarrnnnn-decl/deck.html` 36/36,
  `_schedule_index.md` 30/30. History, `trace`, diff, and revert are intact.

The FK `workspace_file_versions_blob_sha_fkey` is `NO ACTION` (`confdeltype='a'`),
so the database itself would have rejected any attempt to delete a referenced
blob. That is the guarantee that makes the sweep safe independent of script logic.

## Harness bug found and fixed during execution

The first `--sweep` attempt **died on batch 0 and deleted nothing**:

```
postgrest.exceptions.APIError: {'message': 'JSON could not be generated',
  'code': 400, ... "b'Bad Request'"}
```

Cause: `BATCH = 500`. A sha256 is 64 chars and PostgREST puts `in_()` filters in
the **URL**, so 500 of them is ~34 KB of query string — past the server's limit.
Two fixes, both in the harness:

1. `BATCH` 500 → **100** (~7 KB URL, comfortably inside the limit).
2. The per-batch delete is now wrapped: a failed batch is **reported and
   skipped** rather than killing the sweep with a traceback. A referenced blob
   cannot be deleted (the FK forbids it), so a failure here is transport-shaped,
   never a safety breach.

The failed first attempt left **no partial state** — verified before retrying
(34,851 blobs before and after, all 450 roots intact).

## What this does NOT fix

**The tap is still running.** The sweep is a mop:

- `workspace_purge` still mentions `workspace_blobs` **zero times**, and cannot
  reach them — `workspace_blobs` has **no owner column** (`sha256, content,
  size_bytes, storage_key, byte_size, created_at`). Every workspace reset will
  orphan its blobs again.
- `write_revision` is still non-atomic between step 1 (upsert blob) and step 3
  (insert revision); a failure in between orphans a blob permanently.

The A-vs-B decision (recurring GC vs. giving blobs an owner) is **still open**
and is the subject of its own discourse. Sweeping does not prejudge it.
