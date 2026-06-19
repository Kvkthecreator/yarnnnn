/**
 * ADR-023: Supervisor Desk Architecture
 * ADR-034: Context (emergent domains)
 *
 * Type definitions for the desk surface system
 */

// =============================================================================
// Desk Surface Types
// =============================================================================

// ADR-297 axiom (2026-05-21): surface = viewport panel, not URL
// destination. KernelSurfaceSlug enumerates the 15 atomic surfaces
// declared by api/services/kernel_surfaces.py.
// ADR-309 (2026-06-01): `brand` slug DELETED — Brand is not a standalone
// surface; the Identity surface (IdentityBrandCard) owns Brand. /brand is
// a server redirect → /identity per ADR-308. Surfaces also carry a
// `register` (intent | os-config | application per ADR-309 + ADR-312 D5).
// D19.4 (2026-05-22): settings + connectors promoted from legacy
// pages to atomic kernel surfaces — reverses D19.7. Inside the
// authenticated workspace, every surface is a window.
// ADR-312 D1 (2026-06-02): `cockpit` slug renamed → `home`.
// 2026-06-03: `cadence` slug renamed → `recurrence` (substrate already
// spoke "recurrence"; only the surface label lagged). /cadence is a
// redirect stub.
export type KernelSurfaceSlug =
  | 'feed'
  | 'home'
  | 'recurrence'
  | 'budget'
  | 'autonomy'
  | 'expected-output'  // ADR-348 — Expected Output pane (Contract group)
  | 'mandate'
  | 'principles'
  | 'identity'
  | 'files'
  | 'agents'
  | 'setup'  // ADR-331 D1 — guided first-boot Sequence surface
  | 'program'
  | 'queue'
  | 'operation'  // ADR-346 — the Operation composition (Decide · Read · Tune)
  | 'activity'
  | 'settings'
  | 'workspace-settings'  // ADR-341 — the second Settings door (the operation)
  | 'connectors'
  | 'sources';  // ADR-338 D4.1 — standing-watch drivers view

export type DeskSurface =
  // ADR-297: atomic kernel surface — slug identifies which surface
  // component to mount; params carry optional deep-link state
  // (e.g. `task` slug on recurrence, `agent` slug on agents).
  | { type: 'atomic'; slug: KernelSurfaceSlug; params?: Record<string, string> }
  // Legacy surface kinds — predate ADR-297 and remain in use by the
  // NarrativeContext handoff machinery + signal-shaped deep-links.
  // Subsumed by `atomic` over time; kept until call sites migrate.
  | { type: 'agent-review'; agentId: string; runId: string }
  | { type: 'agent-detail'; agentId: string }
  | { type: 'agent-list'; status?: 'active' | 'paused' | 'archived' }
  | { type: 'task-detail'; taskSlug: string }
  | { type: 'context-browser'; scope: 'user' | 'agent'; scopeId?: string }
  | { type: 'context-editor'; memoryId: string }
  | { type: 'document-viewer'; documentId: string }
  | { type: 'document-list' }
  | { type: 'platform-list' }
  | { type: 'platform-detail'; platform: 'slack' | 'notion' }
  | { type: 'workspace-explorer'; path: string; navigation_type?: 'file' | 'folder' }
  // Idle state
  | { type: 'idle' };

export const KERNEL_SURFACE_SLUGS: readonly KernelSurfaceSlug[] = [
  'feed', 'home', 'recurrence', 'budget', 'autonomy', 'expected-output', 'mandate', 'principles',
  'identity', 'files', 'agents', 'setup', 'program', 'queue', 'operation', 'activity',
  'settings', 'workspace-settings', 'connectors', 'sources',
] as const;

export function isKernelSurfaceSlug(s: string): s is KernelSurfaceSlug {
  return (KERNEL_SURFACE_SLUGS as readonly string[]).includes(s);
}

// =============================================================================
// TP (Thinking Partner)
// =============================================================================

/** Image attachment sent inline as base64 (not stored, ephemeral) */
export interface TPImageAttachment {
  /** Base64-encoded image data */
  data: string;
  /** MIME type (image/jpeg, image/png, image/gif, image/webp) */
  mediaType: 'image/jpeg' | 'image/png' | 'image/gif' | 'image/webp';
}

/**
 * ADR-042: Streaming Process Visibility
 * Message content blocks for inline tool display
 */
export type SystemCardType =
  | 'workspace_init_complete'
  | 'task_complete'
  // ADR-219 Commit 3: rolled-up housekeeping digest written by
  // back-office-narrative-digest. Frontend renders as a collapsed
  // card with expand-to-list using metadata.rolled_up_ids/counts.
  | 'narrative_digest';

/**
 * ADR-219 Commit 2: narrative envelope per session_messages row.
 * Mirrors the metadata fields that services.narrative.write_narrative_entry
 * stamps. Available on every TPMessage post-Commit-2; older rows
 * surface with only the fields that were set when they were written.
 */
// ADR-277 (2026-05-15): housekeeping weight retired. Emission is by-intent
// at source per the feed emission policy — mechanical-fire successes that
// were once tagged housekeeping (and never finished migrating into a
// roll-up digest) no longer emit. Surviving narrative entries are either
// material (operator must see) or routine (context if reading the feed).
export type NarrativeWeight = 'material' | 'routine';
export type NarrativePulse = 'periodic' | 'reactive' | 'addressed' | 'heartbeat';

export interface NarrativeEnvelope {
  /** One-line headline used for collapsed (routine) rendering. */
  summary?: string;
  pulse?: NarrativePulse;
  weight?: NarrativeWeight;
  /** Task slug nameplate, when this invocation was labeled. */
  taskSlug?: string;
  /** ADR-289 D2: the execution_events.id of the cycle that emitted this
   *  narrative entry. All rows produced during one Reviewer cycle share
   *  this id; the Feed surface groups them into one InvocationCard. */
  invocationId?: string;
  /** Audit-pass-2 DD-4: when this narration entry corresponds to a
   * ProposeAction tool call (System Agent on Reviewer's direction),
   * the resulting action_proposal id. The FE renders an inline
   * ProposalCard chip on these entries so the operator can tap-to-
   * inspect-and-act directly from the feed without navigating to the
   * cockpit Queue. */
  proposalId?: string;
}

export type MessageBlock =
  | { type: 'text'; content: string }
  | { type: 'thinking'; content: string }
  | { type: 'tool_call'; id: string; tool: string; input?: Record<string, unknown>; status: 'pending' | 'success' | 'failed'; result?: TPToolResult }
  | { type: 'clarify'; question: string; options?: string[] }
  | { type: 'notification'; title: string; description?: string; toolName: string }
  | { type: 'system_card'; card_type: SystemCardType; data: Record<string, unknown> };

/**
 * ADR-212 / 2026-04-23: Reviewer verdict metadata surfaced as chat messages.
 * Populated when role === 'reviewer'. Enables ReviewerCard rendering.
 */
export interface ReviewerCardData {
  proposalId?: string;
  verdict?: 'approve' | 'reject' | 'defer' | 'observation' | string;
  occupant?: string;
  actionType?: string;
  taskSlug?: string;
}

export interface TPMessage {
  id: string;
  /**
   * ADR-219 Commit 2 widened the session_messages.role enum to include
   * the full Identity taxonomy: user, assistant, system, reviewer, agent,
   * external, system_agent. The frontend mirrors that union so every narrative
   * entry round-trips through TPMessage without conflation.
   * ADR-252 D4: system_agent added for System Agent execution narration.
   * assistant is preserved for historical rows (pre-ADR-252).
   */
  role: 'user' | 'assistant' | 'system' | 'reviewer' | 'agent' | 'external' | 'system_agent';
  content: string;
  /** Images attached to this message (user messages only) */
  images?: TPImageAttachment[];
  /** Legacy: tool results shown at end of message */
  toolResults?: TPToolResult[];
  /** ADR-042: Structured content blocks for inline display */
  blocks?: MessageBlock[];
  timestamp: Date;
  /** ADR-124: Author attribution for meeting room messages */
  authorAgentId?: string;
  authorAgentSlug?: string;
  authorRole?: string;
  authorName?: string;
  /** ADR-212: reviewer verdict metadata (role === 'reviewer') */
  reviewer?: ReviewerCardData;
  /** ADR-219 Commit 2: narrative envelope (weight, pulse, summary, …). */
  narrative?: NarrativeEnvelope;
}

export interface TPToolResult {
  toolName: string;
  success: boolean;
  data?: Record<string, unknown>;
  uiAction?: TPUIAction;
}

export interface TPUIAction {
  type: 'OPEN_SURFACE' | 'RESPOND' | 'CLARIFY' | 'SHOW_SETUP_CONFIRM' | 'UPDATE_TODOS' | 'NAVIGATE';
  surface?: string;
  data: Record<string, unknown>;
}

// =============================================================================
// Todo Tracking (ADR-025 Claude Code Alignment)
// =============================================================================

/** ADR-155: Notification from tool side effects */
export interface TPNotification {
  id: string;
  toolName: string;
  title: string;
  description?: string;
  timestamp: Date;
}

/** A single todo item in TP's work progress */
export interface Todo {
  /** Task description in imperative form (e.g., "Gather details") */
  content: string;
  /** Current status of the task */
  status: 'pending' | 'in_progress' | 'completed';
  /** Task description in present continuous (e.g., "Gathering details") */
  activeForm?: string;
}

// =============================================================================
// TP State
// =============================================================================

export interface TPState {
  messages: TPMessage[];
  isLoading: boolean;
  error: string | null;
  /** ADR-025: Current todo list for multi-step work */
  todos: Todo[];
  /** ADR-025: Active slash command name (e.g., "recap", "summary") */
  activeCommand: string | null;
  /** ADR-025: Whether work panel is expanded */
  workPanelExpanded: boolean;
  /** ADR-155: Notifications from tool side effects (queued when chat closed) */
  pendingNotifications: TPNotification[];
}

export type TPAction =
  | { type: 'ADD_MESSAGE'; message: TPMessage }
  | { type: 'SET_MESSAGES'; messages: TPMessage[] }
  | { type: 'CLEAR_MESSAGES' }
  // ADR-042: Update streaming message blocks in real-time
  // ADR-124: author fields for meeting room attribution
  | { type: 'UPDATE_STREAMING_MESSAGE'; messageId?: string; blocks: MessageBlock[]; content?: string; authorAgentId?: string; authorAgentSlug?: string; authorRole?: string; authorName?: string }
  | { type: 'SET_LOADING'; isLoading: boolean }
  | { type: 'SET_ERROR'; error: string | null }
  // ADR-025: Todo tracking actions
  | { type: 'SET_TODOS'; todos: Todo[] }
  | { type: 'SET_ACTIVE_COMMAND'; command: string | null }
  | { type: 'SET_WORK_PANEL_EXPANDED'; expanded: boolean }
  | { type: 'CLEAR_WORK_STATE' }
  // ADR-155: Notification channel
  | { type: 'ADD_NOTIFICATION'; notification: TPNotification }
  | { type: 'FLUSH_NOTIFICATIONS' };

// =============================================================================
// Utility functions
// =============================================================================

/**
 * Map TP tool ui_action to DeskSurface
 */
export function mapToolActionToSurface(action: TPUIAction): DeskSurface | null {
  const { surface, data } = action;

  switch (surface) {
    // Agents (create handled by YARNNN chat — /dashboard?create)
    case 'agent':
      return { type: 'agent-detail', agentId: data.agentId as string };
    case 'agent-review':
      return {
        type: 'agent-review',
        agentId: data.agentId as string,
        runId: data.runId as string,
      };
    case 'agent-list':
      return {
        type: 'agent-list',
        status: data.status as 'active' | 'paused' | 'archived' | undefined,
      };

    // Tasks (ADR-139)
    case 'task':
    case 'task-detail':
      return { type: 'task-detail', taskSlug: data.taskSlug as string };

    // Context (ADR-034)
    case 'context':
    case 'memory':
      return {
        type: 'context-browser',
        scope: (data.scope as 'user' | 'agent') || 'user',
        scopeId: data.scopeId as string | undefined,
      };
    case 'memory-edit':
      return { type: 'context-editor', memoryId: data.memoryId as string };

    // Documents
    case 'document':
      return { type: 'document-viewer', documentId: data.documentId as string };
    case 'document-list':
      return { type: 'document-list' };

    // Platforms (ADR-033)
    case 'platforms':
    case 'platform-list':
      return { type: 'platform-list' };
    case 'platform':
    case 'platform-detail':
      return {
        type: 'platform-detail',
        platform: data.platform as 'slack' | 'notion',
      };

    // Dashboard/Home
    case 'dashboard':
    case 'home':
    case 'idle':
      return { type: 'idle' };

    default:
      return null;
  }
}
