# yarnnn for Chrome

The executor of yarnnn's browser tools in the member's own Chrome (ADR-662 D15). How it works, what it may and
may not do, and how to change it: [docs/architecture/local-hands.md](../docs/architecture/local-hands.md).

**Try it unpacked**: `chrome://extensions` → Developer mode → Load unpacked → this folder. Then open yarnnn in
that Chrome; Settings → Desktop app says it is connected.

**Drive it**: `cd e2e && npm install --no-save playwright-core && node run.mjs` (Chrome for Testing).
