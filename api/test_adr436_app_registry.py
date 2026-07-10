"""
Validation Suite — ADR-436 (the App Registry: frame-agnostic renderers)

The named-but-missing ratchet for ADR-436. Source-text assertions over the FE
`file-types` + `viewers` layer — the same shape as the ADR-209 banned-pattern
guard. Pure text checks (no build, no DB): the contract is the FILE SHAPE
(dispatch-via-table, no inline monolith, closed union held), which text encodes.

Guards the debt half against regression:
  1. FileBody is a THIN DISPATCHER — it resolves via `resolveApp` and mounts the
     app renderer; it does NOT re-grow the pre-ADR-436 monolithic kind-switch.
  2. The `APPS` table is code-seeded with the 7 kernel viewer apps + the
     download terminal (the LaunchServices rows).
  3. Each of the 7 renderer apps + the terminal exists in `viewers/index.tsx`.
  4. `resolveApps` returns an ordered LIST (ADR-436 D2 — the Open-With seam);
     `resolveApp` is the singleton convenience over it.
  5. THE POSITIONING RATCHET (ADR-436 §3): `ViewerApplication` is STILL a closed
     union and `AppId` is an OPAQUE string. This pair is the "can a third party
     replace your viewer with no kernel change?" gate — it runs RED (this test
     asserts closed) until a future App(principal) ADR flips it in one file. If
     someone flips the union to open WITHOUT that ADR, this test fails loudly.

Usage:
    cd api && python test_adr436_app_registry.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    icon = "✓" if ok else "✗"
    logger.info(f"{icon} {name}: {detail}")


# Repo root is one level up from api/.
ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

FILEBODY = WEB / "components" / "workspace" / "FileBody.tsx"
APPS_TSX = WEB / "lib" / "file-types" / "apps.tsx"
VIEWERS = WEB / "components" / "workspace" / "viewers" / "index.tsx"
FILE_TYPES_INDEX = WEB / "lib" / "file-types" / "index.ts"

# The 7 kernel viewer apps + the download terminal (ADR-436 D1).
EXPECTED_APP_IDS = [
    "text.viewer",
    "markdown.viewer",
    "web.viewer",
    "image.viewer",
    "media.player",
    "pdf.viewer",
    "table.viewer",
    "download.terminal",
]

EXPECTED_RENDERERS = [
    "TextViewer",
    "MarkdownViewer",
    "WebViewer",
    "ImageViewer",
    "MediaPlayer",
    "PdfViewer",
    "TableViewer",
    "DownloadTerminal",
]


def run() -> None:
    # Read the four source files once.
    for label, path in [
        ("FileBody.tsx", FILEBODY),
        ("apps.tsx", APPS_TSX),
        ("viewers/index.tsx", VIEWERS),
        ("file-types/index.ts", FILE_TYPES_INDEX),
    ]:
        if not path.exists():
            record(f"0. {label} exists", False, f"missing: {path}")
            return
    filebody = FILEBODY.read_text()
    apps = APPS_TSX.read_text()
    viewers = VIEWERS.read_text()
    index = FILE_TYPES_INDEX.read_text()

    # 1. FileBody dispatches via resolveApp — the thin-dispatcher contract.
    dispatches = "resolveApp(" in filebody
    record("1. FileBody dispatches via resolveApp", dispatches,
           "resolveApp( call present" if dispatches else "no resolveApp dispatch")

    # 1b. FileBody has NOT re-grown the monolithic kind-switch. The pre-ADR-436
    #     monolith was a flat run of `kind === '…'` branches; assert none remain
    #     in the dispatcher body.
    no_monolith = "kind ===" not in filebody
    record("1b. FileBody has no inline kind-switch monolith", no_monolith,
           "clean" if no_monolith else "found `kind ===` — the monolith re-grew")

    # 2. The APPS table is code-seeded with all 8 rows.
    missing_ids = [aid for aid in EXPECTED_APP_IDS if f"'{aid}'" not in apps]
    record("2. APPS table seeds the 7 apps + terminal", not missing_ids,
           "all 8 rows present" if not missing_ids else f"missing ids: {missing_ids}")

    # 3. Each renderer component is defined in viewers/index.tsx.
    missing_renderers = [r for r in EXPECTED_RENDERERS if f"const {r}" not in viewers
                         and f"function {r}" not in viewers]
    record("3. All 8 renderer apps defined in viewers", not missing_renderers,
           "all present" if not missing_renderers else f"missing: {missing_renderers}")

    # 4. resolveApps returns an ordered list; resolveApp is the singleton.
    has_list = "resolveApps" in apps and "AppId[]" in apps
    has_singleton = "resolveApp" in apps
    record("4. resolveApps (ordered list) + resolveApp (singleton)",
           has_list and has_singleton,
           f"resolveApps+AppId[]={has_list}, resolveApp={has_singleton}")

    # 5a. THE RATCHET — ViewerApplication is STILL a closed union (a `type X = ...`
    #     union of string literals, NOT `string`). This is the red-until-App-
    #     (principal) gate. If the union opens without that ADR, fail.
    union_closed = "export type ViewerApplication =" in index
    # A closed union enumerates literals; an opened one would be `= string`.
    union_not_string = "ViewerApplication = string" not in index
    record("5a. RATCHET: ViewerApplication is a closed union",
           union_closed and union_not_string,
           "closed (correct — runs red until App(principal) ADR)"
           if union_closed and union_not_string
           else "union appears OPENED without an App(principal) ADR")

    # 5b. THE RATCHET — AppId is an OPAQUE string (the table's shape admits a
    #     stranger's row, but the vocabulary stays closed). ADR-436 §3.
    appid_opaque = "export type AppId = string" in apps
    record("5b. RATCHET: AppId is an opaque string", appid_opaque,
           "opaque (table admits a stranger's row; union stays closed)"
           if appid_opaque else "AppId is not the opaque-string shape")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # surface any wiring failure as a hard fail
        logger.exception("suite crashed")
        record("SUITE", False, f"crashed: {exc}")

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    failed = total - passed
    print(f"\n{'='*60}")
    print(f"ADR-436 app-registry ratchet: {passed}/{total} passed, {failed} failed")
    print(f"{'='*60}")
    if failed:
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"  ✗ {name}: {detail}")
    sys.exit(0 if failed == 0 else 1)
