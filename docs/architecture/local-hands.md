# Local hands — the agent works in the member's browser

> **Status**: Canonical — describes the live system.
> **Ruled by**: [ADR-662](../adr/ADR-662-local-hands-the-member-keeps-the-machine.md) (proposed; amendment 1 D14 the desktop pane, amendment 2 D15 the member's own Chrome) · [ADR-663](../adr/ADR-663-the-desktop-app-is-the-website-the-host-is-versioned.md) D4 (only the executor asks for consent).
> **Gate**: `api/test_adr662_local_hands.py` · **Instrument**: `extension/e2e/run.mjs` (the extension in a real Chrome).

In a conversation, the member's agent can open web pages, read them, fill fields and press buttons — sending
and posting included — while the member keeps using their computer. It works in **a tab of its own**, and every
step is said back in plain words. The server never touches a website: an **executor** on the member's machine
performs each act.

## 1. The two executors

| | **The yarnnn Chrome extension** (D15) | **The desktop app's browser pane** (D14) |
|---|---|---|
| Where | the member's own Chrome (and Edge, Brave, Arc) | a second window of the yarnnn desktop app |
| Sign-ins | every one the member already has | only those made inside the pane |
| Reached by | a yarnnn page in that Chrome | a yarnnn page in the desktop app |
| Consent | per site, asked once, drawn by the extension; categories denied by default | one switch, drawn by the host |
| Code | `extension/` | `src-tauri/src/hands/` |

**The extension is the executor going forward.** The pane is deleted once the desktop app reaches the extension
(native messaging — ADR-662 §7 amendment 2, owed). Both run the same page routines, `extension/page.js` — one
copy; the host `include_str!`s it.

## 2. A turn that uses it

1. The page finds its executor (`browserHands()` in `web/lib/shell/hands.ts`) and, when it is on, the turn's
   request carries `client_tools: ["browser"]` plus the executor's identity — the desktop host by its
   `X-Yarnnn-Client` header, the extension as `executor: "extension/X.Y.Z"`.
2. The API offers the five browser tools only if that executor is at or above its minimum
   (`client_tools.offered`: `BROWSER_MIN_VERSION` for the host, `EXTENSION_MIN_VERSION` for the extension). The
   member's message row records what was offered (`metadata.client_tools`). The frame's tool edge becomes
   `BROWSER_FRAME` (`services/primitives/browser.py`): the agent may act on the web for the member.
3. When the model calls one, the stream carries `{"client_tool": {call_id, name, arguments, nonce}}` and the
   turn waits (`client_tools.wait`, 150 s, then fails closed).
4. `performClientTool` hands the act to the executor, then posts the result to
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
- **Permissions.** `tabs`, `tabGroups`, `scripting`, `storage`, and host access to web pages — nothing for
  cookies, the clipboard, history, the network or the debugger.
- **Identity.** The manifest's public `key` fixes the id (`flkcmnbfjjkglgaakihlcdfocecfaccb`), so an unpacked
  build and a published one are the same extension to the website (`CHROME_EXTENSION.id`). No private key is
  kept; the Chrome Web Store signs what it publishes.
- **Languages.** English and Korean (`_locales/`), following Chrome's language.

## 5. Trying it before it is published

1. `chrome://extensions` → turn on *Developer mode* → *Load unpacked* → choose the repo's `extension/` folder.
2. Open yarnnn in that Chrome. Settings → Desktop app shows *Connected to the yarnnn extension*.
3. Ask for something on a website in a conversation. The first time on each site, the extension asks.

Publishing waits on ADR-662's ratification: ADR-661's tripwire refuses a `storeUrl` (and a desktop download)
while ADR-662 is Proposed.

## 6. Changing it

- **A new act**: a routine in `extension/page.js`, the act in `extension/background.js` (and the pane's
  `src-tauri/src/hands/mod.rs` until it is deleted), a schema in `services/primitives/browser.py`, and a
  `record.act` the client words (`RECEIPT_ACTS` in `toolLabels.ts`, `chat.receipts` in both catalogs). The gate
  checks that both executors' acts and the client's words agree.
- **A new permission** in the manifest fails the gate on purpose; argue it in ADR-662 first.
- **Run** `api/test_adr662_local_hands.py` and `extension/e2e/run.mjs` — the second is the only one that drives
  the extension in a real Chrome.
