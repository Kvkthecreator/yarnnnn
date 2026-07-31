/**
 * Refusals must be LEGIBLE, not merely correct (2026-07-31 click-pass F2/F3/F4).
 *
 * The pass found three defects of one shape: yarnnn refuses correctly at the
 * server and says nothing at the surface. Each was a swallowed throw or a
 * collapsed error state — invisible to TypeScript and to any test that only
 * asserts the happy path.
 *
 * Run: node web/lib/workspace/__tests__/refusals-are-legible.test.mjs
 * (from the REPO ROOT — the FE .mjs gates read paths relative to cwd.)
 */
import { readFileSync } from 'node:fs';
import assert from 'node:assert';

const MEMBERS_CARD = 'web/components/workspace-concepts/WorkspaceMembersCard.tsx';
const VIEWER = 'web/lib/workspace/viewer.ts';
const WS_SETTINGS = 'web/app/(authenticated)/workspace-settings/page.tsx';

const read = (p) => readFileSync(p, 'utf8');
let failures = 0;
const check = (name, fn) => {
  try { fn(); console.log(`  PASS  ${name}`); }
  catch (e) { failures++; console.log(`  FAIL  ${name}\n        ${e.message}`); }
};

console.log('\nrefusals-are-legible:');

// ---- F4: the governance verbs must surface the server's refusal ------------
/** The body of an arrow-function handler, brace-matched from its `=> {`.
 *
 * A fixed-size slice is NOT good enough here: the handlers sit ~1.3KB apart, so
 * any window wide enough to contain one body reaches into the next one and the
 * assertion passes on its NEIGHBOUR's catch. That produced a gate which stayed
 * green through a deliberate reintroduction of the defect — caught only by
 * falsifying it. Brace-match instead. */
function handlerBody(src, name) {
  const decl = src.indexOf(`const ${name} = async`);
  assert.ok(decl > 0, `${name} not found`);
  const open = src.indexOf('{', src.indexOf('=>', decl));
  assert.ok(open > 0, `${name}: no body`);
  let depth = 0;
  for (let i = open; i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') {
      depth--;
      if (depth === 0) return src.slice(open, i + 1);
    }
  }
  throw new Error(`${name}: unbalanced braces`);
}

check('F4 governance verbs catch and display the server refusal', () => {
  const src = read(MEMBERS_CARD);
  for (const verb of ['onNarrow', 'onRevoke', 'onCap']) {
    const body = handlerBody(src, verb);
    assert.ok(
      /catch\s*\(\s*e\s*\)/.test(body),
      `${verb} has no catch — a 403 throw is swallowed by try/finally and the ` +
      `dialog sits there saying nothing (F4)`
    );
    assert.ok(
      /setGovernError\(/.test(body),
      `${verb} catches but never sets an error state — invisible refusal (F4)`
    );
  }
});

check('F4 the error state is actually RENDERED, not just stored', () => {
  const src = read(MEMBERS_CARD);
  // State that is set but never read is a fix that does nothing.
  const renders = src.match(/\{(governError|error) &&/g) || [];
  assert.ok(
    renders.length >= 3,
    `expected the refusal to render in the narrow, cap and revoke dialogs; ` +
    `found ${renders.length} render site(s)`
  );
  assert.ok(
    /role="alert"/.test(src),
    'the refusal is not announced to assistive tech (role="alert")'
  );
});

check('F4 prefers the SERVER\'s wording over an invented client message', () => {
  const src = read(MEMBERS_CARD);
  assert.ok(
    /function serverDetail\(/.test(src),
    'serverDetail() helper is gone — the server carries the actual reason ' +
    '("Only the workspace owner can…", "narrow cannot widen…")'
  );
  // BOTH wire shapes. The governance verbs answer through the envelope
  // middleware as {error:{message}}, NOT FastAPI's {detail} — verified by
  // probing /narrow as a member. Reading only `detail` compiles, ships, and
  // silently shows the generic fallback forever.
  assert.ok(
    /\.detail/.test(src) && /error\?\.\s*message|error\?\.message/.test(src),
    'serverDetail reads only one wire shape — it must handle {detail} AND ' +
    '{error:{message}} or the real refusal text never reaches the operator'
  );
});

// ---- F2: a transport blip must not read as a loss of authority -------------
check('F2 only a 403 hides the invite affordance', () => {
  const src = read(MEMBERS_CARD);
  const i = src.indexOf('const refreshInvites');
  assert.ok(i > 0, 'refreshInvites not found');
  const body = src.slice(i, i + 900);
  assert.ok(
    /status === 403/.test(body),
    'refreshInvites treats ANY failure as "not the owner", so a blip right ' +
    'after a successful invite blanks the roster and the invite reads as ' +
    'failed (F2)'
  );
  assert.ok(
    !/catch\s*\{\s*\n\s*setInvites\(\[\]\);\s*\n\s*setCanInvite\(false\);/.test(body),
    'the unconditional catch-all is back'
  );
});

// ---- F3: a revoked viewer must be told, not shown empty chrome -------------
check('F3 the roster read distinguishes 403 from an empty/failed read', () => {
  const src = read(VIEWER);
  // Assert the ASSIGNMENT, not the mere presence of the identifier: the
  // declaration and the hook both mention `membersForbidden`, so a name-only
  // check stays green when the 403 discrimination itself is deleted.
  assert.ok(
    /membersForbidden\s*=\s*status === 403/.test(src),
    'fetchMembers no longer derives `forbidden` from a 403 — a refusal ' +
    'collapses into [], indistinguishable from an empty roster, and a revoked ' +
    'viewer renders full chrome (F3)'
  );
  assert.ok(
    /forbidden:\s*boolean/.test(src),
    'useWorkspaceMembers does not expose `forbidden` for surfaces to act on'
  );
  assert.ok(
    /forbidden:\s*membersForbidden/.test(src),
    'the hook never propagates the flag into its state'
  );
});

check('F3 workspace-settings shows a refusal instead of pane chrome', () => {
  const src = read(WS_SETTINGS);
  assert.ok(
    /forbidden:\s*accessRefused/.test(src) || /accessRefused/.test(src),
    'the settings surface never reads the forbidden signal'
  );
  assert.ok(
    /don&rsquo;t have access|do not have access/.test(src),
    'no operator-facing copy for the no-access state'
  );
});

console.log(
  failures === 0
    ? '\nrefusals-are-legible: ALL PASS\n'
    : `\nrefusals-are-legible: ${failures} FAILED\n`
);
process.exit(failures === 0 ? 0 : 1);
