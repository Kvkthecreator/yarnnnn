#!/usr/bin/env bash
#
# Build a SIGNED, NOTARIZED, STAPLED macOS build of the desktop app.
# ADR-661 §8 step 5. The version is src-tauri/Cargo.toml's (ADR-663 D2); tag
# the commit `desktop-vX.Y.Z` once the build is handed to anyone.
#
#   ./scripts/release-shell.sh
#
# WHY EACH STEP EXISTS, because skipping one produces a build that looks fine
# on this machine and is unusable on anyone else's:
#
#   sign      — without a Developer ID certificate the app is ad-hoc signed.
#               It runs here (the machine that built it) and nowhere else.
#   notarize  — Apple scans the signed build and issues a ticket. WITHOUT
#               this, a DOWNLOADED app is quarantined and macOS says
#               "yarnnn is damaged and can't be opened" — which reads as
#               malware, not as a warning. It is the single most common way a
#               first release fails.
#   staple    — attaches the ticket to the DMG so the check passes offline.
#               Without it a member with no network, or with Apple's service
#               having a bad day, sees the damaged message anyway.
#
# WHAT YOU NEED FIRST (once, ~30 min plus Apple's enrollment wait):
#
#   1. Enrol in the Apple Developer Program — https://developer.apple.com
#      ($99/yr). An individual account is enough.
#   2. Create a "Developer ID Application" certificate and install it in your
#      login keychain. `security find-identity -v -p codesigning` must list it.
#   3. Create an app-specific password at https://account.apple.com (Sign-In
#      and Security → App-Specific Passwords) — NOT your Apple ID password.
#   4. Store the notarization credentials once:
#
#        xcrun notarytool store-credentials yarnnn \
#          --apple-id "you@example.com" \
#          --team-id  "YOURTEAMID" \
#          --password "abcd-efgh-ijkl-mnop"
#
# Nothing secret lives in this repo: the identity comes from the keychain and
# the credentials from a named keychain profile.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="${YARNNN_NOTARY_PROFILE:-yarnnn}"

cd "$REPO/src-tauri"

# ── Preflight ────────────────────────────────────────────────────────────────
# Fail here with a sentence you can act on, rather than 20 minutes later with
# a codesign error code.

# rustup installs to ~/.cargo/bin, which a non-login shell (a CI step, a
# script run from an editor) does not have on PATH. Add it before deciding
# cargo is missing — otherwise this reports "install Rust" to someone who
# already has it.
export PATH="$PATH:$HOME/.cargo/bin"

if ! command -v cargo >/dev/null; then
  echo "✗ cargo not found. Install Rust: https://rustup.rs" >&2
  exit 1
fi

IDENTITY="${APPLE_SIGNING_IDENTITY:-}"
if [[ -z "$IDENTITY" ]]; then
  # `|| true`: with no certificate the grep matches nothing and exits 1, and
  # under `set -e` that kills the script HERE — before the message below that
  # explains what to do. The preflight would then fail silently with exit 1,
  # which is the worst possible version of a helpful check. Found by tracing
  # it after exactly that happened.
  IDENTITY="$(security find-identity -v -p codesigning 2>/dev/null \
    | grep "Developer ID Application" | head -1 \
    | sed -E 's/.*"(.*)".*/\1/' || true)"
fi

if [[ -z "$IDENTITY" ]]; then
  cat >&2 <<'MSG'
✗ No "Developer ID Application" certificate found.

  Without one the build is ad-hoc signed: it runs on THIS machine and shows
  "yarnnn is damaged and can't be opened" on every other one.

  See the header of this script for the four setup steps.

  To build an unsigned copy anyway (local use only):
      cd src-tauri && cargo tauri build
MSG
  exit 1
fi
echo "▸ signing identity: $IDENTITY"

if ! xcrun notarytool history --keychain-profile "$PROFILE" >/dev/null 2>&1; then
  cat >&2 <<MSG
✗ No notarization credentials stored under the profile "$PROFILE".

  Run:
      xcrun notarytool store-credentials $PROFILE \\
        --apple-id "you@example.com" --team-id "YOURTEAMID" \\
        --password "<app-specific-password>"
MSG
  exit 1
fi
echo "▸ notary profile:   $PROFILE"

# ── Build + sign ─────────────────────────────────────────────────────────────
# Tauri signs during the bundle step when this is set, so the .app inside the
# DMG is signed too — signing only the DMG leaves the app inside it unsigned,
# and Gatekeeper checks the app.
echo "▸ building the host (the interface is the website — ADR-663 D1)…"
APPLE_SIGNING_IDENTITY="$IDENTITY" cargo tauri build

DMG="$(find target/release/bundle/dmg -name '*.dmg' -maxdepth 1 | head -1)"
APP="target/release/bundle/macos/yarnnn.app"
[[ -f "$DMG" ]] || { echo "✗ no DMG produced" >&2; exit 1; }

echo "▸ verifying the signature…"
codesign --verify --deep --strict --verbose=2 "$APP"

# ── Notarize + staple ────────────────────────────────────────────────────────
echo "▸ notarizing (Apple's scan — usually 1–5 minutes)…"
xcrun notarytool submit "$DMG" --keychain-profile "$PROFILE" --wait

echo "▸ stapling the ticket…"
xcrun stapler staple "$DMG"

# The real question is not "did the commands succeed" but "will Gatekeeper let
# a stranger open this". Ask it directly.
echo "▸ verifying as Gatekeeper will see it…"
spctl --assess --type open --context context:primary-signature -vv "$DMG"

echo
echo "✓ Ready to publish:"
echo "  $REPO/src-tauri/$DMG"
echo
echo "  Verify on a machine that never built it:"
echo "    curl -LO <your-url>/$(basename "$DMG") && open $(basename "$DMG")"
