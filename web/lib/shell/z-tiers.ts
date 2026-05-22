/**
 * Z-tier ladder — ADR-297 D18 + D19.5.1.
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
 *   Z_DRAWER_BACKDROP     100    ChatDrawer backdrop (D16)
 *   Z_DRAWER_BODY         101    ChatDrawer body (D16)
 *   Z_FAB                 150    ChatDrawer FAB (D19.5.1 — viewport-fixed,
 *                                floats above windows)
 *   Z_POPOVER             200    UserMenu / TopBar context menu / cap-hit toast
 *   Z_LAUNCHER_OVERLAY    400    Launcher search overlay (D4 + D11)
 *
 * Note: Z_DRAWER_BACKDROP (100) intentionally falls between WINDOW_Z_MAX
 * (effective 109) and Z_POPOVER (200). Windows can raise above the
 * drawer backdrop if there are enough open windows, but the
 * Z_LAUNCHER_OVERLAY (400) is high enough that windows can never reach
 * it — the launcher always wins when summoned. This matches the
 * operator's intent: the launcher is a deliberate summon affordance;
 * the drawer is a context-aware overlay; windows are content.
 *
 * D19.5.1 (2026-05-22): Z_DESKTOP_FAB (was 5, below windows) DELETED.
 * Replaced by Z_FAB (150, above windows). The FAB is a workspace-level
 * universal summon affordance — it must float above everything except
 * the operator-summoned launcher overlay. Pre-D19.5.1 the FAB sat at
 * z=5 inside the Desktop layer and got covered by every window
 * (operator-felt bug). The FAB is also viewport-fixed now (was
 * Desktop-fixed), so it stays at viewport bottom-right regardless of
 * the Desktop's coordinate frame.
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
export const Z_DRAWER_BACKDROP = 100;
export const Z_DRAWER_BODY = 101;
// D19.5.1: FAB floats above windows + above drawer backdrop. Drawer
// body (101) covers FAB visually when open — the FAB is hidden via
// pointer-events + opacity when the drawer is open anyway, so the
// visual stacking doesn't matter operationally.
export const Z_FAB = 150;
export const Z_POPOVER = 200;

// Topmost shell overlay — operator-summoned, must win.
export const Z_LAUNCHER_OVERLAY = 400;
