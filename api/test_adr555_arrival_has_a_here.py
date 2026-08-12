"""ADR-555 — arrival has a "here", and placement has one law.

Two defects, one root:

  1. Every OS-file drop ignored which folder was open. The destination was
     fixed three levels down in `resolve_upload_raw_path` with
     `principal = "operator"` as a literal — while `New Folder`, in the same
     file, already honoured the open folder (Finder's rule).
  2. THREE verbs answered the placement question differently:
     `create_folder` used `operator_can_organize`, `create_artifact` fenced to
     `operation/`, and `upload_documents` fenced to `inbound/uploads/` AND
     AUTHORIZED NOTHING AT ALL — because a hardcoded destination had nothing to
     authorize.

The second is the sharp one: the moment a caller can name a destination, the
missing check becomes the ADR-549 F1 defect (a door that accepts what the
substrate refuses). This gate EXECUTES the resolver and the predicate rather
than grepping, and compares the FE mirror against the server over one folder
set — the shape that caught F1.

Run: python3 test_adr555_arrival_has_a_here.py   (check()-style, NOT pytest)
"""

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

_pass = 0
_fail = 0


def _check(label: str, cond: bool) -> None:
    global _pass, _fail
    if cond:
        _pass += 1
        print(f"[PASS] {label}")
    else:
        _fail += 1
        print(f"[FAIL] {label}")


def main() -> int:
    from services.documents import resolve_upload_raw_path as resolve
    from services.workspace_paths import operator_can_organize

    root = pathlib.Path(__file__).parent.parent
    upload_route = (root / "api/routes/documents.py").read_text()
    studio_route = (root / "api/routes/studio.py").read_text()
    naming = (root / "web/components/authoring/artifactNaming.ts").read_text()
    modal = (root / "web/components/authoring/NewArtifactModal.tsx").read_text()
    tree = (root / "web/components/workspace/WorkspaceTree.tsx").read_text()

    print("── 1. D3 — an arrival lands WHERE THE MEMBER PUT IT ───────────")
    _check(
        "D3 [FALSIFIER]: a destination wins — the file lands in that folder",
        resolve("operator", "q3", "pdf", destination="operation/fundraising")
        == "/workspace/operation/fundraising/q3.pdf",
    )
    _check(
        "D3 [FALSIFIER]: a PEER folder works too (ADR-424 D2 is honoured)",
        resolve("operator", "q3", "pdf", destination="the-acme-deal")
        == "/workspace/the-acme-deal/q3.pdf",
    )
    _check(
        "D3: no destination = the intake lane, byte-identical to before",
        resolve("operator", "q3", "pdf") == "/workspace/inbound/uploads/operator/q3.pdf",
    )
    _check(
        "D3: the `{principal}/` sublane belongs to the DEFAULT home only",
        "/operator/" not in resolve("operator", "q3", "pdf", destination="ops"),
    )
    for messy in ("/workspace/operation/", "workspace/operation", "operation/"):
        _check(
            f"D3: a messy destination normalizes ({messy!r})",
            resolve("operator", "q3", "pdf", destination=messy)
            == "/workspace/operation/q3.pdf",
        )

    print("\n── 2. D2/D4 — the upload door AUTHORIZES (it never did) ───────")
    # The check that did not exist. Read the handler, not the module: the
    # module has other `operator_can_organize` calls (move, rename, delete), so
    # a file-wide grep would go green while the upload door authorized nothing.
    handler = re.search(
        r"async def upload_documents\([\s\S]*?(?=\n@router|\n(?:async )?def )",
        upload_route,
    )
    _check("the upload handler is readable", bool(handler))
    body = handler.group(0) if handler else ""
    _check(
        "D4 [FALSIFIER]: the upload door calls operator_can_organize",
        "operator_can_organize(" in body,
    )
    _check(
        "D4 [FALSIFIER]: …and refuses with 403, not a silent redirect",
        "403" in body,
    )
    _check(
        "D4: traversal in a destination is refused",
        '".." in dest' in body or "'..' in dest" in body,
    )

    print("\n── 3. D2 — ONE placement law, asked by every verb ─────────────")
    create = re.search(
        r"async def create_artifact\([\s\S]*?(?=\n@router|\Z)", studio_route
    )
    create_body = create.group(0) if create else ""
    _check(
        "D2 [FALSIFIER]: create_artifact asks the organize predicate",
        "operator_can_organize(" in create_body,
    )
    _check(
        "D2 [FALSIFIER]: …and no longer fences creation to the region",
        "not path.startswith(STUDIO_ARTIFACT_REGION)" not in create_body,
    )
    # The WRITE door asks the same law. Found 2026-08-12: create was relaxed
    # (region = default, ADR-549 D3) while write kept the prefix fence — so a
    # doc created beside its source accepted typing and 403'd every save.
    # The F1 shape one seam over: two doors, one placement question, two answers.
    write = re.search(
        r"async def write_artifact\([\s\S]*?(?=\n@router|\Z)", studio_route
    )
    write_body = write.group(0) if write else ""
    _check(
        "D2 [FALSIFIER]: write_artifact asks the organize predicate",
        "operator_can_organize(" in write_body,
    )
    _check(
        "D2 [FALSIFIER]: …and no longer fences saves to the region",
        "not path.startswith(STUDIO_ARTIFACT_REGION)" not in write_body,
    )
    # Executed: the law itself, over the folders a member can reach.
    FOLDERS = [
        ("/workspace/operation/fundraising", True),
        ("/workspace/the-acme-deal", True),
        ("/workspace/inbound/uploads", True),
        ("/workspace/memory", True),
        ("/workspace/system", False),
        ("/workspace/inbound/slack", False),
    ]
    for folder, allowed in FOLDERS:
        _check(
            f"D2: {folder.replace('/workspace/', '')} → {'allowed' if allowed else 'refused'}",
            operator_can_organize(f"{folder}/x") is allowed,
        )

    print("\n── 4. THE FE MIRROR agrees with the server (the F1 shape) ─────")
    # The defect ADR-549 F1 fixed, re-checked after the fence moved: the create
    # picker must offer exactly what the server accepts. Mirrors are compared,
    # not assumed — that is the only thing that catches a one-sided change.
    _check(
        "the FE declares the create-placement predicate in ONE place",
        "export function canCreateFileIn(" in naming,
    )
    for prop in ("selectable", "canConfirm", "folderDisabledTitle"):
        m = re.search(rf"{prop}=\{{[\s\S]*?\n        \}}", modal)
        expr = m.group(0) if m else ""
        _check(
            f"[FALSIFIER]: `{prop}` asks the one law, not the old region fence",
            "canCreateFileIn" in expr and "isArtifactRegion" not in expr,
        )
    _check(
        "isArtifactRegion survives as a HOME test, not a gate",
        "export function isArtifactRegion(" in naming
        and "defaultDestinationFor" in naming,
    )

    print("\n── 5. THE DROP TARGET — a folder row accepts an OS file ───────")
    # The gesture that was silently swallowed: a folder row only handled the
    # internal MIME, so dropping a PDF on `fundraising/` did nothing at all.
    code = re.sub(r"/\*[\s\S]*?\*/", "", tree)
    code = re.sub(r"(^|[^:])//[^\n]*", r"\1", code)
    _check(
        "[FALSIFIER]: a folder row handles a FILE drop, not only an internal move",
        "onDropFiles" in code and "dataTransfer.files" in code,
    )
    _check(
        "the drop effect distinguishes an import from a move",
        "'copy'" in code and "'move'" in code,
    )
    _check(
        "the internal move still wins when both are present",
        bool(re.search(r"getData\(DRAG_MIME\)[\s\S]{0,200}?return", code)),
    )

    print(f"\n{'PASS' if _fail == 0 else 'FAIL'}: {_pass}/{_pass + _fail} checks")
    return 0 if _fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
