/** Typing a list CONTINUES it — the keyboard path, not the toolbar path.
 *
 * ## The defect
 *
 * `ProseCanvas` built its keymap as `defaultKeymap + historyKeymap +
 * searchKeymap` and never wired `@codemirror/lang-markdown`'s own bindings —
 * present in `node_modules` for the language, referenced nowhere in the tree.
 * So Enter after `- first` produced a bare line and the member typed `- `
 * again for every item.
 *
 * On a desktop keyboard that is a shrug. On a phone `-` and the space sit on a
 * symbol layer, so a list was the one thing a thumb could not write — which is
 * how this was reported. Meanwhile `markdownEdits.ts` carries ~600 lines of
 * careful list-toggle logic for the TOOLBAR, polished across three ADR-cited
 * caret fixes. The polished path was the one nobody's thumb uses.
 *
 * ## What this gate holds
 *
 * It EXECUTES the real commands against the real markdown language rather than
 * grepping for the import — the house rule (ADR-544/546): a gate that pins a
 * spelling goes red on a rename and green on a real regression. A `keymap.of`
 * that is present but out-ranked by `defaultKeymap` greps identically to one
 * that works, and that is exactly the bug this defends.
 *
 *   1. the continuation gesture, per list shape (bullet, ordered, task, quote,
 *      nested) — the ordered case must RENUMBER, not repeat `1.`;
 *   2. the EXIT gesture: Enter on an empty marker ends the list cleanly. Stock
 *      `markdownKeymap` fails this — it starts a non-tight list, leaving a
 *      stray bullet under a blank line — so the canvas configures
 *      `nonTightLists: false`, and this asserts that choice by behaviour;
 *   3. prose is UNTOUCHED: off block markup the command declines, so Enter
 *      falls through to the generic newline;
 *   4. Backspace at the head of a marker strips the MARKER, not the line;
 *   5. the wiring: the canvas binds these commands ABOVE `defaultKeymap`. A
 *      binding listed after it never sees Enter, which is invisible to every
 *      other check here — all four behavioural claims above pass against the
 *      library whether or not the app wires it.
 *
 * Run from the REPO ROOT (resolution needs the web package):
 *   node --experimental-strip-types web/scripts/gates/prose_typing_continues_a_list.mjs
 */
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';

const ROOT = process.cwd();
const require$ = createRequire(`${ROOT}/web/package.json`);

let pass = 0;
let fail = 0;
const t = (label, cond, detail = '') => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label + (cond || !detail ? '' : ` — ${detail}`));
  cond ? pass++ : fail++;
};

const read = (p) => {
  try {
    return readFileSync(`${ROOT}/${p}`, 'utf8');
  } catch {
    t(`the gate reads a path that still exists — ${p}`, false, 'renamed or deleted; re-anchor');
    return '';
  }
};

// ── The commands, from the installed library ──────────────────────────────
const { EditorState } = require$('@codemirror/state');
const {
  markdown,
  markdownLanguage,
  insertNewlineContinueMarkupCommand,
  deleteMarkupBackward,
} = require$('@codemirror/lang-markdown');

// The canvas's own configuration, restated so the gate drives what ships.
// Asserted against the source in §5 so this cannot silently diverge.
const enterCmd = insertNewlineContinueMarkupCommand({ nonTightLists: false });

/** Run a command at `pos` and report the resulting doc + caret. */
function run(cmd, doc, pos) {
  const state = EditorState.create({
    doc,
    selection: { anchor: pos },
    extensions: [markdown({ base: markdownLanguage })],
  });
  let next = null;
  const handled = cmd({ state, dispatch: (tr) => { next = tr.state ?? state.update(tr).state; } });
  const s = next ?? state;
  return { handled, doc: s.doc.toString(), caret: s.selection.main.head };
}

const enter = (doc, pos) => run(enterCmd, doc, pos ?? doc.length);

// ── 1. The continuation, per list shape ───────────────────────────────────
t('a bullet continues', enter('- first').doc === '- first\n- ');
t('an ordered item RENUMBERS', enter('1. first').doc === '1. first\n2. ');
t('a task carries its box', enter('- [ ] a').doc === '- [ ] a\n- [ ] ');
t('a quote continues', enter('> a').doc === '> a\n> ');
t('a nested item keeps its indent', enter('- a\n  - b').doc === '- a\n  - b\n  - ');

// ── 2. The EXIT gesture ───────────────────────────────────────────────────
// The whole reason the canvas configures the command instead of taking
// `markdownKeymap` as-is. Driven as the member drives it: two Enters.
const first = enter('- a');
const second = enter(first.doc, first.caret);
t(
  'Enter on an empty marker ENDS the list, leaving no stray bullet',
  second.doc === '- a\n',
  `got ${JSON.stringify(second.doc)}`,
);
// Falsifier's twin: the stock default is the shape we are rejecting. If this
// ever stops being true the library changed and the config above is moot.
const stock = insertNewlineContinueMarkupCommand();
const stockSecond = run(stock, first.doc, first.caret);
t(
  'the stock default would leave the stray bullet (so the config is load-bearing)',
  stockSecond.doc !== '- a\n',
  `stock gave ${JSON.stringify(stockSecond.doc)} — if this now matches, drop the config`,
);

// ── 3. Prose is untouched ─────────────────────────────────────────────────
const prose = enter('just a sentence');
t('off block markup the command DECLINES, so prose falls through', prose.handled === false);

// ── 4. Backspace strips the marker, not the line ──────────────────────────
t('Backspace at the marker head strips the MARKER', run(deleteMarkupBackward, '- item', 2).doc === 'item');

// ── 5. The wiring — the half no behavioural check can see ─────────────────
// Comments are stripped first: an absence assertion must not match its own
// explanatory prose (the recorded `feedback_gate_assertion_matches_its_own_comment`).
const canvas = read('web/components/text/ProseCanvas.tsx')
  .replace(/\/\*[\s\S]*?\*\//g, '')
  .replace(/^\s*\/\/.*$/gm, '');

t(
  'the canvas binds the markdown continuation command',
  /insertNewlineContinueMarkupCommand\(\s*\{[^}]*nonTightLists:\s*false/.test(canvas),
  'the exit gesture depends on nonTightLists:false',
);
t('the canvas binds deleteMarkupBackward to Backspace', /deleteMarkupBackward/.test(canvas));

// The precedence claim, asserted by ORDER in the extension list. `Prec.high`
// is what lets a later-listed keymap win; without it `defaultKeymap`'s Enter
// takes the key and every behavioural assertion above still passes.
const precAt = canvas.search(/Prec\.high\(\s*keymap\.of\(/);
const defaultAt = canvas.search(/keymap\.of\(\s*\[\s*\.\.\.defaultKeymap/);
t('the markdown bindings are raised with Prec.high', precAt !== -1);
t(
  'they out-rank defaultKeymap (which binds Enter to a plain newline)',
  precAt !== -1 && defaultAt !== -1 && precAt < defaultAt,
);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
