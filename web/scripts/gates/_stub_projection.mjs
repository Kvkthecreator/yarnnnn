/** Load hook: stub `projection.ts` down to the pure constants that the
 *  mechanical-ops modules import from it.
 *
 *  `artifactOps.ts` needs exactly two values from projection — `DEEPEST_RUNG`
 *  and `OUT_OF_RUNG_TAGS`, both pure rung arithmetic. But projection also
 *  reaches the API client, whose TypeScript parameter properties node's
 *  type-strip loader cannot parse. Without this, any gate wanting to EXECUTE
 *  the real ops dies at import and has to fall back to text assertions —
 *  which is exactly what lets a wrong predicate pass.
 *
 *  The stub restates the rung law rather than importing it, so it is asserted
 *  against projection's own source at load: if the declaration there changes,
 *  this throws instead of silently testing against a stale rung set.
 *
 *  Registered alongside the TS resolver:
 *    node --import ./web/scripts/gates/_ts_register.mjs \
 *         --import ./web/scripts/gates/_stub_projection_register.mjs <gate>
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const HEADING_RUNGS = [1, 2, 3];
const DEEPEST_RUNG = Math.max(...HEADING_RUNGS);
const OUT_OF_RUNG_TAGS = [1, 2, 3, 4, 5, 6]
  .filter((n) => !HEADING_RUNGS.includes(n))
  .map((n) => `h${n}`);

export async function load(url, context, nextLoad) {
  if (!url.endsWith('/components/workspace/viewers/projection.ts')) {
    return nextLoad(url, context);
  }
  // Drift guard: the stub must agree with the module it replaces.
  const src = readFileSync(fileURLToPath(url), 'utf8');
  const declared = src.match(/export const HEADING_RUNGS = \[([0-9, ]+)\]/);
  if (!declared) {
    throw new Error('_stub_projection: HEADING_RUNGS no longer declared as a literal in projection.ts');
  }
  const actual = declared[1].split(',').map((n) => Number(n.trim()));
  if (actual.join() !== HEADING_RUNGS.join()) {
    throw new Error(
      `_stub_projection: rung set drifted — projection declares [${actual}], stub has [${HEADING_RUNGS}]`,
    );
  }
  return {
    format: 'module',
    shortCircuit: true,
    source: `
      export const HEADING_RUNGS = ${JSON.stringify(HEADING_RUNGS)};
      export const DEEPEST_RUNG = ${JSON.stringify(DEEPEST_RUNG)};
      export const OUT_OF_RUNG_TAGS = ${JSON.stringify(OUT_OF_RUNG_TAGS)};
    `,
  };
}
