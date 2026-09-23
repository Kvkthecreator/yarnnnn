/**
 * Local hands, the browser first — ADR-662 D6/D14.
 *
 * The desktop app's host owns a browser pane the agent can work in. This file
 * is the page's side of it, and the only place the page talks to that part
 * of the host:
 *
 *  - `browserHandsOn()` — whether this is the desktop app, its host carries
 *    the pane, and the member switched it on there. A turn asks for the
 *    browser tools only when this is true; the server still decides by the
 *    host's version (`client_tools.offered`).
 *  - `enableBrowserHands()` / `disableBrowserHands()` — the Settings switch.
 *    Enabling asks the HOST, which draws the consent dialog the member answers
 *    (ADR-663 D4); the page cannot switch it on by itself.
 *  - `performClientTool()` — one act the server handed to this app mid-turn:
 *    the host performs it, and its result is posted back to the waiting turn
 *    with the turn's nonce.
 *
 * Off the desktop app, or on a host older than the pane, every function here
 * answers "no" — an older host has no such command, and the call rejects.
 */

import { isNativeShell } from "./external-navigation";

export type ClientToolFrame = {
  call_id: string;
  name: string;
  arguments: Record<string, unknown>;
  nonce: string;
};

/** What an act changed, for the member's own language (the server persists
 *  it beside the model's sentence). */
export type ActRecord = { act: string; subject: string; changed: boolean };

async function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  // Imported dynamically: `@tauri-apps/api` must stay out of the web chunk.
  const { invoke: tauriInvoke } = await import("@tauri-apps/api/core");
  return tauriInvoke<T>(cmd, args);
}

export async function browserHandsOn(): Promise<boolean> {
  if (!isNativeShell()) return false;
  try {
    const status = await invoke<{ browser?: boolean }>("hands_status");
    return status?.browser === true;
  } catch {
    return false; // a host older than the pane
  }
}

/** True when this host carries the pane at all — whether or not it is on. */
export async function browserHandsAvailable(): Promise<boolean> {
  if (!isNativeShell()) return false;
  try {
    await invoke("hands_status");
    return true;
  } catch {
    return false;
  }
}

export async function enableBrowserHands(): Promise<boolean> {
  try {
    return await invoke<boolean>("hands_enable");
  } catch {
    return false;
  }
}

export async function disableBrowserHands(): Promise<void> {
  try {
    await invoke("hands_disable");
  } catch {
    /* nothing to switch off on this host */
  }
}

/**
 * Perform one act the server handed to this app, and post the result to the
 * turn waiting for it. Never throws: a failure becomes a result the model can
 * read, because a turn that never hears back only fails closed after its
 * timeout.
 */
export async function performClientTool(
  laneId: string,
  frame: ClientToolFrame,
  post: (path: string, body: unknown) => Promise<unknown>,
): Promise<void> {
  let result: Record<string, unknown>;
  try {
    result = await invoke<Record<string, unknown>>("browser_act", {
      tool: frame.name,
      args: frame.arguments ?? {},
    });
  } catch (err) {
    result = {
      success: false,
      error: "host_failed",
      receipt: `The desktop app could not perform this: ${String((err as Error)?.message ?? err)}`,
      record: { act: "failed", subject: "", changed: false },
    };
  }
  try {
    await post(`/api/lanes/${laneId}/tool-results/${encodeURIComponent(frame.call_id)}`, {
      nonce: frame.nonce,
      result,
    });
  } catch {
    /* the turn ended (stopped, or timed out) — nothing is waiting */
  }
}
