/**
 * Gate — `MouseEvent.detail` counts the GESTURE, not the element.
 *
 * Operator-observed KVK 2026-09-13: "on files surface, delete item auto opens
 * the file, redirecting to text app." The trash always succeeded; the
 * navigation after it was spurious.
 *
 * THE MECHANISM, established by CDP and reproduced here:
 *
 *   Chrome does NOT reset its multi-click counter when the element under the
 *   pointer changes between two presses at one point. It will deliver
 *   `detail: 2` to an element that never received click #1. (Driven: two
 *   stacked elements, the top removing itself on its own click — the element
 *   underneath receives `{detail: 2}`.)
 *
 *   The confirm dialog is centred on the viewport and the Files listing fills
 *   the centre pane, so "Move to Trash" sits directly over a row (measured at
 *   [838,477], over `file-10.md` in a 30-row listing). The commit click is #1;
 *   the member's next click lands on the row as #2; `handleFileClick` read
 *   `detail >= 2` as a double-click and called `openPath`.
 *
 * A PRIOR DIAGNOSIS OF THIS SAME REPORT WAS WRONG and is recorded so it is not
 * re-derived: "the portal unmounts mid-dispatch so the click RE-TARGETS onto
 * the row". It does not — removing an element during `mousedown` or during its
 * own `click` handler leaves the original target intact. The modal hardening
 * shipped for that theory (`dismissModal`) does NOT fix this bug; driven
 * before and after, both arms opened the file. It was kept on its own merits.
 *
 * WHY THIS GATE EXECUTES RATHER THAN GREPS: the defect lives in the INTERACTION
 * between a browser fact and a rule, which no substring check can see. So the
 * real rule is extracted from the shipped source and RUN against a real Chrome
 * with real dispatched input. If someone deletes the anchor, this reddens.
 *
 * Run:  node web/scripts/gates/detail_counts_the_gesture_not_the_element.mjs
 */

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, '../../..');
const PAGE = resolve(REPO, 'web/app/(authenticated)/files/page.tsx');
const PUPPETEER = resolve(
  process.env.HOME,
  '.claude/plugins/cache/claude-plugins-official/chrome-devtools-mcp/1.9.0'
    + '/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js',
);
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

let pass = 0;
const fails = [];
const check = (label, ok, detail = '') => {
  if (ok) { pass++; console.log(`  ok   ${label}`); }
  else { fails.push(label); console.log(`  FAIL ${label}${detail ? `\n         ${detail}` : ''}`); }
};

// ── 1. Extract the REAL rule from the shipped source ───────────────────────
//
// Not a copy. If the anchor is removed from page.tsx, the extracted body no
// longer contains it and check 2 fails — which is the whole point.

const src = readFileSync(PAGE, 'utf8');
const m = src.match(/const handleFileClick = useCallback\(\s*\(([\s\S]*?)\n  \);/);
check('handleFileClick is extractable from page.tsx', !!m);
const body = m ? m[1] : '';

check(
  'the double-click test is anchored to the row (not detail alone)',
  /\(e\?\.detail \?\? 0\) >= 2\s*&&\s*clickSeqPathRef\.current === node\.path/.test(body),
  'a bare `(e?.detail ?? 0) >= 2` opens a row whose sequence began on a modal button',
);
check(
  'the anchor is written on every click',
  /clickSeqPathRef\.current = node\.path;/.test(body),
);
check(
  'a completed organize verb ends the sequence',
  /endClickSeq\(\);/.test(src) && /clickSeqPathRef\.current = null/.test(src),
);

// ── 2. RUN the real rule against a real browser ────────────────────────────

let puppeteer;
try {
  puppeteer = (await import(PUPPETEER)).default;
} catch {
  console.log('\n  SKIP browser arm — puppeteer-core not found at the plugin cache path.');
  console.log(`  ${pass}/${pass + fails.length} static checks passed`);
  process.exit(fails.length ? 1 : 0);
}

// Translate the extracted rule into something runnable in the page, keeping
// the CONDITION verbatim so the gate tests what ships.
const condition = body.match(
  /const isDoubleClick =\s*([\s\S]*?);/,
)?.[1]?.trim();
check('the isDoubleClick condition is extractable', !!condition);

const browser = await puppeteer.launch({
  executablePath: CHROME, headless: 'new', args: ['--no-sandbox'],
});
const page = await browser.newPage();
// A THROWN HANDLER LOOKS EXACTLY LIKE A FIXED ONE — both produce no openPath.
// This gate first ran 8/8 with the injected condition never substituted (the
// token appeared in a COMMENT first, so a first-match .replace() rewrote that
// and left the code's token undefined): every anchored arm threw
// ReferenceError and the "does not open" check passed vacuously. Any page
// error now fails the run outright.
const pageErrors = [];
page.on('pageerror', (err) => pageErrors.push(String(err).slice(0, 200)));
page.on('console', (m) => { if (m.type() === 'error') pageErrors.push(m.text().slice(0, 200)); });
await page.setViewport({ width: 1440, height: 900 });

await page.setContent(`
<style>html,body{margin:0;font:14px system-ui}
 .listing{position:fixed;inset:0;overflow:auto}
 .row{display:block;width:100%;text-align:left;padding:14px 16px;border-bottom:1px solid #eee;background:#fff}
 .backdrop{position:fixed;inset:0;background:rgba(0,0,0,.5)}
 .wrap{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;padding:16px;pointer-events:none}
 .panel{pointer-events:auto;width:100%;max-width:24rem;background:#fff;border:1px solid #ccc;padding:20px}
</style>
<div class="listing" id="listing"></div>
<script>
 window.EVENTS=[]; window.ANCHORED=true;
 window.clickSeqPathRef={current:null};
 const L=document.getElementById('listing');
 for(let i=0;i<30;i++){
   const b=document.createElement('button');
   b.className='row'; b.textContent='file-'+i+'.md';
   const node={path:'/workspace/Documents/file-'+i+'.md'};
   b.addEventListener('click',(e)=>{
     // THE SHIPPED CONDITION, injected verbatim by the runner.
     const isDoubleClick = window.ANCHORED ? (__COND__) : ((e?.detail ?? 0) >= 2);
     window.clickSeqPathRef.current = node.path;
     window.EVENTS.push({act:isDoubleClick?'openPath':'selectOne',file:b.textContent,detail:e.detail});
   });
   L.appendChild(b);
 }
 window.openConfirm=function(){
   const bd=document.createElement('div'); bd.className='backdrop';
   const w=document.createElement('div'); w.className='wrap';
   const p=document.createElement('div'); p.className='panel';
   const ok=document.createElement('button'); ok.textContent='Move to Trash';
   ok.addEventListener('click',()=>{
     window.EVENTS.push({act:'TRASHED'});
     if(window.ANCHORED) window.clickSeqPathRef.current=null;   // endClickSeq()
     bd.remove(); w.remove();
   });
   p.appendChild(ok); w.appendChild(p);
   document.body.appendChild(bd); document.body.appendChild(w);
   const r=ok.getBoundingClientRect();
   bd.style.display='none'; w.style.display='none';
   const under=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
   bd.style.display=''; w.style.display='';
   return {x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2),
           under:under?under.textContent:null};
 };
 window.reset=(anchored)=>{window.EVENTS=[];window.ANCHORED=anchored;
   window.clickSeqPathRef.current=null;
   document.querySelectorAll('.backdrop,.wrap').forEach(n=>n.remove());};
</script>`.replaceAll('__COND__', condition ?? '(e?.detail ?? 0) >= 2'));

const cdp = await page.target().createCDPSession();
const press = async (x, y, clickCount) => {
  await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed',  x, y, button: 'left', clickCount, buttons: 1 });
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount, buttons: 0 });
};
const settle = () => new Promise((s) => setTimeout(s, 50));

// THE BUG: delete, then a click at the same point.
const deleteFlow = async (anchored) => {
  await page.evaluate((a) => window.reset(a), anchored);
  const pt = await page.evaluate(() => window.openConfirm());
  await press(pt.x, pt.y, 1); await settle();
  await press(pt.x, pt.y, 2); await settle();
  return { pt, events: await page.evaluate(() => window.EVENTS) };
};

console.log('\n  --- the delete flow');
const unanchored = await deleteFlow(false);
check(
  'FALSIFIER: without the anchor the bug reproduces',
  unanchored.events.some((e) => e.act === 'openPath'),
  'the bare detail rule no longer opens the row — this gate can no longer prove the bug',
);
console.log(`       confirm sits over: ${JSON.stringify(unanchored.pt.under)}`);

const anchored = await deleteFlow(true);
check(
  'the shipped rule does NOT open a row after the delete confirm',
  !anchored.events.some((e) => e.act === 'openPath'),
  `events: ${JSON.stringify(anchored.events)}`,
);

// THE REGRESSION: a genuine double-click must still open.
console.log('\n  --- a genuine double-click on a row');
await page.evaluate(() => window.reset(true));
// Ask the page where a row actually is — a hardcoded point silently misses and
// reports an empty event list, which reads as "the fix broke double-click".
const rowPt = await page.evaluate(() => {
  const r = document.querySelectorAll('.row')[3].getBoundingClientRect();
  const pt = { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) };
  pt.at = (() => { const el = document.elementFromPoint(pt.x, pt.y); return el ? el.className : null; })();
  return pt;
});
console.log('       row target:', JSON.stringify(rowPt));
await press(rowPt.x, rowPt.y, 1); await settle();
await press(rowPt.x, rowPt.y, 2); await settle();
const dbl = await page.evaluate(() => window.EVENTS);
check(
  'a real double-click still opens the row',
  dbl.some((e) => e.act === 'openPath'),
  `events: ${JSON.stringify(dbl)}`,
);

check(
  'no page errors — a thrown handler would fake every negative result',
  pageErrors.length === 0,
  pageErrors.join(' | '),
);

await browser.close();

console.log('\n' + '='.repeat(62));
console.log(`${pass}/${pass + fails.length} checks passed`);
if (fails.length) {
  console.log('\nFAILED:');
  for (const f of fails) console.log(`  - ${f}`);
  process.exit(1);
}
console.log('\nGreen — driven against real Chrome with real dispatched input.');
