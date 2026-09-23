#!/usr/bin/env bash
#
# Build the Chrome Web Store upload of the yarnnn extension from extension/.
#
#   scripts/package-extension.sh [out.zip]
#   # default: ~/Downloads/yarnnn-chrome-extension-<version>-store.zip
#
# The repo's extension/ is the development copy; the store upload differs in
# exactly three ways, applied here so no upload is ever edited by hand:
#   · the manifest's `key` is removed — the store refuses an upload that carries
#     one and signs the item with its own. (Once the store's public key is IN the
#     manifest, a hand-loaded copy already has the store's id; the store still
#     wants the field absent from the upload.)
#   · `http://localhost:*` leaves `externally_connectable` — a development
#     origin has no business in a published extension.
#   · the development files stay out: README.md, e2e/.
# ADR-662 D15; the listing's history is in docs/SESSION-HANDOFF.md.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO/extension"
VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$SRC/manifest.json")"
OUT="${1:-$HOME/Downloads/yarnnn-chrome-extension-$VERSION-store.zip}"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

rsync -a --exclude README.md --exclude e2e --exclude '.*' "$SRC/" "$STAGE/"

python3 - "$STAGE" <<'EOF'
import json, os, sys
root = sys.argv[1]
path = os.path.join(root, "manifest.json")
m = json.load(open(path))
m.pop("key", None)
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
echo "✓ $OUT ($(unzip -l "$OUT" | tail -1 | awk '{print $2}') files, version $VERSION)"
