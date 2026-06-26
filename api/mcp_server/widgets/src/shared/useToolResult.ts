// Generic tool-result reader shared by all widgets (ADR-372). Mirrors OpenAI's
// reference reader (openai-apps-sdk-examples/src/use-openai-global.ts): read at
// mount + subscribe to `openai:set_globals` + POLL `window.openai.toolOutput`
// (the at-mount race fix). Also supports the open MCP Apps host path
// (`ui/notifications/tool-result` postMessage) so the same bundle renders on
// non-ChatGPT hosts.
//
// Generic over the result shape T, with a `recognize` predicate so each widget
// accepts only its own result (and unwraps a nested structuredContent if the
// host delivers the full CallToolResult).

import { useEffect, useState } from "react";

declare global {
  interface Window {
    openai?: { toolOutput?: unknown };
  }
}

const SET_GLOBALS_EVENT = "openai:set_globals";

function makeCoerce<T>(recognize: (v: Record<string, unknown>) => boolean) {
  return function coerce(value: unknown): T | null {
    if (!value || typeof value !== "object") return null;
    const v = value as Record<string, unknown>;
    if (v.structuredContent && typeof v.structuredContent === "object") {
      const sc = v.structuredContent as Record<string, unknown>;
      return recognize(sc) ? (sc as T) : null;
    }
    return recognize(v) ? (v as T) : null;
  };
}

export function useToolResult<T>(recognize: (v: Record<string, unknown>) => boolean): T | null {
  const coerce = makeCoerce<T>(recognize);
  const read = (): T | null => {
    try {
      return coerce(window.openai?.toolOutput);
    } catch {
      return null;
    }
  };

  const [result, setResult] = useState<T | null>(() => read());

  useEffect(() => {
    let settled = result != null;

    function onSetGlobals(event: Event) {
      const detail = (event as CustomEvent).detail;
      const next = coerce(detail?.globals?.toolOutput) ?? read();
      if (next) {
        settled = true;
        setResult(next);
      }
    }
    function onMessage(event: MessageEvent) {
      const msg = event.data;
      if (msg && typeof msg === "object" && msg.method === "ui/notifications/tool-result" && msg.params) {
        const next = coerce(msg.params.structuredContent);
        if (next) {
          settled = true;
          setResult(next);
        }
      }
    }

    window.addEventListener(SET_GLOBALS_EVENT, onSetGlobals as EventListener, { passive: true } as AddEventListenerOptions);
    window.addEventListener("message", onMessage);

    let remaining = 40; // ~10s (40 × 250ms)
    const pollId = window.setInterval(() => {
      if (settled) {
        window.clearInterval(pollId);
        return;
      }
      const next = read();
      if (next) {
        settled = true;
        window.clearInterval(pollId);
        setResult(next);
        return;
      }
      remaining -= 1;
      if (remaining <= 0) window.clearInterval(pollId);
    }, 250);

    return () => {
      window.removeEventListener(SET_GLOBALS_EVENT, onSetGlobals as EventListener);
      window.removeEventListener("message", onMessage);
      window.clearInterval(pollId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return result;
}
