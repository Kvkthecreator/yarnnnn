/**
 * sseEvents — THE one SSE transport loop (ADR-441 D4).
 *
 * The lane streaming reader (ADR-441; the steward's reader retired with it —
 * `/api/feed` and the lane reader on `/api/lanes/{id}/messages`) share this
 * byte-level transport: read chunks, buffer on '\n', take `data: {json}`
 * lines, skip the `[DONE]` sentinel, yield parsed events. A final line that
 * arrives without its newline terminator is flushed at stream end.
 *
 * The transport is shared; the EVENT VOCABULARIES are deliberately not
 * (ADR-441 D1): the steward protocol (`stream_start`/`content`/`tool_use`/
 * `tool_result`/…) and the lane protocol (`text_delta`/`tool`/`artifact`/
 * `done`) are the wire expression of the ADR-408 altitude seam. Each caller
 * dispatches on its own vocabulary; this module never learns either.
 */

/**
 * Raised when no bytes arrive for `idleMs` (ADR-651 D3). A proxy can keep a
 * dead socket half-open indefinitely; a reader with no deadline would wait on
 * it for ever with the surface's spinner up. Any bytes reset the deadline —
 * including the server's `: ping` comment frames, which readers skip by spec.
 */
export class SseIdleError extends Error {
  constructor(idleMs: number) {
    super(`No data for ${Math.round(idleMs / 1000)}s`);
    this.name = 'SseIdleError';
  }
}

function readWithin<T>(
  reader: { read(): Promise<T>; cancel(): Promise<void> },
  idleMs: number,
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = setTimeout(() => {
      void reader.cancel().catch(() => {}); // the server sees a disconnect and persists the partial
      reject(new SseIdleError(idleMs));
    }, idleMs);
    reader.read().then(resolve, reject).finally(() => clearTimeout(timer));
  });
}

function parseSseLine(line: string): Record<string, unknown> | null {
  if (!line.startsWith('data: ')) return null;
  const data = line.slice(6);
  if (!data || data === '[DONE]') return null;
  try {
    return JSON.parse(data) as Record<string, unknown>;
  } catch {
    return null; // a malformed frame is dropped, never fatal
  }
}

export async function* sseEvents(
  body: ReadableStream<Uint8Array>,
  opts: {
    /** Give up after this long with no bytes — once the server has sent a
     *  comment frame, proving it heartbeats. */
    idleMs?: number;
    /** The window before that proof. A server deployed before the heartbeat,
     *  or a proxy that strips comments, still gets a bounded wait — a long
     *  one, sized to the engine's own timeout — instead of a cut mid-thought. */
    idleMsUntilHeartbeat?: number;
  } = {},
): AsyncGenerator<Record<string, unknown>> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let heartbeats = false;
  for (;;) {
    const idle = heartbeats ? opts.idleMs : (opts.idleMsUntilHeartbeat ?? opts.idleMs);
    const { done, value } = idle ? await readWithin(reader, idle) : await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (line.startsWith(':')) {
        heartbeats = true; // an SSE comment — the keepalive, skipped by spec
        continue;
      }
      const evt = parseSseLine(line);
      if (evt) yield evt;
    }
  }
  const tail = parseSseLine(buffer);
  if (tail) yield tail;
}
