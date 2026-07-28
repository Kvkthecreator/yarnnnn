// Executing check of the ADR-482 D11 slash-OPEN path on flow.
// Extracts the REAL post-input body from projection.ts and runs it against the
// four caret states a flow root produces. The regression it guards: pressing
// '/' on a native <div> line (the block-level element Enter creates on a flow
// root) left the caret in an ELEMENT node, and the pre-D11 `nodeType !== 3`
// bail dropped the gesture — the '/' landed as literal text, no palette.
import { readFileSync } from 'fs';

const src = readFileSync('web/components/workspace/viewers/projection.ts', 'utf8');
// The body inside the post-input setTimeout: from `var c2 = slashCaret();`
// up to (not including) the closing `}, 0);`.
const from = src.indexOf('var c2 = slashCaret();');
const to = src.indexOf('}, 0);', from);
const body = src.slice(from, to);

// A tiny DOM: <main> holding one line node whose caret state we vary.
function TextNode(text, parent) {
  return { nodeType: 3, textContent: text, parentElement: parent, parentNode: parent };
}
function El(tag, parent) {
  const el = {
    nodeType: 1, tagName: tag.toUpperCase(), parentElement: parent || null,
    parentNode: parent || null, childNodes: [], lastChild: null,
    appendChild(n) { this.childNodes.push(n); this.lastChild = n; n.parentElement = this; return n; },
  };
  return el;
}

// Run the real body with locals for slashNode/slashStart + a captured post sink.
function run(stageCaret) {
  const posted = [];
  const sink = {};
  const g = new Function(
    'slashCaret', 'id', 'empty', 'rect', 'parent', 'sink',
    'var slashNode=null, slashStart=-1;\n' + body +
    '\nsink.slashNode=slashNode; sink.slashStart=slashStart;',
  );
  g(stageCaret, 'blk-x', true, { left: 1, top: 2, bottom: 3, width: 4 },
    { postMessage: (m) => posted.push(m) }, sink);
  return { posted, slashStart: sink.slashStart };
}

let pass = 0, fail = 0;
const t = (label, cond) => { console.log((cond ? '[PASS] ' : '[FAIL] ') + label); cond ? pass++ : fail++; };

// A: caret inside a text node "/" — the always-worked case.
{
  const main = El('main');
  const tn = TextNode('/', main); main.appendChild(tn);
  const r = run(() => ({ startContainer: tn, startOffset: 1 }));
  t('A text-node caret: slash-open posted', r.posted.length === 1);
}
// B: THE REGRESSION — caret in the ELEMENT node after '/' lands, text node is
//    the child just before the offset.
{
  const div = El('div');
  const tn = TextNode('/', div); div.appendChild(tn);
  // caret in the element at offset 1 (after the text node).
  const r = run(() => ({ startContainer: div, startOffset: 1 }));
  t('B element-node caret: slash-open IS posted (D11)', r.posted.length === 1);
  t('B element-node caret: slashStart anchors the last char', r.slashStart === 0);
}
// C: element caret whose child-before is an inline <span> ending in the text node.
{
  const div = El('div');
  const span = El('span', div); div.appendChild(span);
  const tn = TextNode('a/', span); span.appendChild(tn);
  const r = run(() => ({ startContainer: div, startOffset: 1 }));
  t('C element caret, nested inline: descends to the text node', r.posted.length === 1);
  t('C nested: slashStart at the trailing slash', r.slashStart === 1);
}
// D: a genuine non-slash element caret must still NOT open (offset 0, no child).
{
  const div = El('div');
  const r = run(() => ({ startContainer: div, startOffset: 0 }));
  t('D empty element caret, no slash: NOTHING posted', r.posted.length === 0);
}

// FALSIFIER: the pre-D11 body bailed on nodeType !== 3 — restore it, B must break.
{
  const old = 'var c2 = slashCaret();\n      if (!c2 || c2.startContainer.nodeType !== 3) return;\n' +
    '      var node = c2.startContainer;\n      var at = c2.startOffset - 1;\n' +
    "      if (at < 0 || (node.textContent || '').charAt(at) !== '/') return;\n" +
    '      slashNode = node; slashStart = at;\n' +
    "      parent.postMessage({ type: 'yarnnn-slash-open', blockId: id, empty: empty, rect: rect }, '*');";
  const div = El('div');
  const tn = TextNode('/', div); div.appendChild(tn);
  const posted = [];
  const g = new Function('slashCaret', 'id', 'empty', 'rect', 'parent',
    'var slashNode=null, slashStart=-1;\n' + old);
  g(() => ({ startContainer: div, startOffset: 1 }), 'blk-x', true, {}, { postMessage: (m) => posted.push(m) });
  t('FALSIFIER: the pre-D11 nodeType-3 bail posts nothing on an element caret', posted.length === 0);
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
