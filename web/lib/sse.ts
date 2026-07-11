/**
 * sseEvents — THE one SSE transport loop (ADR-441 D4).
 *
 * Both live streaming readers (the steward's NarrativeContext reader on
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
): AsyncGenerator<Record<string, unknown>> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      const evt = parseSseLine(line);
      if (evt) yield evt;
    }
  }
  const tail = parseSseLine(buffer);
  if (tail) yield tail;
}
