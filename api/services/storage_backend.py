"""
Storage Backend — ADR-427 Phase 1 (the storage seam)

The single interface through which ALL blob physical I/O routes. `write_revision`
and the read path call the seam, never a concrete store. This is the down-payment
that makes the local-disk fork a driver swap rather than a rewrite (ADR-427 D2).

Two decisions this module encodes (ADR-427 D2a / D2b):

  1. STREAM-FIRST, not bytes-first. `open_read_stream` / `open_write_stream` are
     the primitives; `get_blob` / `put_blob` are convenience wrappers over them.
     A 25 GB `.mov` must never be forced to materialize in Python memory to
     satisfy the interface — so the signature carries range/streaming from birth,
     even though Phase-1's Postgres driver (text blobs, small) implements them by
     full-materialization. Phase 3's real streaming driver drops in behind the
     same interface with no caller change.

  2. The wire shape is git-lfs-batch-compatible. Blobs are content-addressed by
     sha256; the store is a pointer→bytes CAS. `PostgresObjectStoreBackend` is
     an LFS-batch-server-shaped driver (small/text blobs inline in
     `workspace_blobs`, large/binary blobs served via presigned range-capable
     URLs — the latter lands in Phase 2/3). `LocalDiskBackend` (the fork,
     ADR-427 D3, NOT built here) is a real `git + git-lfs` working tree.

PHASE 1 SCOPE (this module): the interface + the Postgres driver that wraps
today's EXACT blob behavior (`workspace_blobs` upsert-by-sha256, read-by-sha256).
Text is byte-identical — the refactor is behind the seam, the behavior is
unchanged. Binary (Phase 2), streaming impl + minted serving URLs (Phase 3),
and the local-disk driver (the fork) are all reserved.

Canonical reference: docs/adr/ADR-427-binary-native-substrate-and-the-storage-seam.md
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Iterator, Optional


# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ByteRange:
    """A half-open byte range [start, end) for a range read. `end=None` means
    "to the end of the blob". The stream-first read primitive takes one of
    these; None (the default) means the whole blob."""
    start: int = 0
    end: Optional[int] = None


def sha256_bytes(data: bytes) -> str:
    """Content address of a blob: hex sha256 of the raw bytes.

    Text is the utf-8 case (ADR-427 D1: bytes-addressed, content-agnostic).
    This is the single hashing definition; `authored_substrate._sha256` (text)
    is `sha256_bytes(text.encode("utf-8"))` and must stay byte-identical to it.
    """
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# The seam
# ---------------------------------------------------------------------------

class StorageBackend(ABC):
    """The only code that knows WHERE bytes physically live.

    Stream-first (ADR-427 D2a): the streaming methods are the primitives; the
    `bytes` methods are convenience wrappers a driver MAY override for its
    common case but MUST behave identically to the stream form.
    """

    # -- primitives (stream/range, both directions) --

    @abstractmethod
    def open_read_stream(
        self, sha: str, byte_range: Optional[ByteRange] = None
    ) -> Iterator[bytes]:
        """Yield the blob's bytes (optionally a range). The read primitive.

        Phase-1 Postgres driver yields one chunk (text blobs are small); a
        Phase-3 object-store driver yields chunks / honors HTTP range. Callers
        that need the whole blob use `get_blob`; range-aware callers iterate.
        Raises KeyError if the sha is absent.
        """
        raise NotImplementedError

    @abstractmethod
    def has_blob(self, sha: str) -> bool:
        """True if a blob with this content address already exists (dedup check)."""
        raise NotImplementedError

    @abstractmethod
    def _write_bytes(self, data: bytes) -> str:
        """Idempotently store `data`, return its sha256 content address.

        The write primitive's Phase-1 form (one-shot; the resumable/multipart
        `open_write_stream` form is a Phase-3 addition for large binary — the
        interface reserves it below). Idempotent by content address: writing
        identical bytes twice is a no-op that returns the same sha (the CAS
        dedup property).
        """
        raise NotImplementedError

    # -- convenience wrappers (small common case) --

    def get_blob(self, sha: str) -> bytes:
        """Read the whole blob as bytes (== full-range read). Convenience over
        `open_read_stream`; do NOT use for large binary — iterate the stream."""
        return b"".join(self.open_read_stream(sha, None))

    def put_blob(self, data: bytes) -> str:
        """Store bytes, return the content address. Convenience over the write
        primitive for the small/text common case."""
        return self._write_bytes(data)

    # -- text convenience (the byte-identical bridge for today's callers) --

    def put_text(self, content: str) -> str:
        """Store text (utf-8), return the content address. This is the exact
        byte-identical replacement for the pre-seam `_upsert_blob` + `_sha256`
        pair — text → utf-8 bytes → sha256, same address as before."""
        return self._write_bytes(content.encode("utf-8"))

    def get_text(self, sha: str) -> str:
        """Read a text blob back as a utf-8 string."""
        return self.get_blob(sha).decode("utf-8")


# ---------------------------------------------------------------------------
# Driver 1 — Postgres + object store (the cloud driver; built Phase 1)
# ---------------------------------------------------------------------------

class PostgresObjectStoreBackend(StorageBackend):
    """The cloud driver, LFS-batch-server-shaped.

    Phase 1: wraps today's EXACT behavior — blobs live inline in the
    `workspace_blobs` table (`sha256` PK, `content` TEXT), upserted with
    ON CONFLICT DO NOTHING by sha. Text is byte-identical to the pre-seam path.

    Phase 2/3 (reserved, NOT here): large/binary blobs move to the object-store
    bucket keyed by sha256, served via presigned range-capable URLs minted
    per-request (ADR-427 D4); `open_read_stream` gains real range support and
    `open_write_stream` gains resumable multipart. The interface already carries
    those shapes; only this driver's internals change.
    """

    def __init__(self, db_client: Any) -> None:
        self._db = db_client

    def has_blob(self, sha: str) -> bool:
        result = (
            self._db.table("workspace_blobs")
            .select("sha256")
            .eq("sha256", sha)
            .limit(1)
            .execute()
        )
        return bool(result.data)

    def open_read_stream(
        self, sha: str, byte_range: Optional[ByteRange] = None
    ) -> Iterator[bytes]:
        result = (
            self._db.table("workspace_blobs")
            .select("content")
            .eq("sha256", sha)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise KeyError(f"blob not found: {sha}")
        # Phase 1: text blobs are stored as a string in `content`; the bytes are
        # its utf-8 encoding (byte-identical to how sha was computed on write).
        data = (result.data[0].get("content") or "").encode("utf-8")
        if byte_range is not None:
            data = data[byte_range.start : byte_range.end]
        yield data

    def _write_bytes(self, data: bytes) -> str:
        sha = sha256_bytes(data)
        # Phase 1: content is stored as TEXT — this driver's inline lane is the
        # text/small-blob case. `data` here is always a utf-8 text encoding in
        # Phase 1 (the only caller is `put_text` via the write path); the binary
        # lane (bytes that are NOT valid utf-8 → object-store bucket) lands in
        # Phase 2. Decoding is therefore safe and byte-identical to today.
        content = data.decode("utf-8")
        self._db.table("workspace_blobs").upsert(
            {"sha256": sha, "content": content},
            on_conflict="sha256",
        ).execute()
        return sha


# ---------------------------------------------------------------------------
# Driver factory
# ---------------------------------------------------------------------------

def get_storage_backend(db_client: Any) -> StorageBackend:
    """Return the active storage backend for a db client.

    Phase 1: always the Postgres+object-store cloud driver. When the local-disk
    fork ships (ADR-427 D3), this is where `LocalDiskBackend` is selected by
    deployment config — the single switch that makes the fork a driver swap.
    """
    return PostgresObjectStoreBackend(db_client)
