"""Regression guard — ADR-309: two registers + type→application association.

Enforces the surface-concept hardening:

  1. Register coherence — every CONTENT kernel surface declares a
     `register` (intent | os-config | application per ADR-312 D5);
     chrome declares none. (The
     primary register assertions live in test_adr297_phase1.py; this file
     adds the FE-side + the association-layer guards.)

  2. The type→application association layer is SINGULAR — file-type → viewer
     application is resolved through one shared module (web/lib/file-types),
     not re-implemented per component. ADR-309 lifted the private
     `getFileKind` out of ContentViewer into the shared kernel-default
     table; no viewer may carry its own private file-type detection.

  3. `brand` is not a surface (Identity owns Brand) — FE union + registry.

Run: cd api && python test_adr309_two_registers.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB = REPO_ROOT / "web"

_passed = 0
_failed = 0


def _assert(cond: bool, msg: str) -> None:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {msg}")
    else:
        _failed += 1
        print(f"  FAIL  {msg}")


# =============================================================================
# Group 1 — FE Surface type carries the `register` field (ADR-309 mirror)
# =============================================================================


def test_fe_surface_register_field() -> None:
    print("\n[1] FE Surface type mirrors the two-register model")

    types_ts = (WEB / "lib" / "compositor" / "types.ts").read_text()
    # ADR-312 D5 cleaved `settings` → `intent` + `os-config`; ADR-653 D3.a
    # added `composition`.
    #
    # ⚠️ DERIVED, not restated. This was a hand-spelled regex over the exact
    # three-member sequence until 2026-09-17, so adding a register to the
    # backend reddened a check that named no new member and the fix looked
    # like "update the regex" rather than "mirror the class". Both directions
    # are asserted against the shipped `REGISTERS`, so a member added on
    # either side without the other is RED.
    from services.kernel_surfaces import REGISTERS

    _assert("SurfaceRegister" in types_ts, "compositor/types.ts declares SurfaceRegister")
    _union = re.search(r"export type SurfaceRegister\s*=\s*([^;]+);", types_ts)
    _assert(_union is not None, "SurfaceRegister is a declared union")
    _fe_members = set(re.findall(r"['\"]([a-z-]+)['\"]", _union.group(1)))
    _assert(
        _fe_members == set(REGISTERS),
        f"SurfaceRegister mirrors the shipped REGISTERS "
        f"(backend-only: {sorted(set(REGISTERS) - _fe_members)}; "
        f"FE-only: {sorted(_fe_members - set(REGISTERS))})",
    )
    _assert(
        re.search(r"register\?\s*:\s*SurfaceRegister", types_ts) is not None,
        "Surface interface carries optional `register: SurfaceRegister`",
    )


# =============================================================================
# Group 2 — type→application association is singular
# =============================================================================


def test_association_layer_singular() -> None:
    print("\n[2] type→application association is a single shared layer")

    ft = WEB / "lib" / "file-types" / "index.ts"
    _assert(ft.is_file(), "web/lib/file-types/index.ts exists (the association layer)")
    if ft.is_file():
        src = ft.read_text()
        _assert(
            "resolveViewerApplication" in src and "ViewerApplication" in src,
            "file-types exports resolveViewerApplication + ViewerApplication",
        )

    # No component may re-implement file-type detection. The signature of
    # the old private helper was `function getFileKind(`. It must not exist
    # anywhere under web/ (it was lifted into file-types).
    hits = []
    for p in WEB.rglob("*.ts*"):
        if "node_modules" in str(p) or "/.next/" in str(p):
            continue
        if re.search(r"function\s+getFileKind\s*\(", p.read_text()):
            hits.append(str(p.relative_to(WEB)))
    _assert(
        not hits,
        f"No private getFileKind() re-implementation (lifted into file-types). "
        f"Found: {hits or 'none'}",
    )

    # The mount dispatches through the shared layer.
    #
    # ⚠️ RE-ANCHORED 2026-09-17. This asserted `resolveViewerApplication` in
    # ContentViewer.tsx and had been RED since ADR-436 split the monolithic
    # viewer into renderer apps: the resolution moved INTO `FileBody`, which
    # is that ADR's ruling ("one renderer, N frames — the mount owns the
    # frame, never a branch in a mount"), so the mount stopped resolving and
    # started mounting. The check was pinning a CALL SITE the architecture
    # deliberately relocated.
    #
    # What ADR-309 actually protects is that there is ONE type→app layer and
    # mounts reach it rather than re-deriving a kind. So: the mount reaches
    # the shared layer, and the resolution lives in the one renderer.
    cv = (WEB / "components" / "workspace" / "ContentViewer.tsx").read_text()
    fb = (WEB / "components" / "workspace" / "FileBody.tsx").read_text()
    _assert(
        "@/lib/file-types" in cv and "FileBody" in cv,
        "ContentViewer reaches the shared type layer and mounts the one renderer",
    )
    _assert(
        "@/lib/file-types" in fb,
        "FileBody — the one renderer — resolves through @/lib/file-types (ADR-436)",
    )


# =============================================================================
# Group 3 — brand is not a surface
# =============================================================================


def test_brand_not_a_surface() -> None:
    print("\n[3] brand is not a kernel surface (Identity owns Brand)")

    desk = (WEB / "types" / "surface.ts").read_text()
    # The KernelSurfaceSlug union + KERNEL_SURFACE_SLUGS array must not list brand.
    _assert(
        re.search(r"\|\s*['\"]brand['\"]", desk) is None,
        "KernelSurfaceSlug union does not include 'brand'",
    )
    _assert(
        re.search(r"['\"]brand['\"]\s*,", desk) is None,
        "KERNEL_SURFACE_SLUGS array does not include 'brand'",
    )

    reg = (WEB / "components" / "shell" / "SurfaceRegistry.tsx").read_text()
    _assert(
        re.search(r"\bbrand\s*:", reg) is None,
        "KERNEL_SURFACE_REGISTRY has no brand entry",
    )


def main() -> int:
    print("=" * 70)
    print("ADR-309 — Two Registers + Type→Application Association — guard")
    print("=" * 70)

    test_fe_surface_register_field()
    test_association_layer_singular()
    test_brand_not_a_surface()

    print("\n" + "=" * 70)
    print(f"  {_passed} passed, {_failed} failed")
    print("=" * 70)
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
