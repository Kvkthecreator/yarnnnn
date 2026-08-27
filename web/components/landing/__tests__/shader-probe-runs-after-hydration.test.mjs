/**
 * The WebGL probe must not decide the FIRST render (2026-08-27).
 *
 * ShaderCanvas guards a real crash: three.webgpu.js throws
 * "Cannot read properties of null (reading 'getSupportedExtensions')" when the
 * browser hands back a null GL context (hardware acceleration off, GPU process
 * crashed, sandboxed context). That guard — commit 8bdebbd — is load-bearing
 * and must stay.
 *
 * But the probe can only run in a browser, so WHERE it runs decides whether the
 * page hydrates. Run it as a `useState` lazy initialiser and it executes during
 * render: the server (no `window`) renders null, the client's first render
 * renders <Shader>, and React tears the tree down with #418 (hydration mismatch)
 * + #423 (error recovering from it). Measured on production before the fix:
 * 5x #418 + 1x #423 on every load, across 7 marketing routes — the SSR HTML
 * carried 0 <canvas> inside a wrapper the client filled on hydration.
 *
 * The probe therefore belongs in an effect, which is what 8bdebbd's own message
 * said it did ("probes WebGL support once on mount"). This gate holds that.
 *
 * Run: node web/components/landing/__tests__/shader-probe-runs-after-hydration.test.mjs
 * (from the REPO ROOT — the FE .mjs gates read paths relative to cwd.)
 */
import { readFileSync } from 'node:fs';
import assert from 'node:assert';

const CANVAS = 'web/components/landing/ShaderCanvas.tsx';
const LIGHT = 'web/components/landing/ShaderBackground.tsx';
const DARK = 'web/components/landing/ShaderBackgroundDark.tsx';

const read = (p) => readFileSync(p, 'utf8');
let failures = 0;
const check = (name, fn) => {
  try { fn(); console.log(`  PASS  ${name}`); }
  catch (e) { failures++; console.log(`  FAIL  ${name}\n        ${e.message}`); }
};

console.log('\nshader-probe-runs-after-hydration:');

/** The body of a named function declaration, brace-matched from its `{`.
 *
 * Brace-match rather than slice: ShaderCanvas is small today, but a fixed
 * window would reach into the component below the probe and assert against its
 * neighbour's code — the failure mode documented in refusals-are-legible. */
function functionBody(src, name) {
  const decl = src.indexOf(`function ${name}`);
  assert.ok(decl > 0, `${name} not found in ${CANVAS}`);
  // Skip the PARAMETER LIST before hunting the body's brace. ShaderCanvas
  // destructures its props — `({ className, children }: {...})` — so the first
  // `{` after the declaration opens the params, not the body. Brace-matching
  // from there returns the destructuring pattern and never reaches the hooks,
  // which made the effect assertion fail on a CORRECT file. Walk the parens to
  // their close first, then take the next brace.
  let i = src.indexOf('(', decl);
  assert.ok(i > 0, `${name}: no parameter list`);
  let paren = 0;
  for (; i < src.length; i++) {
    if (src[i] === '(') paren++;
    else if (src[i] === ')') { paren--; if (paren === 0) break; }
  }
  const open = src.indexOf('{', i);
  assert.ok(open > 0, `${name}: no body`);
  let depth = 0;
  for (let j = open; j < src.length; j++) {
    if (src[j] === '{') depth++;
    else if (src[j] === '}') {
      depth--;
      if (depth === 0) return src.slice(open, j + 1);
    }
  }
  throw new Error(`${name}: unbalanced braces`);
}

// ---- The probe still exists, and still guards the null context -------------
// Deleting the guard would "fix" hydration by reintroducing the crash 8bdebbd
// closed. Both halves have to hold at once.
check('the null-GL-context guard still exists', () => {
  const src = read(CANVAS);
  const body = functionBody(src, 'probeWebGLSupport');
  assert.ok(
    /getContext\(\s*["']webgl2["']\s*\)/.test(body),
    'probeWebGLSupport no longer probes for a webgl2 context — the three.webgpu.js ' +
    'null-context crash (8bdebbd) is unguarded again'
  );
  assert.ok(
    /return\s+gl\s*!==\s*null/.test(body),
    'probeWebGLSupport no longer returns the null-context verdict'
  );
});

// ---- ...but it must NOT be wired into the first render ---------------------
check('the probe is not a useState lazy initialiser', () => {
  const src = read(CANVAS);
  assert.ok(
    !/useState\(\s*probeWebGLSupport\s*\)/.test(src),
    'probeWebGLSupport is passed to useState as a lazy initialiser. That runs ' +
    'DURING the first client render, which disagrees with SSR (where the probe ' +
    'returns false for lack of `window`) — React #418/#423 on every ' +
    'WebGL-capable visitor. Call it from a useEffect instead.'
  );
  assert.ok(
    !/useState\(\s*\(\s*\)\s*=>\s*probeWebGLSupport/.test(src),
    'probeWebGLSupport is invoked inside a useState lazy initialiser arrow — ' +
    'same render-time execution, same hydration mismatch.'
  );
});

check('the probe is called from inside an effect body', () => {
  const src = read(CANVAS);
  // Anchor on the COMPONENT body, not the file. An `import { useEffect }` line
  // survives the defect untouched, so searching the whole file finds the import
  // and then finds `probeWebGLSupport` at its DECLARATION — the assertion passes
  // on the very file it is meant to reject. Falsifying this gate is how that was
  // caught; it had been green against the reintroduced bug.
  const body = functionBody(src, 'ShaderCanvas');
  const effect = body.indexOf('useEffect');
  assert.ok(
    effect > 0,
    'ShaderCanvas\'s body has no useEffect — the probe cannot be running on mount'
  );
  const open = body.indexOf('{', body.indexOf('=>', effect));
  let depth = 0, effectBody = null;
  for (let i = open; i < body.length; i++) {
    if (body[i] === '{') depth++;
    else if (body[i] === '}') {
      depth--;
      if (depth === 0) { effectBody = body.slice(open, i + 1); break; }
    }
  }
  assert.ok(effectBody, 'could not brace-match the useEffect body');
  assert.ok(
    /probeWebGLSupport\(\)/.test(effectBody),
    'probeWebGLSupport() is not CALLED inside the useEffect body — the shader ' +
    'would never mount, silently degrading every marketing route to a flat ' +
    'background'
  );
});

check('the first render matches the server (initial state is a constant false)', () => {
  const src = read(CANVAS);
  assert.ok(
    /useState(<[^>]*>)?\(\s*false\s*\)/.test(src),
    'the supported-state no longer initialises to a literal false. SSR renders ' +
    'null; anything else as the initial value re-opens the mismatch.'
  );
});

// ---- Both variants stay on the one wrapper --------------------------------
// A second spelling of the probe is how this defect comes back on one route
// only, which is the hardest version to notice.
for (const [label, path] of [['light', LIGHT], ['dark', DARK]]) {
  check(`the ${label} background routes through ShaderCanvas`, () => {
    const src = read(path);
    assert.ok(
      /<ShaderCanvas\b/.test(src),
      `${path} no longer mounts <ShaderCanvas> — it has grown its own shader ` +
      `mount, and the hydration fix (and the null-context guard) do not cover it`
    );
    assert.ok(
      !/getContext\(/.test(src),
      `${path} probes for a GL context itself — a second spelling of the guard. ` +
      `The probe lives in ShaderCanvas alone.`
    );
  });
}

console.log(failures ? `\n${failures} FAILED\n` : '\nall passed\n');
process.exit(failures ? 1 : 0);
