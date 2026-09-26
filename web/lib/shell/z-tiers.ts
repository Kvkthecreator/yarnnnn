/**
 * Z-tier ladder — ADR-297 D18.
 *
 * Canonical z-index constants for the shell. ONE source of truth.
 * Every shell component imports from here; no hardcoded z-* classes
 * or inline zIndex values anywhere else in web/components/shell/.
 *
 * The ladder (bottom to top):
 *
 *   WINDOW_Z_BASE          10    Window z-baseline (D15)
 *   WINDOW_Z_BASE + N      11..  Raised windows (capped at +WINDOW_Z_MAX)
 *   WINDOW_Z_BASE +99     109    Window z-cap (D18 — never exceed)
 *   Z_POPOVER             200    UserMenu / TopBar context menu / bell popover
 *   Z_LAUNCHER_OVERLAY    400    Launcher search overlay (D4 + D11)
 *
 * The launcher tier (400) is high enough that windows can never reach it
 * — the launcher always wins when summoned.
 *
 * Z-cap rationale: `windowState.z` increments on every raiseWindow
 * call. Without a cap, after dozens of raise events the value drifts
 * arbitrarily high — easily exceeding 50 (the pre-D18 launcher tier),
 * which is what triggered the operator-observed "launcher gets
 * covered by windows" bug. D18 caps the z value at WINDOW_Z_MAX and
 * compacts the values back to 1..N when the cap is hit, preserving
 * relative order without unbounded growth.
 */

// Window stack — baseline + cap.
export const WINDOW_Z_BASE = 10;
export const WINDOW_Z_MAX = 99;

// Above the window stack.
export const Z_POPOVER = 200;

// Topmost shell overlay — operator-summoned, must win.
export const Z_LAUNCHER_OVERLAY = 400;

// Universal feedback layer (ADR-400 polish, 2026-07-03). Toasts + the
// blocking confirm dialog float above EVERYTHING — including the launcher —
// because they report the outcome of / gate an action the operator just took,
// and must never be occluded by the surface they were triggered from. The
// confirm dialog sits one tier above its own backdrop.
export const Z_CONFIRM_BACKDROP = 500;
export const Z_CONFIRM_DIALOG = 501;
export const Z_TOAST = 550;

/**
 * A dialog opened FROM a confirm-tier dialog — the folder picker inside a
 * create door, and nothing else so far.
 *
 * ⚠️ IT SITS BELOW `Z_TOAST` ON PURPOSE. A toast reports the outcome of what
 * the member just did and must never be occluded (the note above), so a nested
 * picker that outranked it would hide its own failure message. Above the
 * confirm tier, below the feedback layer.
 *
 * Without this, a nested picker's BACKDROP shares `Z_CONFIRM_BACKDROP` with
 * the dialog it was opened from and therefore renders behind it: the picker
 * appears on top (later in DOM order) while the form beneath stays at full
 * contrast, so the two read as one layer. Driven 2026-09-21.
 */
export const Z_NESTED_BACKDROP = 520;
export const Z_NESTED_DIALOG = 521;

// ---------------------------------------------------------------------------
// The dismissal half of the modal contract (2026-09-13)
// ---------------------------------------------------------------------------

/**
 * A MODAL'S COMMITTING CLICK ENDS AT THE MODAL.
 *
 * Hardening, NOT a diagnosed fix — the distinction is recorded because the
 * commit that added this began from a WRONG diagnosis and the wrong one is
 * seductive.
 *
 * The claim that was falsified: "the portal unmounts inside the click's own
 * dispatch, so the click re-targets onto the row underneath." It does not.
 * Removing an element during `mousedown`, or during its own `click` handler,
 * leaves the original target intact — the browser does not re-dispatch to
 * whatever is revealed. Driven in Chrome both ways, 2026-09-13. Any future
 * reader tempted by that story should re-run it before believing it.
 *
 * What IS true and worth keeping:
 *   - A modal button sits dead-centre over the Files listing (measured: the
 *     confirm's centre and the page centre are the same point), so anything
 *     that does leak past it lands on a row, and a row is
 *     `<button onClick={onNavigate}>` -> `openPath` -> another surface.
 *   - `stopPropagation` keeps the commit off any ancestor handler.
 *   - Deferring the commit past the current event means the state change
 *     cannot interleave with the rest of THIS gesture's dispatch.
 *
 * Neither is load-bearing against a proven bug today; together they make the
 * modal's click self-contained, which is cheap and removes a class of
 * coupling between a dialog and the surface it floats over.
 *
 * THE REPORTED BUG WAS SOMETHING ELSE, and is now fixed elsewhere. Settled by
 * CDP 2026-09-13: `MouseEvent.detail` counts the GESTURE, not the element —
 * Chrome does not reset its multi-click counter when the thing under the
 * pointer changes between two presses at one point, so the row under the
 * dismissed dialog received `detail: 2` and `handleFileClick` read it as a
 * double-click. The fix is the sequence anchor in
 * app/(authenticated)/files/page.tsx, gated by
 * web/scripts/gates/detail_counts_the_gesture_not_the_element.mjs.
 *
 * `dismissModal` does NOT fix that — driven before and after, both arms opened
 * the file. It is kept because a self-contained modal click is worth having on
 * its own, not because it repairs anything.
 *
 * A z-tier does not speak to any of this: layering decides who receives a
 * click while both are mounted. This lives beside the ladder because it is the
 * other half of the same question, not because a tier implies it.
 */
export function dismissModal(fn: () => void) {
  return (e: { preventDefault: () => void; stopPropagation: () => void }) => {
    e.preventDefault();
    e.stopPropagation();
    // Past the dispatch of THIS click — the state change cannot interleave
    // with the rest of this gesture.
    requestAnimationFrame(() => fn());
  };
}
