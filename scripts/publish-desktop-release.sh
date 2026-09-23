#!/usr/bin/env bash
#
# Publish a desktop installer to our own storage — the file
# www.yarnnn.com/download/{platform} serves (ADR-661 §7q).
#
#   scripts/publish-desktop-release.sh mac <the DMG release-shell.sh printed>
#   scripts/publish-desktop-release.sh windows            # fetches the CI build of HEAD
#   scripts/publish-desktop-release.sh windows <an .exe>
#
# Each upload lands twice in the public `desktop-releases` bucket
# (supabase/migrations/261): under its STABLE name, which the download links
# point at and every release overwrites, and under `<version>/`, which is kept
# — the history, and the rollback (re-publish an old version's file).
#
# WHY THE NAMES ARE STABLE: web/lib/shell/desktop-app.ts links to the bucket
# path by name, so a versioned name would break every link on the next
# release. The roster below and DESKTOP_ASSET_NAMES are held equal by the
# ADR-661 gate.
#
# The two platforms publish one at a time, so for a few minutes the Mac and
# Windows files can be different versions. Both hosts load the same website
# (ADR-663 D1), so nothing a member sees depends on the pair matching.
#
# Needs SUPABASE_URL and SUPABASE_SERVICE_KEY — the environment, else api/.env.
# The bucket has no write policy: only the service key can publish.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUCKET="desktop-releases"

# The roster — platform → stable name and the MIME the bucket admits.
asset_name() {
  case "$1" in
    mac)     echo "yarnnn-mac-arm64.dmg" ;;
    windows) echo "yarnnn-windows-x64-setup.exe" ;;
    *)       return 1 ;;
  esac
}
asset_mime() {
  case "$1" in
    mac)     echo "application/x-apple-diskimage" ;;
    windows) echo "application/vnd.microsoft.portable-executable" ;;
  esac
}

PLATFORM="${1:-}"
FILE="${2:-}"
NAME="$(asset_name "$PLATFORM")" || {
  echo "✗ usage: $0 <mac|windows> [installer]" >&2; exit 1; }

if [[ -z "${SUPABASE_URL:-}" || -z "${SUPABASE_SERVICE_KEY:-}" ]] && [[ -f "$REPO/api/.env" ]]; then
  set -a; source "$REPO/api/.env"; set +a
fi
[[ -n "${SUPABASE_URL:-}" && -n "${SUPABASE_SERVICE_KEY:-}" ]] || {
  echo "✗ SUPABASE_URL / SUPABASE_SERVICE_KEY not set (environment or api/.env)" >&2; exit 1; }

# The version is the host's (ADR-663 D2), read from the one place it lives.
VERSION="$(sed -nE 's/^version = "([^"]+)"/\1/p' "$REPO/src-tauri/Cargo.toml" | head -1)"
[[ -n "$VERSION" ]] || { echo "✗ no version in src-tauri/Cargo.toml" >&2; exit 1; }
COMMIT="$(git -C "$REPO" rev-parse HEAD)"

# A published build must be one someone else can rebuild: HEAD on GitHub.
git -C "$REPO" fetch -q origin
git -C "$REPO" merge-base --is-ancestor "$COMMIT" origin/main || {
  echo "✗ ${COMMIT:0:7} is not on origin/main — push it first." >&2; exit 1; }

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# Windows is built on a runner (.github/workflows/shell-windows.yml). With no
# file given, take that workflow's artifact for THIS commit — never an older
# run's, which would publish a different host under this version.
if [[ "$PLATFORM" == windows && -z "$FILE" ]]; then
  RUN="$(gh run list --workflow shell-windows.yml --status success --limit 30 \
    --json databaseId,headSha --jq ".[] | select(.headSha==\"$COMMIT\") | .databaseId" | head -1)"
  [[ -n "$RUN" ]] || {
    echo "✗ no successful shell-windows run for ${COMMIT:0:7}." >&2
    echo "  Run: gh workflow run shell-windows.yml && gh run watch" >&2; exit 1; }
  gh run download "$RUN" --name yarnnn-windows --dir "$STAGE/ci"
  FILE="$(find "$STAGE/ci" -name '*.exe' | head -1)"
fi
[[ -f "$FILE" ]] || { echo "✗ no such file: $FILE" >&2; exit 1; }

upload() {  # $1 = object path, $2 = cache seconds
  curl -sf -X POST "$SUPABASE_URL/storage/v1/object/$BUCKET/$1" \
    -H "apikey: $SUPABASE_SERVICE_KEY" \
    -H "Content-Type: $(asset_mime "$PLATFORM")" \
    -H "cache-control: max-age=$2" \
    -H "x-upsert: true" \
    --data-binary "@$FILE" >/dev/null
}

echo "▸ $PLATFORM $VERSION (${COMMIT:0:7}) → $BUCKET"
upload "$VERSION/$NAME" 31536000   # a version's file never changes
upload "$NAME" 300                 # the stable name: a new release shows within minutes

# The question is not "did the upload succeed" but "does the public link serve
# this file". Ask it.
URL="$SUPABASE_URL/storage/v1/object/public/$BUCKET/$NAME"
SERVED="$(curl -sI "$URL?v=$VERSION" | tr -d '\r' | awk 'tolower($1)=="content-length:"{print $2}')"
WANT="$(wc -c < "$FILE" | tr -d ' ')"
[[ "$SERVED" == "$WANT" ]] || { echo "✗ $URL serves $SERVED bytes, expected $WANT" >&2; exit 1; }

# Mark the commit a handed-out build came from (ADR-663 D2). One version, one commit.
TAG="desktop-v$VERSION"
if git -C "$REPO" rev-parse -q --verify "refs/tags/$TAG" >/dev/null \
   || git -C "$REPO" fetch -q origin "refs/tags/$TAG:refs/tags/$TAG" 2>/dev/null; then
  [[ "$(git -C "$REPO" rev-list -n1 "$TAG")" == "$COMMIT" ]] || \
    echo "⚠ $TAG already marks a different commit — bump the version for a new host." >&2
else
  git -C "$REPO" tag "$TAG" "$COMMIT" && git -C "$REPO" push -q origin "$TAG"
fi

echo "✓ serving $WANT bytes at $URL"
