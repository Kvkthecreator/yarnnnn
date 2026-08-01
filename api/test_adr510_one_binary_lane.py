"""
ADR-510 — one binary lane: design-system import binaries ride the ONE door.

Executable gate, pure-Python (no DB). Run directly:
`python test_adr510_one_binary_lane.py`.

The 2026-07-31 audit's finding, made a guard: the importer's 2026-07-16 shape
wrote binaries to the `documents` bucket with a stored `content_url`, which
left the substrate's own record of every binary EMPTY (blob_sha = the empty
sha) — bytes the revision chain could not see and an export could not carry.
ADR-510 deletes that lane: binaries go through `write_revision(content_bytes=…)`
(the ADR-427 CAS seam) like every other substrate write.

This gate EXECUTES the import against recording fakes (never greps alone):
  1. A font + an image land as `content_bytes` revisions through the one door,
     on the service client, with the derived-at-the-door contract (no
     content_url kwarg, no caller-supplied content_type).
  2. NOTHING touches a storage bucket from this module — any `.storage` access
     on either client trips the gate.
  3. A binary that fails to land is NAMED in the receipt's warnings and the
     import still lands the rest — never a silent half-landing.

Falsified against the pre-ADR-510 code: no `content_bytes` call ever happened
there (binaries went to `db.storage.from_("documents")`, which check 2 trips),
so this gate is RED on the bucket lane by construction.
"""

import sys


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


class _NoTouchClient:
    """A client that trips on ANY attribute access — write_revision is patched,
    so the importer has no business touching either client directly."""

    def __init__(self, name):
        self._name = name

    def __getattr__(self, attr):
        raise AssertionError(
            f"unexpected {self._name} client access: .{attr} — the importer "
            f"must reach substrate ONLY through write_revision (ADR-510)"
        )


_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
_TTF = b"\x00\x01\x00\x00" + b"\x00" * 64

_FILES = {
    "styles.css": b":root { --accent: #e46e2e; }",
    "readme.md": b"# The system",
    "assets/logos/m.png": _PNG,
    "assets/fonts/f.ttf": _TTF,
    "_ds_bundle.js": b"vendor",
}

_FOLDER = "/workspace/design-system/gate"


def _run_import(write_revision_fake):
    import services.authored_substrate as auth_sub
    from services.design_system_import import import_design_system

    original = auth_sub.write_revision
    auth_sub.write_revision = write_revision_fake
    try:
        return import_design_system(
            _NoTouchClient("db"),
            user_id="00000000-0000-0000-0000-000000000001",
            folder=_FOLDER,
            display_name="Gate",
            files=dict(_FILES),
            service_client=_NoTouchClient("service"),
        )
    finally:
        auth_sub.write_revision = original


def run() -> int:
    passed = True

    # ── 1+2. the happy path: binaries through the one door, no bucket ──────
    calls = []

    def _recorder(client, **kwargs):
        calls.append({"client": client, **kwargs})
        return "v-gate"

    result = _run_import(_recorder)

    binary = [c for c in calls if c.get("content_bytes") is not None]
    text = [c for c in calls if c.get("content") is not None]

    passed &= _check(
        "the import lands (receipt ok, manifest written)",
        result.get("ok") is True and result.get("manifest_path", "").endswith("_design.yaml"),
    )
    passed &= _check(
        "font + image land as content_bytes revisions (the ADR-427 CAS lane)",
        sorted(c["path"] for c in binary)
        == [f"{_FOLDER}/assets/fonts/f.ttf", f"{_FOLDER}/assets/logos/m.png"],
        f"binary paths: {[c.get('path') for c in binary]}",
    )
    passed &= _check(
        "binary writes ride the SERVICE client (seam-managed storage, like uploads)",
        binary and all(getattr(c["client"], "_name", "") == "service" for c in binary),
    )
    passed &= _check(
        "binary revisions are observations (retained raw intake, ADR-423)",
        binary and all(c.get("revision_kind") == "observation" for c in binary),
    )
    passed &= _check(
        "no write stores an address or declares a type — both are the door's "
        "job (content_url minted at read, type derived from bytes; ADR-427 D4/D5)",
        all("content_url" not in c and "content_type" not in c for c in calls),
    )
    passed &= _check(
        "text (css/readme/manifest) stays on the member's client",
        text and all(getattr(c["client"], "_name", "") == "db" for c in text),
    )
    passed &= _check(
        "the receipt carries the binaries (written + fonts)",
        f"{_FOLDER}/assets/logos/m.png" in result.get("written", [])
        and result.get("fonts") == ["assets/fonts/f.ttf"],
    )
    passed &= _check(
        "vendor material is skipped and named",
        result.get("skipped") == ["_ds_bundle.js"],
    )

    # ── 3. a binary that fails to land is NAMED, never silent ──────────────
    def _failing(client, **kwargs):
        if kwargs.get("content_bytes") is not None and kwargs["path"].endswith("m.png"):
            raise RuntimeError("storage said no")
        return "v-gate"

    result2 = _run_import(_failing)
    passed &= _check(
        "a failed binary is a WARNING naming the file (the import still lands)",
        result2.get("ok") is True
        and any(
            w.startswith("binary write failed: assets/logos/m.png")
            for w in result2.get("warnings", [])
        )
        and f"{_FOLDER}/assets/logos/m.png" not in result2.get("written", []),
        f"warnings: {result2.get('warnings')}",
    )
    passed &= _check(
        "the failure does not swallow the font",
        f"{_FOLDER}/assets/fonts/f.ttf" in result2.get("written", []),
    )

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(run())
