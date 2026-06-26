// Build MCP widget bundles into single self-contained HTML files (ADR-372).
//
// Each widget under src/<name>/index.tsx is bundled (React inlined, minified) and
// wrapped in an HTML shell, emitted to dist/<name>.html. The output is ONE file
// with no external requests for code — required because the host renders it in a
// sandboxed iframe and the Python MCP service serves it verbatim at runtime
// (the service does not run this build; dist/ is committed).
//
//   node build.mjs              # build all widgets
//   node build.mjs trace-timeline   # build one
//
// CSP note: connectDomains is declared on the served resource's _meta.ui
// (registry.py). The bundle itself makes no network calls in v1 — it renders the
// trace result the host pushes over the MCP Apps bridge.

import { build } from "esbuild";
import { readdirSync, mkdirSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC = join(__dirname, "src");
const DIST = join(__dirname, "dist");

function htmlShell(js) {
  // Minimal shell: a root div + the inlined bundle. No external <script>/<link>.
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>YARNNN</title>
</head>
<body>
<div id="root"></div>
<script type="module">
${js}
</script>
</body>
</html>
`;
}

async function buildWidget(name) {
  const entry = join(SRC, name, "index.tsx");
  if (!existsSync(entry)) {
    throw new Error(`widget entry not found: ${entry}`);
  }
  const result = await build({
    entryPoints: [entry],
    bundle: true,
    minify: true,
    format: "esm",
    target: "es2020",
    jsx: "automatic",
    write: false,
    define: { "process.env.NODE_ENV": '"production"' },
    logLevel: "warning",
  });
  const js = result.outputFiles[0].text;
  mkdirSync(DIST, { recursive: true });
  const out = join(DIST, `${name}.html`);
  writeFileSync(out, htmlShell(js), "utf-8");
  console.log(`built ${name} → dist/${name}.html (${(js.length / 1024).toFixed(1)} KB js)`);
}

const arg = process.argv[2];
const widgets = arg
  ? [arg]
  : readdirSync(SRC, { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => d.name);

for (const w of widgets) {
  await buildWidget(w);
}
