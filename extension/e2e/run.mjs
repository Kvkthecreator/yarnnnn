// The extension, driven end to end in a real Chrome — ADR-662 D15's instrument.
//
//   cd extension/e2e && npm install --no-save playwright-core && node run.mjs
//
// Chrome for Testing is used because branded Chrome no longer loads unpacked
// extensions from the command line. Set CHROME_FOR_TESTING to its binary, or
// let this find Playwright's cached copy (`npx playwright install chromium`).
//
// It serves a stand-in yarnnn page on http://localhost:3000 (an origin the
// manifest lets through) and fixture pages on 127.0.0.1:8765, answers the
// extension's consent windows the way a member would, and asserts each act's
// receipt. It prints a count; read it.
//
// NOT covered here: the yarnnn website itself and the server (the ADR-662 gate
// drives the lane loop), and the member's real profile and sign-ins.

import { chromium } from "playwright-core";
import http from "node:http";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const EXT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const EXT_ID = "flkcmnbfjjkglgaakihlcdfocecfaccb";

function chromeForTesting() {
  if (process.env.CHROME_FOR_TESTING) return process.env.CHROME_FOR_TESTING;
  const cache = path.join(os.homedir(), "Library/Caches/ms-playwright");
  for (const d of fs.existsSync(cache) ? fs.readdirSync(cache).filter((d) => /^chromium-\d+$/.test(d)).sort().reverse() : []) {
    const bin = path.join(cache, d, "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing");
    if (fs.existsSync(bin)) return bin;
  }
  throw new Error("Chrome for Testing not found — set CHROME_FOR_TESTING or run `npx playwright install chromium`.");
}

const PAGES = {
  "/harness.html": `<!doctype html><title>yarnnn stand-in</title><script>
    window.send = (msg) => new Promise((res) => chrome.runtime.sendMessage("${EXT_ID}", msg, res));</script>`,
  "/form.html": `<!doctype html><title>Fixture form</title><form action="done.html" method="post">
    <label for="em">Email</label><input id="em" name="email">
    <label for="pw">Password</label><input id="pw" name="pw" type="password" value="secret123">
    <select aria-label="Plan" name="plan"><option value="f">Free</option><option value="p">Pro</option></select>
    <button type="submit">Create account</button></form>
    <button type="button">Nothing</button>
    <button type="button" onclick="document.body.insertAdjacentHTML('beforeend','<p>Grown</p>')">Grow</button>
    <a href="done.html" target="_blank">New tab link</a>`,
  "/done.html": `<!doctype html><title>Done page</title><p>Thanks</p>`,
};
const serve = (port) => new Promise((ok) => {
  const s = http.createServer((req, res) => {
    const body = PAGES[req.url.split("?")[0]];
    res.writeHead(body ? 200 : 404, { "content-type": "text/html" });
    res.end(body || "");
  });
  s.listen(port, "127.0.0.1", () => ok(s));
});

let pass = 0, fail = 0;
const expect = (name, cond, got) => {
  if (cond) { pass++; console.log(`  ✓ ${name}`); }
  else { fail++; console.log(`  ✗ ${name} — got ${JSON.stringify(got).slice(0, 300)}`); }
};

const servers = [await serve(3000), await serve(8765)];
const ctx = await chromium.launchPersistentContext(fs.mkdtempSync(path.join(os.tmpdir(), "yarnnn-ext-")), {
  executablePath: chromeForTesting(), headless: true,
  args: [`--disable-extensions-except=${EXT}`, `--load-extension=${EXT}`],
});
let consentAnswer = true;
const consents = [];
ctx.on("page", async (p) => {
  if (!p.url().includes("consent.html")) return;
  await p.waitForLoadState();
  consents.push(await p.textContent("#title"));
  await p.click(consentAnswer ? "#allow" : "#deny");
});

try {
  const h = await ctx.newPage();
  await h.goto("http://localhost:3000/harness.html");
  const act = (tool, args = {}) => h.evaluate(([t, a]) => send({ type: "act", tool: t, args: a }), [tool, args]);

  const hello = await h.evaluate(() => send({ type: "hello" }));
  expect("a yarnnn page reaches the extension", hello?.ok && hello.enabled, hello);

  const opened = await act("BrowserOpen", { url: "http://127.0.0.1:8765/form.html" });
  expect("a new site is asked about once, by the extension", consents.length === 1 && /127\.0\.0\.1/.test(consents[0]), consents);
  expect("open says what opened", opened.success && opened.record.act === "opened" && /Fixture form/.test(opened.receipt), opened);

  const page = await act("BrowserRead");
  const ref = (label) => page.elements.find((e) => e.label === label)?.ref;
  expect("read lists what can be acted on", ["Email", "Password", "Plan", "Create account", "Nothing", "Grow", "New tab link"].every((l) => ref(l) !== undefined), page.elements);
  expect("a password never leaves the page", !JSON.stringify(page).includes("secret123"), "leaked");

  const fill = await act("BrowserFill", { ref: ref("Email"), text: "a@b.co" });
  expect("fill reads its value back", fill.success && fill.record.changed, fill);
  const plan = await act("BrowserFill", { ref: ref("Plan"), text: "Pro" });
  expect("a dropdown is filled by its option's text", plan.success, plan);
  const nothing = await act("BrowserClick", { ref: ref("Nothing") });
  expect("a click that changes nothing says so", nothing.success && !nothing.changed && /no change observed/.test(nothing.receipt), nothing);
  const grow = await act("BrowserClick", { ref: ref("Grow") });
  expect("a click that changes the page says so", grow.changed && /the page changed/.test(grow.receipt), grow);
  const stale = await act("BrowserClick", { ref: 999 });
  expect("a ref that is gone fails in words", !stale.success && /read the page again/.test(stale.receipt), stale);
  const sent = await act("BrowserFill", { ref: ref("Email"), text: "a@b.co", submit: true });
  expect("submitting a form follows it to the next page", sent.success && /now on “Done page”/.test(sent.receipt), sent);
  const back = await act("BrowserBack");
  expect("back goes back", back.success && /Fixture form/.test(back.receipt), back);
  const again = await act("BrowserRead");
  const newTab = await act("BrowserClick", { ref: again.elements.find((e) => e.label === "New tab link").ref });
  expect("a new-tab link is followed in the agent's tab", newTab.changed && /Done page/.test(newTab.receipt), newTab);
  expect("the member's own tab never moved", h.url() === "http://localhost:3000/harness.html", h.url());

  const bank = await act("BrowserOpen", { url: "https://www.paypal.com/" });
  expect("a default-denied site is refused without asking", !bank.success && bank.record.act === "refused" && consents.length === 1, bank);
  const js = await act("BrowserOpen", { url: "javascript:alert(1)" });
  expect("a non-web address is refused", !js.success && js.record.act === "refused", js);
  consentAnswer = false;
  const declined = await act("BrowserOpen", { url: "http://localhost:8765/form.html" });
  expect("a site the member declines stays refused", !declined.success && /not allowed localhost/.test(declined.receipt), declined);

  const sw = ctx.serviceWorkers()[0] || (await ctx.waitForEvent("serviceworker"));
  const groups = await sw.evaluate(async () => (await chrome.tabGroups.query({})).map((g) => g.title));
  expect("the agent works in a tab group named yarnnn", groups.includes("yarnnn"), groups);

  // The Settings switch, asked from a yarnnn page.
  const setEnabled = (enabled) => h.evaluate((e) => send({ type: "setEnabled", enabled: e }), enabled);
  const asked = consents.length;
  const offReply = await setEnabled(false);
  expect("a yarnnn page can switch it OFF at once, without a question", offReply?.enabled === false && consents.length === asked, offReply);
  const off = await act("BrowserRead");
  expect("switched off, it does nothing", !off.success && /switched yarnnn off/.test(off.receipt), off);
  consentAnswer = false;
  const refused = await setEnabled(true);
  expect("a page asking to switch it ON gets the extension's own question — and a no stays off",
    refused?.enabled === false && consents.length === asked + 1 && /use Chrome/.test(consents[asked]), { refused, consents });
  consentAnswer = true;
  const onReply = await setEnabled(true);
  expect("…and a yes switches it on", onReply?.enabled === true && consents.length === asked + 2, onReply);
  const hello2 = await h.evaluate(() => send({ type: "hello" }));
  expect("hello reports the switch", hello2?.enabled === true, hello2);
  await sw.evaluate(() => chrome.storage.local.set({ enabled: false }));

  const stranger = await ctx.newPage();
  await stranger.goto("http://127.0.0.1:8765/form.html");
  const reach = await stranger.evaluate(() => typeof chrome !== "undefined" && !!chrome.runtime?.sendMessage);
  expect("a page that is not yarnnn cannot even see it", reach === false, reach);
} finally {
  await ctx.close();
  servers.forEach((s) => s.close());
}
console.log(`\n  ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
