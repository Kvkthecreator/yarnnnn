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

// ── 1bis. the per-file STORE is wired end to end (D2.4) ─────────────────────
// The algebra above is inert unless something persists an override AND the open
// path reads it. A setting that does not change what Open does is decoration —
// assert both halves, not just the affordance.
const details = read('components/workspace/NodeDetailsPanel.tsx');
const client = read('lib/api/client.ts');
const docsRoute = read('../api/routes/documents.py');

check('1g the store is metadata-only — no revision minted for a preference',
  /def set_launch_handler/.test(docsRoute) &&
    !/write_revision\(/.test(
      docsRoute.slice(docsRoute.indexOf('def set_launch_handler'),
                      docsRoute.indexOf('class DuplicateRequest'))));

check('1h the store consults the grant (every door, ADR-501 S1)',
  /_is_path_locked_for_principal/.test(
    docsRoute.slice(docsRoute.indexOf('def set_launch_handler'),
                    docsRoute.indexOf('class DuplicateRequest'))));

check('1i the client exposes the binding',
  /setLaunchHandler: \(path: string, handlerId: string \| null\)/.test(client));

check('1j Get Info renders the row ONLY when the file has a choice',
  /function FileOpensWith/.test(details) &&
    /if \(handlers\.length < 2\) return null;/.test(details));

// The load-bearing half: openPath must APPLY the override, or the setting is
// cosmetic — exactly the "declared but not consumed" shape that shipped in
// cfc8e87 for the cite param.
check('1k the OPEN path applies the override (the setting is not cosmetic)',
  /applyDefaultOverride\(/.test(filesPage) &&
    /launch\s*\n?\s*\?\.handler|launch\?\.handler/.test(filesPage));

check('1l choosing the registry default CLEARS the override (no dead rows)',
  /=== handlers\[0\]\.id \? null : id/.test(details));

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

// ── 2bis. the cite RECEIVER exists (the delivery actually lands) ─────────────
// Declaring a delivery is not delivering it: the first D2 commit shipped the
// registry row while nothing consumed `chat.cite`, so Open-With-Chat navigated
// to a surface that ignored the file. These assert the receiving half.
const lane = read('components/chat-surface/LanePanel.tsx');
const chatSurface = read('components/chat-surface/ChatSurface.tsx');

check('2f ChatSurface READS the cite param',
  /getParam\('cite'\)/.test(chatSurface));

check('2g cited paths are handed to the composer',
  /citePaths=\{citePaths\}/.test(chatSurface));

check('2h the composer BINDS them via the existing attach path (no upload)',
  /citePaths\.forEach\(attachWorkspaceFile\)/.test(lane));

check('2i the bind is consumed ONCE (a re-render cannot re-attach)',
  /citedOnce/.test(lane) && /citedOnce\.current === key/.test(lane));

check('2j the param is CLEARED after consumption (an act, not window state)',
  /onCiteConsumed=\{\(\) => setParam\(\{ cite: null \}\)\}/.test(chatSurface));

// Plural by construction — the whole reason reference delivery answers
// multi-select and folders.
check('2k the receiver is plural (a multi-selection arrives whole)',
  /citePaths\?: string\[\]/.test(lane) && /split\(' '\)/.test(chatSurface));

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

// 2026-08-04: the raw `{...verbs}` spread this check used to REQUIRE was itself
// a defect — FileVerbs carries `handlersFor` (a function) while the menu takes
// `handlers` (the resolved array), and only useFileContextMenu translates. The
// spread skipped the translation, so Open With ▸ never rendered in the tree.
// Every mount must go through the shared hook; nothing but the hook may render
// <FileContextMenu> directly.
check('4b WorkspaceTree renders its menu through the SHARED hook (no local spread)',
  /useFileContextMenu\(/.test(tree) &&
    !/<FileContextMenu/.test(tree) &&
    !/\{\.\.\.verbs\}/.test(tree));

check('4b2 the hook is the ONE translation site (handlersFor → handlers)',
  /handlers=\{verbs\.handlersFor\?\.\(state\.target\)\}/.test(menu));

// Completeness, not a pinned spelling (the counting-gate lesson): enumerate
// every JSX mount of <FileContextMenu> across the FE — the hook's own render
// must be the only one.
import { readdirSync, statSync } from 'node:fs';
const walk = (dir, out = []) => {
  for (const name of readdirSync(join(WEB, dir))) {
    const rel = `${dir}/${name}`;
    if (name === 'node_modules' || name.startsWith('.')) continue;
    if (statSync(join(WEB, rel)).isDirectory()) walk(rel, out);
    else if (/\.(tsx|ts)$/.test(name)) out.push(rel);
  }
  return out;
};
// `<FileContextMenu` followed by whitespace = a JSX mount with props; a prose
// mention in a comment is `<FileContextMenu>` (no whitespace) and is not one.
const jsxMounts = [...walk('components'), ...walk('app')]
  .filter((f) => /<FileContextMenu\s/.test(read(f)));
check('4b3 exactly ONE <FileContextMenu> JSX mount — the hook itself',
  jsxMounts.length === 1 && jsxMounts[0].endsWith('FileContextMenu.tsx'),
  jsxMounts.join(', '));

// The open FILE is a mount too (2026-08-04): right-clicking the file you just
// opened must offer the file's own verbs, not bubble to the canvas menu. The
// bundle reaches FileView through ContentViewer, and FileView mounts the hook.
const contentViewer = read('components/workspace/ContentViewer.tsx');
check('4b4 the open file (FileView) is a verb mount',
  /<FileView[\s\S]{0,200}verbs=\{verbs\}/.test(contentViewer) &&
    /function FileView\([\s\S]{0,800}useFileContextMenu\(verbs\)/.test(contentViewer));

check('4c the Files page hands the tree the same bundle the grid gets',
  /verbs=\{fileVerbs\}/.test(filesPage));

// The any-verb-earns-the-menu decision lives in the HOOK alone; a mount that
// re-derives it (as the tree once did) is a second state machine waiting to
// drift.
check('4d only the hook decides whether the menu exists',
  /Object\.values\(verbs\)\.some\(Boolean\)/.test(menu) &&
    !/Object\.values\(verbs\)/.test(tree));

check('4e the handler set is wired into the shared bundle (reaches every mount)',
  /handlersFor,/.test(filesPage) && /onOpenWith: openWith/.test(filesPage));

// The menu and the open funnel must consult the SAME registry, or they can
// disagree about what opens a file.
check('4f menu + open funnel share one resolver',
  /resolveHandlers/.test(filesPage) &&
    /from '@\/lib\/file-types\/handlers'/.test(filesPage));

// ── 5. folder-scoped create (2026-08-04) ─────────────────────────────────────
// A folder target offers "New Folder" (create INSIDE it — the Explorer grammar);
// files never do. The destination folder travels in its own VERBATIM field so
// the backend never re-sanitizes an existing segment into a different path.
check('5a New Folder renders for FOLDER targets only',
  /\{!isFile && onNewFolder &&/.test(menu));

check('5b the hook threads onNewFolder like every other verb',
  /onNewFolder=\{verbs\.onNewFolder/.test(menu));

check('5c the page wires it into the ONE bundle (reaches every mount)',
  /onNewFolder: \(t/.test(filesPage));

check('5d the parent is its own field, not a concatenated re-sanitized path',
  /createFolder\(name, parentRel\)/.test(filesPage));

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
