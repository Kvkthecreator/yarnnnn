/**
 * ADR-514 D2 gate — the handler set, EXECUTED.
 *
 * Run: node web/lib/file-types/__gate_adr514_d2.mjs   (from the repo root)
 *
 * The D1 gate could not see that Duplicate never reached the Files tree,
 * because it asserted the KERNEL verb and the kernel verb was fine. This gate
 * is written against that lesson: it EXECUTES the resolution order and asserts
 * PER-MOUNT reachability by source, rather than counting rows.
 *
 * The resolver is TypeScript with React-ish imports, so rather than compile it
 * we re-derive its ORDERING CONTRACT here and pin the source's structure. What
 * executes is the override algebra (pure, copied verbatim from the module —
 * kept honest by check 0, which fails if the source drifts from this copy).
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const WEB = join(here, '..', '..');
const read = (p) => readFileSync(join(WEB, p), 'utf8');

const results = [];
const check = (label, ok, detail = '') => results.push([label, !!ok, detail]);

const handlers = read('lib/file-types/handlers.ts');
const menu = read('components/workspace/FileContextMenu.tsx');
const tree = read('components/workspace/WorkspaceTree.tsx');
const filesPage = read('app/(authenticated)/files/page.tsx');

// ── 0. the executable copy still matches the source ──────────────────────────
// applyDefaultOverride is re-implemented below so it can RUN. If the real one
// changes shape, this gate must be updated with it — otherwise checks 1a-1e
// would be testing a fiction.
const overrideSrc = handlers.slice(
  handlers.indexOf('export function applyDefaultOverride'),
  handlers.indexOf('/** The default handler for a subject'),
);
check(
  '0 the override algorithm still has the shape this gate executes',
  overrideSrc.includes('if (!override || handlers.length < 2) return handlers;') &&
    overrideSrc.includes('const idx = handlers.findIndex((h) => h.id === override);') &&
    overrideSrc.includes('if (idx <= 0) return handlers;'),
);

// verbatim from handlers.ts
function applyDefaultOverride(hs, override) {
  if (!override || hs.length < 2) return hs;
  const idx = hs.findIndex((h) => h.id === override);
  if (idx <= 0) return hs;
  return [hs[idx], ...hs.slice(0, idx), ...hs.slice(idx + 1)];
}

// ── 1. resolution order, EXECUTED (D2.4) ─────────────────────────────────────
const set = [{ id: 'studio.app' }, { id: 'web.viewer' }, { id: 'chat.app' }];
const ids = (hs) => hs.map((h) => h.id);

check('1a no override → registry rank is preserved',
  JSON.stringify(ids(applyDefaultOverride(set, null))) ===
    JSON.stringify(['studio.app', 'web.viewer', 'chat.app']));

check('1b an override promotes its handler to default',
  ids(applyDefaultOverride(set, 'web.viewer'))[0] === 'web.viewer');

check('1c promotion preserves the other handlers (none dropped)',
  applyDefaultOverride(set, 'chat.app').length === 3 &&
    new Set(ids(applyDefaultOverride(set, 'chat.app'))).size === 3);

// The load-bearing one: a stale override must never make a file unopenable.
check('1d a STALE/unknown override falls through — file stays openable',
  JSON.stringify(ids(applyDefaultOverride(set, 'deleted.app'))) ===
    JSON.stringify(['studio.app', 'web.viewer', 'chat.app']));

check('1e overriding to the existing default is a no-op',
  JSON.stringify(ids(applyDefaultOverride(set, 'studio.app'))) ===
    JSON.stringify(['studio.app', 'web.viewer', 'chat.app']));

check('1f a single-handler set is never re-ranked',
  ids(applyDefaultOverride([{ id: 'text.viewer' }], 'chat.app'))[0] === 'text.viewer');

// ── 2. the delivery axis + cardinality (D2.3) ────────────────────────────────
// Closed at two values. Checked against the CODE, not the prose — the header
// names edit/reason/observe precisely to record that they were rejected, so a
// whole-file grep would fail on its own explanation.
const handlerCode = handlers.slice(handlers.indexOf('export type HandlerDelivery'));
check('2a delivery is closed at document|reference (no intent taxonomy in code)',
  /export type HandlerDelivery = 'document' \| 'reference'/.test(handlers) &&
    !/'(edit|reason|observe)'/.test(handlerCode));

check('2b a FOLDER resolves to reference handlers only (no document handler)',
  /if \(isFolder\) return \[CHAT_HANDLER\]/.test(handlers));

check('2c a MULTI-selection admits only handlers that accept it',
  /paths\.length > 1[\s\S]{0,120}filter\(\(h\) => h\.acceptsMultiple\)/.test(handlers));

check('2d Chat is the reference handler and accepts multiple',
  /CHAT_HANDLER[\s\S]{0,400}delivery: 'reference'[\s\S]{0,200}acceptsMultiple: true/.test(handlers));

check('2e Chat rides the existing bind param, not a new receiving contract',
  /surface: 'chat', param: 'cite'/.test(handlers));

// ── 3. the Finder grammar (D2.2) ─────────────────────────────────────────────
check('3a Open With renders ONLY when the set has >1 handler',
  /handlers && handlers\.length > 1/.test(menu));

check('3b exactly one (default) marker, on the first row',
  /i === 0 &&[\s\S]{0,120}\(default\)/.test(menu));

check('3c Open With is a SUBMENU, not flattened rows',
  /OpenWithItem/.test(menu) && /absolute left-full/.test(menu));

check('3d Open still fires the default independently of the submenu',
  /\{onOpen && \(/.test(menu));

// ── 4. PER-MOUNT reachability (the D2.6 lesson) ──────────────────────────────
// A counting gate is exactly what could not see Duplicate missing from the
// tree. Assert the bundle reaches each mount by SOURCE, per mount.
check('4a WorkspaceTree takes the verb bundle WHOLE (no hand-listed props)',
  /verbs\?: FileVerbs/.test(tree) &&
    !/onDuplicate\?: \(node/.test(tree) &&
    !/onRename\?: \(node/.test(tree));

check('4b WorkspaceTree SPREADS the bundle into the menu',
  /\{\.\.\.verbs\}/.test(tree));

check('4c the Files page hands the tree the same bundle the grid gets',
  /verbs=\{fileVerbs\}/.test(filesPage));

check('4d no mount enumerates verbs to decide the menu exists',
  /Object\.values\(verbs\)\.some\(Boolean\)/.test(tree) &&
    /Object\.values\(verbs\)\.some\(Boolean\)/.test(menu));

check('4e the handler set is wired into the shared bundle (reaches every mount)',
  /handlersFor,/.test(filesPage) && /onOpenWith: openWith/.test(filesPage));

// The menu and the open funnel must consult the SAME registry, or they can
// disagree about what opens a file.
check('4f menu + open funnel share one resolver',
  /resolveHandlers/.test(filesPage) &&
    /from '@\/lib\/file-types\/handlers'/.test(filesPage));

// ── report ───────────────────────────────────────────────────────────────────
let failed = 0;
for (const [label, ok, detail] of results) {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}${detail ? '  ' + detail : ''}`);
  if (!ok) failed++;
}
console.log('');
if (failed) {
  console.log(`FAILED — ${results.length - failed}/${results.length}`);
  process.exit(1);
}
console.log(`ALL PASS — ${results.length}/${results.length}`);
