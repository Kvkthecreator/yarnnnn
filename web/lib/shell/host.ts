/**
 * The desktop host's identity, as the page sees it (ADR-663 D2/D3).
 *
 * The desktop app is the website in a native window (D1), so the PAGE is always
 * current and the only thing with a version is the host — the installed
 * program around it. The page asks the host for that version once and names it
 * on every API request, `X-Yarnnn-Client: desktop/X.Y.Z` (the shape of Claude
 * Code's `claude-cli/X.Y.Z`). The API refuses a host older than its minimum with
 * 426 `desktop_update_required`, and `UpdateNotice` says so in words.
 *
 * Off the desktop app every function here answers "no host": a browser sends no
 * header and is never refused.
 */

import { isNativeShell } from "./external-navigation";

export const CLIENT_HEADER = "X-Yarnnn-Client";

/** The event `request()` raises when the API refuses this host. */
export const DESKTOP_UPDATE_EVENT = "yarnnn:desktop-update-required";

let versionPromise: Promise<string | null> | null = null;

/** The host's version (`src-tauri/Cargo.toml`), or null off the desktop app. */
export function hostVersion(): Promise<string | null> {
  if (!isNativeShell()) return Promise.resolve(null);
  if (!versionPromise) {
    // Imported dynamically: `@tauri-apps/api` must stay out of the web chunk.
    versionPromise = import("@tauri-apps/api/app")
      .then(({ getVersion }) => getVersion())
      .catch(() => null);
  }
  return versionPromise;
}

/** The header to add to an API request — empty in a browser. */
export async function clientHeaders(): Promise<Record<string, string>> {
  const version = await hostVersion();
  return version ? { [CLIENT_HEADER]: `desktop/${version}` } : {};
}

/** Called by the API client on every failed response. One door: a 426 with the
 *  update code becomes an event the notice listens for. */
export function noticeHostRefusal(status: number, data: unknown): void {
  if (status !== 426 || typeof window === "undefined") return;
  const error = (data as { error?: { code?: unknown } } | null)?.error;
  if (error?.code !== "desktop_update_required") return;
  window.dispatchEvent(new CustomEvent(DESKTOP_UPDATE_EVENT));
}

/**
 * ADR-663 D6 — the host's own updater (`src-tauri/src/update.rs`) downloads and
 * verifies a new host in the background and installs it when the member quits.
 * The page may learn that one is waiting and ask for it NOW — never choose what
 * is installed. A host older than 0.4.3 has no updater: the command is refused,
 * so every function here answers "nothing waiting".
 */
export const HOST_UPDATE_EVENT = "update-ready";

async function hostInvoke<T>(cmd: string): Promise<T | null> {
  if (!isNativeShell()) return null;
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    return await invoke<T>(cmd);
  } catch {
    return null;
  }
}

/** The host version downloaded and waiting to install, or null. */
export function hostUpdateReady(): Promise<string | null> {
  return hostInvoke<string | null>("update_ready");
}

/** Call `handler` with the version when the host finishes downloading one. */
export async function onHostUpdateReady(handler: (version: string) => void): Promise<() => void> {
  if (!isNativeShell()) return () => {};
  try {
    const { listen } = await import("@tauri-apps/api/event");
    return await listen<string>(HOST_UPDATE_EVENT, (event) => {
      if (typeof event.payload === "string") handler(event.payload);
    });
  } catch {
    return () => {};
  }
}

/** Install the waiting host update now and relaunch into it. */
export function restartToUpdate(): Promise<unknown> {
  return hostInvoke("update_restart");
}
