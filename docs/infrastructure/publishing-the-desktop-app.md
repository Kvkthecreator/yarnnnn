# Publishing the desktop app

What stands between a build and a stranger downloading it and it just working.
ADR-661 §8 steps 4–5 (macOS) and §7o (Windows); ADR-663 for what is versioned.
How the app works is [docs/architecture/desktop-app.md](../architecture/desktop-app.md); this is the
operator's release checklist.

**The desktop app is the website in a native window** (ADR-663). The installer
carries only the host (`src-tauri/`) and a bootstrap page; the interface loads
from `https://www.yarnnn.com/desktop`, so a web deploy updates every installed
app. A new installer is needed only when the HOST changes.

## Versioning — one number, the host's

- The version lives in **`src-tauri/Cargo.toml`** and nowhere else (Tauri reads
  it; `tauri.conf.json` carries none). macOS and Windows share it.
- Bump it when the host changes. The tag `desktop-vX.Y.Z` on that commit IS
  the release: pushing it builds both installers (*Publishing a release*).
- The app sends `X-Yarnnn-Client: desktop/<version>` on every API request. To
  retire old installs, raise `DESKTOP_MIN_VERSION` in
  `api/services/desktop_client.py` **after** the new build is published: an
  older app then shows *"This version of the yarnnn app is out of date"* with a
  link to Settings → Desktop app.
- Downloads are objects in our public `desktop-releases` storage bucket under
  STABLE names, served through our own `www.yarnnn.com/download/{mac,windows}` — see *Publishing a release*
  below. The opener scope already allows `www.yarnnn.com`, so no host change
  is needed for the in-app Download link to open.

| | macOS | Windows |
|---|---|---|
| Built on | GitHub Actions — `.github/workflows/desktop-release.yml`, macOS runner | the same workflow, Windows runner |
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

**4. Hand the release workflow the certificate and the credentials** — as
GitHub repository secrets (Settings → Secrets and variables → Actions), never
in this repo. `.github/workflows/desktop-release.yml` passes each to Tauri only
when it is set, and Tauri then signs with the Developer ID, notarizes and
staples; with none set the build is ad-hoc sealed, as today.

| Secret | Value |
|---|---|
| `APPLE_CERTIFICATE` | the Developer ID certificate exported from Keychain Access as `.p12`, then `base64 -i cert.p12` (one line) |
| `APPLE_CERTIFICATE_PASSWORD` | the password you gave the `.p12` export |
| `APPLE_SIGNING_IDENTITY` | the full name, `Developer ID Application: Your Name (TEAMID)` |
| `APPLE_ID` | your Apple ID email |
| `APPLE_PASSWORD` | the app-specific password from step 3 |
| `APPLE_TEAM_ID` | the parenthesised code in the certificate name |

The next tagged release comes out signed. Nothing else changes.

---

⚠️ **The Mac build is Apple Silicon only** (the `macos-latest` runner). An
Intel Mac cannot run it. If that is ever needed, the workflow's Mac leg adds
`--target universal-apple-darwin` and `rustup target add x86_64-apple-darwin`.

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

The release workflow builds it on a Windows runner beside the Mac build. To
try a build of main without releasing it:

```bash
gh workflow run desktop-release.yml         # or: Actions tab → desktop-release → Run
gh run watch                                # ~10–15 min
gh run download --name yarnnn-windows       # → yarnnn_<ver>_x64-setup.exe
```

The installer carries only the native host and its bootstrap page — the
interface is the website, loaded at launch (ADR-663 D1) — so the runner builds
no web code and needs no web secrets.

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
and `desktop-release.yml` gains the credential as a secret. Nothing else changes.

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

## Publishing a release

Operator ruling, 2026-09-23: **during the beta, unsigned builds are published**,
behind `www.yarnnn.com/download` (`/ko/download`), which says they are unsigned
and gives each platform its one step to open. Signing, when it lands, removes
those steps from the page and changes nothing else.

**Where the files live.** Our own public Supabase Storage bucket,
`desktop-releases` (`supabase/migrations/261`). Each installer is uploaded
twice: under its STABLE name, which every release overwrites and every link
reads, and under `X.Y.Z/`, which is kept (the history; roll back by
re-publishing an old version's file). The names are the roster in
`scripts/publish-desktop-release.sh`, mirrored by `DESKTOP_ASSET_NAMES` in
`web/lib/shell/desktop-app.ts` (the ADR-661 gate holds the two equal). The
bucket has no write policy, so only the service key can publish; reads need no
token.

**The address people get is ours.** Every link points at
`/download/{platform}` (`web/app/download/[platform]/route.ts`), a 302 to the
bucket object. The file can move later without breaking a shared link.

**A release is one tag.** For version X.Y.Z:

```bash
# 1. bump `version` in src-tauri/Cargo.toml (cargo check updates Cargo.lock), commit, push
# 2. tag that commit — this starts .github/workflows/desktop-release.yml
git tag desktop-vX.Y.Z <commit> && git push origin desktop-vX.Y.Z
gh run watch                                  # both platforms, ~15 min
# 3. publish both installers from that run
scripts/publish-desktop-release.sh X.Y.Z
```

The workflow refuses a tag that is not Cargo.toml's version. The script takes
the run built from the TAG's commit — never HEAD, which other sessions move
while a release builds — fetches both installers before uploading either,
refuses a tag not on `origin/main`, and checks the public URL serves the
uploaded byte count. The stable name is cached for five minutes, so a new
release reaches every link within that. No web change is needed per release.

⚠️ **"Unsigned" must still be SEALED on the Mac.** `tauri.conf.json` carries
`signingIdentity: "-"`, so the bundle is ad-hoc signed and `codesign --verify`
passes. With `null` the app has only the linker's signature, verification fails
(*"code has no resources but signature indicates they must be present"* — the
0.2.0 build), and macOS calls it **"damaged"**, with no Open Anyway. A sealed
build gets the milder *cannot verify the developer* prompt, which System
Settings → Privacy & Security → **Open Anyway** clears. The workflow refuses to
keep a Mac build whose seal does not verify. The page keeps the `xattr` line as the
fallback for the damaged case only.

**Where members find it**: `/download` on the site (footer → Download), and
Settings → Desktop app, which links each platform through `/download/{platform}`
and, once one is live, to the page's steps.

## Updating

The interface updates itself: it is the website (ADR-663 D1), and a window left
open across a web deploy offers *Reload* (D7). The HOST does not yet: a new host
means a new release, the links do not change, and members find out through the
out-of-date notice (the 426) or by visiting /download.

Tauri's updater is next (ADR-663 D6): a signed manifest published beside the
installers, which the host checks at launch and every few hours. It needs a
signing keypair of its own — generated and held by the operator, the private
half a GitHub secret for `desktop-release.yml` — and it reaches only hosts
built with it, so the first updater-carrying version is installed by hand once.
