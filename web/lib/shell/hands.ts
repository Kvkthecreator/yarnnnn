/**
 * Local hands — the page's side of the browser tools (ADR-662 D6/D14/D15).
 *
 * The browser tools are performed by an EXECUTOR on the member's own machine,
 * never by the server. This file finds the one this page can reach and is the
 * only place the page talks to it:
 *
 *  - In Chrome (or Edge, Brave, Arc): the **yarnnn extension**, reached with
 *    `chrome.runtime.sendMessage(CHROME_EXTENSION.id, …)`. It works in the
 *    member's own Chrome, with their sign-ins, in a tab group of its own, and
 *    asks once per site (`extension/`).
 *  - In the desktop app: the **host** (`src-tauri/src/hands/`), reached with
 *    Tauri's `invoke` — which relays each act to that same extension over
 *    Chrome's native messaging. The host performs nothing itself.
 *
 * Either way the extension performs the act and draws the consent; the page
 * can only ask. The contract is `{success, receipt, record}` per act.
 *
 *  - `browserHands()` — which executor this page has, and whether the member
 *    has it on. A turn asks for the browser tools only when it is on, naming
 *    the extension's version (`executor`) so the server can decide.
 *  - `performClientTool()` — one act the server handed to this page mid-turn:
 *    the executor performs it, and the result is posted back to the waiting
 *    turn with the turn's nonce. A declared run's `sites` ride with the act
 *    (ADR-668 D8), so the executor can refuse where the tab IS.
 *
 *  - `setBrowserHands()` — the Settings switch. OFF applies at once; ON is the
 *    member's to say in a window the EXTENSION draws (ADR-663 D4) — the page
 *    can ask, never switch it on by itself. The site lists stay in the
 *    extension's toolbar button.
 */

import { isNativeShell } from "./external-navigation";

/** The yarnnn Chrome extension. The id is fixed by the public `key` in
 *  `extension/manifest.json`, so an unpacked build and a published one share
 *  it. `storeUrl` stays null until a published listing exists — and ADR-661's
 *  tripwire keeps it null until ADR-662 is Accepted. */
export const CHROME_EXTENSION = {
  id: "apafdkhjahbjdmlfmpdgmjfbanmchoae",
  storeUrl: null as string | null,
};

export type ClientToolFrame = {
  call_id: string;
  name: string;
  arguments: Record<string, unknown>;
  nonce: string;
  /** ADR-668 D8 — a declared run's scope (bare hosts); absent on a chat turn. */
  sites?: string[];
};

/** What an act changed, for the member's own language (the server persists
 *  it beside the model's sentence). */
export type ActRecord = { act: string; subject: string; changed: boolean };

/** `connected`: the extension answers this page (directly, or through the
 *  desktop app). `on`: connected AND its switch is on. */
export type BrowserHands =
  | { executor: "host"; connected: boolean; on: boolean; version?: string }
  | { executor: "extension"; connected: true; on: boolean; version: string }
  | { executor: null; on: false; hostTooOld?: boolean };

type ChromeRuntime = {
  sendMessage: (id: string, msg: unknown, cb: (reply: unknown) => void) => void;
  lastError?: unknown;
};

function chromeRuntime(): ChromeRuntime | null {
  if (typeof window === "undefined") return null;
  const runtime = (window as unknown as { chrome?: { runtime?: ChromeRuntime } }).chrome?.runtime;
  // Chrome exposes `runtime.sendMessage` to a page only when an installed
  // extension lists that page in `externally_connectable`.
  return runtime && typeof runtime.sendMessage === "function" ? runtime : null;
}

function toExtension<T>(msg: unknown, timeoutMs: number): Promise<T | null> {
  const runtime = chromeRuntime();
  if (!runtime) return Promise.resolve(null);
  return new Promise((resolve) => {
    const timer = setTimeout(() => resolve(null), timeoutMs);
    try {
      runtime.sendMessage(CHROME_EXTENSION.id, msg, (reply) => {
        clearTimeout(timer);
        // Reading lastError is what tells Chrome the failure was handled.
        resolve(runtime.lastError ? null : ((reply as T) ?? null));
      });
    } catch {
      clearTimeout(timer);
      resolve(null);
    }
  });
}

async function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  // Imported dynamically: `@tauri-apps/api` must stay out of the web chunk.
  const { invoke: tauriInvoke } = await import("@tauri-apps/api/core");
  return tauriInvoke<T>(cmd, args);
}

/** How long a whole act may take in the extension: a consent question the
 *  member answers, then a page load. The server fails the act closed at its
 *  own bound (`client_tools.ACT_TIMEOUT_S`) either way. */
const ACT_TIMEOUT_MS = 180_000;

export async function browserHands(): Promise<BrowserHands> {
  if (isNativeShell()) {
    try {
      const status = await invoke<{ extension?: boolean; version?: string | null; enabled?: boolean | null }>(
        "hands_status",
      );
      // A host before the relay (0.3.x, the retired pane) answers another shape.
      if (typeof status?.extension !== "boolean") return { executor: null, on: false, hostTooOld: true };
      return {
        executor: "host",
        connected: status.extension,
        // A host before 0.4.2 does not report the switch: count it on, and
        // the extension still refuses an act while it is off.
        on: status.extension && status.enabled !== false,
        version: status.version ?? undefined,
      };
    } catch {
      return { executor: null, on: false, hostTooOld: true };
    }
  }
  const hello = await toExtension<{ ok?: boolean; enabled?: boolean; version?: string }>(
    { type: "hello" },
    1_500,
  );
  if (hello?.ok && typeof hello.version === "string") {
    return { executor: "extension", connected: true, on: hello.enabled === true, version: hello.version };
  }
  return { executor: null, on: false };
}

/** What a turn adds to its request when this page can act in a browser. */
export async function clientToolsRequest(): Promise<Record<string, unknown>> {
  const hands = await browserHands();
  if (!hands.on) return {};
  return hands.executor === "extension"
    ? { client_tools: ["browser"], executor: `extension/${hands.version}` }
    : { client_tools: ["browser"] };
}

/** The Settings switch — see the file header. Resolves to the switch's state
 *  after the ask (still off when the member declined in the extension). */
export async function setBrowserHands(enabled: boolean): Promise<boolean> {
  try {
    const reply = isNativeShell()
      ? await invoke<{ enabled?: boolean }>("hands_set_enabled", { enabled })
      : await toExtension<{ enabled?: boolean }>({ type: "setEnabled", enabled }, ACT_TIMEOUT_MS);
    return reply?.enabled === true;
  } catch {
    return false;
  }
}

async function act(frame: ClientToolFrame): Promise<Record<string, unknown>> {
  const args = frame.arguments ?? {};
  // ADR-668 D8 — the run's scope goes with the act. The extension refuses an
  // act outside it where the tab IS; the server refused only what BrowserOpen
  // named. A host that does not yet forward `sites` (≤0.4.3) drops the key,
  // and the act is gated as before.
  const sites = Array.isArray(frame.sites) && frame.sites.length > 0 ? frame.sites : undefined;
  if (isNativeShell()) {
    return invoke<Record<string, unknown>>("browser_act", { tool: frame.name, args, ...(sites ? { sites } : {}) });
  }
  const reply = await toExtension<Record<string, unknown>>(
    { type: "act", tool: frame.name, args, ...(sites ? { sites } : {}) },
    ACT_TIMEOUT_MS,
  );
  if (!reply) throw new Error("the yarnnn extension did not answer");
  return reply;
}

/**
 * Perform one act the server handed to this page, and post the result to the
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
    result = await act(frame);
  } catch (err) {
    result = {
      success: false,
      error: "executor_failed",
      receipt: `The browser could not perform this: ${String((err as Error)?.message ?? err)}`,
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
