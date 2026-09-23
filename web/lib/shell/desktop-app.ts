/**
 * The desktop app's downloads — the ONE place a published build is switched on
 * (ADR-661; ADR-662's "desktop features are first-class", operator 2026-09-23).
 *
 * ## Where the file lives, and the address a person is given
 *
 * Each build is an object in our own public Supabase Storage bucket,
 * `desktop-releases` (supabase/migrations/261), uploaded by
 * `scripts/publish-desktop-release.sh` under a STABLE name that every release
 * overwrites. The URLs below therefore never change between releases.
 *
 * Nobody is handed those URLs. Every link — the /download page, Settings →
 * Desktop app — points at `downloadPath(platform)`, our own
 * `/download/{platform}`, which redirects here
 * (`app/download/[platform]/route.ts`). Two reasons:
 *   · The file can move (a CDN, a signed-build store) without breaking a link
 *     anyone has shared or bookmarked.
 *   · The installed app's opener scope already allows `www.yarnnn.com`, so the
 *     in-app Download works on every host ever shipped. A storage URL would
 *     open nothing until a new host widened its scope.
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

/** The file each platform's `/download/{platform}` redirects to; `null` = not
 *  published. The bucket's public path plus the platform's asset name; set it
 *  only once the file has been published, or the link is a 404. */
export const DESKTOP_DOWNLOADS: Record<DesktopPlatform, string | null> = {
  mac: "https://noxgqcwynkzqabljjyon.supabase.co/storage/v1/object/public/desktop-releases/yarnnn-mac-arm64.dmg",
  windows: "https://noxgqcwynkzqabljjyon.supabase.co/storage/v1/object/public/desktop-releases/yarnnn-windows-x64-setup.exe",
};

/** Our own address for a platform's download, or `null` if unpublished. Relative:
 *  in the desktop app, prefix `webOrigin()` before handing it to the opener. */
export function downloadPath(platform: DesktopPlatform): string | null {
  return DESKTOP_DOWNLOADS[platform] ? `/download/${platform}` : null;
}

export function isDesktopPlatform(value: string): value is DesktopPlatform {
  return (DESKTOP_PLATFORMS as readonly string[]).includes(value);
}
