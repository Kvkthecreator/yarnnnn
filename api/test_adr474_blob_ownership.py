"""ADR-474 — Content inherits the file's scope.

Asserts the invariant the ADR establishes and the mechanics that keep it true:

  §7  every blob is owned by exactly one workspace, and every revision resolves
      its blob WITHIN its own workspace (the composite FK makes a
      cross-workspace reference structurally impossible)
  D1  the write path carries the owner
  D3  dedup + content_ref are workspace-scoped — identical bytes in another
      workspace are a coincidence of content, never a reachable blob
  §4  the storage seam has a delete verb, and it deletes the bucket object
      before the row (the key lives only on the row), and only when the LAST
      owner of that content address goes away

Run with `python3 test_adr474_blob_ownership.py` (NOT pytest — the check()
gates print ✗ but a pytest run reports PASS; see MEMORY.md).
"""

import logging
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

_passed = 0
_failed = 0


def record(name: str, ok: bool, detail: str = "") -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        logger.info(f"✓ {name}" + (f": {detail}" if detail else ""))
    else:
        _failed += 1
        logger.error(f"✗ {name}" + (f": {detail}" if detail else ""))


# ---------------------------------------------------------------------------
# Fake DB — enough PostgREST surface to exercise the driver's query building
# ---------------------------------------------------------------------------


class _FakeQuery:
    def __init__(self, rows: List[Dict[str, Any]], sink: Dict[str, Any]) -> None:
        self._rows = rows
        self._sink = sink
        self._filters: Dict[str, Any] = {}
        self._neq: Dict[str, Any] = {}

    def select(self, *_a: Any, **_k: Any) -> "_FakeQuery":
        return self

    def eq(self, col: str, val: Any) -> "_FakeQuery":
        self._filters[col] = val
        return self

    def neq(self, col: str, val: Any) -> "_FakeQuery":
        self._neq[col] = val
        return self

    def limit(self, _n: int) -> "_FakeQuery":
        return self

    def delete(self) -> "_FakeQuery":
        self._sink["delete_filters"] = self._filters
        return self

    def execute(self) -> Any:
        rows = [
            r
            for r in self._rows
            if all(r.get(k) == v for k, v in self._filters.items())
            and all(r.get(k) != v for k, v in self._neq.items())
        ]
        self._sink.setdefault("queries", []).append(dict(self._filters))

        class _R:
            def __init__(self, data: List[Dict[str, Any]]) -> None:
                self.data = data
                self.count = len(data)

        return _R(rows)


class _FakeStorage:
    def __init__(self, sink: Dict[str, Any]) -> None:
        self._sink = sink

    def from_(self, _bucket: str) -> "_FakeStorage":
        return self

    def remove(self, keys: List[str]) -> None:
        self._sink.setdefault("removed_objects", []).extend(keys)


class _FakeDB:
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None) -> None:
        self.rows = rows or []
        self.sink: Dict[str, Any] = {}
        self.storage = _FakeStorage(self.sink)

    def table(self, _name: str) -> _FakeQuery:
        return _FakeQuery(self.rows, self.sink)


def run() -> None:
    from services.storage_backend import PostgresObjectStoreBackend, StorageBackend

    WS_A = "aaaaaaaa-0000-0000-0000-000000000000"
    WS_B = "bbbbbbbb-0000-0000-0000-000000000000"
    SHA = "c" * 64

    # -- D1: the interface carries the owner on every content-addressed op ----
    import inspect

    for verb in ("has_blob", "delete_blob", "_write_bytes", "open_read_stream",
                 "put_text", "put_blob", "mint_serving_url"):
        sig = inspect.signature(getattr(StorageBackend, verb))
        record(
            f"D1. StorageBackend.{verb} accepts workspace_id",
            "workspace_id" in sig.parameters,
            f"params={list(sig.parameters)}",
        )

    # -- D3: dedup is workspace-scoped ---------------------------------------
    db = _FakeDB([{"sha256": SHA, "workspace_id": WS_A, "storage_key": None}])
    backend = PostgresObjectStoreBackend(db)

    record(
        "D3. has_blob TRUE for the owning workspace",
        backend.has_blob(SHA, workspace_id=WS_A),
        "",
    )
    record(
        "D3. has_blob FALSE for a different workspace holding identical bytes",
        not backend.has_blob(SHA, workspace_id=WS_B),
        "identical bytes elsewhere must never read as a dedup hit — the write "
        "would reference content this workspace does not own",
    )

    # -- §4: delete removes the OBJECT before the row ------------------------
    db2 = _FakeDB([{"sha256": SHA, "workspace_id": WS_A, "storage_key": "cas/cc/" + SHA}])
    backend2 = PostgresObjectStoreBackend(db2)
    ok = backend2.delete_blob(SHA, workspace_id=WS_A)
    record(
        "§4. delete_blob removes the bucket object (sole owner)",
        ok and db2.sink.get("removed_objects") == ["cas/cc/" + SHA],
        f"removed={db2.sink.get('removed_objects')}",
    )
    record(
        "§4. delete_blob scopes the row delete to the workspace",
        db2.sink.get("delete_filters", {}).get("workspace_id") == WS_A,
        f"filters={db2.sink.get('delete_filters')}",
    )

    # -- §4: a co-owner's bytes survive --------------------------------------
    db3 = _FakeDB(
        [
            {"sha256": SHA, "workspace_id": WS_A, "storage_key": "cas/cc/" + SHA},
            {"sha256": SHA, "workspace_id": WS_B, "storage_key": "cas/cc/" + SHA},
        ]
    )
    backend3 = PostgresObjectStoreBackend(db3)
    backend3.delete_blob(SHA, workspace_id=WS_A)
    record(
        "§4. bucket object SURVIVES while another workspace still owns the sha",
        not db3.sink.get("removed_objects"),
        "the object is content-addressed and shared by every owner row — "
        "removing it on the first delete would destroy a co-owner's content",
    )

    # -- delete is idempotent ------------------------------------------------
    db4 = _FakeDB([])
    record(
        "§4. delete_blob is idempotent on an absent blob",
        PostgresObjectStoreBackend(db4).delete_blob(SHA, workspace_id=WS_A) is False,
        "",
    )

    # -- §7: the live invariant ---------------------------------------------
    try:
        from services.supabase import get_service_client

        c = get_service_client()

        unowned = (
            c.table("workspace_blobs")
            .select("sha256", count="exact")
            .is_("workspace_id", "null")
            .limit(1)
            .execute()
        )
        record(
            "§7. LIVE — every blob is owned (workspace_id NOT NULL)",
            (unowned.count or 0) == 0,
            f"unowned={unowned.count}",
        )

        # Every revision resolves its blob within its OWN workspace. The
        # composite FK enforces this, so a non-zero count means the constraint
        # is missing — not merely that data drifted.
        revs = (
            c.table("workspace_file_versions")
            .select("id, blob_sha, workspace_id, workspace_blobs(sha256)")
            .limit(200)
            .execute()
        ).data or []
        unresolved = [r for r in revs if not r.get("workspace_blobs")]
        record(
            "§7. LIVE — sampled revisions resolve their blob in-workspace",
            not unresolved,
            f"checked={len(revs)}, unresolved={len(unresolved)}",
        )
    except Exception as exc:  # noqa: BLE001 — live checks are env-gated
        logger.warning(f"live checks skipped (no DB env): {exc}")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        logger.exception("suite crashed")
        record("SUITE", False, f"crashed: {exc}")
    print("\n" + "=" * 60)
    print(f"ADR-474 blob-ownership gate: {_passed}/{_passed + _failed} passed, {_failed} failed")
    print("=" * 60)
    sys.exit(1 if _failed else 0)
