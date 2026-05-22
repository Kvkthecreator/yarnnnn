/**
 * Z-tier ladder — ADR-297 D18.
 *
 * Canonical z-index constants for the shell. ONE source of truth.
 * Every shell component imports from here; no hardcoded z-* classes
 * or inline zIndex values anywhere else in web/components/shell/.
 *
 * The ladder (bottom to top):
 *
 *   Z_DESKTOP_FAB           5    Desktop layer FAB (D17)
 *   WINDOW_Z_BASE          10    Window z-baseline (D15)
 *   WINDOW_Z_BASE + N      11..  Raised windows (capped at +WINDOW_Z_MAX)
 *   WINDOW_Z_BASE +99     109    Window z-cap (D18 — never exceed)
 *   Z_DRAWER_BACKDROP     100    ChatDrawer backdrop (D16)
 *   Z_DRAWER_BODY         101    ChatDrawer body (D16)
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
 * Z-cap rationale: `windowState.z` increments on every raiseWindow
 * call. Without a cap, after dozens of raise events the value drifts
 * arbitrarily high — easily exceeding 50 (the pre-D18 launcher tier),
 * which is what triggered the operator-observed "launcher gets
 * covered by windows" bug. D18 caps the z value at WINDOW_Z_MAX and
 * compacts the values back to 1..N when the cap is hit, preserving
 * relative order without unbounded growth.
 */

// Below the window stack.
export const Z_DESKTOP_FAB = 5;

// Window stack — baseline + cap.
export const WINDOW_Z_BASE = 10;
export const WINDOW_Z_MAX = 99;

// Above the window stack.
export const Z_DRAWER_BACKDROP = 100;
export const Z_DRAWER_BODY = 101;
export const Z_POPOVER = 200;

// Topmost shell overlay — operator-summoned, must win.
export const Z_LAUNCHER_OVERLAY = 400;
