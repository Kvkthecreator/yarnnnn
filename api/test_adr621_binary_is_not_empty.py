"""ADR-621 — a binary file is not an empty file, and a text save cannot replace it.

THE DEFECT (measured live, 2026-08-31, before the fix):

    compose_open("marketing/assets/chatgpt-image-aug-20-2026-…png")
      → success: true, found: true, content: "", content_chars: 0,
        stored_chars: 0, complete_for_write: TRUE

The file holds 902,508 bytes in the CAS (`cas/38/38e0a34e…`, content_type
image/png). Every machine-readable field said "empty file", and the word
"binary" appeared nowhere in the 1,840-line interop composition layer. 32 live
binary files answered this way — the ADR-373 D6 incorrect-success class.

`complete_for_write: true` made it a DATA-LOSS door, not just a bad read: it is
the signature a caller uses for "I hold the whole file", so a caller following
the documented read-before-write contract exactly would `save` the empty string
back over a binary head. The ADR-545 D4 size guard could not stop it (it reads
`content_bytes`, which is 0 for a CAS head), and the elision guard keys on a
marker only artifacts carry.

WHAT IS GATED HERE
  1. `resolve_binary_head` discriminates on `storage_key`, not on empty content
     (a genuinely empty TEXT file must stay a genuinely empty text file).
  2. `compose_open` answers binary with found:true + binary:true + type + size
     + complete_for_write:FALSE, and never `content: ""`.
  3. `compose_save` REFUSES a binary head, and `confirm_full_replace` cannot
     override it (intent cannot confirm an impossibility).
  4. `compose_list` marks binary rows and reports the blob's true size.
  5. The ADR-427 §8 reader classification records mcp_composition as
     binary-aware — the misclassification that let this ship.

Falsified against the pre-fix code: assertions 2, 3, 4 all fail (2 on
complete_for_write + the absent `binary` key, 3 because the save returns
success, 4 on bytes==0).

Usage:  cd api && python3 test_adr621_binary_is_not_empty.py
"""

from __future__ import annotations

import asyncio
import inspect
import re
import sys
from pathlib import Path

API_ROOT = Path(__file__).parent
sys.path.insert(0, str(API_ROOT))

FAILURES: list[str] = []
PASSES = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global PASSES
    if ok:
        PASSES += 1
        print(f"PASS  {label}  {detail}")
    else:
        FAILURES.append(label)
        print(f"FAIL  {label}  {detail}")


# ---------------------------------------------------------------------------
# A fake substrate: one binary file, one text file, one EMPTY text file.
# The empty text file is the falsifier for a lazy `content == ''` test — it must
# NOT be reported as binary.
# ---------------------------------------------------------------------------

BIN_PATH = "/workspace/operation/photo.png"
TXT_PATH = "/workspace/operation/notes.md"
EMPTY_PATH = "/workspace/operation/blank.md"

_FILES = {
    BIN_PATH: {"path": BIN_PATH, "content": "", "content_type": "image/png",
               "content_bytes": 0, "updated_at": "2026-08-31T00:00:00Z",
               "head_version_id": "rev-bin"},
    TXT_PATH: {"path": TXT_PATH, "content": "# real text", "content_type": "text/markdown",
               "content_bytes": 11, "updated_at": "2026-08-31T00:00:00Z",
               "head_version_id": "rev-txt"},
    EMPTY_PATH: {"path": EMPTY_PATH, "content": "", "content_type": "text/markdown",
                 "content_bytes": 0, "updated_at": "2026-08-31T00:00:00Z",
                 "head_version_id": "rev-empty"},
}
_VERSIONS = {
    # storage_key present == the CAS binary lane. byte_size is the TRUE size.
    "rev-bin": {"id": "rev-bin", "blob_sha": "deadbeef", "path": BIN_PATH,
                "created_at": "2026-08-31T00:00:00Z", "authored_by": "operator",
                "message": "upload", "workspace_blobs": {"storage_key": "cas/de/deadbeef",
                                                         "byte_size": 902508}},
    # storage_key NULL == the inline text lane, even though content is ''.
    "rev-txt": {"id": "rev-txt", "blob_sha": "aaa", "path": TXT_PATH,
                "created_at": "2026-08-31T00:00:00Z", "authored_by": "operator",
                "message": "write", "workspace_blobs": {"storage_key": None, "byte_size": 11}},
    "rev-empty": {"id": "rev-empty", "blob_sha": "bbb", "path": EMPTY_PATH,
                  "created_at": "2026-08-31T00:00:00Z", "authored_by": "operator",
                  "message": "write", "workspace_blobs": {"storage_key": None, "byte_size": 0}},
}


class _Q:
    def __init__(self, table): self.table, self.filters, self.cols = table, {}, ""
    def select(self, cols, *a, **k): self.cols = cols; return self
    def eq(self, col, val): self.filters[col] = val; return self
    def like(self, col, val): self.filters["_like"] = val; return self
    def in_(self, col, vals): return self
    def or_(self, *a, **k): return self
    def is_(self, *a, **k): return self
    def neq(self, *a, **k): return self
    def gte(self, *a, **k): return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def range(self, *a, **k): return self

    def execute(self):
        class R:
            pass
        r = R()
        if self.table == "workspace_files":
            if "path" in self.filters:
                row = _FILES.get(self.filters["path"])
                r.data = [dict(row)] if row else []
            elif "_like" in self.filters:
                pre = self.filters["_like"].rstrip("%")
                r.data = [
                    {**f, "workspace_file_versions": _VERSIONS[f["head_version_id"]]}
                    for p, f in _FILES.items() if p.startswith(pre)
                ]
            else:
                r.data = []
        elif self.table == "workspace_file_versions":
            if "id" in self.filters:
                v = _VERSIONS.get(self.filters["id"])
                r.data = [dict(v)] if v else []
            elif "path" in self.filters:
                f = _FILES.get(self.filters["path"])
                r.data = [dict(_VERSIONS[f["head_version_id"]])] if f else []
            else:
                r.data = []
        else:
            r.data = []
        return r


class _Client:
    def table(self, name): return _Q(name)


class _Auth:
    client = _Client()
    user_id = "u-1"
    workspace_id = "w-1"
    caller = "mcp"
    scopes = ["files:read", "files:write"]


import services.mcp_composition as m  # noqa: E402

# Neutralize the network-touching mint + the revision-summary primitive; this
# gate is about the ENVELOPE's honesty, not about the storage driver.
m.mint_binary_url = lambda auth, sha: "https://example.test/cas/deadbeef?sig=x"


async def _no_primitive(auth, name, payload):
    return {"revisions": []}


m.__dict__.setdefault("_orig_exec", None)


def _patch_primitive():
    import services.primitives.registry as reg
    reg.execute_primitive = _no_primitive


_patch_primitive()

auth = _Auth()

# ⚠️ A GATE THAT CRASHES ON THE DEFECT IT GUARDS HIDES EVERY ASSERTION AFTER IT.
# Pre-fix, `resolve_binary_head` did not exist, so importing it raised
# AttributeError and this file exited with a stack trace and ZERO reported
# failures — which reads like a broken test, not like a caught defect. Name the
# absence as the first failure and let the rest of the suite still run against
# whatever IS there.
_missing = [n for n in ("resolve_binary_head", "mint_binary_url") if not hasattr(m, n)]
check("0 the binary seam exists in mcp_composition", not _missing,
      f"absent: {_missing}" if _missing else "")
if _missing:
    print("\n  → the seam is absent; the remaining assertions cannot be evaluated.")
    print("=" * 62)
    print(f"ADR-621: FAIL — {len(FAILURES)} assertion(s): {FAILURES}")
    sys.exit(1)

# --- 1. the discriminator -----------------------------------------------------
b = m.resolve_binary_head(auth, BIN_PATH)
check("1a binary head resolves via storage_key",
      bool(b) and b["content_type"] == "image/png" and b["byte_size"] == 902508,
      f"{b}")
check("1b a TEXT head is not binary", m.resolve_binary_head(auth, TXT_PATH) is None)
# ⭐ The falsifier that matters: an EMPTY text file has content == '' exactly like
# a binary head does. Discriminating on emptiness would call this binary.
check("1c an EMPTY TEXT file is NOT binary (content=='' is not the test)",
      m.resolve_binary_head(auth, EMPTY_PATH) is None)

# --- 2. open ------------------------------------------------------------------
o = asyncio.get_event_loop().run_until_complete(m.compose_open(auth, "operation/photo.png"))
check("2a open reports found:true (the file EXISTS and is addressable)",
      o.get("success") is True and o.get("found") is True)
check("2b open marks it binary with type + true size",
      o.get("binary") is True and o.get("content_type") == "image/png"
      and o.get("byte_size") == 902508)
check("2c content is None, never '' (an empty string reads as an empty file)",
      o.get("content") is None)
# The load-bearing one.
check("2d complete_for_write is FALSE (the data-loss signature)",
      o.get("complete_for_write") is False)
check("2e the explanation says it is NOT empty, in words",
      "not an empty file" in (o.get("explanation") or "").lower())
check("2f a serving URL rides the answer", bool(o.get("content_url")))

ot = asyncio.get_event_loop().run_until_complete(m.compose_open(auth, "operation/notes.md"))
check("2g a TEXT read is unchanged (no binary key, real content)",
      ot.get("binary") is None and ot.get("content") == "# real text"
      and ot.get("complete_for_write") is True)

# --- 3. save ------------------------------------------------------------------
s = asyncio.get_event_loop().run_until_complete(
    m.compose_save(auth, "operation/photo.png", "# text over bytes", base_revision="rev-bin"))
check("3a save REFUSES a binary head",
      s.get("success") is False and s.get("error") == "binary_file_not_writable",
      f"error={s.get('error')}")
check("3b the refusal names the type and the size",
      "image/png" in (s.get("message") or "") and "902,508" in (s.get("message") or ""))
s2 = asyncio.get_event_loop().run_until_complete(
    m.compose_save(auth, "operation/photo.png", "# forced", base_revision="rev-bin",
                   confirm_full_replace=True))
check("3c confirm_full_replace CANNOT override it",
      s2.get("success") is False and s2.get("error") == "binary_file_not_writable")

# --- 4. list ------------------------------------------------------------------
lst = asyncio.get_event_loop().run_until_complete(m.compose_list(auth, "operation"))
by_path = {f["path"]: f for f in (lst.get("files") or [])}
png = by_path.get("operation/photo.png") or {}
check("4a list marks the binary row", png.get("binary") is True, f"{png}")
check("4b list reports the BLOB's size, not the empty denorm's 0",
      png.get("bytes") == 902508, f"bytes={png.get('bytes')}")
md = by_path.get("operation/notes.md") or {}
check("4c a text row carries no binary key and keeps its own size",
      md.get("binary") is None and md.get("bytes") == 11)

# --- 5. the classification that let this ship ---------------------------------
ratchet = (API_ROOT / "test_adr427_reader_classification.py").read_text()
mm = re.search(r'"services/mcp_composition\.py":\s*"([a-z-]+)"', ratchet)
check("5a mcp_composition is classified binary-aware (was: safe-on-empty)",
      bool(mm) and mm.group(1) == "binary-aware",
      f"classified={mm.group(1) if mm else 'ABSENT'}")

# The two doors must share ONE resolver — two readers of one fact drift.
src = inspect.getsource(m)
check("5b both open and save go through resolve_binary_head",
      src.count("resolve_binary_head(") >= 3,
      f"call sites+def={src.count('resolve_binary_head(')}")

print()
print("=" * 62)
if FAILURES:
    print(f"ADR-621: FAIL — {len(FAILURES)} assertion(s): {FAILURES}")
    sys.exit(1)
print(f"ADR-621 binary-is-not-empty: {PASSES}/{PASSES} assertions pass")
