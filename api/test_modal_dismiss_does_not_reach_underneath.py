"""Structural gate — a modal's committing click ends at the modal.

HARDENING, NOT A DIAGNOSED FIX. Recorded plainly because the work this gate
holds began from a WRONG diagnosis:

  The falsified claim: "the portal unmounts inside the click's own dispatch, so
  the click re-targets onto the file row underneath, which navigates to Text."
  It does not. Removing an element during `mousedown`, or during its own
  `click` handler, leaves the original target intact — the browser does not
  re-dispatch to whatever is revealed. Driven in Chrome both ways 2026-09-13.

What this gate does NOT claim: that it protects against the reported "delete on
Files opens the file in Text". That bug was something else and is fixed
elsewhere. Settled by CDP 2026-09-13: `MouseEvent.detail` counts the GESTURE,
not the element — Chrome does not reset its multi-click counter when the thing
under the pointer changes between two presses at one point, so the row beneath
the dismissed dialog received `detail: 2` and `handleFileClick` read it as a
double-click. Fixed by the sequence anchor in
web/app/(authenticated)/files/page.tsx and gated, by execution against real
Chrome, in web/scripts/gates/detail_counts_the_gesture_not_the_element.mjs.
The `dismissModal` work here was driven before and after: both arms opened the
file. It repairs nothing about that bug and is kept on its own merits.

What this gate DOES pin, which is worth pinning on its own: every portaled
modal routes its dismiss/commit handlers through `dismissModal`, and that
helper keeps both halves (stopPropagation + a deferred commit). A modal's
click staying self-contained is cheap and decouples a dialog from the surface
it floats over. What decays silently is the roster — the next modal is written
by copying a sibling, and a copy of a pre-fix sibling reintroduces the bare
shape with nothing to notice.

Pure-Python script per ADR-236 Rule 3 (no JS test runner). Run with:
    python3 -B api/test_modal_dismiss_does_not_reach_underneath.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB = REPO_ROOT / "web"

Z_TIERS = WEB / "lib" / "shell" / "z-tiers.ts"

# The portaled modals that sit over a clickable surface and unmount on the same
# click that commits or cancels them. Enumerated rather than globbed: a portal
# that does NOT unmount on its own click (a persistent panel) has no exposure,
# and sweeping every `createPortal` would red-flag those falsely.
GUARDED_MODALS = [
    WEB / "contexts" / "FeedbackContext.tsx",
    WEB / "components" / "workspace" / "RenameModal.tsx",
    WEB / "components" / "workspace" / "NewFolderModal.tsx",
    WEB / "components" / "workspace" / "WorkspacePicker.tsx",
]

failures: list[str] = []
checks = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global checks
    checks += 1
    if ok:
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label}" + (f"\n         {detail}" if detail else ""))
        failures.append(label)


def strip_comments(src: str) -> str:
    """Comments must never satisfy a substring check.

    This gate's own subject is heavily commented — the rule is explained at
    length in z-tiers.ts and cited in each modal. Matching those prose mentions
    would make every check pass on documentation alone.
    """
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"^\s*//.*$", "", src, flags=re.M)
    return src


print("\n=== 1. The helper exists and keeps BOTH halves ===")

if not Z_TIERS.exists():
    check("z-tiers.ts exists", False, f"missing: {Z_TIERS}")
else:
    z_src = strip_comments(Z_TIERS.read_text())
    check("z-tiers exports dismissModal", "export function dismissModal" in z_src)

    # Isolate the helper body so the assertions below cannot be satisfied by
    # unrelated code elsewhere in the module.
    # Match from the declaration to the first column-0 `}` — the signature
    # itself contains `)` (`fn: () => void`), so a `[^)]*` param match stops
    # short and silently hands every check below an EMPTY body. That is how
    # this gate first ran: 3 vacuous checks reported as failures rather than
    # as passes, which is the only reason it was caught.
    m = re.search(
        r"export function dismissModal\b(.*?)^\}", z_src, flags=re.S | re.M
    )
    body = m.group(1) if m else ""
    check("dismissModal body is parseable", bool(m))

    # THE TWO HALVES, and what each actually buys:
    #   - stopPropagation keeps the commit off an ANCESTOR handler while the
    #     modal is still mounted.
    #   - the deferred call keeps the state change from interleaving with the
    #     rest of THIS gesture's dispatch.
    # Neither is proven load-bearing against the reported bug — see the
    # docstring. They are kept because a self-contained modal click is cheap.
    check("half 1 — stops propagation", "stopPropagation()" in body)
    check(
        "half 2 — defers the commit past THIS click's dispatch",
        "requestAnimationFrame" in body,
        "a synchronous commit interleaves with the rest of the gesture's dispatch",
    )

print("\n=== 2. Every guarded modal routes its dismiss through the helper ===")

for path in GUARDED_MODALS:
    name = path.name
    if not path.exists():
        check(f"{name} exists", False, f"missing: {path}")
        continue

    src = strip_comments(path.read_text())

    check(f"{name} imports dismissModal", "dismissModal" in src)

    # THE BARE-HANDLER SWEEP — the check with teeth.
    #
    # A dismissing handler passed bare (`onClick={onClose}`) is exactly the
    # pre-fix shape, and exactly what a copy-paste of a pre-fix sibling
    # reproduces. Anything that closes or commits must be wrapped.
    bare = re.findall(
        r"onClick=\{(onClose|onCancel|onConfirm|submit)\}",
        src,
    )
    check(
        f"{name} has no bare dismissing onClick",
        not bare,
        f"bare handler(s): {sorted(set(bare))} — wrap in dismissModal(...)",
    )

    # The backdrop is the one every modal has and the easiest to forget, since
    # it reads as decoration rather than a control.
    if "fixed inset-0 bg-black/50" in src:
        check(
            f"{name} backdrop dismiss is wrapped",
            re.search(r"onClick=\{dismissModal\(", src) is not None,
        )

print("\n=== 3. The rule is documented where the layering contract lives ===")

# The dismissal rule and the z-ladder are two halves of one contract: layering
# decides who receives a click while both are mounted, dismissal decides who
# receives it once the top layer stops existing. Splitting them is how the
# second half gets lost.
if Z_TIERS.exists():
    raw = Z_TIERS.read_text()
    # The falsification is the most valuable thing in that comment: without it
    # the next reader re-derives the seductive wrong story and "fixes" it again.
    check(
        "z-tiers records the FALSIFIED claim, not just the rule",
        "falsified" in raw.lower(),
        "the wrong diagnosis must stay written down, or it gets re-invented",
    )

print("\n" + "=" * 62)
print(f"{checks - len(failures)}/{checks} checks passed")
if failures:
    print("\nFAILED:")
    for f in failures:
        print(f"  - {f}")
    print(
        "\nNOTE: this gate pins STRUCTURE only, and the modal work is hardening "
        "rather than a diagnosed fix — see the module docstring."
    )
    sys.exit(1)
print("\nAll structural checks green. (Structure only — see the docstring on scope.)")
sys.exit(0)
