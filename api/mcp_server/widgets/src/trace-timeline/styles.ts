// Inline stylesheet for the trace-timeline widget. Injected at module load so
// the bundle stays a single self-contained file (no external <link>). Respects
// the host's light/dark via prefers-color-scheme.

export const CSS = `
:root {
  --bg: transparent; --fg: #e7e7ea; --muted: #8a8a93; --line: #2a2a30; --card: #16161a;
  --operator: #4ea1ff; --reviewer: #b07cff; --mcp: #ffb454; --agent: #4ec9a1; --system: #9aa0a6;
  --add: #2ea043; --del: #f85149;
}
@media (prefers-color-scheme: light) {
  :root { --fg: #1a1a1e; --muted: #6b6b73; --line: #e4e4e8; --card: #f7f7f9; }
}
* { box-sizing: border-box; }
body { margin: 0; font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg); color: var(--fg); padding: 14px; }
.tt-subject { font-weight: 650; font-size: 15px; margin: 0 0 2px; }
.tt-caption { color: var(--muted); margin: 0 0 16px; font-size: 12.5px; }
.tt-empty { color: var(--muted); }
ol.tt-timeline { list-style: none; margin: 0; padding: 0 0 0 20px; border-left: 1px solid var(--line); }
li.tt-rev { position: relative; padding: 0 0 16px 16px; }
li.tt-rev::before { content: ""; position: absolute; left: -25px; top: 5px;
  width: 9px; height: 9px; border-radius: 50%; background: var(--system); box-shadow: 0 0 0 3px var(--bg); }
li.tt-rev.operator::before { background: var(--operator); }
li.tt-rev.reviewer::before { background: var(--reviewer); }
li.tt-rev.mcp::before      { background: var(--mcp); }
li.tt-rev.agent::before    { background: var(--agent); }
.tt-head { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.tt-who { font-weight: 600; }
.tt-badge { font-size: 11px; padding: 1px 7px; border-radius: 999px; border: 1px solid var(--line); color: var(--muted); }
.tt-when { color: var(--muted); font-size: 12px; }
.tt-change { margin: 3px 0 0; }
.tt-difftoggle { margin-top: 5px; font-size: 12px; color: var(--muted); background: none;
  border: none; padding: 0; cursor: pointer; text-decoration: underline; }
.tt-difftoggle:hover { color: var(--fg); }
pre.tt-diff { margin: 7px 0 0; padding: 9px 11px; background: var(--card); border: 1px solid var(--line);
  border-radius: 7px; overflow-x: auto; font: 12px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace; }
pre.tt-diff .add { color: var(--add); }
pre.tt-diff .del { color: var(--del); }
pre.tt-diff .meta { color: var(--muted); }
`;

export function injectStyles(): void {
  if (typeof document === "undefined") return;
  if (document.getElementById("tt-styles")) return;
  const el = document.createElement("style");
  el.id = "tt-styles";
  el.textContent = CSS;
  document.head.appendChild(el);
}
