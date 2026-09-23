#!/usr/bin/env bash
#
# Upload a built desktop installer to the GitHub Release for this host version,
# under the STABLE name the download links point at.
#
#   scripts/publish-desktop-release.sh mac     path/to/yarnnn_0.3.0_aarch64.dmg
#   scripts/publish-desktop-release.sh windows path/to/yarnnn_0.3.0_x64-setup.exe
#
# Run by hand for the Mac (after scripts/release-shell.sh) and by
# .github/workflows/shell-windows.yml for Windows — one script, so the asset
# names cannot drift between the two.
#
# WHY THE NAMES ARE STABLE: web/lib/shell/desktop-app.ts links to
# `releases/latest/download/<name>`, which GitHub resolves to the newest
# release. A versioned name (yarnnn_0.3.0_…) would break every link on the
# next release. The ADR-661 gate holds the names here and there in step.
#
# WHY A RELEASE ONLY BECOMES "LATEST" WHEN BOTH FILES ARE ON IT: `latest` is
# one release for every asset. If 0.4.0 became latest with only the DMG
# uploaded, the Windows link would 404 until the Windows build caught up. So a
# release is created as NOT latest, and promoted only once it carries the
# whole roster below.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# The roster — platform → the stable asset name. Mirrors DESKTOP_DOWNLOADS.
asset_name() {
  case "$1" in
    mac)     echo "yarnnn-mac-arm64.dmg" ;;
    windows) echo "yarnnn-windows-x64-setup.exe" ;;
    *)       return 1 ;;
  esac
}
PLATFORMS=(mac windows)

PLATFORM="${1:-}"
FILE="${2:-}"
NAME="$(asset_name "$PLATFORM")" || {
  echo "✗ usage: $0 <mac|windows> <installer>" >&2; exit 1; }
[[ -f "$FILE" ]] || { echo "✗ no such file: $FILE" >&2; exit 1; }
command -v gh >/dev/null || { echo "✗ gh not found: https://cli.github.com" >&2; exit 1; }

# The version is the host's (ADR-663 D2), read from the one place it lives.
VERSION="$(sed -nE 's/^version = "([^"]+)"/\1/p' "$REPO/src-tauri/Cargo.toml" | head -1)"
[[ -n "$VERSION" ]] || { echo "✗ no version in src-tauri/Cargo.toml" >&2; exit 1; }
TAG="desktop-v$VERSION"

# The release is tagged at the commit the build was cut from, so that commit
# must already be on GitHub — otherwise the tag would point at nothing, or at
# a commit other than the one built.
COMMIT="${GITHUB_SHA:-$(git -C "$REPO" rev-parse HEAD)}"
if ! gh api "repos/{owner}/{repo}/commits/$COMMIT" --silent 2>/dev/null; then
  echo "✗ $COMMIT is not on GitHub — push it first, then publish." >&2
  exit 1
fi

if ! gh release view "$TAG" >/dev/null 2>&1; then
  echo "▸ creating release $TAG at ${COMMIT:0:7} (not latest until complete)…"
  gh release create "$TAG" --target "$COMMIT" --latest=false \
    --title "yarnnn desktop $VERSION" \
    --notes "The yarnnn desktop app, host $VERSION. Download from https://www.yarnnn.com/download — the page says how to open a build that is not yet signed."
fi

# Upload under the stable name. `#` sets the file's display label; the copy
# keeps the source name out of the asset.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp "$FILE" "$STAGE/$NAME"
echo "▸ uploading $NAME to $TAG…"
gh release upload "$TAG" "$STAGE/$NAME" --clobber

# Promote only a complete release.
HAVE="$(gh release view "$TAG" --json assets --jq '.assets[].name')"
MISSING=()
for p in "${PLATFORMS[@]}"; do
  n="$(asset_name "$p")"
  grep -qx "$n" <<<"$HAVE" || MISSING+=("$p")
done

if (( ${#MISSING[@]} == 0 )); then
  gh release edit "$TAG" --latest
  echo "✓ $TAG carries every platform and is now latest — /download serves it."
else
  echo "✓ uploaded. $TAG is NOT latest yet; still missing: ${MISSING[*]}."
  echo "  /download keeps serving the previous release until they are published."
fi
