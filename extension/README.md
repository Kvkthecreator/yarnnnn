# yarnnn for Chrome

The executor of yarnnn's browser tools in the member's own Chrome (ADR-662 D15). How it works, what it may and
may not do, and how to change it: [docs/architecture/local-hands.md](../docs/architecture/local-hands.md).

**Try it unpacked**: `chrome://extensions` → Developer mode → Load unpacked → this folder. Then open yarnnn in
that Chrome; Settings → Your browser says it is connected. Members get the same thing as a zip from that pane
(ADR-664 am.2) — after changing this folder, re-publish it with `scripts/package-extension.sh manual`.

**Drive it**: `cd e2e && npm install --no-save playwright-core && node run.mjs` (Chrome for Testing).
