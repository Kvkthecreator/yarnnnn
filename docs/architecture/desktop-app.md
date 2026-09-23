# The desktop app

> **Status**: Canonical — describes the live system.
> **Ruled by**: [ADR-661](../adr/ADR-661-the-shell-may-be-native-the-hands-may-not.md) (a native client is permitted; sign-in is the browser's; the conditions on local hands) · [ADR-663](../adr/ADR-663-the-desktop-app-is-the-website-the-host-is-versioned.md) (the shape: the website in a native window; what is versioned) · bound on [ADR-662](../adr/ADR-662-local-hands-the-member-keeps-the-machine.md) (local hands, proposed).
> **Operations**: [publishing-the-desktop-app.md](../infrastructure/publishing-the-desktop-app.md) — signing, notarizing, cutting installers.
> **Gates**: `api/test_adr663_the_desktop_app_is_the_website.py` (the shape) · `api/test_adr661_the_shell_may_be_native.py` (sign-in, the host's chrome, the rulings) · `api/test_adr662_local_hands.py` (the browser pane).

This is the reference for anyone changing the desktop app, or changing the web product in a way the desktop app
will feel. The ADRs hold the reasoning and the history; this document holds how it works **now**. When they
disagree, fix this document in the same commit as the code.

---

## 1. The shape

**The desktop app is the website in a native window.** The installer carries a small native program — the
**host** — and one local page. Everything a member sees is `https://www.yarnnn.com`, loaded live.

```
┌────────────────────── installed on the member's machine ──────────────────────┐
│                                                                                │
│  HOST  src-tauri/  (Rust, Tauri 2)            ← the ONLY versioned thing       │
│   • the window, and on macOS its title bar                                     │
│   • the system-browser hand-off (opener, URL-scoped)                           │
│   • the yarnnn:// return leg (deep link; single-instance on Windows)           │
│   • the capability roster — what the page may ask of the host                  │
│   • the browser pane — local hands (ADR-662 D14), switched on by the member     │
│                                                                                │
│  BOOTSTRAP  src-tauri/bootstrap/index.html   ← the only bundled page           │
│   • opens the website when it answers; says "offline" when it does not         │
│                                                                                │
└──────────────────────────────┬─────────────────────────────────────────────────┘
                               │ loads
                               ▼
        https://www.yarnnn.com/desktop   ← web/, deployed by Vercel, always current
                               │ calls, with X-Yarnnn-Client: desktop/X.Y.Z
                               ▼
        https://yarnnn-api.onrender.com  ← api/, may refuse a host that is too old (426)
```

Three consequences follow from that shape, and most decisions about the desktop app reduce to one of them:

1. **A web deploy updates every desktop app.** There is no second build of the interface and nothing to keep in
   step with it.
2. **The installer changes only when the host changes.** Most product work never touches `src-tauri/`.
3. **The host is a security boundary.** The page it runs is whatever the website serves right now, so what the
   page may ask of the host is the thing to guard (§6).

Why this shape rather than bundling the interface (which ADR-661 first built): yarnnn's logic is server-side, so
the client is an interface over the server — Claude's desktop app's situation, not Claude Code's. ADR-663 §2
records the comparison.

## 2. What lives where

| Concern | Path |
|---|---|
| The host: window, plugins, dev/release address, macOS title bar | `src-tauri/src/main.rs` |
| The one version | `src-tauri/Cargo.toml` → `version` (`tauri.conf.json` carries none) |
| Bundle config: targets (`app`, `dmg`, `nsis`), icons, `frontendDist: bootstrap` | `src-tauri/tauri.conf.json` |
| What the page may ask of the host | `src-tauri/capabilities/default.json` |
| macOS entitlements (hardened runtime needs `allow-jit`) | `src-tauri/entitlements.plist` |
| The bundled page | `src-tauri/bootstrap/index.html` |
| "Am I in the app?" — runtime, never build-time | `isNativeShell()` in `web/lib/shell/external-navigation.ts` |
| Leaving the product (OAuth, checkout, downloads) | `openExternal()` in the same file |
| A link meant for someone else | `webOrigin()` in the same file |
| The return leg | `web/lib/shell/deep-link.ts` + `web/components/shell/DeepLinkBridge.tsx` (mounted in the ROOT layout) |
| The host's version and the client header | `web/lib/shell/host.ts` |
| The update notice | `web/components/shell/DesktopUpdateNotice.tsx` (mounted in `app/(authenticated)/layout.tsx`) |
| The app's sign-in panel | `web/components/auth/DesktopSignIn.tsx`, chosen by `app/auth/login/page.tsx` |
| The browser half of sign-in | `web/app/auth/desktop/page.tsx` |
| Download links (null until a signed build exists) | `web/lib/shell/desktop-app.ts`, shown in Settings → Desktop app |
| The minimum host version the API accepts | `api/services/desktop_client.py`, registered in `api/main.py` |
| Local hands: the browser pane, its consent, its five acts | `src-tauri/src/hands/mod.rs` + `src-tauri/src/hands/page.js` |
| The app's own commands (each gets an `allow-…` permission) | `src-tauri/build.rs` |
| The page's side of the pane, and the Settings switch | `web/lib/shell/hands.ts` · `web/components/settings/DesktopBrowserSetting.tsx` |
| The hand-off: offered tools, the pending acts, stop-when-stuck | `api/services/client_tools.py`; tool definitions `api/services/primitives/browser.py` |
| Build the Mac release | `scripts/release-shell.sh` |
| Build the Windows installer | `.github/workflows/shell-windows.yml` (manual dispatch) |

## 3. A launch, step by step

1. The host opens the window on the bootstrap and injects `window.__YARNNN_APP_URL__` — the website in a release
   build, `http://localhost:3000/desktop` in a debug build.
2. The bootstrap checks the website answers, then `location.replace`s to it. If it does not answer, it says so
   in English or Korean and retries when the network returns.
3. The website loads exactly as in a browser: `middleware.ts` gates it, and a member with no session lands on
   `/auth/login`.
4. `/auth/login` sees it is inside the app (`isNativeShell()`, after mount) and renders `DesktopSignIn` instead
   of the form.
5. Every API call carries `X-Yarnnn-Client: desktop/<host version>`.

The host's initialization script also runs on the website's pages, which is how macOS marks
`<html data-titlebar="overlay">` before first paint (§7).

## 4. Sign-in

**The app never signs in by itself. The browser does, and hands the session over.** An email link or an OAuth return
completes only in the context that began it, and a native window has none of a member's password manager,
passkeys or Google session (Google also blocks sign-in inside embedded windows).

1. `DesktopSignIn` → `openExternal("https://www.yarnnn.com/auth/desktop")` opens the member's browser.
2. `/auth/desktop` signs the member in with the website's ordinary flow, then navigates to
   `yarnnn://auth/session?refresh_token=…`.
3. The OS hands that URL to the running app — natively on macOS; on Windows through the single-instance plugin,
   which forwards a second launch to the first.
4. The host emits a `deep-link` event; `DeepLinkBridge` calls `refreshSession({ refresh_token })`. The session
   lands in the website's own cookie, exactly as a browser sign-in would, and the app routes to `/desktop`.

A failure comes back to `/auth/login?error=…&message=…` and is shown in words (ADR-661 §7h). There is no
`yarnnn://auth/callback`: nothing in the app starts an auth flow.

## 5. Versioning and compatibility

**Only the host has a version.** It lives in `src-tauri/Cargo.toml`; macOS and Windows share it.

| When | Do |
|---|---|
| You change `web/` | Nothing. It ships with the next deploy, to browsers and apps alike. |
| You change `src-tauri/` | Bump `version` in `Cargo.toml`, cut both installers, tag the commit `desktop-vX.Y.Z`. |
| The website starts depending on a host change | Publish the new host first, **then** raise `DESKTOP_MIN_VERSION` in `api/services/desktop_client.py`. |
| One feature needs a newer host | Give that feature its own minimum beside the global one — `BROWSER_MIN_VERSION` (0.3.0) is the first, in `api/services/desktop_client.py`. Below it the feature is simply not offered; the host is never refused for it. Do not raise the global minimum for one feature. |
| A download goes live | Set its https URL in `web/lib/shell/desktop-app.ts` **and** allow its host in the opener scope in `capabilities/default.json`. |

**How refusal works.** The API answers a request whose `X-Yarnnn-Client` is below the minimum with **426** and
`error.code = "desktop_update_required"`. `request()` in `web/lib/api/client.ts` turns that into an event;
`DesktopUpdateNotice` shows *"This version of the yarnnn app is out of date"* with a button to Settings → Desktop app.
A browser sends no header and is never refused. The middleware sits **inside** CORS in `api/main.py` — if it moved
outside, the 426 would lose its CORS headers and the page would see only a network error.

**Every request door sends the header.** Today there are two: `getAuthHeaders()` (all of `client.ts`) and
`postChatWithFallback` in `chatTransport.ts`. A new fetch to the API must go through one of them, or add
`await clientHeaders()` itself.

**Auto-update is not built** (ADR-663 D6): it needs its own signing keypair and a hosted manifest. The 426 is the
lever until then.

## 6. The security boundary

The page in the window is the live website. A compromised deploy, a poisoned dependency or an injected script
**is** the page talking to the host. So:

- **`capabilities/default.json` is an explicit list, never a default set.** Today: `core:event:default` (deep-link
  events), `core:app:allow-version` (the header), `core:window:default` (chrome), `core:window:allow-start-dragging`
  (the top bar is the grab handle), `deep-link:default`, `opener:allow-open-url` with a URL scope, and the app's
  four hands commands (`allow-hands-status`, `allow-hands-enable`, `allow-hands-disable`, `allow-browser-act` — §6a).
- **The roster names the `main` window only.** A window the host opens for anything else — the browser pane —
  gets no capability, so the internet pages loaded there can ask the host for nothing.
- **Remote origins: `https://www.yarnnn.com/*` and `https://yarnnn.com/*` only.** `"local": false` — the bootstrap
  needs nothing from the host.
- **Nothing that acts on the member's machine may be granted to the website's origin unless the host itself draws
  the consent prompt the member answers** (ADR-663 D4). The page may request; only the host may ask. This is the
  rule ADR-662's local hands must meet.
- **The opener is URL-scoped.** An empty scope refuses every URL silently (ADR-661 §7j); a wildcard would let any
  page the app renders open anything. Add hosts one at a time.
- A debug build grants the SAME roster to `http://localhost:3000/*`, read from the same file at startup
  (`add_capability` in `main.rs`). There is never a second, hand-written list.
- `tauri.conf.json` sets no CSP. The bootstrap is one local page with an inline script, and Tauri's nonce
  injection would block it (ADR-661 §7e); the website carries its own headers from Vercel.

## 6a. Local hands: the browser pane (ADR-662 D14)

The agent can work in a **browser pane** — a second window the host owns, labelled `browser` — while the member
keeps using their machine. It is the first local hands, and it touches nothing outside its own window: no other
app, no pointer, no keyboard, no screen capture, no clipboard.

**Switching it on.** Settings → Desktop app → *Let your agent use a browser* calls `hands_enable`, and the HOST
draws the consent dialog (ADR-663 D4 — the page may ask, only the host may ask the member). The answer is kept in
the app's config directory (`hands.json`), on this machine only. Off → `hands_disable` closes the pane.

**A turn that uses it.**

1. The page sends a turn with `client_tools: ["browser"]` — only when `hands_status` says the member switched it
   on (`web/lib/api/client.ts`, `browserHandsOn()`).
2. The API offers the five browser tools only if `X-Yarnnn-Client` is at or above `BROWSER_MIN_VERSION`
   (`client_tools.offered`). A browser tab never gets them.
3. When the model calls one, the stream carries `{"client_tool": {call_id, name, arguments, nonce}}` and the
   turn waits (`client_tools.wait`, 60 s, then fails closed).
4. `performClientTool` (`web/lib/shell/hands.ts`) invokes `browser_act`; the host runs the act in the pane and
   reads its effect back; the page posts the result to `POST /api/lanes/{id}/tool-results/{call_id}` with the
   nonce. Only that turn's nonce, from the same member, is accepted.
5. The stream carries `{"tool_receipt": {name, text, ok, record}}`; the chat's step row turns into what happened
   ("Pressed “Sign in” — no change"), worded from `record` in the member's language. The receipts persist on the
   reply's `metadata.receipts`.

**The acts** (`src-tauri/src/hands/page.js`, run with JSON-encoded arguments — the model never writes script):
`BrowserOpen` (http/https only) · `BrowserRead` (title, text, and every actionable element with a `ref`; a password
field's value never leaves the page) · `BrowserClick` · `BrowserFill` (text fields and dropdowns; optional submit)
· `BrowserBack`. Each answers `{success, receipt, record}`.

**Bounds.** A hands turn has 30 rounds (`HANDS_MAX_ROUNDS`), and stops when stuck (`StuckWatch`). The pending acts
live in the API process — correct on today's single worker; a second worker needs them shared.

**Changing it.** A new act is a routine in `page.js` + an arm in `act()` + a schema in `primitives/browser.py` + a
`record.act` the client words (`RECEIPT_ACTS` and `chat.tools.receipts` in both catalogs) — the ADR-662 gate checks
that the host's acts and the client's words agree. A new host command goes in `build.rs` AND the roster, and
anything that acts on the machine needs the host-drawn consent first.

## 7. Platform differences

The web layer **never detects a platform** (ADR-661 §7.6). A difference lives in the host, behind a `cfg`, and
the host tells the page what it needs to know.

| | macOS | Windows |
|---|---|---|
| Title bar | Overlaid: the traffic lights sit in the app's 56px top bar. The host positions them and sets `data-titlebar="overlay"`; `--titlebar-inset` reserves the space. | The native frame, above the app's top bar. The page is never marked, so the inset stays 0. |
| Deep links | Delivered to the running app by the OS. | A second launch; `tauri-plugin-single-instance` (registered FIRST) forwards it. |
| Webview | WebKit | WebView2 (Chromium; ships with Windows 10/11, installer fetches it otherwise) |
| Installer | DMG, Apple Silicon, needs a Developer ID to open without "damaged" | NSIS, per-user, no admin; unsigned warns via SmartScreen |
| Built on | the developer's Mac | a GitHub Actions Windows runner |

⚠️ Tauri's `title_bar_style`, `hidden_title` and `traffic_light_position` exist **only** on macOS — called
outside the `#[cfg(target_os = "macos")]` block, the host does not compile for Windows (ADR-661 §7o). Check a host
change for Windows with the `shell-windows.yml` workflow: `cargo check --target x86_64-pc-windows-msvc` on a Mac
stops in `tauri-winres` without `llvm-rc`, before it reaches the host's own code.

## 8. Writing web code the desktop app will run

- **Ask at runtime:** `isNativeShell()`. There is no build flag and no second build.
- **Choosing a whole component by it?** Decide after mount (`useEffect`), as `app/auth/login/page.tsx` does —
  the server render cannot know, and choosing during render mismatches hydration.
- **Leaving the product** (OAuth consent, checkout, a download, any third-party page): `openExternal(url)`.
  Never `window.location.href = external` and never `window.open` — inside the app one strands the member in a
  frame with no address bar, the other does nothing. The target's host must be in the opener scope.
- **A link someone else will open** (share links, copied URLs): build it from `webOrigin()`.
- **A new call to the API:** go through `getAuthHeaders()` so the version header rides along (§5).
- **Copy about the app** lives in the catalogs like all copy; platform names ("Mac", "Windows") are proper names,
  not catalog entries.

## 9. Develop and release

**Develop** — two terminals:

```bash
cd web && pnpm dev                 # the website on :3000
cd src-tauri && cargo tauri dev    # the host, opening localhost:3000/desktop
```

**Release** — see [publishing-the-desktop-app.md](../infrastructure/publishing-the-desktop-app.md):

```bash
./scripts/release-shell.sh                                        # Mac: build, sign, notarize, staple
gh workflow run shell-windows.yml && gh run download --name yarnnn-windows   # Windows
git tag desktop-vX.Y.Z <commit> && git push origin desktop-vX.Y.Z
```

## 10. Do not

Each of these was built once, and each is why the current shape exists:

- **Bundle the interface into the installer.** The static export (ADR-661 §7b) froze each install against a
  moving API; ADR-663 replaced it.
- **Branch the build.** The `.web.tsx` / `pageExtensions` split (§7b) made two route sets from one tree, and it
  silently blinded seven gates that read the renamed paths.
- **Give the app its own auth.** A second Supabase client, and an auth flow begun in the app, each failed in ways
  only a real sign-in found (§7d, §7g, §7p).
- **Freeze an origin at build time.** A developer's `localhost:8000` shipped once (§7m).
- **Grant `core:default` to the website**, or add a machine-acting permission to the remote roster (§6).
- **Keep a second version number** — in `tauri.conf.json`, in `web/`, anywhere.
- **Detect a platform in `web/`.** Put the difference in the host and have it tell the page.

## 11. History

ADR-661 (2026-09-21) permitted a native client and built it as a static export, then spent §7a–§7p learning what
that shape cost: sign-in rebuilt three times, build-time origin pinning, a two-build route split, Windows blockers.
ADR-663 (2026-09-23) replaced the shape with the website in a native window and made the host the only versioned
thing. ADR-662 (proposed) plans local hands on that host, under ADR-663 D4; its amendment 1 built the browser pane
first (host 0.3.0), ahead of the member's-own-apps path.
