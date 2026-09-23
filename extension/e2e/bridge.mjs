// The desktop app's relay, driven — ADR-662 D15's second instrument.
//
//   cd src-tauri && cargo build && cd ../extension/e2e && npm install --no-save playwright-core && node bridge.mjs
//
// Chrome for Testing with the extension loaded launches the REAL host binary
// (src-tauri/target/debug/yarnnn) as its native-messaging host, from a manifest
// in a throwaway profile; HOME is a throwaway too, so the bridge dials a socket
// this script owns. A stand-in app on that socket sends acts and reads results
// — the protocol the running app speaks (src-tauri/src/hands/mod.rs). Prints a
// count; read it.
//
// NOT covered: the running app's own listener and `browser_act` from its page
// (drive the installed app for those), and the member's real Chrome profile.
import { chromium } from "playwright-core";
import fs from "node:fs"; import net from "node:net"; import http from "node:http"; import os from "node:os"; import path from "node:path";
import { fileURLToPath } from "node:url";
const EXT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const BIN = path.resolve(EXT, "../src-tauri/target/debug/yarnnn");
function chromeForTesting() {
  if (process.env.CHROME_FOR_TESTING) return process.env.CHROME_FOR_TESTING;
  const cache = path.join(os.homedir(), "Library/Caches/ms-playwright");
  for (const d of fs.existsSync(cache) ? fs.readdirSync(cache).filter((d) => /^chromium-\d+$/.test(d)).sort().reverse() : []) {
    const bin = path.join(cache, d, "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing");
    if (fs.existsSync(bin)) return bin;
  }
  throw new Error("Chrome for Testing not found — set CHROME_FOR_TESTING or run `npx playwright install chromium`.");
}
const exe = chromeForTesting();
// /tmp, not os.tmpdir(): a macOS socket path must stay under 104 bytes.
const home = fs.mkdtempSync("/tmp/yh-");               // the bridge computes its socket from HOME
const sock = path.join(home, "Library/Application Support/com.yarnnn.desktop/hands.sock");
fs.mkdirSync(path.dirname(sock), { recursive: true });
const udd = fs.mkdtempSync(path.join(os.tmpdir(), "yu-"));
fs.mkdirSync(path.join(udd, "NativeMessagingHosts"));
fs.writeFileSync(path.join(udd, "NativeMessagingHosts/com.yarnnn.desktop.json"), JSON.stringify({
  name: "com.yarnnn.desktop", description: "test", path: BIN, type: "stdio",
  allowed_origins: ["chrome-extension://flkcmnbfjjkglgaakihlcdfocecfaccb/"] }));
const fx = http.createServer((q, r) => { r.writeHead(200, { "content-type": "text/html" });
  r.end('<!doctype html><title>Fixture form</title><label for=e>Email</label><input id=e><button onclick="document.title=\'Pressed\'">Go</button>'); }).listen(8765, "127.0.0.1");
// the stand-in app
const got = []; let client = null; const waiters = [];
const app = net.createServer((c) => { client = c; let buf = "";
  c.on("data", (d) => { buf += d; let i; while ((i = buf.indexOf("\n")) >= 0) { const line = buf.slice(0, i); buf = buf.slice(i + 1); const m = JSON.parse(line); got.push(m); waiters.splice(0).forEach((w) => w()); } }); }).listen(sock);
const next = (pred, ms = 60000) => new Promise((res, rej) => { const t = setTimeout(() => rej(new Error("timeout; got " + JSON.stringify(got))), ms);
  const check = () => { const m = got.find(pred); if (m) { clearTimeout(t); res(m); } else waiters.push(check); }; check(); });
const ctx = await chromium.launchPersistentContext(udd, { executablePath: exe, headless: true, env: { ...process.env, HOME: home },
  args: [`--disable-extensions-except=${EXT}`, `--load-extension=${EXT}`] });
ctx.on("page", async (p) => { if (p.url().includes("consent.html")) { await p.waitForLoadState(); await p.click("#allow"); } });
let pass = 0, fail = 0; const expect = (n, c, g) => { if (c) { pass++; console.log("  ✓ " + n); } else { fail++; console.log("  ✗ " + n + " — " + JSON.stringify(g).slice(0, 300)); } };
try {
  const hello = await next((m) => m.type === "hello");
  expect("the extension reaches the app through the bridge and says hello", hello.version === "0.1.0", hello);
  const send = (m) => client.write(JSON.stringify(m) + "\n");
  send({ type: "act", id: 1, tool: "BrowserOpen", args: { url: "http://127.0.0.1:8765/" } });
  const r1 = await next((m) => m.type === "result" && m.id === 1);
  expect("an act from the app is performed and answered by id", r1.result?.success && r1.result.record?.act === "opened", r1);
  send({ type: "act", id: 2, tool: "BrowserRead", args: {} });
  const r2 = await next((m) => m.type === "result" && m.id === 2);
  expect("a read comes back whole through the bridge", r2.result?.elements?.length === 2, r2.result?.elements);
  send({ type: "act", id: 3, tool: "BrowserOpen", args: { url: "https://www.paypal.com/" } });
  const r3 = await next((m) => m.type === "result" && m.id === 3);
  expect("the app's acts pass the same gate", r3.result?.record?.act === "refused", r3);
  // the app restarts: the bridge must find it again and the extension say hello again
  client.destroy(); got.length = 0;
  const again = await next((m) => m.type === "hello", 15000);
  expect("after the app goes away and comes back, the bridge reconnects", !!again, again);
} catch (e) { fail++; console.log("  ✗ " + e.message.slice(0, 400)); }
finally { await ctx.close(); app.close(); fx.close(); }
console.log(`\n  ${pass} passed, ${fail} failed`); process.exit(fail ? 1 : 0);
