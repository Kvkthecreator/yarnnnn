/**
 * The desktop app's downloads — the ONE place a published build is switched on
 * (ADR-661; ADR-662's "desktop features are first-class", operator 2026-09-23).
 *
 * ## Where the file lives, and the address a person is given
 *
 * Each build is an asset on a GitHub Release of this repo, cut and uploaded by
 * `scripts/publish-desktop-release.sh` under a STABLE asset name. GitHub's
 * `releases/latest/download/<name>` then always serves the newest build, so the
 * URLs below never change between releases.
 *
 * Nobody is handed those URLs. Every link — the /download page, Settings →
 * Desktop app, the in-app update notice — points at `downloadPath(platform)`,
 * our own `/download/{platform}`, which redirects here
 * (`app/download/[platform]/route.ts`). Two reasons:
 *   · The host can move (a CDN, a signed-build store) without breaking a link
 *     anyone has shared or bookmarked.
 *   · The installed app's opener scope already allows `www.yarnnn.com`, so the
 *     in-app Download works on every host ever shipped. A github.com link
 *     would open nothing until a new host widened its scope.
 *
 * ## Unsigned, during the beta (operator ruling, 2026-09-23)
 *
 * The builds are not yet signed by Apple or by a Windows certificate. The
 * operator ruled to publish them anyway while yarnnn is in beta, WITH the
 * /download page saying so and showing the one step each needs to open. A
 * link to an unsigned build without that page in front of it is the trap the
 * earlier rule guarded against — so every link goes through the page's
 * platform, never straight to an asset. Signing, when it lands, changes the
 * page's words and nothing here.
 * How to cut, sign and publish: docs/infrastructure/publishing-the-desktop-app.md.
 *
 * The roster is listed, never chosen for the visitor: the client does not
 * detect a platform (ADR-661 §7.6), so every surface shows every entry.
 */
export const DESKTOP_PLATFORMS = ["mac", "windows"] as const;
export type DesktopPlatform = (typeof DESKTOP_PLATFORMS)[number];

/** Proper names, not copy: they read the same in every language, so they are
 *  not catalog entries (ADR-660 — identifiers are not translated). */
export const DESKTOP_PLATFORM_NAMES: Record<DesktopPlatform, string> = {
  mac: "Mac",
  windows: "Windows",
};

/** The stable name each platform's build is uploaded under — the roster in
 *  `scripts/publish-desktop-release.sh`. The ADR-661 gate holds the two in
 *  step, and holds every published URL below to end in its platform's name. */
export const DESKTOP_ASSET_NAMES: Record<DesktopPlatform, string> = {
  mac: "yarnnn-mac-arm64.dmg",
  windows: "yarnnn-windows-x64-setup.exe",
};

/** The asset each platform's `/download/{platform}` redirects to; `null` = not
 *  published. To publish, write the literal
 *  `https://github.com/Kvkthecreator/yarnnnn/releases/latest/download/<name>`
 *  — only once that release exists, or the link is a 404. */
export const DESKTOP_DOWNLOADS: Record<DesktopPlatform, string | null> = {
  mac: null,
  windows: null,
};

/** Our own address for a platform's download, or `null` if unpublished. Relative:
 *  in the desktop app, prefix `webOrigin()` before handing it to the opener. */
export function downloadPath(platform: DesktopPlatform): string | null {
  return DESKTOP_DOWNLOADS[platform] ? `/download/${platform}` : null;
}

export function isDesktopPlatform(value: string): value is DesktopPlatform {
  return (DESKTOP_PLATFORMS as readonly string[]).includes(value);
}
