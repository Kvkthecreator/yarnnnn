"""
A FOLDER VERB IS A FAN-OUT, and a TEXT FILE CAN BE SAVED — the two gaps gate.

Run directly: `python3 test_folder_verbs_and_download.py` from `api/`.
(Script-style, like test_files_selection_model.py. Running it under pytest
collects nothing and reports a silent green — check how a gate runs before
trusting its colour.)

WHAT THIS DEFENDS. Two absences on the Files surface, both of the same shape:
an affordance MISSING rather than refused, which reads to the operator as "the
product cannot do this."

  1. FOLDER VERBS. Right-clicking a folder offered Open · Properties · Share ·
     New Folder — no Rename, no Move, no Move to Trash. The reason was
     structural: since ADR-588 a folder is a marker row plus whatever files
     share its path prefix, so a folder verb is a FAN-OUT over the subtree, and
     no fan existed. It does now.

  2. TEXT DOWNLOAD. `downloadFor` resolved only a file with a `content_url` —
     the blob-store lane. A `.md`/`.csv`/`.yaml` has NO content_url (its bytes
     are the `content` column), so right-clicking `gtm-strategy.md` offered no
     Download at all and nothing explained why. The content was already in the
     payload the surface had just fetched.

THE CLAIMS:
  1.  The fan-out exists, ONCE, and both the COUNT and the ACT read the same
      enumeration — a count from a second query would be a blast-radius promise
      the act does not keep.
  2.  It writes through `write_revision`, the ADR-209 single write path, and
      moves through `MoveFile`, the ONE mover. No second write path, no bulk
      mover.
  3.  Locked children are REPORTED, never silently skipped — every fan response
      carries `locked` beside the performed set.
  4.  The COUNT IS IN THE MENU LABEL, before the click.
  5.  Trash GROUPS by the deleted root, and the group restores WHOLE.
  6.  The grouping stamp is a READ-MERGE-WRITE — a blind replace would destroy
      a file's Open-With binding on its way to the Trash.
  7.  A TEXT file resolves a download; the BINARY lane still carries the
      filename (1069fe3 — the CAS is keyed by content address).
  8.  A FOLDER and a MULTI-SELECTION yield NO download item, and no zip builder
      exists (ADR-417 — generation is rented; the export door is the bulk answer).
  9.  Duplicate stays FILE-ONLY; the organize verbs no longer branch on isFile.
 10.  The object URL a text download mints is REVOKED.

Assertions run over COMMENT-STRIPPED source. A gate that reads its own
explanatory prose is testing its documentation, not its code.
"""

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_WEB = os.path.normpath(os.path.join(_HERE, "..", "web"))


def _read_web(rel: str) -> str:
    p = os.path.join(_WEB, rel)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def _read_api(rel: str) -> str:
    p = os.path.join(_HERE, rel)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def _strip_ts_comments(src: str) -> str:
    """Drop // line-comments and /* */ blocks — LINE COMMENTS FIRST.

    THE ORDER IS LOAD-BEARING, and getting it wrong cost this gate four false
    failures before it was written correctly. `lib/api/client.ts` contains a
    line comment mentioning a glob — `// … uploads/*.md)` — whose `/*` opens a
    phantom block. Stripping blocks first, with DOTALL, then runs to the next
    real `*/` and silently swallows 12,817 characters of live code, including
    every symbol this gate asserts on. The gate then reports FAIL against source
    that is entirely correct.

    Line comments first removes the phantom opener before it can be read as one.

    A JSX comment `{/* … */}` loses its body here and leaves a bare `{}`, which
    is inert for these assertions. Deliberately NOT a `\\{\\s*/\\*.*?\\*/\\s*\\}`
    pattern: `\\{` matches ANY brace, so with DOTALL that swallows everything
    from the first `interface X {` to the next `*/}` — the same class of defect
    at a different address.
    """
    src = re.sub(r"//[^\n]*", "", src)
    return re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)


def _strip_py_comments(src: str) -> str:
    """Drop `#` comments and triple-quoted docstrings.

    The docstrings here are long and state the very claims being asserted, so
    leaving them in would let this gate pass on its own prose — the exact
    failure the comment-stripping discipline exists to prevent.
    """
    src = re.sub(r'"""(?:.|\n)*?"""', '""', src)
    src = re.sub(r"'''(?:.|\n)*?'''", "''", src)
    return re.sub(r"#[^\n]*", "", src)


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def run() -> int:
    passed = True

    fan_raw = _read_api("services/folder_organize.py")
    docs_raw = _read_api("routes/documents.py")
    page_raw = _read_web("app/(authenticated)/files/page.tsx")
    menu_raw = _read_web("components/workspace/FileContextMenu.tsx")
    hook_raw = _read_web("hooks/useFileOrganizeVerbs.tsx")
    trash_raw = _read_web("components/workspace/TrashView.tsx")
    client_raw = _read_web("lib/api/client.ts")

    if not (fan_raw and docs_raw and page_raw and menu_raw and hook_raw and trash_raw):
        return _check("all six modules are readable", False) or 1

    fan = _strip_py_comments(fan_raw)
    docs = _strip_py_comments(docs_raw)
    page = _strip_ts_comments(page_raw)
    menu = _strip_ts_comments(menu_raw)
    hook = _strip_ts_comments(hook_raw)
    trash = _strip_ts_comments(trash_raw)
    client = _strip_ts_comments(client_raw)

    # ── 1. ONE ENUMERATION, shared by the count and the act ───────────────
    #
    # The menu label says "(40 items)" and the act must move 40. If the preflight
    # counted with its own query, the two could drift silently — and the drift
    # would only ever be visible as a broken promise after a destructive click.
    #
    # Asserted as a COUNT of callers, not as "the function exists": three call
    # sites (preflight, trash, move) must all route through `enumerate_subtree`.
    # A fourth folder verb added later that counts for itself trips this.
    enum_callers = len(re.findall(r"enumerate_subtree\(", docs)) + len(
        re.findall(r"enumerate_subtree\(\n?\s*client", fan)
    )
    passed &= _check(
        "1a. the subtree is enumerated by ONE function",
        "def enumerate_subtree(" in fan,
    )
    passed &= _check(
        "1b. every folder verb reads that one enumeration (count == act)",
        len(re.findall(r"enumerate_subtree\(", docs)) >= 2
        and "enumerate_subtree(" in fan,
        f"route call sites={len(re.findall(r'enumerate_subtree.', docs))}",
    )
    # And the preflight is a READ — a count that mutated would be a preview
    # with a side effect.
    pre = re.search(r"async def folder_preflight\((.*?)\n@router", docs, re.DOTALL)
    prebody = pre.group(1) if pre else ""
    passed &= _check(
        "1c. the preflight has no write in it",
        pre is not None
        and "write_revision" not in prebody
        and ".update(" not in prebody
        and ".insert(" not in prebody,
    )

    # ── 2. THE ONE WRITE PATH, and the ONE MOVER ──────────────────────────
    #
    # ADR-209: `write_revision` is the single write path for every content-layer
    # mutation. ADR-337 D3 / ADR-554 D1: `MoveFile` is the one mover, and it
    # carries an upload's `.extracted.md` projection with its raw — a bespoke
    # bulk mover would silently drop that.
    # Anchored on the ARCHIVE CALL ITSELF inside `trash_folder`, not on the
    # string `lifecycle="archived"` appearing anywhere in the module — the
    # marker-archival inside `move_folder` carries the same kwarg, so a bare
    # substring test passes even after the trash archive is deleted (observed
    # while falsifying this gate). Isolate the function, then assert.
    trash_fn = re.search(r"def trash_folder\((.*?)\ndef ", fan, re.DOTALL)
    tfbody = trash_fn.group(1) if trash_fn else ""
    passed &= _check(
        "2a. the fan archives through write_revision (ADR-209 single write path)",
        "from services.authored_substrate import write_revision" in fan
        and trash_fn is not None
        and "write_revision(" in tfbody
        and 'lifecycle="archived"' in tfbody,
    )
    passed &= _check(
        "2b. the fan moves through the MoveFile primitive, not a second mover",
        'execute_primitive(' in fan and '"MoveFile"' in fan,
    )
    # No parallel bulk write. The only direct workspace_files mutations in the
    # fan are the metadata stamps — asserted by COUNT so a content-layer
    # `.update({"content": …})` added later cannot hide among them.
    updates = re.findall(r"\.update\(\{([^}]*)\}", fan)
    non_metadata = [u for u in updates if "metadata" not in u]
    passed &= _check(
        "2c. the fan makes NO direct content-layer write (only metadata stamps)",
        not non_metadata,
        f"non-metadata direct updates={non_metadata}" if non_metadata else "",
    )
    # The archive must re-reference the head BLOB, not re-write the text denorm
    # — a binary file's denorm is '' and re-writing it would put an EMPTY text
    # revision at the head of every binary chain the fan touches.
    passed &= _check(
        "2d. the archive preserves the head blob (a binary folder survives)",
        "content_ref" in fan and "blob_sha" in fan,
    )

    # ── 3. LOCKED CHILDREN REPORTED, NEVER SKIPPED ────────────────────────
    #
    # `operator_can_organize` refuses system/, raw inbound/, machine-config
    # leaves. A folder holding those can only be PARTIALLY organized. Silently
    # moving 38 of 40 and saying "Moved" is the incorrect-success shape.
    passed &= _check(
        "3a. the fan splits the subtree by the SAME carve predicate the routes use",
        "operator_can_organize" in fan
        and re.search(r"\(files if operator_can_organize\(p\) else locked\)", fan)
        is not None,
    )
    # Every FAN route carries `locked`. A COUNT over the route bodies, so a
    # fourth fan verb that forgets the partial trips this.
    #
    # Scoped to `/documents/folder/<verb>` — the routes that FAN. `POST
    # /documents/folder` (create, ADR-588 D1) writes ONE marker row and has no
    # subtree, so it has nothing to report a partial about; sweeping it in was
    # the first draft's over-broad match, and it failed honestly.
    fan_routes = re.findall(
        r'@router\.(?:get|post)\("/documents/folder/[^"]+"[^)]*\)\n(?:async )?def [^\n]*\n(.*?)(?=\n@router|\nclass |\Z)',
        docs,
        re.DOTALL,
    )
    # The test is on the RETURNED KEY, not on the word appearing in the body.
    # A route that composes a message mentioning `locked` and then drops it from
    # its response still satisfies a bare substring test — the partial would be
    # spoken in a toast and absent from the payload (observed while falsifying).
    # `locked=` covers the preflight's Pydantic field; `"locked":` the dict
    # returns.
    with_locked = [b for b in fan_routes if 'locked=' in b or '"locked":' in b]
    passed &= _check(
        "3b. EVERY fan route RETURNS the locked set alongside what it did",
        len(fan_routes) >= 3 and len(with_locked) == len(fan_routes),
        f"fan routes={len(fan_routes)} returning locked={len(with_locked)}",
    )
    # And the sentence NAMES the carve rather than dropping the number in
    # silence. A COUNT over the fan routes that RETURN a message, not a bare
    # substring: the phrase appears in both the trash and the move route, so
    # removing it from one still satisfies "is it present anywhere" (observed
    # while falsifying). Every fan route that speaks must speak the carve.
    speaking = [b for b in fan_routes if '"message"' in b or "message=" in b]
    naming_carve = [b for b in speaking if "managed by the system and stayed" in b]
    passed &= _check(
        "3c. EVERY fan route that reports SPEAKS the carve, in the operator's words",
        len(speaking) >= 2 and len(naming_carve) == len(speaking),
        f"reporting routes={len(speaking)} naming the carve={len(naming_carve)}",
    )
    # The FE surfaces the backend's own sentence rather than composing a second
    # one from the same numbers — two builders of one sentence is how they drift.
    passed &= _check(
        "3d. the surface reports the SERVER's sentence, not a second derivation",
        "const fanReport" in hook and "res.message" not in hook.replace("fanReport", ""),
        "",
    )

    # ── 4. THE COUNT IS IN THE LABEL, BEFORE THE CLICK ────────────────────
    #
    # "Move to Trash" on a folder is one label wearing forty acts. The size of
    # the act must be visible at the moment of POINTING, not discovered in a
    # toast afterwards.
    passed &= _check(
        "4a. the menu renders a resolved delete LABEL, not a fixed string",
        "deleteLabel" in menu
        and re.search(r"\{deleteLabel \?\? 'Move to Trash'\}", menu) is not None,
    )
    passed &= _check(
        "4b. the label carries the COUNT, composed from the resolved number",
        re.search(r"Move to Trash \(\$\{blastRadius\} item", menu) is not None,
    )
    # And it is resolved on MENU OPEN, the same lifecycle as the download href —
    # a label that resolved on click would name the radius after the deed.
    passed &= _check(
        "4c. the radius is resolved when the menu OPENS",
        "blastRadiusFor" in menu
        and re.search(r"const resolveOnOpen = useCallback", menu) is not None
        and "verbs.blastRadiusFor" in menu,
    )
    # The FE asks for what will ACTUALLY move (`count`), not the folder's total.
    # Promising 40 and moving 38 is the same broken promise with a number on it.
    radius = re.search(r"blastRadiusFor: async \(t: \{[^}]*\}\) => \{(.*?)\n    \},", page, re.DOTALL)
    rbody = radius.group(1) if radius else ""
    passed &= _check(
        "4d. the label counts what MOVES, not what the folder holds",
        radius is not None
        and "folderPreflight" in rbody
        and "return r.count;" in rbody
        and "locked.length" not in rbody,
    )

    # ── 5. TRASH GROUPS BY THE DELETED ROOT ───────────────────────────────
    #
    # 40 loose rows makes a folder unrecoverable AS a folder — 40 restores and a
    # hand-rebuilt shape. Trash must mirror the ACT: one folder deleted, one
    # thing shown, restored whole.
    passed &= _check(
        "5a. the fan stamps each archived row with the deleted root",
        "TRASHED_WITH_KEY" in fan and 'TRASHED_WITH_KEY = "trashed_with"' in fan,
    )
    passed &= _check(
        "5b. the trash listing collapses stamped rows into GROUPS",
        "class TrashGroup" in docs
        and "groups: List[TrashGroup]" in docs
        and "TRASHED_WITH_KEY" in docs,
    )
    # A grouped member must NOT also appear as a loose row, or the operator sees
    # the folder AND its forty files and cannot tell which restore is which.
    listing = re.search(r"async def list_trash\((.*?)\n(?:class |@router)", docs, re.DOTALL)
    lbody = listing.group(1) if listing else ""
    passed &= _check(
        "5c. a grouped member is NOT repeated as a loose row",
        listing is not None
        and re.search(r"if root:\n(?:.|\n)*?\n            continue", lbody) is not None,
    )
    # The group restores by the KEY, never by a path prefix: a file trashed
    # separately AFTER the folder went would match the prefix but was not part
    # of that act, and sweeping it back in restores what nobody asked for.
    restore = re.search(r"def restore_group\((.*?)\ndef ", fan, re.DOTALL)
    resbody = restore.group(1) if restore else fan[fan.find("def restore_group"):]
    passed &= _check(
        "5d. the group restore is addressed by the KEY, not by a path prefix",
        "contains(" in resbody
        and "TRASHED_WITH_KEY" in resbody
        and ".like(" not in resbody,
    )
    passed &= _check(
        "5e. the Trash surface renders groups and restores them whole",
        "TrashGroup" in trash
        and "restoreTrashGroup" in trash
        and "Restore all" in trash,
    )
    # The header count and the empty state read the SAME number, or a trash
    # holding only folders would say "0 items" above a list of folders.
    passed &= _check(
        "5f. the header, the empty state and Empty-Trash agree on one count",
        "const rowCount = items.length + groups.length;" in trash
        and len(re.findall(r"\browCount\b", trash)) >= 4,
        f"rowCount uses={len(re.findall(r'.rowCount.', trash))}",
    )

    # ── 6. THE STAMP IS A READ-MERGE-WRITE ────────────────────────────────
    #
    # `metadata` also carries the ADR-514 D2.4 Open-With binding. A blind
    # `update({"metadata": {...}})` would destroy it on the way to the Trash, and
    # Restore would bring back a file that had forgotten how to open.
    stamp = re.search(r"def _merge_metadata_trashed_with\((.*?)\ndef ", fan, re.DOTALL)
    sbody = stamp.group(1) if stamp else ""
    passed &= _check(
        "6. the grouping stamp MERGES metadata (Open-With survives the Trash)",
        stamp is not None
        and 'select("metadata")' in sbody
        and re.search(r"metadata = dict\(", sbody) is not None,
    )

    # ── 7. A TEXT FILE RESOLVES A DOWNLOAD ────────────────────────────────
    #
    # The real gap. A `.md`'s bytes ARE its `content` column — no content_url at
    # all — so the pre-fix resolver returned null for every text file and the
    # entry did not render. Nothing explained why.
    dl = re.search(r"downloadFor: async \(t: \{[^}]*\}\) => \{(.*?)\n    \},", page, re.DOTALL)
    dbody = dl.group(1) if dl else ""
    passed &= _check(
        "7a. the resolver exists and takes ONE target",
        dl is not None,
    )
    passed &= _check(
        "7b. a TEXT file downloads its content as a typed Blob",
        "new Blob(" in dbody
        and "URL.createObjectURL" in dbody
        and "textDownloadMime(" in dbody,
    )
    # The type must be STATED. A Blob with no type saves as
    # application/octet-stream, which the OS shows as a nameless binary even
    # when the extension is right.
    passed &= _check(
        "7c. the Blob carries a real MIME type (not an untyped blob)",
        re.search(r"\{ type: textDownloadMime\(filename\) \}", dbody) is not None
        and "function textDownloadMime(" in page,
    )
    # 7d. THE BINARY LANE IS PRESERVED, filename and all. This is 1069fe3's fix:
    # the CAS is keyed by CONTENT ADDRESS, so a bare `download` attribute saved
    # the blob as its 64-char SHA with no extension. Asserted on BOTH halves —
    # the resolver returning the pair, and the anchor consuming it.
    passed &= _check(
        "7d. the BINARY lane still resolves a signed URL and its own filename",
        "content_url" in dbody
        and "blobUrl(" in dbody
        and re.search(r"return \{ href: r\.url, filename \}", dbody) is not None
        and "download={download.filename}" in menu,
    )
    # 7e. Both lanes take the leaf from the PATH, never from the href — one
    # derivation, so the text lane cannot reintroduce the SHA-named-file bug at
    # a new address. A COUNT: exactly one filename derivation in the resolver.
    _leaf_derivations = len(re.findall(r"t\.path\.split\('/'\)\.pop\(\)", dbody))
    passed &= _check(
        "7e. the filename is derived ONCE, from the path",
        _leaf_derivations == 1,
        f"leaf derivations in the resolver={_leaf_derivations} (must be 1)",
    )

    # ── 8. NO FOLDER DOWNLOAD, NO MULTI DOWNLOAD, NO ZIP ──────────────────
    #
    # Dropbox / Drive / OneDrive all zip a folder server-side. We deliberately do
    # not: ADR-417 (generation is rented, not owned — yarnnn hosts no
    # generation/rendering engine) and the bulk door already exists and is
    # strictly better (GET /api/workspace/export, ADR-328 D4 — a real git repo
    # WITH history and attribution; a zip has none of that).
    #
    # The entry simply does not render. No dead affordance, no disabled row.
    passed &= _check(
        "8a. a FOLDER resolves no download at all",
        re.search(r"if \(!t\.isFile\) return null;", dbody) is not None,
    )
    # And the menu renders the entry ONLY when a download resolved — an entry
    # that did nothing when clicked would be the same defect at a new address.
    passed &= _check(
        "8b. the menu renders Download only when one resolved",
        re.search(r"\{download && \(\s*<a", menu) is not None,
    )
    # No zip builder anywhere in the surface or the routes.
    zip_words = [
        w for w in ("createZip", "zipFolder", "downloadZip", "JSZip", "archiver")
        if w in page or w in menu or w in docs or w in fan
    ]
    passed &= _check(
        "8c. no zip builder was introduced (ADR-417: generation is rented)",
        not zip_words,
        f"found: {zip_words}" if zip_words else "",
    )
    # 8d. A MULTI-SELECTION yields no download either — structurally, because the
    # resolver takes ONE target and the menu holds ONE. Asserted as the ABSENCE
    # of any selection read in the resolver: a future edit that made it
    # set-aware would have to reach for `selection`, and this trips.
    passed &= _check(
        "8d. the resolver is single-target (a multi-selection cannot download)",
        "selection" not in dbody,
    )

    # ── 9. THE isFile GATE IS RESTRUCTURED, NOT LAYERED ───────────────────
    #
    # The organize verbs no longer branch on isFile — that WAS the gate keeping
    # them off folders. Duplicate stays file-only (deep-copying a subtree with a
    # derived_from edge per file is a different act, out of scope).
    organize = re.search(r"\{\(onRename \|\| onMove \|\| onDelete(.*?)</div>\s*\);\s*\}", menu, re.DOTALL)
    obody = organize.group(1) if organize else ""
    passed &= _check(
        "9a. Rename / Move / Trash no longer branch on isFile",
        organize is not None
        and "isFile && onRename" not in obody
        and "isFile && onMove" not in obody
        and "isFile && onDelete" not in obody,
    )
    # Anchored on the ENTRY, not on the string `isFile && onDuplicate` anywhere
    # in the file: the organize group's own separator condition contains that
    # same expression, so a bare substring test still passes after the entry's
    # gate is removed and Duplicate starts appearing on folders (observed while
    # falsifying this gate — an assertion satisfied by a neighbouring line).
    dup_entry = re.search(r"\{(\w+ && )*onDuplicate && \(\s*<MenuItem", menu)
    passed &= _check(
        "9b. Duplicate is STILL file-only (a folder deep-copy is a different act)",
        dup_entry is not None and dup_entry.group().startswith("{isFile && onDuplicate"),
        f"guard on the Duplicate entry: {dup_entry.group()[:40] if dup_entry else 'ENTRY NOT FOUND'}",
    )
    # The hook routes a folder to the FAN, a file to the single act — one
    # implementation each, addressed by the target's own kind.
    passed &= _check(
        "9c. the organize hook routes a folder target to the fan-out",
        "isFolder" in hook
        and "api.documents.trashFolder(" in hook
        and "api.documents.moveFolder(" in hook,
    )
    # RENAME and MOVE on a folder are the SAME act with a different destination.
    # Two implementations would drift; assert they share the one route.
    passed &= _check(
        "9d. a folder rename IS the folder move (one route, so no drift)",
        len(re.findall(r"api\.documents\.moveFolder\(", hook)) == 2,
        f"moveFolder call sites in the hook={len(re.findall(r'api.documents.moveFolder.', hook))} (rename + move)",
    )
    # The picker refuses a destination INSIDE the folder being moved — a fan-out
    # that chases its own tail. Refused by CONSTRUCTION, not by a post-hoc 400:
    # a refusal met only after choosing is a dead end wearing a live affordance.
    picker = _strip_ts_comments(_read_web("components/workspace/MoveToFolderModal.tsx"))
    passed &= _check(
        "9e. the Move picker refuses a destination inside the moved folder",
        "isInsideSelf" in picker
        and len(re.findall(r"isInsideSelf\(", picker)) >= 3,
        f"isInsideSelf uses={len(re.findall(r'isInsideSelf.', picker))} (predicate + selectable + disabled-title + canConfirm)",
    )
    # ...and the backend refuses it too, so a non-cockpit caller cannot perform
    # it. The FE guard is courtesy; this is the actual boundary.
    passed &= _check(
        "9f. the backend refuses a self-containing folder move",
        re.search(r'if dst\.startswith\(src \+ "/"\)', docs) is not None,
    )

    # ── 10. THE OBJECT URL IS REVOKED ─────────────────────────────────────
    #
    # `URL.createObjectURL` is held by the document until explicitly revoked —
    # never GC'd while the page lives. A member right-clicking twenty .md files
    # would leak twenty file bodies. It cannot be revoked at mint (that
    # invalidates the href before the anchor is followed) nor on menu close (the
    # click that closes the menu IS the navigation), so it is collected and
    # released on unmount.
    passed &= _check(
        "10a. minted object URLs are collected",
        "objectUrlsRef" in page
        and "objectUrlsRef.current.push(href)" in page,
    )
    passed &= _check(
        "10b. and REVOKED (the leak is closed, not merely tracked)",
        "URL.revokeObjectURL" in page,
    )

    # ── 11. THE API CLIENT EXPOSES THE FOUR DOORS ─────────────────────────
    #
    # A capability with no caller is a capability that does not exist
    # (the ADR-328 export shipped that way and reached nobody for months).
    for name in ("folderPreflight", "trashFolder", "moveFolder", "restoreTrashGroup"):
        passed &= _check(
            f"11. the client exposes {name}",
            f"{name}: (" in client,
        )

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(run())
