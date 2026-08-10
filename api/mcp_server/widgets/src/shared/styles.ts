// Shared inline stylesheet for the search-results + receipt widgets
// (ADR-372). Injected at module load so each bundle stays a single
// self-contained file. Respects the host's light/dark via prefers-color-scheme.
// `yz-` namespace (history-timeline keeps its own `tt-` styles untouched).

export const CSS = `
:root {
  --yz-bg: transparent; --yz-fg: #e7e7ea; --yz-muted: #8a8a93; --yz-line: #2a2a30; --yz-card: #16161a;
  --yz-operator: #4ea1ff; --yz-reviewer: #b07cff; --yz-mcp: #ffb454; --yz-agent: #4ec9a1; --yz-system: #9aa0a6;
  --yz-ok: #4ec9a1;
}
@media (prefers-color-scheme: light) {
  :root { --yz-fg: #1a1a1e; --yz-muted: #6b6b73; --yz-line: #e4e4e8; --yz-card: #f7f7f9; }
}
* { box-sizing: border-box; }
body { margin: 0; font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--yz-bg); color: var(--yz-fg); padding: 14px; }
.yz-subject { font-weight: 650; font-size: 15px; margin: 0 0 2px; }
.yz-caption { color: var(--yz-muted); margin: 0 0 14px; font-size: 12.5px; }
.yz-empty { color: var(--yz-muted); }

/* provenance chip (shared visual language with the history timeline) */
.yz-chip { font-size: 11px; padding: 1px 8px; border-radius: 999px; border: 1px solid var(--yz-line);
  color: var(--yz-muted); display: inline-flex; align-items: center; gap: 5px; }
.yz-chip::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--yz-system); }
.yz-chip.operator::before { background: var(--yz-operator); }
.yz-chip.reviewer::before { background: var(--yz-reviewer); }
.yz-chip.mcp::before      { background: var(--yz-mcp); }
.yz-chip.agent::before    { background: var(--yz-agent); }

/* search result cards */
.yz-cards { display: flex; flex-direction: column; gap: 10px; }
.yz-card { background: var(--yz-card); border: 1px solid var(--yz-line); border-radius: 9px; padding: 11px 13px; }
.yz-card-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }
.yz-when { color: var(--yz-muted); font-size: 12px; }
.yz-excerpt { margin: 0; white-space: pre-wrap; }
.yz-path { display: block; margin-top: 7px; color: var(--yz-muted); font-size: 11.5px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; word-break: break-all; }

/* search confidence (ADR-543 D2, rendered 2026-08-10). The signal the server
   ALWAYS sends and the widget used to drop. Reuses the existing accent tokens —
   ambiguous/weak borrow the warm marker the conflict state uses, because
   both mean the same thing to a reader: do not just take the top one.
   (No backticks in this file: the whole stylesheet is one template literal.) */
.yz-confidence { font-size: 11px; padding: 1px 7px; border-radius: 999px;
  border: 1px solid var(--yz-line); color: var(--yz-muted); white-space: nowrap; }
.yz-conf-high { color: var(--yz-ok); border-color: var(--yz-ok); }
.yz-conf-ambiguous, .yz-conf-weak { color: var(--yz-mcp); border-color: var(--yz-mcp); }
.yz-explanation { margin-top: -8px; }

/* receipt (save-receipt — ADR-533 D4) */
.yz-receipt { display: flex; align-items: flex-start; gap: 10px; background: var(--yz-card);
  border: 1px solid var(--yz-line); border-radius: 9px; padding: 11px 13px; }
.yz-check { color: var(--yz-ok); font-weight: 700; font-size: 16px; line-height: 1.4; }
.yz-receipt-body { flex: 1; }
.yz-receipt-title { font-weight: 600; margin: 0 0 3px; }
.yz-receipt-meta { color: var(--yz-muted); font-size: 12px; margin: 0; }

/* save receipt — the conflict state (ADR-533 D4). A stale_write is the one
   outcome the user must ACT on, so it gets the accent border + a warm marker;
   everything else reuses the plain receipt above. */
.yz-warn { color: var(--yz-mcp); }
.yz-conflict { border-color: var(--yz-mcp); }
.yz-change { margin-top: 5px; font-style: italic; }
.yz-resolve { margin-top: 6px; color: var(--yz-fg); font-size: 12.5px; }

/* the retry basis (conflict) + the provenance edge (success), 2026-08-10.
   yz-rev is a shared inline-code token: a revision id and a cited path are
   both exact strings the reader may need to copy, so they render alike. */
.yz-basis { margin-top: 6px; }
.yz-derived { margin-top: 6px; }
.yz-rev { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11.5px; word-break: break-all; }

/* file header (open — ADR-533 D4). Identity, not content: the host renders the
   text; this renders whose version it is. */
.yz-file { background: var(--yz-card); border: 1px solid var(--yz-line);
  border-radius: 9px; padding: 11px 13px; }
.yz-file-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.yz-file-name { font-weight: 650; font-size: 15px; word-break: break-all; }
.yz-trunc { font-size: 11px; padding: 1px 7px; border-radius: 999px;
  border: 1px solid var(--yz-line); color: var(--yz-muted); }
.yz-revcount { margin-top: 5px; }
`;

export function injectStyles(id: string): void {
  if (typeof document === "undefined") return;
  if (document.getElementById(id)) return;
  const el = document.createElement("style");
  el.id = id;
  el.textContent = CSS;
  document.head.appendChild(el);
}
