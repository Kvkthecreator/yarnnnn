# Publishing the Mac app

What stands between the build on your machine and a stranger downloading it and
it just working. ADR-661 §8 steps 4–5.

Everything in the repo is already wired. This is the part only you can do,
because it needs an Apple account and a payment method.

---

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
steps is missing. Otherwise it builds the web export, bundles and signs the
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

## Two settings outside this repo

**1. The Supabase redirect allowlist.** The shell signs in through
`yarnnn://auth/callback`, which the provider will refuse unless it is listed.
In the Supabase dashboard → Authentication → URL Configuration → Redirect URLs,
add:

```
yarnnn://auth/callback
```

alongside the existing `https://` entries. Without it a member reaches the
consent screen, approves, and lands on an error they cannot act on.

**2. The API's CORS allowlist** already carries the shell's origins
(`tauri://localhost`, `http://tauri.localhost` — `api/main.py`). They ship with
the code; nothing to do unless the origins change.

---

## The download page

A version, a size, and what it needs. The shell is not a different product, so
it does not need its own pitch:

> **yarnnn for Mac** — 7.9 MB · macOS 10.15 or later · Apple Silicon
> [Download](…)

Do **not** ship instructions to bypass Gatekeeper (`xattr -cr`, right-click →
Open). If those are needed, the build is not ready — asking a stranger to
disable a security check to try your product is a worse first impression than
having no Mac app at all.

---

## Updating

There is no auto-update yet. A new version means a new DMG and a new link, and
members find out by visiting the site.

Tauri's updater is the eventual answer — it needs a signing keypair and a
manifest the app polls. It is deliberately not built yet: it has its own key
management, and shipping one unversioned build first is the smaller step.
