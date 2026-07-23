// Executing check of the ADR-482 D1 slash-take path.
// Extracts the REAL handler body from projection.ts and runs it in both grains.
import { readFileSync } from 'fs';
const src = readFileSync('web/components/workspace/viewers/projection.ts','utf8');
const i = src.indexOf("else if (d.type === 'yarnnn-slash-take')");
const body = src.slice(src.indexOf('{', i)+1, src.indexOf("\n    }", i));

function mkBlock(id, text){
  const el = { _id:id, nodeType:1, getAttribute:(k)=>k==='data-block-id'?id:null,
               closest:(sel)=> sel==='[data-block]'? el : null, textContent:text };
  return el;
}
function run({FLOW_MODE, editingEl, editingId}){
  const blk = mkBlock('blk-42','hello /');
  const slashNode = { nodeType:3, textContent:'hello /', parentElement: blk };
  const posted = [];
  const ctx = {
    FLOW_MODE, editingEl, editingId,
    slashStart: 6, slashNode,
    d: { filterLen: 0 },
    flowRoot: ()=> FLOW_MODE ? {nodeType:1} : null,
    editHost: ()=> FLOW_MODE ? {nodeType:1} : editingEl,
    splitHalves: ()=> ({before:'hello ', after:''}),
    exit: ()=>{ ctx._exited = true; },
    document: { createRange: ()=>({setStart(){},collapse(){}}) },
    window: { getSelection: ()=>({removeAllRanges(){},addRange(){}}) },
    parent: { postMessage:(m)=>posted.push(m) },
  };
  const fn = new Function(...Object.keys(ctx), body);
  fn(...Object.values(ctx));
  return { posted, exited: !!ctx._exited };
}

let pass=0, fail=0;
const t=(label,cond)=>{ console.log((cond?'[PASS] ':'[FAIL] ')+label); cond?pass++:fail++; };

// FLOW: the regression. Pre-fix this posted NOTHING.
const flow = run({FLOW_MODE:true, editingEl:null, editingId:null});
t('flow: slash-taken IS posted (the ADR-482 D1 regression)', flow.posted.length===1);
t('flow: blockId resolved from the caret, not null editingId',
  flow.posted[0]?.blockId==='blk-42');
t('flow: no per-block exit() is called (no session to leave)', flow.exited===false);

// PAGED: unchanged.
const pagedEl = mkBlock('blk-7','hello /');
const paged = run({FLOW_MODE:false, editingEl:pagedEl, editingId:'blk-7'});
t('paged: still posts slash-taken', paged.posted.length===1);
t('paged: blockId still comes from the edit session', paged.posted[0]?.blockId==='blk-7');
t('paged: exit() still called (silent commit discipline)', paged.exited===true);

// FALSIFIER: restore the old guard -> flow must break again.
const old = body.replace('!editHost()','!editingEl').replace(/if \(FLOW_MODE\) \{[\s\S]*?\n      \}/, '');
const posted=[];
new Function('FLOW_MODE','editingEl','editingId','slashStart','slashNode','d','flowRoot','editHost','splitHalves','exit','document','window','parent', old)(
  true,null,null,6,{nodeType:3,textContent:'hello /',parentElement:mkBlock('b','x')},{filterLen:0},
  ()=>({}),()=>({}),()=>({before:'',after:''}),()=>{},{createRange:()=>({setStart(){},collapse(){}})},
  {getSelection:()=>({removeAllRanges(){},addRange(){}})},{postMessage:m=>posted.push(m)});
t('FALSIFIER: the pre-fix guard posts nothing on flow', posted.length===0);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail?1:0);
