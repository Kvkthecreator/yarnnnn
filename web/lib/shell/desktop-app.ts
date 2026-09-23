/**
 * The desktop app's downloads — the ONE place a published build is switched on
 * (ADR-661; ADR-662's "desktop features are first-class", operator 2026-09-23).
 *
 * A link goes here only for a SIGNED build. An unsigned one downloads and then
 * tells a stranger it is "damaged" (macOS) or "unrecognized" (Windows), which
 * reads as malware — worse than no link. Until then the entry is `null` and the
 * Settings pane says it is not published yet; it never shows a dead link.
 * How to cut and sign each build: docs/infrastructure/publishing-the-desktop-app.md.
 *
 * The roster is listed, never chosen for the visitor: the client does not
 * detect a platform (ADR-661 §7.6), so the pane shows every entry.
 */
export const DESKTOP_PLATFORMS = ["mac", "windows"] as const;
export type DesktopPlatform = (typeof DESKTOP_PLATFORMS)[number];

/** Proper names, not copy: they read the same in every language, so they are
 *  not catalog entries (ADR-660 — identifiers are not translated). */
export const DESKTOP_PLATFORM_NAMES: Record<DesktopPlatform, string> = {
  mac: "Mac",
  windows: "Windows",
};

export const DESKTOP_DOWNLOADS: Record<DesktopPlatform, string | null> = {
  mac: null,
  windows: null,
};
