# ADR-663 — The desktop app is the website in a native window; the host is what is versioned

> **Status**: **Accepted** (2026-09-23, operator-ratified: *"aligned in full"*). Implemented with this document.
> **Date**: 2026-09-23
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Channel** (the form of a client — where its interface comes from).
> **No authority change**: no grant, no credential, no kernel mechanism.
> **Gate**: `api/test_adr663_the_desktop_app_is_the_website.py`.
>
> **Origin** — the operator, after the first Windows installer was cut (ADR-661 §7o): *"can we talk about
> versioning and management of this now that we will now potentially have different app, program and platform
> considerations? is that a non issue or do we need to formally make that a decision"* — then, weighing the two
> shapes: *"to me B sounds like a blunter but more web friendly approach"*, and *"how do you think claude code and
> claude's offering of different programs handles this … just want to do a double check."*

**Supersedes** the static-export MECHANISM of ADR-661 — §7a (the export spike's route work, where it was
export-only), §7b (one tree, two builds, `pageExtensions`), §7f (the shell's client-redirect root), §7m (build-time
origin pinning), the launcher half of §7o, and the page pair of §7p. **Preserves** every ruling those sections
served: ADR-661 D1–D4 (a native shell is a permitted client form; one codebase — now literally one build), D5
(the shell does not authenticate; the website does), §7p D6 (the app has one sign-in: the browser's), §6 in full.

**Binds**: ADR-662 (proposed) — D3 below is a condition on any local-hands implementation.

---

## 1. The question underneath "versioning"

ADR-661 §7b built the desktop app as a **static export**: the whole interface compiled into the installer. That
made every installed copy a frozen interface calling a live API — and the API moved 99 times in `api/routes` alone
in the 30 days before this ADR. Nothing told the server which interface was calling (no client-version header
existed anywhere), no updater existed, and nothing recorded which build a member held. A frozen interface against
a moving API does not fail loudly; it degrades into bugs that look like bugs.

So "how do we version the desktop app" was really **"where does the interface come from"**. Two shapes:

| | **A — the interface ships in the installer** | **B — the interface loads from the website** |
|---|---|---|
| Industry | VS Code, 1Password, **Claude Code** | Slack, Notion, Linear, **Claude's desktop app** |
| Interface version | one per install, many in the wild | always current, the same as the web |
| Must be built | updater, version header, server minimum, API compatibility for every live version | an offline screen; the installer version moves only when the host does |

## 2. The deciding principle: where the product's logic runs

The double-check the operator asked for, against Anthropic's own products:

- **Claude Code is A**, because its logic runs on the member's machine — the tool loop, file edits, shell
  commands and their permission prompts. It therefore carries the full version kit, read from its source
  (vendored, gitignored, `docs/analysis/src_claudeCC/`): every request names its version
  (`claude-cli/${VERSION}`, `utils/http.ts:34`); the server holds a minimum and stops an older client
  (`assertMinVersion`, `utils/autoUpdater.ts:70`); a feature holds its own minimum
  (`tengu_bridge_min_version`, `bridge/bridgeEnabled.ts:160`); a maximum can hold back a bad release; an
  auto-updater closes the loop.
- **Claude's desktop app behaves as B** (observed from outside, not from source): new chat features arrive with
  claude.ai, without a reinstall, because the conversation, the model and the history live on the server; the
  machine-touching parts run in the native process behind the app's own permission prompts.

**yarnnn's logic is server-side** — lanes, agents, standing work, the substrate all run on the API. The desktop app
is an interface over the server: Claude's desktop app's situation, not Claude Code's. **B fits.** The one exception
is local hands (ADR-662), which is Claude Code-shaped — privileged work on the member's machine — and it takes
Claude Code's discipline, confined to the part that performs it: the host.

## 3. Decisions

**D1 — The desktop app loads the website.** The window opens `https://www.yarnnn.com/desktop`. The installer carries
the native host (`src-tauri/`) and one local page, `src-tauri/bootstrap/index.html`, which opens the website when it
is reachable and says so plainly when it is not (in English or Korean, from `navigator.language` — it runs before any
catalog exists). There is one web build; the desktop app is a window onto it. A debug build opens
`http://localhost:3000/desktop` instead, so `cargo tauri dev` runs against `pnpm dev`.

**D2 — The host is what is versioned, and it has one version.** `src-tauri/Cargo.toml` `version` is the only source
(`tauri.conf.json` carries none, so Tauri reads Cargo's). macOS and Windows share it. A build handed to anyone is
tagged `desktop-vX.Y.Z` on the commit it was cut from. The web keeps no desktop version of its own.

**D3 — The host tells the server who it is, and the server may refuse it.** The page reads the host's version from
the host (`getVersion()`) and every API request from the app carries `X-Yarnnn-Client: desktop/X.Y.Z`. The API holds
one minimum, `DESKTOP_MIN_VERSION` in `api/services/desktop_client.py`, and answers a request from an older host
with **426** and `error.code = "desktop_update_required"`. The page turns that into a notice, not a broken screen.
A web request carries no header and is never refused. **A feature that needs a newer host gets its own minimum
beside the global one** (Claude Code's per-feature pattern) — none exists until a feature needs it; ADR-662 is the
first expected.

**D4 — Anything that acts on the member's machine asks through the host, never through the page.** Under B the page
is whatever the website serves now, so a compromised deploy, dependency or injected script IS the page talking to
the host. The host's capability roster (`src-tauri/capabilities/default.json`) grants the website's origin only
what the interface needs today — window chrome, the scoped opener, deep-link events, the host's version — and **no
permission that acts on the machine may be granted to a remote origin unless the host itself draws the consent
prompt the member answers**. The page may request; only the host may ask. This binds ADR-662: its "layered consent"
is load-bearing under B, not belt-and-braces.

**D5 — Sign-in stays the browser's, decided at runtime.** §7p D6 holds unchanged in meaning: an email link or an
OAuth return can only complete in the context that began it, and a native window is not where a member's password
manager, passkeys and Google session live. `/auth/login` renders the website's form on the web and the hand-off
panel (`components/auth/DesktopSignIn.tsx`) in the app, chosen after mount by `isNativeShell()`; the page is
client-rendered behind a Suspense boundary already, so choosing at mount paints nothing twice.

**D6 — Auto-update is named and deferred.** Tauri's updater needs a signing keypair of its own and a hosted
manifest; it is built with the first public release, not before. Until then D3's 426 is the lever: a host that is
too old is told so in words, and `web/lib/shell/desktop-app.ts` is where the download lives.

## 4. What this deletes

The static export and everything that existed only to survive it:

- `output: 'export'`, `YARNNN_SHELL`, `distDir: .next-shell`, the `pageExtensions` switch and **all 45 `.web.tsx` /
  `.web.ts` route files, renamed back to Next's own names** — the `.web` convention has no meaning with one build.
- The four shell twins: the shell root redirect (`app/page.tsx`, §7f), the shell authenticated layout, the shell
  sign-in layout, and the shell sign-in page (now `DesktopSignIn`, chosen at runtime — D5).
- `ShellIntlScope` and `resolveLocaleClient` — the client-side locale chain existed because an export has no
  request; the website has one. `FallbackWait` with them.
- The shell's Supabase client (plain supabase-js over `localStorage`, `storageKey: yarnnn-shell-auth`) — the app
  holds the website's cookie session, refreshed by the same `middleware.ts` as every browser. §4.1a's "one place
  the port is a security change" is gone: the app's session is the web's.
- §7m's and §7o's build-time guards and the launcher `web/scripts/shell-next.mjs` — nothing is frozen into the
  installer, so there is nothing to pin.
- The Windows workflow's Node, npm and Supabase-secret steps; the two repo secrets themselves.
- `tauri://localhost` and `http://tauri.localhost` from the API's CORS allowlist — the app's requests carry the
  website's origin. ⚠️ **This retires every 0.1.x install**: a static-export host can no longer reach the API. Two
  existed, both the operator's; they are replaced by 0.2.0.

## 5. What it keeps

The host's own work, unchanged: the window, the macOS title-bar overlay (§7n — the host's initialization script runs
on the website's pages too), the system-browser opener with its URL scope (§7j), the `yarnnn://` return leg and its
single-instance forwarding on Windows (§7i, §7o), the signing and notarization script. On the web side: `AuthGate`
(it owns live sign-out invalidation on the web), `DeepLinkBridge`, `openExternal`, `webOrigin`, and the page-level
Suspense boundaries (ADR-661 §7a.1 — an improvement to first paint that never depended on the export).

## 6. Consequences

- **A web deploy updates the desktop app.** Feature parity is structural, not a release chore.
- **The installer changes rarely** — only when the host changes — so the version kit is small and stays small.
- **The desktop app needs a network to start.** It always needed one to do anything; now it says so at launch
  rather than after.
- **The security boundary moved into the capability roster** (D4). The gate reads it.

## 7. Gate

`api/test_adr663_the_desktop_app_is_the_website.py`: the window opens the website (release) and the local dev server
(debug); the bootstrap is the only bundled page; no static-export configuration or `.web` route file survives; one
version source; the header is sent and the minimum refuses with 426 (driven against the real middleware); the
remote capability grants nothing outside today's roster; the login page chooses at runtime; the retired origins
are gone from CORS.
