# Local hands — the agent works in the member's browser

> **Status**: Canonical — describes the live system.
> **Ruled by**: [ADR-662](../adr/ADR-662-local-hands-the-member-keeps-the-machine.md) (proposed; amendment 2 D15, the member's own Chrome) · [ADR-664](../adr/ADR-664-the-members-browser-is-reach.md) (the browser is reach — how the agent and Reach state it) · [ADR-665](../adr/ADR-665-browser-workflows.md) (proposed: workflows that run in the browser) · [ADR-663](../adr/ADR-663-the-desktop-app-is-the-website-the-host-is-versioned.md) D4 (only the executor asks for consent).
> **Gates**: `api/test_adr662_local_hands.py` · `api/test_adr664_the_browser_is_reach.py` · **Instruments**: `extension/e2e/run.mjs` (the extension in a real Chrome) · `extension/e2e/bridge.mjs` (the extension ↔ the real native-messaging bridge).

In a conversation, the member's agent can open web pages, read them, fill fields and press buttons — sending
and posting included — while the member keeps using their computer. It works in **a tab of its own**, and every
step is said back in plain words. The server never touches a website: an **executor** on the member's machine
performs each act.

## 1. One executor, two ways to reach it

The **yarnnn Chrome extension** (`extension/`) performs every act, in the member's own Chrome (and Edge, Brave,
Arc) — every sign-in they already have, in a tab of its own, asking once per site.

| A yarnnn page in… | reaches the extension by |
|---|---|
| Chrome, with the extension | `chrome.runtime.sendMessage` straight to it (`externally_connectable`) |
| the desktop app | `invoke("browser_act")` → the host → **Chrome's native messaging** → the extension (§4a) |

The host performs nothing and draws no consent of its own. (ADR-662 D14's browser pane — a second window with its
own sessions — was built, met a sign-in wall on its first test, and was deleted for this.)

## 2. A turn that uses it

1. The page finds its way to the extension (`browserHands()` in `web/lib/shell/hands.ts`) and, when it is
   connected and on, the turn's request carries `client_tools: ["browser"]` plus who will relay it — the desktop
   host by its `X-Yarnnn-Client` header, the extension itself as `executor: "extension/X.Y.Z"`.
2. The API offers the five browser tools only if that executor is at or above its minimum
   (`client_tools.offered`: `BROWSER_MIN_VERSION` 0.4.0 for the host — 0.3.x carried the deleted pane —
   `EXTENSION_MIN_VERSION` for the extension). The
   member's message row records what was offered (`metadata.client_tools`). The frame's reach section — the
   one place reach is stated (ADR-644/664, `reach_status.browser_sentence`) — says the member's browser reaches
   any website and a website task goes to it first; a turn WITHOUT the tools is told how the member gets one.
3. When the model calls one, the stream carries `{"client_tool": {call_id, name, arguments, nonce}}` and the
   turn waits (`client_tools.wait`, 150 s, then fails closed).
4. `performClientTool` hands the act to the extension (directly, or through the host), then posts the result to
   `POST /api/lanes/{id}/tool-results/{call_id}` with the nonce. Only that turn's nonce, from the same member,
   is accepted.
5. The stream carries `{"tool_receipt": {name, text, ok, record}}`. `text` is the model's sentence; `record`
   (`{act, subject, changed}`) is worded in the member's language (`chat.receipts`) and persisted on the reply
   as `metadata.receipts`.

## 3. The acts

`BrowserOpen` (http/https only) · `BrowserRead` (title, text, every actionable element with a `ref`; a password
field's value never leaves the page) · `BrowserClick` (a new-tab link is followed in the agent's tab) ·
`BrowserFill` (text fields and dropdowns; optional submit) · `BrowserBack` (the page's own history — Chrome's
Back skips gesture-less entries). Each answers `{success, receipt, record}` and reads its effect back: a fill
compares the field's value, a click compares the page's fingerprint, and "no change observed" is said in those
words. The model never writes script: an act is `page.js` plus one call with JSON-encoded arguments.

## 4. The extension

- **Its tab.** Opened in the background (`active: false`), in a tab group named *yarnnn*; the member's tab never
  moves. A link that opens a new tab moves the agent's tab with it.
- **Who can reach it.** Only yarnnn's origins — Chrome enforces `externally_connectable`, and the worker checks
  `sender.origin` against `YARNNN_ORIGINS` again (`policy.js`). Any other page cannot even see
  `chrome.runtime.sendMessage`.
- **Sites.** `verdictFor` (`policy.js`): a default-denied category (banking and payments, trading and crypto,
  password managers, account security) is refused whatever the member allowed; a site the member said no to is
  refused; an allowed site covers its subdomains; anything else asks the member once, in a window the extension
  draws (`consent.html`) — no answer in two minutes is a no. The gate is asked of where the tab IS, so a redirect
  to a new site asks again.
- **The member's controls.** The toolbar button (`popup.html`): on/off, the allowed and refused lists, the
  categories that are never allowed. All of it in `chrome.storage.local` — this machine, never the workspace.
- **Permissions.** `tabs`, `tabGroups`, `scripting`, `storage`, `nativeMessaging` (the desktop app), and host
  access to web pages — nothing for cookies, the clipboard, history, the network or the debugger.
- **Identity.** The manifest's public `key` fixes the id (`flkcmnbfjjkglgaakihlcdfocecfaccb`), so an unpacked
  build and a published one are the same extension to the website (`CHROME_EXTENSION.id`). No private key is
  kept; the Chrome Web Store signs what it publishes.
- **Languages.** English and Korean (`_locales/`), following Chrome's language.

## 4a. The desktop app's relay (native messaging)

- **Registration.** At startup the host writes `com.yarnnn.desktop.json` into each installed Chromium browser's
  `NativeMessagingHosts` folder (`register_with_browsers`): the path is the app's own binary, and
  `allowed_origins` is the yarnnn extension only. Rewritten every start, so a moved app keeps working.
- **The bridge.** The extension calls `chrome.runtime.connectNative("com.yarnnn.desktop")` when its worker
  starts. Chrome launches the app's binary with the extension's origin as its argument; `main` sees it and runs
  `hands/bridge.rs` before Tauri starts — no window, no second app. The bridge relays Chrome's length-prefixed
  stdio to JSON lines on `~/Library/Application Support/com.yarnnn.desktop/hands.sock`, retries the socket every
  two seconds while the app is away, and exits when Chrome lets go.
- **The app.** Listens on that socket, owner-only (`0600`), one bridge at a time. `browser_act` writes
  `{type: "act", id, tool, args}` and waits (150 s) for `{type: "result", id, result}`; with no bridge it
  refuses in words. `hands_status` answers `{extension, version}` from the extension's hello.
- **The extension** treats an act from the app exactly as one from a yarnnn page — the same `perform`: the same
  site gate, consent and tab.
- **Windows** is owed: its native messaging is a registry key and a named pipe. Until then the Windows app says
  it cannot reach Chrome.

## 5. Trying it before it is published

1. `chrome://extensions` → turn on *Developer mode* → *Load unpacked* → choose the repo's `extension/` folder.
2. Open yarnnn in that Chrome — or the desktop app (host 0.4.0+), with Chrome running. Settings → Desktop app
   says *Connected to the yarnnn extension*.
3. Ask for something on a website in a conversation. The first time on each site, the extension asks.

Publishing waits on ADR-662's ratification: ADR-661's tripwire refuses a `storeUrl` while ADR-662 is Proposed. (A
desktop download carries no hands of its own — the host only relays — so it is not held back.)

## 6. Changing it

- **A new act**: a routine in `extension/page.js`, the act in `extension/background.js`, a schema in
  `services/primitives/browser.py`, and a `record.act` the client words (`RECEIPT_ACTS` in `toolLabels.ts`,
  `chat.receipts` in both catalogs). The gate checks that the extension's acts and the client's words agree. The
  host needs nothing — it relays whatever the extension answers.
- **A new permission** in the manifest fails the gate on purpose; argue it in ADR-662 first.
- **Run** `api/test_adr662_local_hands.py`, `extension/e2e/run.mjs` and (for a host or relay change, after
  `cargo build`) `extension/e2e/bridge.mjs` — the last two are the only ones that drive the extension.
