"""
ADR-510 — the portability export: Category 1 leaves as a VALID git repository.

Executable gate, pure-Python (no DB). Run directly:
`python test_adr510_git_export.py`.

The export is ADR-328 D4's falsifiability artifact — so this gate does not
trust the writer's own vocabulary: it re-parses the emitted loose objects with
an INDEPENDENT reader (zlib + manual tree/commit decode), walks the commit
chain from refs/heads/main, and checks the worktree bytes. When a `git` binary
is present it additionally runs `git fsck --strict`, `git log`, and
`git status --porcelain` (which must be EMPTY — the index must agree with the
worktree on arrival).

Also gates ADR-328 D8's binding discipline: the manifest DECLARES the legacy
raw-lane binary (bytes never entered Category 1) and the narrowed-grant
omission count — silent omission is the failure this export exists to refuse.
"""

import hashlib
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path
from types import SimpleNamespace

from services.export.git_export import (
    EMPTY_SHA256,
    build_workspace_export,
    manifest_markdown,
)


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


# ── the fixture substrate ────────────────────────────────────────────────────

_PNG = b"\x89PNG\r\n\x1a\n" + bytes(range(256))
_BIN_SHA = hashlib.sha256(_PNG).hexdigest()

_VERSIONS = [
    {
        "id": "v1", "path": "/workspace/notes/a.md", "blob_sha": "t1" * 32,
        "authored_by": "operator", "author_identity_uuid": "kvk-uuid",
        "message": "first note", "created_at": "2026-07-01T10:00:00+00:00",
        "revision_kind": "authored",
        "workspace_blobs": {"content": "hello", "storage_key": None, "byte_size": None},
    },
    {
        "id": "v2", "path": "/workspace/notes/a.md", "blob_sha": "t2" * 32,
        "authored_by": "operator", "author_identity_uuid": "kvk-uuid",
        "message": "second thoughts", "created_at": "2026-07-02T10:00:00+00:00",
        "revision_kind": "authored",
        "workspace_blobs": {"content": "hello world", "storage_key": None, "byte_size": None},
    },
    {
        "id": "v3", "path": "/workspace/assets/logo.png", "blob_sha": _BIN_SHA,
        "authored_by": "operator", "author_identity_uuid": "kvk-uuid",
        "message": "the logo (binary)", "created_at": "2026-07-03T10:00:00+00:00",
        "revision_kind": "observation",
        "workspace_blobs": {"content": "", "storage_key": f"cas/{_BIN_SHA[:2]}/{_BIN_SHA}", "byte_size": len(_PNG)},
    },
    {
        "id": "v4", "path": "/workspace/tmp/x.md", "blob_sha": "t4" * 32,
        "authored_by": "freddie:claude", "author_identity_uuid": None,
        "message": "scratch, later deleted", "created_at": "2026-07-04T10:00:00+00:00",
        "revision_kind": "authored",
        "workspace_blobs": {"content": "gone", "storage_key": None, "byte_size": None},
    },
    {
        "id": "v5", "path": "/workspace/uploads/legacy.pdf", "blob_sha": EMPTY_SHA256,
        "authored_by": "operator", "author_identity_uuid": "kvk-uuid",
        "message": "legacy raw upload (bytes in bucket only)",
        "created_at": "2026-07-05T10:00:00+00:00", "revision_kind": "observation",
        "workspace_blobs": {"content": "", "storage_key": None, "byte_size": None},
    },
]

_HEADS = [
    {"path": "/workspace/notes/a.md", "lifecycle": "active", "content_url": None, "head_version_id": "v2"},
    {"path": "/workspace/assets/logo.png", "lifecycle": "active", "content_url": None, "head_version_id": "v3"},
    {"path": "/workspace/uploads/legacy.pdf", "lifecycle": "active",
     "content_url": "/api/documents/blob?storage_path=u/legacy.pdf", "head_version_id": "v5"},
    # tmp/x.md has NO head row — hard-deleted; the reconcile commit prunes it.
]


class _Q:
    def __init__(self, rows):
        self._rows, self._lo, self._hi = rows, 0, len(rows) - 1

    def select(self, *a, **k): return self
    def eq(self, *a): return self
    def order(self, *a, **k): return self

    def range(self, lo, hi):
        self._lo, self._hi = lo, hi
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows[self._lo:self._hi + 1])


class _DB:
    def __init__(self):
        self._map = {"workspace_file_versions": _VERSIONS, "workspace_files": _HEADS}

    def table(self, name):
        return _Q(list(self._map[name]))


class _Backend:
    def open_read_stream(self, sha, byte_range=None, *, workspace_id=None):
        if sha != _BIN_SHA:
            raise KeyError(sha)
        yield _PNG


# ── an INDEPENDENT loose-object reader ───────────────────────────────────────

def _read_obj(git_dir: Path, sha: str):
    raw = zlib.decompress((git_dir / "objects" / sha[:2] / sha[2:]).read_bytes())
    header, _, body = raw.partition(b"\0")
    kind, size = header.decode().split(" ")
    assert int(size) == len(body), f"size lies in {sha}"
    assert hashlib.sha1(raw).hexdigest() == sha, f"sha lies for {sha}"
    return kind, body


def _parse_commit(body: bytes):
    head, _, message = body.partition(b"\n\n")
    fields = {"parent": []}
    for line in head.decode().splitlines():
        key, _, val = line.partition(" ")
        if key == "parent":
            fields["parent"].append(val)
        else:
            fields[key] = val
    return fields, message.decode()

def _walk_tree(git_dir: Path, sha: str, prefix=""):
    kind, body = _read_obj(git_dir, sha)
    assert kind == "tree"
    out = {}
    i = 0
    while i < len(body):
        j = body.index(b"\0", i)
        mode, name = body[i:j].decode().split(" ", 1)
        entry_sha = body[j + 1:j + 21].hex()
        i = j + 21
        if mode == "40000":
            out.update(_walk_tree(git_dir, entry_sha, f"{prefix}{name}/"))
        else:
            out[f"{prefix}{name}"] = entry_sha
    return out


def run() -> int:
    passed = True
    tmp = Path(tempfile.mkdtemp(prefix="adr510-gate-"))
    try:
        import services.export.git_export as ge
        import services.storage_backend as sb
        import services.workspace_context as wc

        orig_backend, orig_scope = sb.get_storage_backend, wc.substrate_scope_filter
        sb.get_storage_backend = lambda client: _Backend()
        wc.substrate_scope_filter = lambda user_id, workspace_id=None: ("workspace_id", "ws-1")
        try:
            repo_dir = tmp / "workspace"
            manifest = build_workspace_export(
                _DB(), object(), user_id="u1", workspace_id="ws-1", out_dir=repo_dir,
            )
            narrow_dir = tmp / "narrow"
            narrowed = build_workspace_export(
                _DB(), object(), user_id="u1", workspace_id="ws-1", out_dir=narrow_dir,
                readable=lambda p: not p.startswith("/workspace/notes/"),
            )
        finally:
            sb.get_storage_backend, wc.substrate_scope_filter = orig_backend, orig_scope

        git_dir = repo_dir / ".git"
        head_sha = (git_dir / "refs" / "heads" / "main").read_text().strip()

        # ── independent re-parse: the chain ──────────────────────────────
        chain = []
        cursor = head_sha
        while cursor:
            kind, body = _read_obj(git_dir, cursor)
            assert kind == "commit"
            fields, message = _parse_commit(body)
            chain.append((cursor, fields, message))
            cursor = fields["parent"][0] if fields["parent"] else None

        passed &= _check(
            "the chain is 5 revisions + 1 reconcile, root-first attribution intact",
            len(chain) == 6
            and chain[-1][1]["author"].startswith("operator <kvk-uuid@yarnnn.export>")
            and "first note" in chain[-1][2],
            f"commits: {len(chain)}",
        )
        passed &= _check(
            "the reconcile commit names the pruned path (history keeps it, the tree drops it)",
            "tmp/x.md" in chain[0][2] and "reconcile" in chain[0][2],
        )

        # ── the final tree + worktree bytes ──────────────────────────────
        tree = _walk_tree(git_dir, dict(_parse_commit(_read_obj(git_dir, head_sha)[1])[0])["tree"])
        passed &= _check(
            "final tree = live files only (deleted path pruned, legacy placeholder present)",
            sorted(tree) == ["assets/logo.png", "notes/a.md", "uploads/legacy.pdf"],
            f"tree: {sorted(tree)}",
        )
        blob_kind, blob_body = _read_obj(git_dir, tree["assets/logo.png"])
        passed &= _check(
            "the binary traveled byte-identical (CAS → git blob → worktree)",
            blob_kind == "blob" and blob_body == _PNG
            and (repo_dir / "assets" / "logo.png").read_bytes() == _PNG,
        )
        passed &= _check(
            "the text head is the LAST revision's content",
            (repo_dir / "notes" / "a.md").read_text() == "hello world",
        )

        # ── the index agrees with the worktree (v2 format sanity) ────────
        index = (git_dir / "index").read_bytes()
        sig, ver, count = index[:4], *struct.unpack(">II", index[4:12])
        passed &= _check(
            "index: DIRC v2, one entry per live file, valid trailing checksum",
            sig == b"DIRC" and ver == 2 and count == 3
            and hashlib.sha1(index[:-20]).digest() == index[-20:],
        )

        # ── D8: the declared omissions ────────────────────────────────────
        passed &= _check(
            "manifest declares the legacy raw-lane binary (bytes not in Category 1)",
            manifest["legacy_raw_lane_binaries"] == ["uploads/legacy.pdf"],
            f"legacy: {manifest['legacy_raw_lane_binaries']}",
        )
        md = manifest_markdown(manifest, workspace_id="ws-1", generated_at="2026-08-01T00:00:00")
        passed &= _check(
            "manifest markdown names the omission classes AND the legacy path",
            "Declared omissions" in md and "uploads/legacy.pdf" in md
            and "Reconstructable caches" in md,
        )
        passed &= _check(
            "a narrowed grant omits AND declares the count (never silently)",
            narrowed["omitted_unreadable_paths"] == 2
            and not (narrow_dir / "notes").exists(),
            f"omitted: {narrowed['omitted_unreadable_paths']}",
        )

        # ── the commit DATE survives every timestamp shape Postgres emits ──
        # Regression: py3.9's `fromisoformat` accepts ONLY 3 or 6 fractional
        # digits, while Postgres trims trailing zeros ("…39.40728+00") and
        # writes a 2-digit offset. Both raised, fell to epoch 0, and dated 168
        # of 1,613 real commits 1970-01-01 — a silent wrong answer that passed
        # every gate because nothing read the dates back.
        from services.export.git_export import _epoch

        shapes = {
            "2026-07-03 05:37:39.40728+00": 1783057059,   # 5-digit frac, short offset
            "2026-07-03T05:37:39.4+00:00": 1783057059,    # 1-digit frac
            "2026-08-12T00:45:24.554085+00:00": 1786495524,  # 6-digit (always worked)
            "2026-08-19T21:00:29+00:00": 1787173229,      # no frac
            "2026-08-19T21:00:29Z": 1787173229,           # Z form
        }
        bad = {k: _epoch(k) for k, v in shapes.items() if _epoch(k) != v}
        passed &= _check(
            "every timestamp shape Postgres emits dates its commit correctly",
            not bad,
            f"wrong: {bad}",
        )
        passed &= _check(
            "a malformed date still falls back to epoch 0 rather than sinking the export",
            _epoch("garbage") == 0 and _epoch("") == 0,
        )

        # ── the real git, when present (the strongest verifier) ──────────
        git = shutil.which("git")
        if git:
            fsck = subprocess.run([git, "-C", str(repo_dir), "fsck", "--strict"],
                                  capture_output=True, text=True)
            log = subprocess.run([git, "-C", str(repo_dir), "log", "--oneline"],
                                 capture_output=True, text=True)
            status = subprocess.run([git, "-C", str(repo_dir), "status", "--porcelain"],
                                    capture_output=True, text=True)
            passed &= _check("git fsck --strict is clean", fsck.returncode == 0, fsck.stderr.strip())
            passed &= _check(
                "git log sees the whole chain",
                log.returncode == 0 and len(log.stdout.strip().splitlines()) == 6,
            )
            passed &= _check(
                "git status is EMPTY on arrival (index agrees with worktree)",
                status.returncode == 0 and status.stdout.strip() == "",
                repr(status.stdout[:200]),
            )
        else:
            print("SKIP  git binary not present — loose-object re-parse stands alone")

        return 0 if passed else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(run())
