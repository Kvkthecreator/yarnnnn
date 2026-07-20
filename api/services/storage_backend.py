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
import logging
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Iterator, Optional

logger = logging.getLogger(__name__)

# The content-addressed object store for binary bytes (migration 219). Private;
# service-role access only; served via per-request signed URLs (ADR-427 D4).
CAS_BUCKET = "workspace-cas"

# git's loose-object layout: cas/<sha[0:2]>/<sha>
def cas_key(sha: str) -> str:
    return f"cas/{sha[:2]}/{sha}"


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

    # -- write stream (ADR-427 Phase 2/3 — large binary without full RAM) --

    def open_write_stream(self) -> "BlobWriteStream":
        """Begin a streaming write. Feed chunks via `.write()`, then
        `.finalize()` returns the sha256 content address. The default
        implementation spools to disk while writing (RAM-bounded ingest) and
        materializes once at finalize for the driver hand-off — a driver with
        native resumable/multipart upload (git-lfs batch, TUS) may override
        `open_write_stream` to avoid even that."""
        return BlobWriteStream(self)

    # -- serving (ADR-427 D4 — capability minted per-request, never stored) --

    def mint_serving_url(self, sha: str, expires_in: int = 3600) -> Optional[str]:
        """Mint a short-lived, object-scoped URL for a blob's bytes, or None
        when the driver serves no out-of-band URLs (e.g. inline text — callers
        read those through the seam). The LFS-batch `href`+`expires_at` shape."""
        return None


class BlobWriteStream:
    """Default streaming writer: disk-spooled, hash-as-you-go.

    Satisfies the D2a stream-first contract without assuming the driver has
    native multipart: chunks spool to a temp file (RAM-bounded), the sha is
    computed incrementally, and finalize() routes the bytes through the
    driver's `_write_bytes`.
    """

    _SPOOL_MAX = 8 * 1024 * 1024  # spill to disk past 8 MB

    def __init__(self, backend: "StorageBackend") -> None:
        self._backend = backend
        self._spool = tempfile.SpooledTemporaryFile(max_size=self._SPOOL_MAX)
        self._hasher = hashlib.sha256()
        self._finalized: Optional[str] = None

    def write(self, chunk: bytes) -> None:
        if self._finalized is not None:
            raise RuntimeError("write after finalize")
        self._hasher.update(chunk)
        self._spool.write(chunk)

    def finalize(self) -> str:
        if self._finalized is not None:
            return self._finalized
        self._spool.seek(0)
        data = self._spool.read()
        self._spool.close()
        sha = self._backend._write_bytes(data)
        expected = self._hasher.hexdigest()
        if sha != expected:  # pragma: no cover - defensive
            raise RuntimeError(f"stream hash mismatch: {expected} != {sha}")
        self._finalized = sha
        return sha


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
            .select("content, storage_key")
            .eq("sha256", sha)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise KeyError(f"blob not found: {sha}")
        row = result.data[0]
        storage_key = row.get("storage_key")
        if storage_key:
            # Binary lane (ADR-427 Phase 2): bytes live in the object store.
            yield from self._read_external(storage_key, byte_range)
            return
        # Inline text lane: content is a string; the bytes are its utf-8
        # encoding (byte-identical to how sha was computed on write).
        data = (row.get("content") or "").encode("utf-8")
        if byte_range is not None:
            data = data[byte_range.start : byte_range.end]
        yield data

    def _read_external(
        self, storage_key: str, byte_range: Optional[ByteRange]
    ) -> Iterator[bytes]:
        """Read an object-store blob, honoring the range when possible.

        Range path: mint a short-lived signed URL and issue an HTTP Range GET,
        streaming chunks (true range read — never materializes the full blob).
        Fallback (no httpx / range unsupported / signed-URL failure): full
        download + slice, correct if less efficient.
        """
        storage = self._db.storage.from_(CAS_BUCKET)
        if byte_range is not None:
            try:
                import httpx

                signed = storage.create_signed_url(storage_key, 300) or {}
                url = signed.get("signedURL") or signed.get("signedUrl")
                if url:
                    end = "" if byte_range.end is None else str(byte_range.end - 1)
                    headers = {"Range": f"bytes={byte_range.start}-{end}"}
                    with httpx.stream("GET", url, headers=headers, timeout=120.0) as resp:
                        resp.raise_for_status()
                        yield from resp.iter_bytes(chunk_size=1024 * 1024)
                    return
            except Exception as exc:  # noqa: BLE001 — fall back to full download
                logger.warning("[STORAGE] range read fell back to full download: %s", exc)
        data = storage.download(storage_key)
        if byte_range is not None:
            data = data[byte_range.start : byte_range.end]
        yield data

    def _write_bytes(self, data: bytes) -> str:
        sha = sha256_bytes(data)
        # Lane routing (ADR-427 D1/D2c — physical placement is the driver's
        # business): utf-8-decodable bytes without NULs are the inline text
        # lane — the EXACT pre-seam upsert, byte-identical for every existing
        # text caller. Anything else is the binary lane: bytes in the
        # workspace-cas bucket keyed by content address, plus a marker row
        # (content='', storage_key, byte_size) so the FK from
        # workspace_file_versions.blob_sha, has_blob, dedup, and GC all stay
        # single-table.
        try:
            content = data.decode("utf-8")
            if "\x00" not in content:
                self._db.table("workspace_blobs").upsert(
                    {"sha256": sha, "content": content},
                    on_conflict="sha256",
                ).execute()
                return sha
        except UnicodeDecodeError:
            pass
        return self._write_external(sha, data)

    def _write_external(self, sha: str, data: bytes) -> str:
        if self.has_blob(sha):
            return sha  # CAS dedup — bytes already stored, marker row present
        key = cas_key(sha)
        # Bytes first, marker second: a marker row implies the bytes exist. A
        # crash in between leaves an unreferenced object in the bucket —
        # harmless, re-uploaded idempotently (upsert) on the next write.
        self._db.storage.from_(CAS_BUCKET).upload(
            path=key,
            file=data,
            file_options={
                "content-type": "application/octet-stream",
                "upsert": "true",
            },
        )
        self._db.table("workspace_blobs").upsert(
            {
                "sha256": sha,
                "content": "",
                "storage_key": key,
                "byte_size": len(data),
            },
            on_conflict="sha256",
        ).execute()
        return sha

    def mint_serving_url(self, sha: str, expires_in: int = 3600) -> Optional[str]:
        """Per-request, TTL'd signed URL for a binary blob (ADR-427 D4 — a
        capability is minted, never stored). Inline text blobs return None —
        they are read through the seam, not served out-of-band."""
        result = (
            self._db.table("workspace_blobs")
            .select("storage_key")
            .eq("sha256", sha)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        storage_key = result.data[0].get("storage_key")
        if not storage_key:
            return None
        try:
            signed = (
                self._db.storage.from_(CAS_BUCKET).create_signed_url(
                    storage_key, expires_in
                )
                or {}
            )
            return signed.get("signedURL") or signed.get("signedUrl")
        except Exception as exc:  # noqa: BLE001
            logger.error("[STORAGE] signed-URL mint failed for %s: %s", sha, exc)
            return None


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
