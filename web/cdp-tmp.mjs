import { WebSocket } from 'ws';
const BASE = 'http://127.0.0.1:9333';
let id = 0;
export async function conn() {
  const targets = await (await fetch(`${BASE}/json/list`)).json();
  let t = targets.find(x => x.type === 'page');
  if (!t) t = await (await fetch(`${BASE}/json/new?about:blank`)).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl, { maxPayload: 256*1024*1024 });
  await new Promise(r => ws.on('open', r));
  const waiters = new Map(); const events = [];
  ws.on('message', m => {
    const msg = JSON.parse(m.toString());
    if (msg.id && waiters.has(msg.id)) { waiters.get(msg.id)(msg); waiters.delete(msg.id); }
    else if (msg.method) events.push(msg);
  });
  const send = (method, params={}) => new Promise((res, rej) => {
    const i = ++id; waiters.set(i, m => m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result));
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  await send('Page.enable'); await send('Runtime.enable');
  const evalJs = async (expr) => {
    const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || 'eval error');
    return r.result.value;
  };
  return { send, evalJs, events, ws };
}
export const sleep = ms => new Promise(r => setTimeout(r, ms));
