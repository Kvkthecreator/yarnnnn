#!/usr/bin/env bash
#
# Publish a desktop release to our own storage — the files
# www.yarnnn.com/download/{platform} serves (ADR-661 §7q, ADR-663).
#
#   scripts/publish-desktop-release.sh            # the version in src-tauri/Cargo.toml
#   scripts/publish-desktop-release.sh 0.4.3
#
# The release was built by .github/workflows/desktop-release.yml when the tag
# `desktop-vX.Y.Z` was pushed. This takes THAT run's installers — both
# platforms, from the tagged commit, never HEAD (other sessions move main while
# a release builds) — and uploads each to the public `desktop-releases` bucket
# (supabase/migrations/261) twice: under its STABLE name, which the download
# links point at and every release overwrites, and under `<version>/`, which is
# kept — the history, and the rollback (re-publish an old version's files).
#
# WHY THE NAMES ARE STABLE: web/lib/shell/desktop-app.ts links to the bucket
# path by name, so a versioned name would break every link on the next
# release. The roster below and DESKTOP_ASSET_NAMES are held equal by the
# ADR-661 gate.
#
# Needs SUPABASE_URL and SUPABASE_SERVICE_KEY — the environment, else api/.env.
# The bucket has no write policy: only the service key can publish. `gh` must
# be signed in to read the workflow's artifacts.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUCKET="desktop-releases"
WORKFLOW="desktop-release.yml"

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
asset_glob() {
  case "$1" in
    mac)     echo "*.dmg" ;;
    windows) echo "*-setup.exe" ;;
  esac
}
PLATFORMS=(mac windows)

# The version is the host's (ADR-663 D2), read from the one place it lives.
VERSION="${1:-$(sed -nE 's/^version = "([^"]+)"/\1/p' "$REPO/src-tauri/Cargo.toml" | head -1)}"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "✗ usage: $0 [X.Y.Z]" >&2; exit 1; }
TAG="desktop-v$VERSION"

if [[ -z "${SUPABASE_URL:-}" || -z "${SUPABASE_SERVICE_KEY:-}" ]] && [[ -f "$REPO/api/.env" ]]; then
  set -a; source "$REPO/api/.env"; set +a
fi
[[ -n "${SUPABASE_URL:-}" && -n "${SUPABASE_SERVICE_KEY:-}" ]] || {
  echo "✗ SUPABASE_URL / SUPABASE_SERVICE_KEY not set (environment or api/.env)" >&2; exit 1; }

# The tag marks the commit the release was cut from, and must be on main: a
# published build is one anyone can rebuild.
git -C "$REPO" fetch -q origin main "refs/tags/$TAG:refs/tags/$TAG" 2>/dev/null || {
  echo "✗ no tag $TAG on origin. Release: bump Cargo.toml, push, then" >&2
  echo "    git tag $TAG && git push origin $TAG" >&2; exit 1; }
COMMIT="$(git -C "$REPO" rev-list -n1 "$TAG")"
git -C "$REPO" merge-base --is-ancestor "$COMMIT" origin/main || {
  echo "✗ $TAG (${COMMIT:0:7}) is not on origin/main." >&2; exit 1; }

# The builds: the workflow's successful run for that commit — never an older
# run's, which would publish a different host under this version.
RUN="$(gh run list --workflow "$WORKFLOW" --status success --limit 50 \
  --json databaseId,headSha --jq ".[] | select(.headSha==\"$COMMIT\") | .databaseId" | head -1)"
[[ -n "$RUN" ]] || {
  echo "✗ no successful $WORKFLOW run for $TAG (${COMMIT:0:7}) yet." >&2
  echo "  Watch it: gh run watch \$(gh run list --workflow $WORKFLOW --limit 1 --json databaseId --jq '.[0].databaseId')" >&2
  exit 1; }

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# Fetch both before uploading either: a release is both platforms or neither.
for P in "${PLATFORMS[@]}"; do
  gh run download "$RUN" --name "yarnnn-$P" --dir "$STAGE/$P"
  FILE="$(find "$STAGE/$P" -name "$(asset_glob "$P")" | head -1)"
  [[ -f "$FILE" ]] || { echo "✗ run $RUN has no $P installer" >&2; exit 1; }
  [[ "$(basename "$FILE")" == *"_${VERSION}_"* ]] || {
    echo "✗ $P installer $(basename "$FILE") is not version $VERSION" >&2; exit 1; }
done

upload() {  # $1 = platform, $2 = file, $3 = object path, $4 = cache seconds
  curl -sf -X POST "$SUPABASE_URL/storage/v1/object/$BUCKET/$3" \
    -H "apikey: $SUPABASE_SERVICE_KEY" \
    -H "Content-Type: $(asset_mime "$1")" \
    -H "cache-control: max-age=$4" \
    -H "x-upsert: true" \
    --data-binary "@$2" >/dev/null
}

echo "▸ $TAG (${COMMIT:0:7}, run $RUN) → $BUCKET"
for P in "${PLATFORMS[@]}"; do
  FILE="$(find "$STAGE/$P" -name "$(asset_glob "$P")" | head -1)"
  NAME="$(asset_name "$P")"
  upload "$P" "$FILE" "$VERSION/$NAME" 31536000   # a version's file never changes
  upload "$P" "$FILE" "$NAME" 300                 # the stable name: shows within minutes

  # The question is not "did the upload succeed" but "does the public link
  # serve this file". Ask it.
  URL="$SUPABASE_URL/storage/v1/object/public/$BUCKET/$NAME"
  SERVED="$(curl -sI "$URL?v=$VERSION" | tr -d '\r' | awk 'tolower($1)=="content-length:"{print $2}')"
  WANT="$(wc -c < "$FILE" | tr -d ' ')"
  [[ "$SERVED" == "$WANT" ]] || { echo "✗ $URL serves $SERVED bytes, expected $WANT" >&2; exit 1; }
  echo "✓ $P: $WANT bytes at $URL"
done
