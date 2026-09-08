#!/usr/bin/env node
// Verify `.next` can actually be PACKED, not merely that it compiled.
//
// Next writes one `*.nft.json` per function: the manifest of every file that
// function needs. Vercel lstat()s each path while packing and fails the whole
// deploy on the first one missing. Nothing in `next build` reads these, so a
// build that deletes or moves a traced file still exits 0 — and the failure
// only appears on Vercel, after the route table has already printed:
//
//   Error: ENOENT: no such file or directory, lstat '.next/server/chunks/2511.js.map'
//
// That is how a source-map cleanup shipped a broken deploy twice (2026-09-08).
// `pnpm build` is not verification for anything that changes build OUTPUT.
//
// Usage: node scripts/check-build-traces.mjs [--dist .next]
import { readFileSync, statSync, readdirSync } from 'node:fs';
import path from 'node:path';

// Plain recursive walk — `fs.globSync` is too new to rely on across CI images.
function findTraces(dir, out = []) {
  let entries;
  try {
    entries = readdirSync(dir, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) findTraces(full, out);
    else if (e.name.endsWith('.nft.json')) out.push(full);
  }
  return out;
}

const distArg = process.argv.indexOf('--dist');
const dist = distArg !== -1 ? process.argv[distArg + 1] : '.next';

const traces = findTraces(path.join(dist, 'server'));
if (traces.length === 0) {
  console.error(`FAIL: no traces under ${dist}/server — run \`next build\` first.`);
  process.exit(1);
}

const missing = [];
let refs = 0;
let packed = 0;
for (const trace of traces) {
  const base = path.dirname(trace);
  let files;
  try {
    files = JSON.parse(readFileSync(trace, 'utf8')).files ?? [];
  } catch (err) {
    console.error(`FAIL: unreadable trace ${trace}: ${err.message}`);
    process.exit(1);
  }
  for (const rel of files) {
    const p = path.normalize(path.join(base, rel));
    refs++;
    try {
      packed += statSync(p).size;      // exactly what Vercel does
    } catch {
      missing.push({ trace, p });
    }
  }
}

console.log(`traces: ${traces.length}  refs: ${refs}  packed: ${(packed / 1e6).toFixed(0)} MB`);

if (missing.length > 0) {
  console.error(`\nFAIL: ${missing.length} traced path(s) do not exist.`);
  console.error('Vercel will fail this deploy with ENOENT while packing functions.\n');
  for (const { trace, p } of missing.slice(0, 10)) {
    console.error(`  ${p}\n    referenced by ${trace}`);
  }
  if (missing.length > 10) console.error(`  ... and ${missing.length - 10} more`);
  process.exit(1);
}

console.log('OK: every traced path resolves — the build packs clean.');
