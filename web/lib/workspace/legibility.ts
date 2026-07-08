/**
 * File legibility state — the ONE place a file's "how freely can I touch this?"
 * fact becomes an operator-facing affordance (ADR-422 D1).
 *
 * Before ADR-422 the Files surface collapsed three genuinely distinct
 * not-freely-editable cases into a single grey + `sys` tag, and a layman could
 * not tell them apart. The three states are all determined by data ALREADY on
 * every tree node (`path` + `authored_by`) — this module derives them; it adds
 * no backend data.
 *
 * The three states (+ the ordinary operator file), macOS-Finder-native:
 *
 *   machine-config  — a settings file the system reads at an exact path
 *                     (system/ OR _*.{yaml,yml,json}). Renaming/moving breaks the
 *                     reader — a filesystem-integrity fact, not a permission
 *                     hierarchy. Reads as: "managed by the system."
 *   raw-intake      — an immutable attributed observation of what arrived from
 *                     outside (under inbound/, ADR-376 DP32). Retained, never
 *                     rewritten. Reads as: "a record of what came in."
 *   agent-authored  — the operator OWNS + can reorganize it, but its content was
 *                     authored by an agent (Freddie / a hired agent / an MCP
 *                     client / a member's lane). Edited through chat, not typed
 *                     in-app (the ADR-400 GitHub+Copilot boundary). Reads as:
 *                     "authored by {who} — edit via chat."
 *   operator        — the operator's own file. No special affordance.
 *
 * Precedence (ADR-422 D1): machine-config > raw-intake > agent-authored >
 * operator. The stronger operator FACT wins — a machine-config file anywhere
 * reads as machine-config; an inbound file wins over its mcp: authorship because
 * immutability is the stronger thing to know.
 */

import { operatorCanOrganize } from '@/lib/workspace/ownership';
import { authorClass } from '@/lib/workspace/attribution';

export type FileLegibilityState =
  | 'machine-config'
  | 'raw-intake'
  | 'agent-authored'
  | 'operator';

// Author classes that mean "an agent authored this content" (not the operator).
// `system` is deliberately EXCLUDED here — a system: write on an ordinary file is
// covered by machine-config/raw-intake carves where it matters; a stray system
// write on operator prose reads as operator-owned, not as "agent work."
const AGENT_AUTHOR_CLASSES = new Set([
  'reviewer', // freddie:/reviewer:
  'agent', // agent:/a2a:
  'mcp', // yarnnn:mcp:{host}
  'member', // member:{id} via {model}
  'specialist', // specialist:{role}
]);

/**
 * Normalize a workspace path to workspace-relative (strip leading slashes +
 * an optional `workspace/` prefix), mirroring the ownership.ts / backend
 * normalization so the prefix tests agree.
 */
function toRel(path: string): string {
  let rel = path.replace(/^\/+/, '');
  if (rel.startsWith('workspace/')) rel = rel.slice('workspace/'.length);
  return rel;
}

/**
 * Classify a file node into its legibility state. Folders return 'operator'
 * (they carry no not-editable affordance today). Derived from path +
 * authored_by only — no new backend data.
 */
export function fileLegibilityState(node: {
  type: 'file' | 'folder';
  path: string;
  authored_by?: string | null;
}): FileLegibilityState {
  if (node.type !== 'file') return 'operator';

  // machine-config wins: the operator can't organize it (system/ + _*.yaml/json).
  // operatorCanOrganize also returns false for inbound/ — so check raw-intake
  // FIRST by path, then fall to machine-config for the remaining non-organizable
  // set. (Ordering matters: an inbound file is non-organizable AND under inbound/;
  // it should read as raw-intake, not machine-config.)
  const rel = toRel(node.path);
  if (rel.startsWith('inbound/')) return 'raw-intake';
  if (!operatorCanOrganize(node.path)) return 'machine-config';

  if (AGENT_AUTHOR_CLASSES.has(authorClass(node.authored_by))) {
    return 'agent-authored';
  }
  return 'operator';
}

/**
 * The one-line, macOS-plain descriptor for a legibility state — shown in
 * Get-Info (ADR-422 D4). Object-focused, no mechanism jargon. `authorLabel` is
 * the resolved operator-facing author name (agent-authored only); pass it so the
 * descriptor can name who.
 */
export function legibilityDescriptor(
  state: FileLegibilityState,
  authorLabel?: string | null,
): string | null {
  switch (state) {
    case 'machine-config':
      return 'The system reads this to run your workspace. Tune it in Settings — don’t move or rename it.';
    case 'raw-intake':
      return 'A record of something that came into your workspace, kept exactly as it arrived. It doesn’t change.';
    case 'agent-authored':
      return authorLabel
        ? `Authored by ${authorLabel}. You own it — to change it, ask in chat.`
        : 'Authored by an agent. You own it — to change it, ask in chat.';
    case 'operator':
      return null;
  }
}
