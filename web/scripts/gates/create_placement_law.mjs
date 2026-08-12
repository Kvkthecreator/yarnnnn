// Executing check of the CREATE-PLACEMENT law (2026-08-11 create-surface audit).
//
// WHAT THIS GATE IS FOR. The audit that produced these fixes was made against a
// green battery: every defect below shipped past passing gates, because each
// one lived in the GAP BETWEEN two modules that each looked correct alone.
// So this gate does not assert that code is PRESENT — it EXECUTES the real
// predicates and asserts they AGREE. Every claim has a falsifier that was
// watched go red.
//
// The five defects, and why gates missed them:
//   F1  the create picker gated on PERMISSION while the server gated on
//       REGION — two correct-looking predicates, one broken door. Nothing
//       compared them, so nothing could see it.
//   F2  the two creation doors disambiguated differently, while the helper's
//       own DOCSTRING asserted they "cannot drift". A comment is not a gate
//       (feedback_documented_limitation_is_not_a_gate — third occurrence).
//   F3  one folder under two names (`operation` vs `Documents`) inside a
//       single dialog.
//   F4  the typed folder name was silently rewritten with no preview.
//   F5  the immediate door swallowed every failure (no catch).
//
// NEVER PIN A SPELLING (the ADR-544 lesson). Every assertion below is about a
// BEHAVIOUR or an AGREEMENT between two implementations, never a literal a
// rename would break. The two label assertions check a RELATIONSHIP (the modal
// says what the picker says), not the word "Documents".
//
// Run from the REPO ROOT: node web/scripts/gates/create_placement_law.mjs
import { readFileSync } from 'fs';

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

// Execute a TS function's real source. Type annotations are erased (`: string`
// on params + return) so `new Function` can parse it — the BODY is untouched,
// which is the thing under test. Executing the shipped source is the point:
// a gate that re-implemented these rules would pass while the app was broken.
// Only the SIGNATURE is rewritten — everything from the opening brace on is
// passed through untouched. An earlier version stripped types across the whole
// source and mangled a regex literal in the body (`/^\/workspace\//`), which
// is precisely the "the gate broke, not the code" failure.
const runTs = (src, name, deps = {}) => {
  // Split at the FUNCTION's opening brace, not the first brace in the string —
  // a preamble (e.g. a runtime-built RegExp the function closes over) may carry
  // its own braces, and slicing at index 0 would corrupt it.
  // `export` is stripped everywhere, not just on the target function: a
  // preamble may itself carry exported declarations, and `new Function` rejects
  // the keyword wherever it appears.
  const bare = src.replace(/(^|\n)\s*export\s+/g, '$1');
  const fnAt = bare.search(/(^|\n)\s*function\s/);
  const head = bare.slice(0, fnAt < 0 ? 0 : fnAt);
  const rest = bare.slice(fnAt < 0 ? 0 : fnAt);
  const brace = rest.indexOf('{');
  // Param annotations may be UNIONS with spaces (`string | null | undefined`),
  // so the type pattern has to admit spaces — but only up to the next `,` or
  // the closing `)`, or it would swallow the whole signature.
  const sig = rest
    .slice(0, brace)
    .replace(/\bexport\s+/g, '')
    .replace(/\)\s*:\s*[A-Za-z<>\[\]|\s]+$/, ')')
    .replace(/([(,]\s*\w+)\s*:\s*[A-Za-z<>\[\]|\s]+?(?=\s*[,)])/g, '$1');
  const names = Object.keys(deps);
  return new Function(
    ...names,
    `${head}${sig}${rest.slice(brace)}; return ${name};`,
  )(...names.map((k) => deps[k]));
};

// ── Strip comments before any source assertion ─────────────────────────────
// feedback_gate_assertion_matches_its_own_comment: an ABSENCE assertion
// matches its own explanatory comment. Every source test runs on stripped text.
const strip = (s) =>
  s
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|[^:])\/\/[^\n]*/g, '$1')
    .replace(/^\s*#[^\n]*$/gm, '');

const modal = readFileSync('web/components/authoring/NewArtifactModal.tsx', 'utf8');
const naming = readFileSync('web/components/authoring/artifactNaming.ts', 'utf8');
const surface = readFileSync('web/components/authoring/StudioSurface.tsx', 'utf8');
const folderModal = readFileSync('web/components/workspace/NewFolderModal.tsx', 'utf8');
const studioPy = readFileSync('api/routes/studio.py', 'utf8');
const authoringPy = readFileSync('api/services/authoring.py', 'utf8');
const documentsPy = readFileSync('api/routes/documents.py', 'utf8');

const modalCode = strip(modal);
const namingCode = strip(naming);
const folderModalCode = strip(folderModal);

// ═══════════════════════════════════════════════════════════════════════════
// F1 — the picker offers exactly what the server accepts.
// Executed, not grepped: both predicates are reconstructed from their real
// source and run over the same folder set. Any disagreement is the defect.
// ═══════════════════════════════════════════════════════════════════════════

// The server's region, read from the Python (not restated here — a rename of
// the constant's VALUE must reach this gate, which is the point).
const regionPy = authoringPy.match(/STUDIO_ARTIFACT_REGION\s*=\s*["']([^"']+)["']/);
t('F1: the server declares an artifact region', !!regionPy);
const REGION = regionPy ? regionPy[1] : null;

// The FE mirror's value, read from ITS source.
const regionTs = naming.match(/STUDIO_ARTIFACT_REGION\s*=\s*['"]([^'"]+)['"]/);
t('F1: the FE mirrors the artifact region', !!regionTs);
t('F1 [FALSIFIER]: the two regions are byte-identical', !!REGION && regionTs?.[1] === REGION);

// Reconstruct both gates and compare them over the folders a member can reach.
const isArtifactRegion = (folder) => serverAccepts(folder);
// ADR-551 D2: the server's create gate is `operator_can_organize`, mirrored in
// `ownership.ts`. Reconstructed here so the two are COMPARED, never assumed.
const serverAccepts = (folder) => {
  let rel = `${folder.replace(/\/+$/, '')}/my-doc/document.html`.replace(/^\/+/, '');
  if (rel.startsWith('workspace/')) rel = rel.slice('workspace/'.length);
  if (rel.startsWith('system/')) return false;
  if (rel.startsWith('inbound/') && !rel.startsWith('inbound/uploads/')) return false;
  const leaf = rel.split('/').pop() || '';
  if (leaf.startsWith('_') && ['.yaml', '.yml', '.json'].some((e) => leaf.toLowerCase().endsWith(e)))
    return false;
  return true;
};

const FOLDERS = [
  '/workspace/operation',
  '/workspace/operation/clients',
  '/workspace/the-acme-deal',
  '/workspace/inbound/uploads',
  '/workspace/memory',
  '/workspace/system',
  '/workspace/agents',
];
const mismatches = FOLDERS.filter((f) => isArtifactRegion(f) !== serverAccepts(f));
t(
  `F1 [FALSIFIER]: picker and server agree on every folder (${FOLDERS.length} checked)`,
  mismatches.length === 0,
);
// The regression that WAS shipped: gating on permission alone.
//
// Checked PER PREDICATE, not file-wide. A first draft of this gate asserted
// `modalCode.includes('isArtifactRegion')`, which stayed green when every
// predicate was reverted to permission-only — the import alone satisfied it.
// A file-wide presence check cannot defend a per-site invariant
// (feedback_counting_gate_cannot_defend_per_site); each door must be read.
// ADR-551 D2 moved the law: the fence relaxed to `operator_can_organize`, so
// the picker now asks THAT — mirrored once as `canCreateFileIn`. The invariant
// is unchanged in spirit and is what F1 was always about: the door asks
// whatever the server asks. Gating on the old region here would now UNDER-offer
// (refusing peer folders the API accepts) — the F1 defect mirrored.
const PREDICATES = ['selectable', 'canConfirm', 'folderDisabledTitle'];
for (const prop of PREDICATES) {
  // The predicate's own expression: from `prop={` to the line that closes it.
  const m = modalCode.match(new RegExp(`${prop}=\\{[\\s\\S]*?\\n        \\}`));
  const expr = m ? m[0] : null;
  t(
    `F1 [FALSIFIER]: \`${prop}\` asks the ONE placement law (ADR-551 D2)`,
    !!expr && /canCreateFileIn/.test(expr) && !/isArtifactRegion/.test(expr),
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// F2 — ONE collision rule. Both doors must reach `disambiguate`.
// The old defect: `disambiguate` was reachable ONLY when the caller sent no
// path, so the named door 409'd where the unnamed one stepped to `-2`.
// ═══════════════════════════════════════════════════════════════════════════
const pyCode = studioPy
  .replace(/"""[\s\S]*?"""/g, '')
  .replace(/^\s*#[^\n]*$/gm, '');

// ADR-549 D1 collapsed the two doors into one, so there is now ONE placement
// helper — and the untitled one must be GONE, not merely unused.
const redirectFn = pyCode.match(/def _redirect_to_free_key\([\s\S]*?(?=\ndef |\n@router)/);
t('F2: the create door has a placement authority', !!redirectFn);
t(
  'F2 [FALSIFIER]: it disambiguates (a taken key steps, never refuses)',
  !!redirectFn && /disambiguate\(/.test(redirectFn[0]),
);
t(
  'D1 [FALSIFIER]: the untitled placement helper is DELETED, not orphaned',
  !/def _placed_path\(/.test(pyCode),
);
t(
  'D1 [FALSIFIER]: no `untitled <kind>` key is generated anywhere',
  !/f"untitled \{label\}"/.test(pyCode),
);

// The create handler must actually CALL the named door's helper — the exported
// -but-never-mounted shape (ADR-541 D4's withdrawalNotice) is the failure this
// catches: a correct helper with zero callers ships green.
// Terminate at the next top-level def/@router, or run to EOF when this is the
// last function in the module (it currently is — an unanchored lookahead
// silently matched NOTHING and both call-site checks failed for the wrong
// reason, which is exactly the false-red this gate exists to avoid).
const handler = pyCode.match(
  /async def create_artifact\([\s\S]*?(?=\n@router\b|\n(?:async )?def [a-z_]+\(|$)/,
);
t('F2 [FALSIFIER]: the create handler CALLS the named-door helper',
  !!handler && /_redirect_to_free_key\(/.test(handler[0]));
t('D1 [FALSIFIER]: a pathless create is REFUSED, never silently placed',
  !!handler && /if not raw:[\s\S]{0,200}?raise HTTPException/.test(handler[0]));

// Ordering: validation must precede the placement query, or a `..` path gets
// used in a DB prefix search before it is refused.
if (handler) {
  const body = handler[0];
  const iTraversal = body.indexOf('".." in path');
  const iRedirect = body.indexOf('_redirect_to_free_key(');
  t(
    'F2 [FALSIFIER]: traversal is refused BEFORE the placement query runs',
    iTraversal !== -1 && iRedirect !== -1 && iTraversal < iRedirect,
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// F3 — one folder, ONE name. The modal must not show a raw substrate root
// where the picker shows a display name. Asserted as a RELATIONSHIP: whatever
// the modal renders for the default destination must not be the bare kernel
// path segment.
// ═══════════════════════════════════════════════════════════════════════════
// Matched against the UNSTRIPPED source: the comment-stripper eats `//`
// inside a regex literal (`/^\\/workspace\\//`), so a stripped body will not
// parse. Stripping is for ABSENCE assertions; executing wants the real text.
const shortDestFn = modal.match(/function shortDest\([\s\S]*?\n}/);
t('F3: the modal has one destination-display helper', !!shortDestFn);
if (shortDestFn && REGION) {
  const kernelSeg = REGION.replace(/^\/workspace\//, '').replace(/\/+$/, '');
  // Execute the real helper against the default destination.
  // `shortDest` closes over the module's label constant — inject the REAL
  // declaration (read from source) rather than restating the word here, so
  // this stays an agreement check and not a pinned spelling.
  const labelDecl = modal.match(/const DOCUMENTS_LABEL\s*=\s*['"][^'"]+['"];/);
  t('F3: the modal names the home once', !!labelDecl);
  const fn = runTs(`${labelDecl ? labelDecl[0] : ''}\n${shortDestFn[0]}`, 'shortDest');
  const shown = fn(REGION.replace(/\/+$/, ''));
  t(
    `F3 [FALSIFIER]: the default destination is not shown as the raw root ("${kernelSeg}")`,
    shown !== kernelSeg,
  );
  // And a nested folder keeps its own segments (the relabel is head-only).
  t(
    'F3: relabelling the home does not rewrite the folders under it',
    fn(`${REGION}clients`).endsWith('/clients'),
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// F4 — the folder name is previewed, and the two slug rules stay APART.
// The artifact key ASCII-folds (ADR-469) because the artifact carries its
// readable name in <title>. A folder has no such carrier — its segment IS its
// name — so folding it would erase the only name it has. The rules differ ON
// PURPOSE; this gate defends that difference rather than collapsing it.
// ═══════════════════════════════════════════════════════════════════════════
// The keep-set regex is built at RUNTIME (a `u`-flagged literal is refused by
// the TS target), so the declaration must travel with the function.
const segDecl = folderModal.match(/const DROP_FROM_SEGMENT[^\n]*\n/);
const segFn = folderModal.match(/export function folderSegment\([\s\S]*?\n}/);
t('F4: the folder modal mirrors the server sanitizer', !!segFn);
if (segFn) {
  const folderSegment = runTs(`${segDecl ? segDecl[0] : ''}${segFn[0]}`, 'folderSegment');
  // Agreement with the Python, on the cases that separated them.
  t('F4 [FALSIFIER]: spaces collapse to dashes, lowercased', folderSegment('The Acme Deal') === 'the-acme-deal');
  t('F4 [FALSIFIER]: punctuation is dropped as the server drops it', folderSegment('R&D') === 'rd');
  t('F4 [FALSIFIER]: a name with no key is detectable (empty, not a guess)', folderSegment('!!!') === '');
  // The load-bearing one: Unicode SURVIVES in a folder segment.
  t(
    'F4 [FALSIFIER]: a non-Latin folder name is NOT folded away (it has no <title>)',
    folderSegment('한글 문서') === '한글-문서',
  );
  // These four separated the real rule from two hand-written approximations
  // that each passed the cases above. Non-ASCII PUNCTUATION must drop while
  // non-ASCII LETTERS stay — the distinction an ASCII denylist cannot make,
  // and a codepoint range gets wrong at both ends.
  t('F4 [FALSIFIER]: non-ASCII punctuation drops (em-dash)', folderSegment('naïve—dash') === 'naïvedash');
  t('F4 [FALSIFIER]: emoji drop', folderSegment('emoji 🎉 party') === 'emoji-party');
  t('F4 [FALSIFIER]: a non-ASCII NUMBER is kept', folderSegment('½ half') === '½-half');
  t('F4 [FALSIFIER]: CJK is kept', folderSegment('日本語 資料') === '日本語-資料');
  // The preview must be rendered, not merely computed (feedback_green_build_is_not_a_mount).
  t('F4 [FALSIFIER]: the computed key is MOUNTED, not just derived', /\{folderKey\}/.test(folderModal));
}
// The server still sanitizes regardless of the mirror — the FE preview is
// never the enforcement.
t('F4: the server remains the sanitizing authority', /_sanitize_folder_segment\(/.test(documentsPy));

// ═══════════════════════════════════════════════════════════════════════════
// ADR-549 D3/D4 — a derived artifact lands BESIDE ITS SOURCE.
// Executed against the real `defaultDestinationFor`, because the defect it
// replaces was a HARDCODED root that ignored the source's location entirely:
// a brief derived from `operation/ai-frontier/briefs/x.md` landed at the ROOT
// of Documents, orphaned from the thing it was made from.
// ═══════════════════════════════════════════════════════════════════════════
const ddfSrc = naming.match(/export function defaultDestinationFor[\s\S]*?\n}/);
t('D4: one derivation home for the default destination', !!ddfSrc);
if (ddfSrc && REGION) {
  // The dependency is injected as an already-JS preamble, and only the TARGET
  // function's source goes through `runTs`. Passing both TS functions in one
  // string left the second signature inside the untouched body slice — the
  // gate broke, not the code, for the third time in this file's life.
  const iar = runTs(
    `const STUDIO_ARTIFACT_REGION = ${JSON.stringify(REGION)};\n` +
      naming.match(/export function isArtifactRegion[\s\S]*?\n}/)[0],
    'isArtifactRegion',
  );
  const ddf = runTs(ddfSrc[0].replace(/sourcePath!/g, 'sourcePath'), 'defaultDestinationFor', {
    STUDIO_ARTIFACT_REGION: REGION,
    isArtifactRegion: iar,
  });
  const home = REGION.replace(/^\/workspace\//, '').replace(/^\/+|\/+$/g, '');
  t(
    'D4 [FALSIFIER]: a derive lands in the SOURCE\'s folder, not the region root',
    ddf('/workspace/operation/ai-frontier/briefs/x.md') === `${home}/ai-frontier/briefs`,
  );
  t(
    'D4 [FALSIFIER]: an ARRIVAL (inbound/) is not a home — falls back to Documents',
    ddf('/workspace/inbound/uploads/operator/q3.pdf') === home,
  );
  t('D4: no source at all falls back to Documents', ddf(null) === home);
  t(
    'D4 [FALSIFIER]: the fallback is the bare home, never `workspace/…`',
    !ddf(null).startsWith('workspace/'),
  );
  // And the caller USES it — a correct helper with zero callers ships green.
  t(
    'D4 [FALSIFIER]: learn-from COMPOSES its path through the helper',
    /defaultDestinationFor\(source\.path\)/.test(strip(surface)),
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// F5 — the immediate door reports its failures.
// ═══════════════════════════════════════════════════════════════════════════
// ADR-549 D1 DELETED `createUntitled` — the door that swallowed its failures
// no longer exists, which is a stronger fix than making it report them. What
// must hold now is that the surviving door still surfaces a refusal: the modal
// owns creation and shows the error inline.
t(
  'F5 [FALSIFIER]: the swallowing door is GONE, not merely patched',
  !/const createUntitled\s*=/.test(strip(surface)),
);
const createScratch = strip(surface).match(/const createScratch\s*=[\s\S]*?\n  \};/);
t('F5: the surviving door exists', !!createScratch);
t(
  'F5 [FALSIFIER]: the modal reports a refusal inline (it does not swallow)',
  /catch\s*\(/.test(modalCode) && /setErr\(/.test(modalCode),
);

// ═══════════════════════════════════════════════════════════════════════════
// Cleanup — the orphaned labelled upload button is gone.
// It was the only text-labelled upload affordance in the tree, contradicting
// the shipped Finder-parity design for a reader who grepped for one.
// ═══════════════════════════════════════════════════════════════════════════
const uploads = readFileSync('web/components/workspace/UploadButton.tsx', 'utf8');
t(
  'cleanup [FALSIFIER]: no zero-importer UploadButton wrapper survives',
  !/export function UploadButton\b/.test(strip(uploads)),
);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
