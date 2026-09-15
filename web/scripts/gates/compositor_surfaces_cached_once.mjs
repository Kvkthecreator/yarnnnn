/**
 * Gate: the composition is fetched ONCE per session, and the cache has ONE home.
 *
 * FOUND 2026-09-15, driving a real logged-in /desktop load on prod during the
 * beta-readiness pass: SEVEN identical `GET /api/programs/surfaces` requests in
 * a single page load. `useComposition`'s own docstring had claimed since ADR-225
 * that it "caches the response per session" — it never did. Every unprimed mount
 * called the fetcher directly, with no module cache and no in-flight dedupe, for
 * a response the same file describes as changing "only at deploy time".
 *
 * Nothing went red: each request returned 200. The only symptoms were latency
 * and seven times the load on the authenticated hot path — invisible to every
 * structural check, visible the moment the path is driven.
 *
 * FOUR claims, and the last two are the ones that rot:
 *   1. The cache lives at the FETCHER (lib/compositor/client.ts), not the hook —
 *      a hook runs once per mount, so a cache inside it dedupes nothing.
 *   2. In-flight dedupe exists. Seven components mounting in the SAME tick all
 *      miss a still-empty cache; without it they fire seven requests anyway.
 *      This is the observed case, so a cache without it fixes nothing.
 *   3. A FAILED fetch is not cached — otherwise one transient failure makes the
 *      cockpit render kernel defaults for the rest of the session.
 *   4. `reload()` bypasses the cache. A reload that serves the cache is the same
 *      class of lie in the other direction.
 *
 * Run: node scripts/gates/compositor_surfaces_cached_once.mjs   (from web/)
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const WEB = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
let passed = 0;
let failed = 0;
const check = (label, ok) => {
  if (ok) {
    passed += 1;
    console.log(`PASS  ${label}`);
  } else {
    failed += 1;
    console.log(`FAIL  ${label}`);
  }
};

const strip = (s) =>
  s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const fetcher = strip(readFileSync(join(WEB, "lib/compositor/client.ts"), "utf8"));
const hook = strip(readFileSync(join(WEB, "lib/compositor/useComposition.ts"), "utf8"));
const apiClient = strip(readFileSync(join(WEB, "lib/api/client.ts"), "utf8"));

// 1. The cache exists AT THE FETCHER — assert the assignment, not the name.
check(
  "the fetcher holds a module-level response cache",
  /let\s+cached\s*[:=]/.test(fetcher) && /cached\s*=\s*response/.test(fetcher),
);
check(
  "a cache hit returns before any network call",
  /if\s*\(\s*cached\s*\)\s*return\s+cached/.test(fetcher),
);

// 2. In-flight dedupe — the branch the seven simultaneous mounts take.
check(
  "an in-flight request is tracked and reused",
  /let\s+inFlight\s*[:=]/.test(fetcher) &&
    /if\s*\(\s*inFlight\s*\)\s*return\s+inFlight/.test(fetcher) &&
    /inFlight\s*=\s*\(/.test(fetcher),
);
check(
  "the in-flight handle is released in a finally",
  /finally\s*\{[^}]*inFlight\s*=\s*null/.test(fetcher),
);

// 3. A failure must not be cached. The assignment to `cached` must occur only
//    on the success path — i.e. never inside a catch block.
const catchBlocks = fetcher.match(/catch\s*\([^)]*\)\s*\{[\s\S]*?\n\s*\}/g) || [];
check(
  "no catch block caches a failed response",
  !catchBlocks.some((b) => /cached\s*=/.test(b)),
);

// 4. reload() forces past the cache — assert the ARGUMENT, not that reload exists.
check(
  "the hook's reload() forces a refetch past the cache",
  /reload:\s*\(\)\s*=>\s*load\(\s*true\s*\)/.test(hook) &&
    /fetchWorkspaceSurfaces\(\s*\{\s*force\s*\}/.test(hook),
);

// 5. SINGULAR IMPLEMENTATION — the hook must not grow a second cache.
check(
  "the hook holds no cache of its own (one home for the rule)",
  !/let\s+(cached|inFlight)\b/.test(hook) &&
    !/useRef\s*<[^>]*>\s*\(\s*null\s*\)\s*;?\s*\/\/\s*cache/i.test(hook),
);

// 6. A binding change drops the cache — the correctness half. Today every
//    caller hard-navigates, so this is defence in depth against the seventh.
check(
  "setActiveWorkspace invalidates the composition cache",
  /export function setActiveWorkspace[\s\S]{0,900}?invalidateWorkspaceSurfaces\(\)/.test(
    apiClient,
  ),
);
check(
  "the fetcher exports invalidateWorkspaceSurfaces and it clears BOTH handles",
  /export function invalidateWorkspaceSurfaces[\s\S]{0,200}?cached\s*=\s*null[\s\S]{0,120}?inFlight\s*=\s*null/.test(
    fetcher,
  ),
);

// 7. No import cycle: lib/api/client must NOT statically import the compositor
//    (it is imported BY it). A static edge here can leave the binding undefined
//    at call time under the bundler — throwing on the path it protects.
check(
  "api/client does not statically import the compositor client",
  !/^import\s+\{[^}]*invalidateWorkspaceSurfaces/m.test(apiClient) &&
    !/^import[^\n]*from\s+["']@\/lib\/compositor\/client["']/m.test(apiClient),
);

console.log("=".repeat(62));
console.log(
  `compositor cache gate: ${passed}/${passed + failed} passed, ${failed} failed`,
);
console.log("=".repeat(62));
process.exit(failed ? 1 : 0);
