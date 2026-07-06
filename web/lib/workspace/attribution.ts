/**
 * Workspace attribution — the ONE place the ADR-209 `authored_by` taxonomy
 * becomes operator-facing (ADR-388 D3).
 *
 * Before ADR-388 this logic was duplicated four times (files/page.tsx,
 * ContentViewer.tsx, RecentsView.tsx, NodeDetailsPanel.tsx), each subtly
 * different and — critically — each collapsing every `yarnnn:*` write to a
 * flat "YARNNN", which HID the interop story. The moat is *durable attributed
 * memory*: when ChatGPT or Claude writes via MCP, the operator should see
 * exactly that. This module is the single source of truth; every file-display
 * surface renders attribution through it.
 *
 * The `authored_by` taxonomy (ADR-209 + the live MCP forms):
 *   operator                 → You
 *   yarnnn:mcp:{host}         → {Host} (via MCP)   ← the interop wedge, made visible
 *   yarnnn:{model}            → YARNNN
 *   freddie:{...} / reviewer  → Reviewer
 *   agent:{slug}              → Agent ({slug})
 *   specialist:{role}         → Specialist
 *   system:{actor}            → System
 *   a2a:{...}                 → Agent (A2A)
 *   platform:{...}            → Platform
 *   member:{id} via {model}   → Member (via {Model})  ← ADR-411 lane embodiment
 */

export type AuthorClass =
  | 'you'
  | 'mcp'
  | 'yarnnn'
  | 'reviewer'
  | 'agent'
  | 'specialist'
  | 'system'
  | 'platform'
  | 'member'
  | 'unknown';

// Known MCP host id → display name (mirrors api/mcp_server/presentation/hosts.py;
// ADR-379 host profiles). Unknown hosts title-case their raw id.
const MCP_HOST_NAMES: Record<string, string> = {
  chatgpt: 'ChatGPT',
  claude: 'Claude',
  'claude-desktop': 'Claude Desktop',
  'claude-code': 'Claude Code',
  'claude.ai': 'Claude',
  gemini: 'Gemini',
  cursor: 'Cursor',
  copilot: 'Copilot',
  perplexity: 'Perplexity',
};

function mcpHostName(raw: string): string {
  const key = raw.toLowerCase();
  if (MCP_HOST_NAMES[key]) return MCP_HOST_NAMES[key];
  // Title-case a hyphenated/raw id (e.g. "some-host" → "Some Host").
  return raw.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * The raw MCP host id (the `yarnnn:mcp:{host}` tail), or null when this is not
 * an MCP write. Lets a presentational layer pick a host brand mark without
 * re-deriving the slice. (The icon registry — principal-badge.tsx — uses this
 * so the host-string parsing stays in this one module.)
 */
export function mcpHostId(authored_by: string | null | undefined): string | null {
  if (!authored_by || !authored_by.startsWith('yarnnn:mcp:')) return null;
  return authored_by.slice('yarnnn:mcp:'.length) || null;
}

// Lane-model id → display label (mirrors LANE_MODELS in api/services/lane_runner.py).
// Unknown models strip the provider prefix and pass through.
const LANE_MODEL_NAMES: Record<string, string> = {
  'anthropic/claude-sonnet-4-6': 'Claude Sonnet',
  'anthropic/claude-haiku-4-5-20251001': 'Claude Haiku',
  'openai/gpt-4o-mini': 'GPT-4o mini',
};

function laneModelName(raw: string): string {
  if (LANE_MODEL_NAMES[raw]) return LANE_MODEL_NAMES[raw];
  return raw.includes('/') ? raw.split('/').slice(1).join('/') : raw;
}

/**
 * Parse the ADR-411 member-embodiment form: "member:{user_id} via {model}".
 * Returns {memberId, model} or null when this is not a lane write. Lets a
 * viewer-aware surface render "You via GPT-4o mini" / "‹member› via GPT-4o
 * mini" without re-parsing the string; the sync label below is the generic
 * fallback.
 */
export function memberEmbodiment(
  authored_by: string | null | undefined,
): { memberId: string; model: string } | null {
  if (!authored_by || !authored_by.startsWith('member:')) return null;
  const rest = authored_by.slice('member:'.length);
  const sep = rest.indexOf(' via ');
  if (sep === -1) return { memberId: rest, model: '' };
  return { memberId: rest.slice(0, sep), model: rest.slice(sep + ' via '.length) };
}

/** Classify an `authored_by` string into a stable author class. */
export function authorClass(authored_by: string | null | undefined): AuthorClass {
  if (!authored_by) return 'system';
  if (authored_by === 'operator') return 'you';
  if (authored_by.startsWith('yarnnn:mcp:')) return 'mcp';
  if (authored_by.startsWith('yarnnn:')) return 'yarnnn';
  if (authored_by.startsWith('freddie:') || authored_by.startsWith('reviewer:')) return 'reviewer';
  if (authored_by.startsWith('member:')) return 'member';
  if (authored_by.startsWith('agent:')) return 'agent';
  if (authored_by.startsWith('a2a:')) return 'agent';
  if (authored_by.startsWith('specialist:')) return 'specialist';
  if (authored_by.startsWith('platform:')) return 'platform';
  if (authored_by.startsWith('system:')) return 'system';
  return 'unknown';
}

/**
 * The operator-facing label. Returns null when there is no attribution to
 * show (callers decide whether to render "System" or nothing). The MCP form
 * is the load-bearing one — it surfaces *which* external LLM wrote, by name.
 */
export function formatAuthorLabel(authored_by: string | null | undefined): string | null {
  if (!authored_by) return null;
  const cls = authorClass(authored_by);
  switch (cls) {
    case 'you':
      return 'You';
    case 'mcp':
      return `${mcpHostName(authored_by.slice('yarnnn:mcp:'.length))} (via MCP)`;
    case 'yarnnn':
      return 'YARNNN';
    // ADR-381/251 relabel-keep-slug: the `reviewer`/`freddie:` slug is internal;
    // the operator-facing label is "Freddie". (Persona-aware surfaces — chat
    // header, bubble, streaming status — resolve the authored persona name via
    // useFreddiePersona/getFreddiePersonaName; this sync labeler is the generic
    // fallback for glance contexts (Recents, revision panels, routine rows).)
    case 'reviewer':
      return 'Freddie';
    case 'agent': {
      const slug = authored_by.startsWith('agent:')
        ? authored_by.slice('agent:'.length)
        : null;
      return slug ? `Agent (${slug})` : 'Agent (A2A)';
    }
    // ADR-411 lane embodiment — the member's hands, transport named (ADR-408
    // D2). The sync fallback can't resolve the member id to a name; viewer-
    // aware surfaces use memberEmbodiment() + the roster to render
    // "You via GPT-4o mini" / "seulkim88 via GPT-4o mini".
    case 'member': {
      const emb = memberEmbodiment(authored_by);
      return emb?.model ? `Member (via ${laneModelName(emb.model)})` : 'Member';
    }
    case 'specialist':
      return 'Specialist';
    case 'platform':
      return 'Platform';
    case 'system':
      return 'System';
    default:
      return null;
  }
}

/** Like formatAuthorLabel but never null — for glance contexts (Recents/tree). */
export function formatAuthorLabelOrSystem(authored_by: string | null | undefined): string {
  return formatAuthorLabel(authored_by) ?? 'System';
}

/**
 * The author-class accent — a quiet dot color (who, at a glance). Tailwind
 * bg-* class. MCP gets its own accent (amber) so an external-LLM write reads
 * distinctly from a YARNNN write — the interop story is legible even in the
 * one-glance dot.
 */
export function authorAccent(authored_by: string | null | undefined): string {
  switch (authorClass(authored_by)) {
    case 'you':
      return 'bg-primary';
    // Freddie (reviewer) is the TRUSTED management agent — an indigo accent reads
    // as authoritative/steady, not the alarm-red the prior rose implied (an
    // operator read rose + a warning-triangle as "error"). ADR-381 relabel.
    case 'reviewer':
      return 'bg-indigo-400';
    case 'yarnnn':
      return 'bg-sky-400';
    case 'mcp':
      return 'bg-amber-400';
    // Lane embodiment (ADR-411) — a member's hands: teal sits between the
    // member's own primary and the external-LLM amber, which is the honest
    // reading (the member's act, through a model transport).
    case 'member':
      return 'bg-teal-400';
    case 'agent':
      return 'bg-violet-400';
    case 'platform':
      return 'bg-cyan-400';
    default:
      return 'bg-muted-foreground/40';
  }
}
