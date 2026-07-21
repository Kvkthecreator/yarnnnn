"""
Validation Suite — ADR-427 Phase 1 (the Storage Seam)

The gate for Phase 1: the seam exists, is STREAM-FIRST, and its text path is
BYTE-IDENTICAL to the pre-seam `_upsert_blob` + `_sha256` behavior. Pure unit
tests — no DB — because the contract is the interface shape + address stability,
not storage plumbing.

Tests:
  1. Seam is stream-first: open_read_stream / _write_bytes are the primitives;
     get_blob / put_blob are wrappers (the interface carries streaming).
  2. Content address is bytes-addressed (sha256 of raw bytes); text is the
     utf-8 case — and MATCHES the legacy `_sha256(content)` exactly.
  3. put_text → get_text round-trips a string byte-identically.
  4. put_blob → get_blob round-trips arbitrary bytes byte-identically.
  5. Range read returns the requested slice.
  6. CAS dedup: writing identical bytes twice yields ONE stored blob, same sha.
  7. has_blob is true after a write, false before.
  8. The Postgres driver's write emits the EXACT `workspace_blobs` upsert the
     pre-seam `_upsert_blob` did (byte-identical wire shape) — the refactor is
     invisible below the seam.
  9. authored_substrate._sha256 now delegates to the seam and stays identical.

Usage:
    cd api && python test_adr427_storage_seam.py
"""

from __future__ import annotations

import hashlib
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    icon = "✓" if ok else "✗"
    logger.info(f"{icon} {name}: {detail}")


# ---------------------------------------------------------------------------
# A fake Supabase table/client that RECORDS the exact upsert wire calls, so we
# can assert the seam emits byte-identically what the pre-seam code did.
# ---------------------------------------------------------------------------

class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, store, table):
        self._store = store
        self._table = table
        self._select = None
        self._eq = {}
        self._limit = None

    def select(self, cols):
        self._select = cols
        return self

    def eq(self, col, val):
        self._eq[col] = val
        return self

    def limit(self, n):
        self._limit = n
        return self

    def upsert(self, row, on_conflict=None):
        # record the exact wire call
        self._store.upsert_calls.append({"row": dict(row), "on_conflict": on_conflict})
        self._store.blobs[row["sha256"]] = row["content"]
        return self

    def execute(self):
        if "sha256" in self._eq:
            sha = self._eq["sha256"]
            if sha in self._store.blobs:
                return _FakeResult([{"content": self._store.blobs[sha], "sha256": sha}])
            return _FakeResult([])
        return _FakeResult([])


class _FakeDB:
    def __init__(self):
        self.blobs: dict[str, str] = {}
        self.upsert_calls: list[dict] = []

    def table(self, name):
        return _FakeQuery(self, name)


def run() -> None:
    from services.storage_backend import (
        ByteRange,
        PostgresObjectStoreBackend,
        StorageBackend,
        get_storage_backend,
        sha256_bytes,
    )

    db = _FakeDB()
    backend = get_storage_backend(db)

    # 1. stream-first — the primitives exist and the wrappers delegate
    ok = (
        hasattr(backend, "open_read_stream")
        and hasattr(backend, "_write_bytes")
        and callable(getattr(backend, "get_blob"))
        and callable(getattr(backend, "put_blob"))
        and isinstance(backend, StorageBackend)
    )
    record("1. seam is stream-first (primitives + wrappers present)", ok,
           "open_read_stream/_write_bytes primitives, get_blob/put_blob wrappers")

    # 2. bytes-addressed, and text matches the legacy _sha256 exactly
    text = "the quick brown fox — café ☕"
    legacy_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    seam_sha = sha256_bytes(text.encode("utf-8"))
    from services.authored_substrate import _sha256 as as_sha
    ok = (seam_sha == legacy_sha == as_sha(text))
    record("2. address is bytes-addressed; text == legacy _sha256", ok,
           f"{seam_sha[:12]}… all three agree" if ok else
           f"MISMATCH seam={seam_sha[:12]} legacy={legacy_sha[:12]} as={as_sha(text)[:12]}")

    # 3. put_text → get_text round-trips a string
    sha = backend.put_text(text)
    got = backend.get_text(sha)
    ok = (got == text and sha == legacy_sha)
    record("3. put_text → get_text round-trips byte-identically", ok,
           f"in={text!r} out={got!r}")

    # 4. put_blob → get_blob round-trips arbitrary (utf-8) bytes
    #    (Phase-1 Postgres driver stores as TEXT; bytes must be valid utf-8 —
    #    the binary-bytes lane is Phase 2. This asserts the text-bytes path.)
    data = "binary-ish but valid utf-8 \x41\x42\x43".encode("utf-8")
    sha2 = backend.put_blob(data)
    got2 = backend.get_blob(sha2)
    ok = (got2 == data and sha2 == sha256_bytes(data))
    record("4. put_blob → get_blob round-trips bytes", ok,
           f"{len(data)} bytes, sha={sha2[:12]}…")

    # 5. range read returns the requested slice
    full = backend.get_blob(sha)
    sliced = b"".join(backend.open_read_stream(sha, ByteRange(0, 3)))
    ok = (sliced == full[0:3])
    record("5. range read returns the slice", ok, f"[0:3] = {sliced!r}")

    # 6. CAS dedup — identical bytes twice → one blob, same sha
    calls_before = len(db.upsert_calls)
    sha_again = backend.put_text(text)
    ok = (sha_again == sha and len(db.blobs) == 2)  # only 'text' + 'data' blobs
    record("6. CAS dedup — identical content, same sha, no new blob", ok,
           f"blobs stored = {len(db.blobs)} (expected 2), re-write sha == original: {sha_again == sha}")

    # 7. has_blob true after write, false before
    ok = (backend.has_blob(sha) and not backend.has_blob("0" * 64))
    record("7. has_blob true after write / false for absent", ok, "")

    # 8. wire shape — ADR-474 made the blob identity (workspace_id, sha256), so
    #    the upsert carries the owner and its conflict target names BOTH columns.
    #    A single-column target ("sha256") no longer matches any unique
    #    constraint and Postgres rejects it outright — this assertion is what
    #    catches a regression to the pre-474 shape.
    call = db.upsert_calls[0]
    ok = (
        call["row"] == {"sha256": legacy_sha, "content": text, "workspace_id": None}
        and call["on_conflict"] == "workspace_id,sha256"
    )
    record("8. Postgres driver emits the ADR-474 owner-carrying upsert", ok,
           f"row keys={sorted(call['row'])}, on_conflict={call['on_conflict']!r}")

    # 9. _upsert_blob (the refactored legacy fn) still works through the seam,
    #    byte-identically, and the sha-guard passes.
    from services.authored_substrate import _upsert_blob
    db2 = _FakeDB()
    _upsert_blob(db2, legacy_sha, text)
    ok = (db2.blobs.get(legacy_sha) == text and len(db2.upsert_calls) == 1)
    record("9. _upsert_blob routes through seam, byte-identical", ok,
           f"stored={db2.blobs.get(legacy_sha)!r}")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # surface import/wiring failures as a hard fail
        logger.exception("suite crashed")
        record("SUITE", False, f"crashed: {exc}")

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    failed = total - passed
    print(f"\n{'='*60}")
    print(f"ADR-427 Phase 1 storage-seam gate: {passed}/{total} passed, {failed} failed")
    print(f"{'='*60}")
    if failed:
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"  ✗ {name}: {detail}")
    sys.exit(0 if failed == 0 else 1)
