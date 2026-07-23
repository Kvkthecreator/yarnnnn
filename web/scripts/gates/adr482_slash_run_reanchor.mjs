// EXECUTING gate: slashRun() must survive the text node being replaced under it
// (native contenteditable on the flow root splits/re-creates nodes as you type).
import { readFileSync } from 'fs';
const src = readFileSync('web/components/workspace/viewers/projection.ts','utf8');
const i = src.indexOf('function slashRun()');
const body = src.slice(src.indexOf('{', i)+1, src.indexOf('\n  }', i));

function mkText(t){ return { nodeType:3, textContent:t }; }
function run({captured, caretNode, offset}){
  const ctx = {
    slashStart: 4, slashNode: captured,
    slashCaret: () => ({ startContainer: caretNode, startOffset: offset }),
  };
  const fn = new Function('slashStart','slashNode','slashCaret',
    'var __r=(function(){'+body+'})(); return {r:__r, node:slashNode};');
  return fn(ctx.slashStart, ctx.slashNode, ctx.slashCaret);
}
let pass=0,fail=0;
const t=(l,c)=>{console.log((c?'[PASS] ':'[FAIL] ')+l);c?pass++:fail++;};

// Same node — the paged case, and flow when no split happened.
const A = mkText('Star/cal');
t('same node -> the run reads back', run({captured:A,caretNode:A,offset:8}).r === 'cal');

// The regression: native editing replaced the node, same text + same '/' offset.
const B0 = mkText('Star/cal');
const B1 = mkText('Star/cal');
const rB = run({captured:B0,caretNode:B1,offset:8});
t('node REPLACED under the caret -> run still reads (the D10 fix)', rB.r === 'cal');
t('  and slashNode is re-anchored to the live node', rB.node === B1);

// Genuine dismissals must still return null.
const C = mkText('Starcal');           // the '/' was deleted
t("'/' deleted -> null", run({captured:C,caretNode:C,offset:7}).r === null);
const D0 = mkText('Star/cal'), D1 = mkText('no slash here');
t('caret in an unrelated node -> null', run({captured:D0,caretNode:D1,offset:5}).r === null);
const E = mkText('Star/cal');
t('caret before the / -> null', run({captured:E,caretNode:E,offset:2}).r === null);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
