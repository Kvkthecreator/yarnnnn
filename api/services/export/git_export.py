"""The portability export (ADR-328 D4, shipped by ADR-510): Category 1 → git.

ADR-209 adopted git's data model natively in Postgres — `workspace_blobs` IS a
content-addressed object store, `workspace_file_versions` IS a parent-pointered
commit chain. ADR-208 (WITHDRAWN) settled that the STORE stays Postgres; ADR-328
D4 settled that git is the EXPORT FORMAT — the falsifiability artifact under
THESIS Commitment 4 ("the workspace is a sovereign, portable artifact"). This
module is that artifact: it reads the two tables and emits a plain git
repository — a directory of files plus the full attributed history, readable by
any tool that speaks git or POSIX. No `git` binary, no dependency: loose
objects are zlib + sha1, written directly.

THE BINDING DISCIPLINE (ADR-328 D8): **the export declares what it omits.**
Silent omission would make "portable" a lie. `build_workspace_export` returns a
manifest naming every omission class — reconstructable caches, sidecar
descriptors, legacy raw-lane binaries whose bytes never entered Category 1,
paths outside the caller's read grant — and the route writes it BESIDE the
repo, never buried inside it.

Commit mapping (the revision chain → one linear history):
  - every `workspace_file_versions` row, ordered `created_at` (id tiebreak),
    becomes one commit touching its one path;
  - `authored_by` → author name; the identity uuid → author email local-part;
  - `message` → commit message; `created_at` → author/commit date;
  - a final RECONCILE commit prunes paths whose head row no longer exists
    (hard-deleted files stay in history — that is the point — but leave the
    final tree).
"""

from __future__ import annotations

import hashlib
import logging
import re
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

#: sha256 of empty input — the substrate's record of "no bytes here".
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

_PAGE = 1000


# ─────────────────────────────────────────────────────────────────────────────
# The git object layer — loose objects, pure Python
# ─────────────────────────────────────────────────────────────────────────────

class GitRepo:
    """A minimal loose-object git repository writer.

    Writes valid blobs/trees/commits + HEAD/refs/index/worktree. Verified by
    `git fsck` in the ADR-510 gate whenever a git binary is present; the gate
    also re-parses the objects with an independent reader, so correctness never
    rests on grep or on git's availability.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.git_dir = self.root / ".git"
        (self.git_dir / "objects").mkdir(parents=True, exist_ok=True)
        (self.git_dir / "refs" / "heads").mkdir(parents=True, exist_ok=True)

    # ── objects ──────────────────────────────────────────────────────────
    def _put_object(self, kind: str, payload: bytes) -> str:
        raw = f"{kind} {len(payload)}\0".encode() + payload
        sha = hashlib.sha1(raw).hexdigest()
        obj = self.git_dir / "objects" / sha[:2] / sha[2:]
        if not obj.exists():
            obj.parent.mkdir(parents=True, exist_ok=True)
            obj.write_bytes(zlib.compress(raw))
        return sha

    def put_blob(self, data: bytes) -> str:
        return self._put_object("blob", data)

    def put_tree_from_state(self, state: dict) -> str:
        """state: repo-relative path → blob sha1. Builds nested trees."""
        return self._put_dir(self._nest(state))

    def _nest(self, state: dict) -> dict:
        nested: dict = {}
        for path, sha in state.items():
            parts = [p for p in path.split("/") if p]
            node = nested
            for part in parts[:-1]:
                node = node.setdefault(part, {})
                if not isinstance(node, dict):  # a file where a dir is needed
                    raise ValueError(f"path conflict at {part} in {path}")
            node[parts[-1]] = sha
        return nested

    def _put_dir(self, node: dict) -> str:
        entries = []
        for name, val in node.items():
            if isinstance(val, dict):
                entries.append((name + "/", b"40000 " + name.encode() + b"\0"
                                + bytes.fromhex(self._put_dir(val))))
            else:
                entries.append((name, b"100644 " + name.encode() + b"\0"
                                + bytes.fromhex(val)))
        # git tree order: byte-sort by name, directories AS IF suffixed "/".
        entries.sort(key=lambda e: e[0].encode())
        return self._put_object("tree", b"".join(e[1] for e in entries))

    def put_commit(
        self,
        tree_sha: str,
        parent: Optional[str],
        *,
        author: str,
        email: str,
        epoch: int,
        message: str,
    ) -> str:
        author = re.sub(r"[<>\n]", "", author).strip() or "substrate"
        email = re.sub(r"[<>\n\s]", "", email) or "substrate@yarnnn.export"
        when = f"{epoch} +0000"
        lines = [f"tree {tree_sha}"]
        if parent:
            lines.append(f"parent {parent}")
        lines.append(f"author {author} <{email}> {when}")
        lines.append(f"committer {author} <{email}> {when}")
        payload = ("\n".join(lines) + "\n\n" + (message.strip() or "(no message)") + "\n").encode()
        return self._put_object("commit", payload)

    # ── refs + worktree + index ──────────────────────────────────────────
    def finalize(self, head_commit: str, final_files: dict) -> None:
        """final_files: repo-relative path → bytes. Writes HEAD/refs/config,
        checks out the worktree, and writes a v2 index so `git status` is
        clean on arrival."""
        (self.git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        (self.git_dir / "refs" / "heads" / "main").write_text(head_commit + "\n")
        (self.git_dir / "config").write_text(
            "[core]\n\trepositoryformatversion = 0\n\tfilemode = true\n\tbare = false\n"
        )
        for rel, data in final_files.items():
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        self._write_index(final_files)

    def _write_index(self, final_files: dict) -> None:
        entries = b""
        for rel in sorted(final_files, key=lambda p: p.encode()):
            data = final_files[rel]
            sha = hashlib.sha1(f"blob {len(data)}\0".encode() + data).digest()
            name = rel.encode()
            fixed = struct.pack(
                ">10I", 0, 0, 0, 0, 0, 0, 0o100644, 0, 0, len(data)
            ) + sha + struct.pack(">H", min(len(name), 0xFFF))
            entry = fixed + name
            pad = 8 - ((len(entry)) % 8)  # ≥1 NUL, total multiple of 8
            entries += entry + b"\0" * pad
        body = b"DIRC" + struct.pack(">II", 2, len(final_files)) + entries
        (self.git_dir / "index").write_bytes(body + hashlib.sha1(body).digest())


# ─────────────────────────────────────────────────────────────────────────────
# The substrate walk
# ─────────────────────────────────────────────────────────────────────────────

def _repo_rel(path: str) -> Optional[str]:
    """`/workspace/a/b.md` → `a/b.md`. None for a path the repo cannot hold.

    ADR-588 D1: the trailing-slash rejection also excludes every FOLDER MARKER
    from the export, and must stay. A marker is a directory row; git has no
    entry for an empty directory, and writing one as a zero-byte blob named
    `acme` would COLLIDE with the real tree entry `acme/` whenever the folder
    also holds files. Do not "fix" this by stripping the slash.
    """
    rel = (path or "").lstrip("/")
    if rel.startswith("workspace/"):
        rel = rel[len("workspace/"):]
    if not rel or ".." in rel.split("/") or rel.endswith("/"):
        return None
    return rel


#: Postgres renders `timestamptz` with trailing fractional zeros trimmed
#: ("…39.40728+00"), but Python 3.9's `fromisoformat` accepts ONLY 3 or 6
#: fractional digits. The API runs 3.9, so ~10% of real revisions raised here
#: and fell to epoch 0 — dating those commits 1970-01-01 in the export while
#: the ledger held the true time. Silent, and invisible until you read `git
#: log`. Normalize the fraction to 6 digits before parsing.
_FRACTION = re.compile(r"\.(\d{1,6})(?=[+-]|$)")
#: …and Postgres writes a 2-digit offset ("+00"), which 3.9 also rejects.
_SHORT_OFFSET = re.compile(r"([+-]\d{2})$")


def _epoch(created_at: str) -> int:
    raw = (created_at or "").strip().replace("Z", "+00:00").replace(" ", "T")
    raw = _FRACTION.sub(lambda m: "." + m.group(1).ljust(6, "0"), raw)
    raw = _SHORT_OFFSET.sub(lambda m: m.group(1) + ":00", raw)
    try:
        ts = datetime.fromisoformat(raw)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return int(ts.timestamp())
    except Exception:  # noqa: BLE001 — a malformed date must not sink the export
        return 0


def _page_all(query_fn) -> list:
    rows: list = []
    start = 0
    while True:
        page = query_fn(start, start + _PAGE - 1)
        rows.extend(page)
        if len(page) < _PAGE:
            return rows
        start += _PAGE


def build_workspace_export(
    db_client: Any,
    service_client: Any,
    *,
    user_id: str,
    workspace_id: Optional[str],
    out_dir: Path,
    readable: Optional[Callable[[str], bool]] = None,
) -> dict:
    """Emit the Category-1 git repository at `out_dir` and return the manifest.

    `db_client` is the CALLER's client (RLS-scoped — a member exports what the
    commons lets them read); `service_client` only fetches CAS bytes for blobs
    the row walk already authorized. `readable` is the powerbox read-scope
    predicate — a narrowed principal's export omits ungranted paths and the
    manifest declares the count (never the names).
    """
    from services.storage_backend import get_storage_backend
    from services.workspace_context import substrate_scope_filter

    scope_col, scope_val = substrate_scope_filter(user_id, workspace_id)

    def _versions(lo: int, hi: int) -> list:
        return (
            db_client.table("workspace_file_versions")
            .select(
                "id, path, blob_sha, authored_by, author_identity_uuid, "
                "message, created_at, revision_kind, "
                "workspace_blobs(content, storage_key, byte_size)"
            )
            .eq(scope_col, scope_val)
            .order("created_at", desc=False)
            .order("id", desc=False)
            .range(lo, hi)
            .execute()
        ).data or []

    def _heads(lo: int, hi: int) -> list:
        return (
            db_client.table("workspace_files")
            .select("path, lifecycle, content_url, head_version_id")
            .eq(scope_col, scope_val)
            .range(lo, hi)
            .execute()
        ).data or []

    versions = _page_all(_versions)
    heads = _page_all(_heads)

    repo = GitRepo(out_dir)
    backend = get_storage_backend(service_client)

    state: dict = {}          # repo-relative path → blob sha1
    bytes_by_sha1: dict = {}  # blob sha1 → bytes (for worktree + index)
    parent: Optional[str] = None
    commits = 0
    omitted_unreadable = 0
    binary_included: list = []
    cas_read_failures: list = []

    for row in versions:
        rel = _repo_rel(row.get("path") or "")
        if rel is None:
            continue
        if readable is not None and not readable(row["path"]):
            omitted_unreadable += 1
            continue
        blob = row.get("workspace_blobs") or {}
        if not isinstance(blob, dict):
            blob = {}
        if blob.get("storage_key"):
            try:
                data = b"".join(
                    backend.open_read_stream(row["blob_sha"], workspace_id=workspace_id)
                )
                if rel not in binary_included:
                    binary_included.append(rel)
            except Exception as exc:  # noqa: BLE001 — DECLARED, never silent
                logger.warning("[EXPORT] CAS read failed for %s: %s", rel, exc)
                cas_read_failures.append(rel)
                continue
        else:
            data = (blob.get("content") or "").encode("utf-8")

        sha1 = repo.put_blob(data)
        bytes_by_sha1[sha1] = data
        state[rel] = sha1

        identity = (row.get("author_identity_uuid") or "substrate").strip()
        parent = repo.put_commit(
            repo.put_tree_from_state(state),
            parent,
            author=row.get("authored_by") or "substrate",
            email=f"{identity}@yarnnn.export",
            epoch=_epoch(row.get("created_at") or ""),
            message=row.get("message") or "",
        )
        commits += 1

    # ── the reconcile commit: history keeps deleted files, the tree doesn't ─
    live = {
        _repo_rel(h.get("path") or "")
        for h in heads
        if _repo_rel(h.get("path") or "") is not None
        and (readable is None or readable(h["path"]))
    }
    pruned = sorted(p for p in state if p not in live)
    if pruned and parent is not None:
        for p in pruned:
            state.pop(p)
        parent = repo.put_commit(
            repo.put_tree_from_state(state),
            parent,
            author="substrate",
            email="substrate@yarnnn.export",
            epoch=max((_epoch(r.get("created_at") or "") for r in versions), default=0),
            message=(
                "yarnnn export: reconcile to the live tree\n\n"
                "Paths whose file no longer exists leave the final tree; their "
                "full history remains in the commits above:\n"
                + "\n".join(f"  - {p}" for p in pruned)
            ),
        )
        commits += 1

    if parent is None:
        # An empty workspace still exports honestly: one empty commit.
        parent = repo.put_commit(
            repo.put_tree_from_state({}), None,
            author="substrate", email="substrate@yarnnn.export",
            epoch=0, message="yarnnn export: empty workspace",
        )
        commits = 1

    repo.finalize(parent, {p: bytes_by_sha1[s] for p, s in state.items()})

    # ── the declared omissions (ADR-328 D8's binding discipline) ────────────
    version_by_id = {r.get("id"): r for r in versions}
    legacy_binaries = sorted(
        _repo_rel(h["path"]) or h["path"]
        for h in heads
        if h.get("content_url")
        and (
            (version_by_id.get(h.get("head_version_id")) or {}).get("blob_sha")
            in (EMPTY_SHA256, None)
        )
    )

    return {
        "files": len(state),
        "revisions": len(versions),
        "commits": commits,
        "binaries_included": sorted(binary_included),
        "legacy_raw_lane_binaries": legacy_binaries,
        "cas_read_failures": sorted(cas_read_failures),
        "omitted_unreadable_paths": omitted_unreadable,
    }


def manifest_markdown(m: dict, *, workspace_id: Optional[str], generated_at: str) -> str:
    """The declared-omissions manifest (ADR-328 D8): what traveled, what did
    not, and why — written BESIDE the repo at the zip root."""
    legacy = m.get("legacy_raw_lane_binaries") or []
    failures = m.get("cas_read_failures") or []
    omitted = m.get("omitted_unreadable_paths") or 0
    lines = [
        "# YARNNN workspace export",
        "",
        f"Generated: {generated_at} · workspace: {workspace_id or '(owner-scoped)'}",
        "",
        "`workspace/` is a plain **git repository**: the authored filesystem as its",
        "working tree, and the full attributed revision history as the commit chain",
        "(`git log` shows who wrote every change, when, and why). This is Category 1",
        "of ADR-328 — the substrate's authoritative, portable layer.",
        "",
        f"- files in the tree: **{m.get('files', 0)}**",
        f"- revisions exported as commits: **{m.get('revisions', 0)}** (+ reconcile commits: {m.get('commits', 0) - m.get('revisions', 0)})",
        f"- binary files included from the substrate CAS: **{len(m.get('binaries_included') or [])}**",
        "",
        "## Declared omissions",
        "",
        "An export that omits silently makes \"portable\" a lie (ADR-328 D8), so",
        "everything this archive does NOT carry is named here:",
        "",
        "1. **Reconstructable caches** (ADR-328 Category 2) — embeddings, search",
        "   indices, denormalized sizes/pointers. Omitted by design: every byte",
        "   rebuilds from what IS here.",
        "2. **Head-row sidecar descriptors** (Category 3) — `summary`, `tags`,",
        "   `lifecycle`, `content_type`, `metadata`. Operational descriptors, not",
        "   authored truth; not retained in the revision chain.",
        "3. **Non-substrate state** — conversations, execution events, grants,",
        "   schedules. Runtime records of the host, not the authored filesystem.",
    ]
    n = 4
    if legacy:
        lines += [
            f"{n}. **Legacy raw-lane binaries** ({len(legacy)}) — files whose bytes were",
            "   uploaded before the substrate's binary lane existed (ADR-427) and still",
            "   live only in hosted storage. Their paths are in the tree as empty",
            "   placeholders with history; their bytes did not travel:",
        ] + [f"   - `{p}`" for p in legacy]
        n += 1
    if failures:
        lines += [
            f"{n}. **CAS read failures** ({len(failures)}) — binary bytes the export",
            "   could not fetch at generation time (retry the export):",
        ] + [f"   - `{p}`" for p in failures]
        n += 1
    if omitted:
        lines += [
            f"{n}. **Paths outside your read grant** — {omitted} revision(s) were",
            "   omitted because this export was generated under a narrowed read",
            "   scope. Ask the workspace owner for a full export.",
        ]
    lines.append("")
    return "\n".join(lines)
