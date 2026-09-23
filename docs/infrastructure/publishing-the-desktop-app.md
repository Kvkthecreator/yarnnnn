# Publishing the desktop app

What stands between a build and a stranger downloading it and it just working.
ADR-661 §8 steps 4–5 (macOS) and §7o (Windows); ADR-663 for what is versioned.

**The desktop app is the website in a native window** (ADR-663). The installer
carries only the host (`src-tauri/`) and a bootstrap page; the interface loads
from `https://www.yarnnn.com/desktop`, so a web deploy updates every installed
app. A new installer is needed only when the HOST changes.

## Versioning — one number, the host's

- The version lives in **`src-tauri/Cargo.toml`** and nowhere else (Tauri reads
  it; `tauri.conf.json` carries none). macOS and Windows share it.
- Bump it when the host changes. Tag the commit a handed-out build was cut from:
  `git tag desktop-v0.2.0 && git push origin desktop-v0.2.0`.
- The app sends `X-Yarnnn-Client: desktop/<version>` on every API request. To
  retire old installs, raise `DESKTOP_MIN_VERSION` in
  `api/services/desktop_client.py` **after** the new build is published: an
  older app then shows *"This version of the yarnnn app is out of date"* with a
  link to Settings → Desktop app.
- When a download goes live, set its https URL in `web/lib/shell/desktop-app.ts`
  **and** add that host to the opener scope in
  `src-tauri/capabilities/default.json` — otherwise the in-app Download link
  opens nothing.

| | macOS | Windows |
|---|---|---|
| Built on | your Mac — `scripts/release-shell.sh` | GitHub Actions — `.github/workflows/shell-windows.yml` |
| Output | `yarnnn_<ver>_aarch64.dmg` | `yarnnn_<ver>_x64-setup.exe` (per-user install, no admin) |
| Unsigned, a stranger sees | *"yarnnn is damaged"* — a wall | *"Windows protected your PC"* — a warning with *Run anyway* |
| Signing needs | Apple Developer ID ($99/yr) | a code-signing certificate (below) |

Everything in the repo is already wired. What follows is the part only you can
do, because it needs an account and a payment method.

---

# macOS

## The one thing that will bite you

An unsigned, un-notarized app **downloads fine and then refuses to open**, with:

> **"yarnnn is damaged and can't be opened. You should move it to the Trash."**

That is not a warning a curious person clicks through. It says *malware*, and
it is the default experience for every Mac app distributed outside the App
Store without notarization. For a product whose pitch is trust and attribution,
it is the wrong first sentence.

There is no way around it in code. It needs an Apple Developer ID.

---

## Setup — once, about 30 minutes plus Apple's wait

**1. Enrol in the Apple Developer Program** — <https://developer.apple.com>,
$99/year. An **individual** account is enough; an organization account needs a
D-U-N-S number and takes considerably longer. Approval is usually same-day but
can take a few days.

**2. Create a "Developer ID Application" certificate.**
In Xcode: Settings → Accounts → your Apple ID → Manage Certificates → **+** →
*Developer ID Application*. Or generate a CSR in Keychain Access and upload it
at developer.apple.com → Certificates.

Verify it landed:

```bash
security find-identity -v -p codesigning
```

You want a line reading `Developer ID Application: Your Name (TEAMID)`.
⚠️ *Apple Development* and *Mac Developer* certificates are **not** the same
thing and will not work for distribution.

**3. Create an app-specific password** — <https://account.apple.com> → Sign-In
and Security → App-Specific Passwords. **Not** your Apple ID password.

**4. Store the notarization credentials** (once; they live in your keychain,
never in this repo):

```bash
xcrun notarytool store-credentials yarnnn \
  --apple-id "you@example.com" \
  --team-id  "YOURTEAMID" \
  --password "abcd-efgh-ijkl-mnop"
```

Your team ID is the parenthesised code in the certificate name above.

---

## Building a release

```bash
./scripts/release-shell.sh
```

It refuses early, with a sentence you can act on, if any of the four setup
steps is missing. Otherwise it builds the host, bundles and signs the
app, submits it to Apple, waits for the scan (usually 1–5 minutes), staples the
ticket to the DMG, and asks Gatekeeper directly whether a stranger could open
it.

The result:

```
src-tauri/target/release/bundle/dmg/yarnnn_0.1.0_aarch64.dmg
```

⚠️ **This is an Apple Silicon build.** An Intel Mac cannot run it. If you need
both, build on each architecture or add `--target universal-apple-darwin` (and
install the Intel toolchain with `rustup target add x86_64-apple-darwin`).

---

## Before you publish the link

**Verify on a machine that never built it.** This is the whole point — the
build machine trusts its own output, so testing there proves nothing about what
a visitor sees. If you only have one Mac, simulate the download's quarantine
flag:

```bash
xattr -w com.apple.quarantine "0081;00000000;Safari;" ~/Downloads/yarnnn_0.1.0_aarch64.dmg
open ~/Downloads/yarnnn_0.1.0_aarch64.dmg
```

If it opens without a warning, a visitor's will too. If you see "damaged",
something in the sign → notarize → staple chain did not take, and the DMG is
not ready to publish.

---

## Testing leaves ghosts

Every `cargo tauri build` writes a `yarnnn.app` into `src-tauri/target/`, and
every DMG you mount registers the copy inside it. macOS **remembers all of
them**: Spotlight offers several yarnnns, and `yarnnn://` may resolve to a copy
that no longer exists.

Ten stale registrations accumulated during this build-out. To see what macOS
thinks exists:

```bash
LSR=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister
$LSR -dump | grep -oE "/[^ ]*yarnnn\.app" | sort -u
```

Anything other than `/Applications/yarnnn.app` is a ghost. Unregister each:

```bash
$LSR -u "/path/to/the/ghost/yarnnn.app"
```

⚠️ `lsregister -kill -r` (the "rebuild the whole database" incantation every
answer online recommends) **did not clear them** — the entries survived the
rebuild and had to be unregistered by path. Register the installed copy again
afterwards, or the `yarnnn://` deep link has no handler:

```bash
$LSR -f /Applications/yarnnn.app
```

Unmount DMGs when you are done with them (`hdiutil detach /Volumes/yarnnn`), and
prefer testing the copy in `/Applications` over one in `/tmp` — Launch Services
indexes `/Applications` reliably and a temp directory inconsistently.

---

# Windows

## Cutting the installer

A Windows installer needs Windows (the resource compiler and NSIS), so it is
built on a GitHub Actions runner, by hand:

```bash
gh workflow run shell-windows.yml          # or: Actions tab → shell-windows → Run
gh run watch                                # ~10–15 min
gh run download --name yarnnn-windows      # → yarnnn_<ver>_x64-setup.exe
```

The installer carries only the native host and its bootstrap page — the
interface is the website, loaded at launch (ADR-663 D1) — so the runner builds
no web code and needs no secrets.

## Installing it (what a tester sees)

1. Run `yarnnn_<ver>_x64-setup.exe`. It installs for the current user — no
   administrator prompt — and registers `yarnnn://` so sign-in can hand back.
2. **Unsigned builds only:** SmartScreen shows *"Windows protected your PC"*.
   Click **More info → Run anyway**. Fine for a tester you know; not for a
   public link (see signing below).
3. WebView2 ships with Windows 10 and 11. On a machine without it, the
   installer downloads it (needs a network connection).
4. Sign in: the app opens the browser, the browser signs in, the app receives
   the session (ADR-661 §7i). If a second yarnnn window appears instead of the
   first one signing in, the single-instance hand-off (§7o) is broken — report it.

## Signing — before a public link

Unsigned, SmartScreen warns every new downloader. The options, as of 2026:

- **Azure Trusted Signing** — ~$10/month, the cheapest route, and Tauri
  supports it directly. Eligibility is restricted by country and entity type;
  **check whether a Korean entity qualifies before planning around it.**
- **An OV code-signing certificate** from a CA — ~$200–500/year. Since 2023 the
  key must live on a hardware token or a cloud HSM, so issuance takes days. An
  organization certificate needs a registered legal entity; the publisher name
  shown is whatever the certificate names.
- Either way, a new certificate still builds SmartScreen reputation over its
  first downloads; an EV certificate no longer skips that.

Once chosen, signing is configured in `tauri.conf.json` → `bundle.windows`
and the workflow gains the credential as a secret. Nothing else changes.

## Testing leaves ghosts (Windows)

Uninstall from *Settings → Apps* before installing a newer unsigned build, so
only one `yarnnn://` handler is registered.

---

# Both

## Two settings outside this repo

**1. The Supabase redirect allowlist — nothing for the desktop app.** The app
starts no auth flow of its own (ADR-661 §7p): its sign-in page opens
`https://www.yarnnn.com/auth/desktop`, the website signs the member in with any
method it has (password, Google, sign-up, a reset link) through its existing
`https://` callback, and the page hands the session to the app over
`yarnnn://auth/session` — a browser navigation to a local scheme that Supabase
never sees. A `yarnnn://auth/callback` entry left from the superseded design is
unused and can be removed.

**2. The API's CORS allowlist needs nothing.** The app's requests carry the
website's own origin (ADR-663 D1). The Tauri origins the old static-export
builds used were removed, which retired every 0.1.x install.

---

## The download page

**Where members find it**: Settings → Desktop app lists every platform. It
reads ONE roster, `web/lib/shell/desktop-app.ts` — each entry is `null` ("Not
published yet") until you set the https URL of a **signed** build there; the
ADR-661 gate refuses anything else and any installer link outside that file.
Publishing = cut the signed build, upload it, set its URL, ship.

A version, a size, and what it needs. The shell is not a different product, so
it does not need its own pitch:

> **yarnnn for Mac** — 7.9 MB · macOS 10.15 or later · Apple Silicon
> **yarnnn for Windows** — Windows 10 or 11 · x64
> [Download](…)

Do **not** ship instructions to bypass Gatekeeper or SmartScreen (`xattr -cr`,
right-click → Open, *Run anyway*). If those are needed, the build is not ready
for a stranger — asking one to disable a security check to try your product is
a worse first impression than having no desktop app at all. A tester you know
is a different case, and the Windows section says so.

---

## Updating

There is no auto-update yet. A new version means a new DMG or installer and a
new link, and members find out by visiting the site.

Tauri's updater is the eventual answer — it needs a signing keypair and a
manifest the app polls. It is deliberately not built yet: it has its own key
management, and shipping one unversioned build first is the smaller step.
