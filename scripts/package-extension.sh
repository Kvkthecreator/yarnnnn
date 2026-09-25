#!/usr/bin/env bash
#
# Package the yarnnn extension from extension/ — the two forms a member can get.
#
#   scripts/package-extension.sh [store] [out.zip]
#   # the Chrome Web Store upload; default ~/Downloads/yarnnn-chrome-extension-<version>-store.zip
#   scripts/package-extension.sh manual
#   # the manual-install zip members download from Settings → Your browser
#   # (ADR-664 Amendment 2), built AND published to our desktop-releases bucket
#
# The repo's extension/ is the development copy; the store upload differs in
# exactly three ways, applied here so no upload is ever edited by hand:
#   · the manifest's `key` is removed — the store refuses an upload that carries
#     one and signs the item with its own. (Once the store's public key is IN the
#     manifest, a hand-loaded copy already has the store's id; the store still
#     wants the field absent from the upload.)
#   · `http://localhost:*` leaves `externally_connectable` — a development
#     origin has no business in a published extension.
#   · the development files stay out: README.md, e2e/, and store-assets/ (the
#     listing's images, uploaded to the dashboard, never shipped in the package).
# The MANUAL zip differs from the store upload in one way: it KEEPS the `key`.
# Loaded unpacked, the key is what gives it the store's id (apafdk…), which the
# website and the desktop app address — without it Chrome would assign a random
# id and nothing could reach it.
# ADR-662 D15; the listing's history is in docs/SESSION-HANDOFF.md.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO/extension"
VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$SRC/manifest.json")"
MODE=store
if [[ "${1:-}" == store || "${1:-}" == manual ]]; then MODE="$1"; shift; fi
if [[ "$MODE" == manual ]]; then
  OUT="$(mktemp -d)/yarnnn-chrome-extension.zip"
else
  OUT="${1:-$HOME/Downloads/yarnnn-chrome-extension-$VERSION-store.zip}"
fi

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

rsync -a --exclude README.md --exclude e2e --exclude store-assets --exclude '.*' "$SRC/" "$STAGE/"

python3 - "$STAGE" "$MODE" <<'EOF'
import json, os, sys
root, mode = sys.argv[1], sys.argv[2]
path = os.path.join(root, "manifest.json")
m = json.load(open(path))
if mode == "store":
    m.pop("key", None)
elif not m.get("key"):
    sys.exit("✗ the manual zip needs the manifest's key — without it the extension gets a random id")
ec = m.get("externally_connectable", {})
ec["matches"] = [u for u in ec.get("matches", []) if "localhost" not in u]
json.dump(m, open(path, "w"), indent=2, ensure_ascii=False)
# Every locale must parse — a broken one fails review, not the upload.
for loc in os.listdir(os.path.join(root, "_locales")):
    json.load(open(os.path.join(root, "_locales", loc, "messages.json")))
# Every file the manifest names must be in the package.
named = list(m.get("icons", {}).values()) + [m["background"]["service_worker"], m["action"]["default_popup"]]
missing = [f for f in named if not os.path.exists(os.path.join(root, f))]
if missing:
    sys.exit(f"✗ the manifest names files the package lacks: {missing}")
EOF

rm -f "$OUT"
(cd "$STAGE" && zip -qr -X "$OUT" .)
echo "✓ $OUT ($(unzip -l "$OUT" | tail -1 | awk '{print $2}') files, version $VERSION, $MODE)"
[[ "$MODE" == manual ]] || exit 0

# ── Publish the manual zip ───────────────────────────────────────────────────
# Beside the desktop installers, under a STABLE name (what
# www.yarnnn.com/download/chrome-extension redirects to — EXTENSION_DOWNLOAD in
# web/lib/shell/desktop-app.ts) and a kept `extension/<version>/` copy.
if [[ -z "${SUPABASE_URL:-}" || -z "${SUPABASE_SERVICE_KEY:-}" ]] && [[ -f "$REPO/api/.env" ]]; then
  set -a; source "$REPO/api/.env"; set +a
fi
[[ -n "${SUPABASE_URL:-}" && -n "${SUPABASE_SERVICE_KEY:-}" ]] || {
  echo "✗ SUPABASE_URL / SUPABASE_SERVICE_KEY not set (environment or api/.env)" >&2; exit 1; }
BUCKET="desktop-releases"
NAME="yarnnn-chrome-extension.zip"
for OBJ in "extension/$VERSION/$NAME:31536000" "$NAME:300"; do
  curl -sf -X POST "$SUPABASE_URL/storage/v1/object/$BUCKET/${OBJ%%:*}" \
    -H "apikey: $SUPABASE_SERVICE_KEY" -H "Content-Type: application/zip" \
    -H "cache-control: max-age=${OBJ##*:}" -H "x-upsert: true" \
    --data-binary "@$OUT" >/dev/null
done
URL="$SUPABASE_URL/storage/v1/object/public/$BUCKET/$NAME"
SERVED="$(curl -sI "$URL?v=$VERSION" | tr -d '\r' | awk 'tolower($1)=="content-length:"{print $2}')"
WANT="$(wc -c < "$OUT" | tr -d ' ')"
[[ "$SERVED" == "$WANT" ]] || { echo "✗ $URL serves $SERVED bytes, expected $WANT" >&2; exit 1; }
echo "✓ published: $WANT bytes at $URL"
