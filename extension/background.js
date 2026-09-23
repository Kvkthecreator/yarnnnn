// yarnnn for Chrome — the executor of the browser tools (ADR-662 D15).
//
// A yarnnn page (the website in this Chrome) hands an act here with
// `chrome.runtime.sendMessage(EXTENSION_ID, {type: "act", tool, args})`; this
// worker performs it in the AGENT'S OWN TAB — opened in the background, kept in
// a tab group named "yarnnn", never the tab the member is using — and answers
// `{success, receipt, record}` the way every executor does:
//   - `receipt` is the model's sentence: what CHANGED, read back from the page
//     (ADR-662 D3), "no change observed" when nothing did;
//   - `record` is `{act, subject, changed}`, worded in the member's language by
//     the client (`chat.receipts`).
//
// The boundary:
//   - Only a yarnnn origin can reach this worker (`externally_connectable`,
//     checked again below).
//   - The agent acts on a site only after the member allowed it here, once
//     (`consent.html`, drawn by THIS extension — the page can only ask), and
//     never on a default-denied category (`policy.js`).
//   - The page routines are `page.js`, the same file the desktop pane runs; the
//     model's text reaches them only as JSON-encoded arguments.
//   - No clipboard, no screenshots, nothing outside the agent's tab.

import { YARNNN_ORIGINS, hostOf, verdictFor } from "./policy.js";

const VERSION = chrome.runtime.getManifest().version;
const LOAD_TIMEOUT_MS = 30_000;
const NAV_GRACE_MS = 1_500;
const CONSENT_TIMEOUT_MS = 120_000;
const GROUP_TITLE = "yarnnn";

// ---------------------------------------------------------------- settings

async function settings() {
  return chrome.storage.local.get({ enabled: true, allowed: [], denied: [] });
}

async function remember(list, host) {
  const s = await settings();
  const next = Array.from(new Set([...(s[list] || []), host]));
  await chrome.storage.local.set({ [list]: next });
}

// ---------------------------------------------------------------- consent

const pendingConsent = new Map();

/** Ask the member, in a window this extension draws, whether the agent may
 *  use `host`. Resolves true/false; no answer in time is a no. */
async function askConsent(host) {
  const id = crypto.randomUUID();
  const answer = new Promise((resolve) => {
    pendingConsent.set(id, resolve);
    setTimeout(() => {
      if (pendingConsent.delete(id)) resolve(false);
    }, CONSENT_TIMEOUT_MS);
  });
  await chrome.windows.create({
    url: chrome.runtime.getURL(`consent.html?id=${id}&host=${encodeURIComponent(host)}`),
    type: "popup",
    width: 440,
    height: 300,
    focused: true,
  });
  const allowed = await answer;
  await remember(allowed ? "allowed" : "denied", host);
  return allowed;
}

/** Null when the agent may act on `url`; otherwise the refusal to return. */
async function gate(url) {
  const host = hostOf(url);
  const s = await settings();
  const v = verdictFor(host, s);
  if (v.verdict === "allowed") return null;
  if (v.verdict === "ask" && (await askConsent(host))) return null;
  const why =
    v.category === "notAWebPage" ? "Only http and https pages can be used." :
    v.verdict === "ask" || v.category === "yours" ? `The member has not allowed ${host}.` :
    `${host} is in a category yarnnn never lets an agent use (${v.category}).`;
  return failure(`${why} Nothing was done there. Tell the member.`, "refused", host || "");
}

// ---------------------------------------------------------------- the agent's tab

async function agentTab() {
  const { tabId } = await chrome.storage.session.get("tabId");
  if (tabId == null) return null;
  try {
    return await chrome.tabs.get(tabId);
  } catch {
    return null;
  }
}

async function adopt(tab) {
  await chrome.storage.session.set({ tabId: tab.id });
  const groups = await chrome.tabGroups.query({ title: GROUP_TITLE, windowId: tab.windowId });
  const groupId = await chrome.tabs.group({ tabIds: [tab.id], ...(groups[0] ? { groupId: groups[0].id } : { createProperties: { windowId: tab.windowId } }) });
  if (!groups[0]) await chrome.tabGroups.update(groupId, { title: GROUP_TITLE, color: "purple", collapsed: false });
}

// A link that opens a new tab from the agent's tab moves the agent with it.
chrome.tabs.onCreated.addListener(async (tab) => {
  const current = await agentTab();
  if (current && tab.openerTabId === current.id) await adopt(tab);
});

/** Wait for the agent's tab to load. With `graceMs`, a load that has not
 *  STARTED within it means the act navigated nowhere: `{navigated: false}`. */
function settle(tabId, graceMs) {
  return new Promise((resolve) => {
    let started = false;
    let done = false;
    const finish = (navigated) => {
      if (done) return;
      done = true;
      chrome.tabs.onUpdated.removeListener(onUpdated);
      chrome.tabs.onCreated.removeListener(onCreated);
      resolve({ navigated });
    };
    // A page restored from the back/forward cache changes its address
    // WITHOUT a "loading" status, so an address change counts as a start too;
    // the end is then read off the tab rather than waited for as an event.
    const onUpdated = (id, change) => {
      if (id !== tabId) return;
      if (change.status === "loading" || change.url) {
        if (!started) {
          started = true;
          untilComplete(tabId).then(() => finish(true));
        }
      }
      if (change.status === "complete" && started) finish(true);
    };
    const onCreated = (tab) => {
      if (tab.openerTabId === tabId) {
        tabId = tab.id;
        started = true;
        untilComplete(tabId).then(() => finish(true));
      }
    };
    chrome.tabs.onUpdated.addListener(onUpdated);
    chrome.tabs.onCreated.addListener(onCreated);
    if (graceMs != null) setTimeout(() => !started && finish(false), graceMs);
    setTimeout(() => finish(started), LOAD_TIMEOUT_MS);
  });
}

async function untilComplete(tabId) {
  const until = Date.now() + LOAD_TIMEOUT_MS;
  while (Date.now() < until) {
    const t = await chrome.tabs.get(tabId);
    if (t.status === "complete" && t.url && t.url !== "about:blank") return;
    await new Promise((r) => setTimeout(r, 200));
  }
}

/** `page.js`, then one routine, in the extension's isolated world. */
async function run(tabId, routine, args = []) {
  await chrome.scripting.executeScript({ target: { tabId }, files: ["page.js"] });
  const [{ result }] = await chrome.scripting.executeScript({
    target: { tabId },
    func: (r, a) => window.__yarnnnHands[r](...a),
    args: [routine, args],
  });
  return JSON.parse(result);
}

function failure(receipt, act, subject) {
  return { success: false, receipt, record: { act, subject, changed: false } };
}

// ---------------------------------------------------------------- the acts

async function open(url) {
  const refused = await gate(url);
  if (refused) return refused;
  let tab = await agentTab();
  if (tab) {
    const loaded = settle(tab.id, null);
    await chrome.tabs.update(tab.id, { url });
    await loaded;
  } else {
    // A new tab is loading before any listener could know its id: wait on
    // its status instead.
    const win = await chrome.windows.getLastFocused({ windowTypes: ["normal"] }).catch(() => null);
    tab = await chrome.tabs.create({ url, active: false, ...(win ? { windowId: win.id } : {}) });
    await adopt(tab);
    await untilComplete(tab.id);
  }
  const now = await chrome.tabs.get(tab.id);
  const host = hostOf(now.url) || "";
  const title = now.title || host;
  return {
    success: true,
    title,
    url: now.url,
    receipt: `Opened “${title}” (${host}).`,
    record: { act: "opened", subject: title, changed: true },
  };
}

async function withTab(fn) {
  const tab = await agentTab();
  if (!tab) return failure("No page is open yet — use BrowserOpen first.", "failed", "");
  // The page may have moved to another site since it was allowed (a link,
  // a redirect): the gate is asked of where the tab IS, not where it was sent.
  const refused = await gate(tab.url);
  if (refused) return refused;
  return fn(tab);
}

async function read() {
  return withTab(async (tab) => {
    const page = await run(tab.id, "read");
    const n = (page.elements || []).length;
    return {
      ...page,
      success: true,
      receipt: `Read “${page.title}” — ${n} things to act on.`,
      record: { act: "read", subject: page.title, changed: false },
    };
  });
}

async function press(ref, fill) {
  return withTab(async (tab) => {
    const before = await run(tab.id, "state");
    const loaded = settle(tab.id, NAV_GRACE_MS);
    const done = fill
      ? await run(tab.id, "fill", [ref, fill.text, !!fill.submit])
      : await run(tab.id, "click", [ref]);
    const label = done.label || "";
    if (done.error === "stale_ref") return failure("That element is no longer on the page — read the page again for fresh refs.", "failed", "");
    if (done.error === "not_a_field") return failure(`“${label}” is not a field that takes text.`, "failed", label);
    if (done.error === "no_such_option") return failure(`“${label}” has no option with that text.`, "failed", label);
    const waitsForPage = !fill || done.submitted;
    const { navigated } = waitsForPage ? await loaded : { navigated: false };
    const nowTab = (await agentTab()) || tab;
    const after = navigated ? { url: nowTab.url, title: nowTab.title, sig: null } : await run(nowTab.id, "state");
    const changed = navigated || before.sig !== after.sig;
    const title = after.title || "";
    if (!fill) {
      return {
        success: true, changed, title, url: after.url,
        receipt: navigated ? `Pressed “${label}” — now on “${title}”.`
          : changed ? `Pressed “${label}” — the page changed.`
          : `Pressed “${label}” — no change observed.`,
        record: { act: "pressed", subject: label, changed },
      };
    }
    const matches = !!done.matches;
    let receipt = matches
      ? `Filled “${label}”; its value reads back as entered.`
      : `Tried to fill “${label}”, but its value did not read back as entered — no change observed.`;
    if (done.submitted) receipt += navigated ? ` Sent the form — now on “${title}”.` : " Sent the form.";
    return {
      success: matches, changed: matches || navigated, title, url: after.url,
      receipt,
      record: { act: "filled", subject: label, changed: matches },
    };
  });
}

async function back() {
  return withTab(async (tab) => {
    const loaded = settle(tab.id, NAV_GRACE_MS);
    // The page's own history.back(), not chrome.tabs.goBack: Chrome skips
    // history entries made without a user gesture for the browser's Back, and
    // every navigation the agent makes is gesture-less — goBack found "no next
    // page" after two real navigations (driven, 2026-09-23).
    await run(tab.id, "back");
    const { navigated } = await loaded;
    const now = await chrome.tabs.get(tab.id);
    return {
      success: navigated,
      receipt: navigated ? `Went back to “${now.title}”.` : "There was no earlier page to go back to — no change observed.",
      record: { act: "back", subject: now.title || "", changed: navigated },
    };
  });
}

/** One act by name — the executor contract every client calls. */
export async function perform(tool, args = {}) {
  const s = await settings();
  if (!s.enabled) {
    return failure(
      "The member has switched yarnnn off in Chrome, so nothing was done. Ask them to switch it on from the yarnnn button in Chrome's toolbar.",
      "refused", "",
    );
  }
  try {
    if (tool === "BrowserOpen") return await open(String(args.url || "").trim());
    if (tool === "BrowserRead") return await read();
    if (tool === "BrowserClick") return await press(Number(args.ref), null);
    if (tool === "BrowserFill") return await press(Number(args.ref), { text: String(args.text ?? ""), submit: args.submit });
    if (tool === "BrowserBack") return await back();
    return failure(`${tool} is not a browser act this extension performs.`, "refused", "");
  } catch (err) {
    return failure(`The browser could not do that: ${err?.message || err}`, "failed", "");
  }
}

// ---------------------------------------------------------------- the doors

chrome.runtime.onMessageExternal.addListener((msg, sender, sendResponse) => {
  if (!YARNNN_ORIGINS.includes(sender.origin)) return false;
  if (msg?.type === "hello") {
    settings().then((s) => sendResponse({ ok: true, version: VERSION, enabled: s.enabled }));
    return true;
  }
  if (msg?.type === "act") {
    perform(msg.tool, msg.args).then(sendResponse);
    return true;
  }
  return false;
});

// The desktop app reaches this worker through Chrome's native messaging: the
// app registers itself as `com.yarnnn.desktop` (src-tauri/src/hands/), and
// Chrome launches its bridge when we connect. When the app is not installed
// the port closes at once and nothing retries until the worker starts again;
// when the app is installed but not running, the bridge waits for it and
// sends {type: "app"} when it arrives. Acts from the app take the same
// `perform` — same gate, same consent, same tab — as acts from a yarnnn page.
const DESKTOP_HOST = "com.yarnnn.desktop";

function connectDesktop() {
  let port;
  try {
    port = chrome.runtime.connectNative(DESKTOP_HOST);
  } catch {
    return;
  }
  const hello = () => port.postMessage({ type: "hello", version: VERSION });
  port.onMessage.addListener(async (msg) => {
    if (msg?.type === "app") return hello();
    if (msg?.type === "act") {
      const result = await perform(msg.tool, msg.args);
      port.postMessage({ type: "result", id: msg.id, result });
    }
  });
  port.onDisconnect.addListener(() => {
    // Reading lastError marks it handled; "host not found" is the ordinary
    // answer when the desktop app is not installed.
    void chrome.runtime.lastError;
  });
  hello();
}
connectDesktop();

// The consent window answers here (an extension page, so an internal message).
chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg?.type !== "consent" || sender.id !== chrome.runtime.id) return;
  const resolve = pendingConsent.get(msg.id);
  if (resolve) {
    pendingConsent.delete(msg.id);
    resolve(msg.allow === true);
  }
});
