/**
 * Leaving the product — the one way (ADR-661 §4.3, §8 step 3).
 *
 * Seven call sites hand the member to a URL yarnnn does not own: four OAuth
 * authorizations (a platform's consent screen) and three payment pages (the
 * processor's checkout and portal). On the web `window.location.href` is
 * right — the member leaves in the same tab and the platform's redirect brings
 * them back.
 *
 * In a packaged shell it is wrong, and wrong in the way that is hardest to
 * recover from: the app's own window navigates to a page that is not the app,
 * inside a frame with no address bar, no back button and no tabs. The member
 * is stranded, and the only exit is to quit. A native app opens these in the
 * SYSTEM BROWSER instead, where the member already has their platform logins,
 * a back button, and somewhere to go when they change their mind.
 *
 * WHY A HELPER AND NOT A BRANCH AT EACH SITE. There is one question here —
 * *does this act leave the product?* — and it has one answer per build. Seven
 * hand-written branches would be seven chances to forget, and forgetting reads
 * as fine on the web (the failure only appears once packaged), which is the
 * silent-drift shape ADR-592 names.
 *
 * ADR-661 §7.6: this decides a BEHAVIOUR, unlike `modifier-key.ts` which
 * decides a printed name. It is keyed on the host being a native shell, never
 * on the operating system — a Mac and a Windows shell take the same branch,
 * and the web build on a Mac does not.
 */

/**
 * True when the page is running inside the packaged shell rather than a
 * browser tab.
 *
 * Tauri injects `__TAURI_INTERNALS__` (v2) / `__TAURI__` (v1) on `window`
 * before any app code runs, so this is answerable synchronously and without
 * importing the Tauri SDK — which matters because the WEB bundle must not
 * carry a dependency that only exists in the shell. Until the shell ships this
 * is always false, so every call below behaves exactly as it does today.
 */
export function isNativeShell(): boolean {
  if (typeof window === "undefined") return false;
  const w = window as unknown as Record<string, unknown>;
  return "__TAURI_INTERNALS__" in w || "__TAURI__" in w;
}

/**
 * Hand the member to a URL the product does not own: an OAuth consent screen,
 * a checkout page, a processor's portal.
 *
 * On the web this is `window.location.href` — unchanged, so the platform's
 * redirect back into the app still works. In the shell it opens the system
 * browser and leaves the app window where it was, so the member still has the
 * product to come back to.
 *
 * Returning a boolean is deliberate: a caller that set a loading state needs
 * to know whether the member actually left (web — the page is going away and
 * the state does not matter) or stayed (shell — the state must be cleared, or
 * the button spins for ever behind a browser window the member may simply
 * close).
 */
export function openExternal(url: string): boolean {
  if (!url) return false;

  if (isNativeShell()) {
    // `window.open` with `_blank` is routed to the system browser by the
    // shell's own handler; the Tauri opener plugin is wired there, not here,
    // so this module stays importable from the web bundle.
    window.open(url, "_blank", "noopener,noreferrer");
    return false;
  }

  window.location.href = url;
  return true;
}

/**
 * The product's canonical WEB address, for links that leave this machine
 * (ADR-661 §4.4).
 *
 * A share link is pasted into a colleague's chat, an email, a ticket. It must
 * address the product on the web — `window.location.origin` is the address of
 * the window the link was COPIED IN, which in the packaged shell is a custom
 * scheme (`tauri://localhost`). That link is dead everywhere it is pasted,
 * including on the sender's own other devices, and nothing reports it: the
 * copy succeeds, the toast says it worked, and the defect surfaces only in
 * someone else's hands.
 *
 * ⭐ **A share link is a web address even when the shell is not.**
 *
 * `NEXT_PUBLIC_SITE_URL` is the same constant `lib/metadata.ts` uses for
 * canonical and OG URLs, so a link in a share and a link in a meta tag can
 * never name different hosts. The trailing slash is stripped so callers can
 * append a path without minting a double slash.
 */
export function webOrigin(): string {
  const configured = process.env.NEXT_PUBLIC_SITE_URL;
  if (configured) return configured.replace(/\/+$/, "");
  // No env var: on the web the current origin is correct and is what shipped
  // before this helper existed. In the shell it would be a custom scheme, so
  // fall back to the canonical host rather than mint a dead link.
  if (!isNativeShell() && typeof window !== "undefined") {
    return window.location.origin;
  }
  return "https://www.yarnnn.com";
}
