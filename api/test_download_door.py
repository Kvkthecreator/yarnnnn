"""The save door — a binary file can be downloaded, under its own name.

THE DEFECT THIS GUARDS (operator-observed, 2026-08-31).

Right-clicking a real PNG in Files offered NO Download entry at all, and the
browser's own "Save image as" produced an extensionless file no application
would open. Two symptoms, one seam — the content-addressed blob store:

  1. THE ENTRY DID NOT RENDER. The FE resolver built its download from
     `getFile().content_url` + `api.documents.blobUrl(...)`. A CAS-backed
     binary (ADR-427 D4) stores NO `content_url` — the capability is minted per
     read — so `getFile` returns an ABSOLUTE signed URL, while `blobUrl` parses
     only the legacy `documents`-bucket `?storage_path=` form and rejects
     anything else. The reject was caught, null was returned, and a null
     download means the menu entry does not render. Measured at the time:
     39 of 39 live binaries in production, silently undownloadable.

     This is the ADR-373 D6 incorrect-success shape. Nothing looks wrong on
     screen — there is simply no Download — so the operator concludes the
     product cannot save a file and stops asking.

  2. THE SAVED FILE HAD NO NAME. The bucket object is keyed by CONTENT ADDRESS
     (`cas/e7/e78c…`) and stored as `application/octet-stream`. Followed by a
     browser save, that URL names the file after the key: 64 hex characters, no
     extension, typed as unknown by the OS.

The fix is one server door (`GET /workspace/file/download`) that spans BOTH
content lanes, and — for a binary — mints the URL with the file's real name as
a `Content-Disposition: attachment`.

WHY THE VIEWING URL AND THE SAVING URL ARE DIFFERENT URLS, and why that is not
duplication: a viewer wants the bytes INLINE (an `<img src>` must not download),
a save wants them as an ATTACHMENT under a real name. Same object, two
dispositions. The distinction is the fix, so the gate asserts it explicitly —
were they collapsed back into one, symptom 2 returns.

Run: python3 api/test_download_door.py
"""

import ast
import inspect
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = os.path.join(REPO, "api")
WEB = os.path.join(REPO, "web")

failures = []
checks = 0


def check(label, cond, detail=""):
    global checks
    checks += 1
    if not cond:
        failures.append(f"{label}: {detail}" if detail else label)
        print(f"  FAIL  {label}" + (f" — {detail}" if detail else ""))
    else:
        print(f"  ok    {label}")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# 1. THE SEAM — the mint can be asked for a named attachment
# ---------------------------------------------------------------------------
print("\n[1] the seam: a serving URL can be minted as a named download")

from services import storage_backend as sb  # noqa: E402

for cls_label, fn in (
    ("StorageBackend (contract)", sb.StorageBackend.mint_serving_url),
    ("PostgresObjectStoreBackend", sb.PostgresObjectStoreBackend.mint_serving_url),
):
    params = inspect.signature(fn).parameters
    check(
        f"{cls_label}.mint_serving_url takes download_name",
        "download_name" in params,
        # The contract and the driver must BOTH carry it. A driver-only
        # parameter is unreachable through the abstract type the callers hold,
        # and a contract-only one silently does nothing.
        f"params={list(params)}",
    )
    if "download_name" in params:
        check(
            f"{cls_label}.mint_serving_url defaults download_name to None",
            params["download_name"].default is None,
            # The default IS the viewing URL. If minting a download became the
            # default, every `<img src>` in the app would start downloading
            # instead of rendering.
            f"default={params['download_name'].default!r}",
        )

src = inspect.getsource(sb.PostgresObjectStoreBackend.mint_serving_url)
check(
    "the driver passes download_name through to create_signed_url",
    re.search(r'create_signed_url\((?:.|\n)*?"download":\s*download_name', src) is not None,
    # A parameter accepted and dropped is the worst shape: the caller believes
    # it asked for an attachment and gets an inline content-address URL.
    "download_name is accepted but never reaches the signing call",
)
check(
    "a mint with no download_name signs the plain (inline) URL",
    "if download_name else None" in src,
    "the no-name case must not send a download option at all",
)

path_fn = sb.mint_serving_url_for_path
path_params = inspect.signature(path_fn).parameters
check(
    "mint_serving_url_for_path takes as_download",
    "as_download" in path_params,
    # This resolver is the one layer holding BOTH the path (hence the name and
    # extension) and the sha (hence the bytes). Below it there is only a
    # content address; above it the caller would re-derive a name it already
    # handed in.
    f"params={list(path_params)}",
)
check(
    "as_download defaults False (every existing caller is a VIEWER)",
    path_params.get("as_download") is not None
    and path_params["as_download"].default is False,
    "ADR-623 lane vision, the attachment door and interop `open` all want inline",
)

path_src = inspect.getsource(path_fn)
check(
    "the download name is taken from the PATH, not a caller-supplied string",
    re.search(r'abs_path\.rsplit\("/", 1\)\[-1\]\s+if\s+as_download', path_src) is not None,
    # The path is the substrate's own answer to "what is this file called",
    # so the saved name cannot drift from the file's identity.
    "the saved name must derive from the substrate path",
)


# ---------------------------------------------------------------------------
# 2. THE DOOR — one endpoint, both content lanes
# ---------------------------------------------------------------------------
print("\n[2] the door: GET /workspace/file/download spans both lanes")

from routes.workspace import router as ws_router  # noqa: E402

routes = {
    (tuple(sorted(r.methods)), r.path)
    for r in ws_router.routes
    if hasattr(r, "methods") and hasattr(r, "path")
}
check(
    "GET /workspace/file/download is registered",
    (("GET",), "/workspace/file/download") in routes,
    f"registered file routes: {sorted(p for _, p in routes if '/file' in p)}",
)

# The literal sibling routes must not shadow each other. `/workspace/file` is a
# literal path, not a `{param}` catch-all, so it cannot — but assert it, because
# converting it to one later would silently swallow this door.
check(
    "no path-param sibling can shadow the download door",
    not any(
        "{" in p and p.startswith("/workspace/file")
        for _, p in routes
    ),
    "a /workspace/file/{param} route would capture /download",
)

ws_src = read(os.path.join(API, "routes", "workspace.py"))


def slice_between(src, start_marker, *, until="\n@router."):
    """The source of one function, or '' when it is absent.

    Returning '' rather than raising is deliberate: when the door is MISSING —
    which is precisely the defect this file guards — an index() would raise and
    take every remaining assertion down with it, reporting one crash instead of
    the eight real failures below. A gate must fail loudly and COMPLETELY on the
    thing it guards, not stop at the first symptom.
    """
    if start_marker not in src:
        return ""
    body = src[src.index(start_marker) :]
    return body[: body.index(until)] if until in body else body


door = slice_between(ws_src, "async def get_workspace_file_download")

check(
    "the door mints the SAVE form (as_download=True)",
    "as_download=True" in door,
    # THE distinction that fixes symptom 2. Collapsing the save URL back into
    # the viewing URL restores the 64-hex-no-extension save.
    "the binary lane must request the attachment disposition",
)
check(
    "the door serves TEXT inline in the response (no object to sign)",
    "content=row.get(\"content\")" in door.replace(" ", "").replace("\n", "")
    or re.search(r"content=row\.get\(\s*[\"']content[\"']", door) is not None,
    # A text file's bytes ARE its `content` column. Returning only a URL would
    # reintroduce the *other* half of the original defect: no download for text.
    "text files have no blob; the door must return their content",
)
check(
    "the door refuses a FOLDER rather than serving a blank-named empty file",
    "A folder cannot be downloaded" in door,
    # ADR-588: an empty folder is a trailing-slash marker row, whose leaf name
    # is ''. Served, it would save as a nameless empty file.
    "the folder-marker case must be refused explicitly",
)
check(
    "the door is scoped to the caller's substrate",
    "_substrate_scope_filter(auth)" in door,
    # The door hands out a signed URL. It must only ever do so for a file the
    # caller's own (user_id, workspace_id) scope already reaches.
    "a download door without the scope filter leaks blobs across workspaces",
)


# ---------------------------------------------------------------------------
# 3. THE RESOLVER — one FE resolver, and it does NOT rebuild the old pair
# ---------------------------------------------------------------------------
print("\n[3] the FE resolver: one module, and the broken pair is gone")

dl_path = os.path.join(WEB, "lib", "workspace", "download.ts")
check("lib/workspace/download.ts exists", os.path.exists(dl_path))
dl = read(dl_path) if os.path.exists(dl_path) else ""

check(
    "the resolver calls the download door",
    "fileDownload(" in dl,
    "resolveDownload must go through the one server door",
)
# THE REGRESSION ASSERTION. This is the exact pair that produced symptom 1.
# Note it must not match the prose: the doc comment quotes the old code to
# explain the defect, so scan the CODE, with comments stripped.
code_only = re.sub(r"/\*(?:.|\n)*?\*/", "", dl)
code_only = re.sub(r"^\s*//.*$", "", code_only, flags=re.M)
check(
    "the resolver does NOT rebuild the broken content_url + blobUrl pair",
    # `dl` must be non-empty, or this passes VACUOUSLY: a MISSING resolver
    # contains no "blobUrl" either, and would report ok while the verb it
    # guards does not exist. Absent is not the same as correct.
    bool(dl) and "blobUrl" not in code_only,
    # `blobUrl` is still correct for what IT is — resolving a stored
    # `documents`-bucket reference for an <img> src. It is simply not a
    # download resolver, and cannot see the CAS lane at all.
    "blobUrl cannot resolve a CAS binary; using it here is the original defect",
)
check(
    "the filename travels WITH the href",
    re.search(r"filename\s*[:,}]", dl) is not None and "href" in dl,
    # The pair is inseparable: the href points at a content address, so the
    # name is the only thing carrying the file's identity to the save.
    "href without filename is the 64-hex-SHA save",
)

# ---------------------------------------------------------------------------
# 4. BOTH SURFACES offer the verb, and both use the ONE resolver
# ---------------------------------------------------------------------------
print("\n[4] both surfaces: the menu AND Properties, through one resolver")

menu = read(os.path.join(WEB, "components", "workspace", "FileContextMenu.tsx"))
check(
    "the right-click menu still renders a Download entry",
    re.search(r"download=\{download\.filename\}", menu) is not None,
    "the anchor must carry the resolved filename, not a bare download attribute",
)

props = read(os.path.join(WEB, "components", "workspace", "NodeDetailsPanel.tsx"))
check(
    "Properties offers Download (the operator asked for it here by name)",
    "FileDownload" in props and "resolveDownload" in props,
    # Properties is where an operator asks "what IS this file"; "and give me a
    # copy" is that question's second half.
    "the Properties panel must mount the download row",
)
check(
    "Properties uses the SHARED resolver, not its own inline copy",
    "resolveDownload" in props and "blobUrl" not in props,
    # Two inline copies would be two chances to reproduce the defect this
    # whole file guards.
    "a second inline resolver would drift from the menu's",
)
check(
    "Properties mounts Download on the FILE branch only",
    # `find` (-1 on absent), not `index` (raises) — an absent mount is a
    # FAILURE of this assertion, not a crash that hides the ones after it.
    props.find("<FileDownload") > props.find("<FileProperties") >= 0,
    "a folder has no download; the row must not render for one",
)

files_page = read(os.path.join(WEB, "app", "(authenticated)", "files", "page.tsx"))
check(
    "the Files page delegates downloadFor to the shared resolver",
    "resolveDownload(" in files_page,
    "the page must not carry a second implementation",
)
files_code = re.sub(r"/\*(?:.|\n)*?\*/", "", files_page)
files_code = re.sub(r"^\s*//.*$", "", files_code, flags=re.M)
check(
    "the Files page no longer builds a download from blobUrl",
    "blobUrl" not in files_code,
    "the original defect lived here",
)


# ---------------------------------------------------------------------------
# 5. THE VIEWING PATH IS UNCHANGED — the fix must not download the app's images
# ---------------------------------------------------------------------------
print("\n[5] the viewing path still serves INLINE")

# Every pre-existing caller of the path resolver is a VIEWER (lane vision, the
# attachment door, interop `open`). If any of them started passing
# as_download=True, images would download instead of render.
for rel in ("services/lane_runner.py", "routes/lanes.py", "services/mcp_composition.py"):
    p = os.path.join(API, rel)
    if not os.path.exists(p):
        continue
    body = read(p)
    for m in re.finditer(r"mint_serving_url(?:_for_path)?\((?:[^()]|\([^()]*\))*\)", body):
        check(
            f"{rel}: viewing mint stays inline",
            "as_download=True" not in m.group(0)
            and "download_name=" not in m.group(0),
            f"a viewer must not request an attachment: {m.group(0)[:90]}",
        )

# The file-read endpoint mints the VIEWING url — `<img src>` points at it.
file_read = slice_between(
    ws_src,
    "async def get_workspace_file(",
    until="async def get_workspace_file_download",
)
check(
    "GET /workspace/file keeps minting the INLINE url",
    "as_download" not in file_read and "download_name" not in file_read,
    # This is what the image viewer renders. An attachment here would make
    # every preview in the app download itself.
    "the read endpoint must not mint an attachment",
)


print(f"\n{'=' * 62}")
if failures:
    print(f"FAILED {len(failures)}/{checks}")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(f"PASSED {checks}/{checks}")
