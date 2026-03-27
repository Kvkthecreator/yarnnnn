'use client';

/**
 * IsometricRoom — Habbo Hotel-inspired agent display
 *
 * CSS isometric floor with agents positioned on tiles.
 * Each agent is a clickable sprite with state-based animations (via AgentAvatar).
 * Mobile (<768px) falls back to a compact horizontal scroll strip.
 */

import Link from 'next/link';
import { Loader2 } from 'lucide-react';
import {
  FlaskConical,
  FileText,
  TrendingUp,
  Users,
  MessageCircle,
  BookOpen,
  Cog,
} from 'lucide-react';
import type { Agent, Task } from '@/types';
import { AgentAvatar } from '@/components/agents/AgentAvatar';
import { cn } from '@/lib/utils';

// =============================================================================
// Agent type → color + icon mapping (simplified from old TYPE_CONFIG)
// =============================================================================

const AGENT_COLORS: Record<string, { hex: string; icon: typeof FlaskConical }> = {
  research:   { hex: '#3b82f6', icon: FlaskConical },
  content:    { hex: '#a855f7', icon: FileText },
  marketing:  { hex: '#ec4899', icon: TrendingUp },
  crm:        { hex: '#f97316', icon: Users },
  slack_bot:  { hex: '#14b8a6', icon: MessageCircle },
  notion_bot: { hex: '#6366f1', icon: BookOpen },
  briefer:    { hex: '#3b82f6', icon: FlaskConical },
  researcher: { hex: '#3b82f6', icon: FlaskConical },
  analyst:    { hex: '#3b82f6', icon: FlaskConical },
  drafter:    { hex: '#a855f7', icon: FileText },
  writer:     { hex: '#a855f7', icon: FileText },
  custom:     { hex: '#6b7280', icon: Cog },
};

function getAgentConfig(role: string) {
  return AGENT_COLORS[role] || AGENT_COLORS.custom;
}

// =============================================================================
// Tile positions — 2 rows × 3 columns, isometric coordinates
// =============================================================================

// Isometric tile positions: [col, row] mapped to pixel offsets
// In isometric space: x moves right-down, y moves left-down
const TILE_POSITIONS = [
  { col: 0, row: 0 },
  { col: 1, row: 0 },
  { col: 2, row: 0 },
  { col: 0, row: 1 },
  { col: 1, row: 1 },
  { col: 2, row: 1 },
];

const TILE_WIDTH = 90;
const TILE_HEIGHT = 52; // isometric tile height (roughly TILE_WIDTH / √3)

function tileToPixel(col: number, row: number): { x: number; y: number } {
  // Isometric projection: diamond grid
  return {
    x: (col - row) * (TILE_WIDTH / 2),
    y: (col + row) * (TILE_HEIGHT / 2),
  };
}

// =============================================================================
// Single tile (floor diamond)
// =============================================================================

function FloorTile({ col, row, highlight }: { col: number; row: number; highlight?: boolean }) {
  const { x, y } = tileToPixel(col, row);

  return (
    <div
      className="absolute"
      style={{
        left: `calc(50% + ${x}px - ${TILE_WIDTH / 2}px)`,
        top: `${y + 20}px`,
        width: TILE_WIDTH,
        height: TILE_HEIGHT,
      }}
    >
      {/* Diamond shape via clip-path */}
      <div
        className={cn(
          'w-full h-full transition-colors duration-300',
          highlight
            ? 'bg-primary/8 dark:bg-primary/10'
            : (col + row) % 2 === 0
              ? 'bg-muted/40 dark:bg-muted/20'
              : 'bg-muted/25 dark:bg-muted/12'
        )}
        style={{
          clipPath: 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)',
        }}
      />
    </div>
  );
}

// =============================================================================
// Agent sprite on a tile
// =============================================================================

function AgentSprite({
  agent,
  tasks,
  col,
  row,
}: {
  agent: Agent;
  tasks: Task[];
  col: number;
  row: number;
}) {
  const config = getAgentConfig(agent.role);
  const { x, y } = tileToPixel(col, row);

  const agentSlug = agent.slug || agent.title.toLowerCase().replace(/\s+/g, '-');
  const assignedTasks = tasks.filter(t => t.status !== 'archived' && t.agent_slugs?.includes(agentSlug));
  const activeTask = assignedTasks[0];

  const isRunning = agent.latest_version_status === 'generating';
  const isPaused = agent.status === 'paused';
  const hasFailed = agent.latest_version_status === 'failed';

  const avatarState: 'working' | 'ready' | 'paused' | 'idle' | 'error' =
    isRunning ? 'working' : isPaused ? 'paused' : hasFailed ? 'error' : activeTask ? 'ready' : 'idle';

  const Icon = config.icon;

  return (
    <Link
      href={`/agents/${agent.id}`}
      className="absolute flex flex-col items-center group transition-transform hover:-translate-y-1 z-10"
      style={{
        left: `calc(50% + ${x}px - 32px)`,
        top: `${y - 24}px`, // offset up so avatar sits "on" the tile
        width: 64,
      }}
    >
      {/* Avatar */}
      <AgentAvatar
        state={avatarState}
        color={config.hex}
        size={48}
        icon={<Icon size={10} strokeWidth={2.5} />}
      />

      {/* Name label */}
      <span className="text-[9px] font-medium text-center mt-0.5 truncate w-16 text-foreground/80 group-hover:text-foreground">
        {agent.title.replace(' Agent', '').replace(' Bot', '')}
      </span>

      {/* Active task indicator */}
      {activeTask && (
        <span className="text-[7px] text-muted-foreground/40 truncate w-16 text-center">
          {activeTask.title}
        </span>
      )}
    </Link>
  );
}

// =============================================================================
// Mobile fallback — horizontal scroll strip
// =============================================================================

function MobileAgentStrip({ agents, tasks }: { agents: Agent[]; tasks: Task[] }) {
  return (
    <div className="flex gap-3 overflow-x-auto pb-2 -mx-2 px-2 scrollbar-hide">
      {agents.map(agent => {
        const config = getAgentConfig(agent.role);
        const agentSlug = agent.slug || agent.title.toLowerCase().replace(/\s+/g, '-');
        const assignedTasks = tasks.filter(t => t.status !== 'archived' && t.agent_slugs?.includes(agentSlug));
        const activeTask = assignedTasks[0];
        const isRunning = agent.latest_version_status === 'generating';
        const isPaused = agent.status === 'paused';
        const hasFailed = agent.latest_version_status === 'failed';
        const avatarState: 'working' | 'ready' | 'paused' | 'idle' | 'error' =
          isRunning ? 'working' : isPaused ? 'paused' : hasFailed ? 'error' : activeTask ? 'ready' : 'idle';
        const Icon = config.icon;

        return (
          <Link
            key={agent.id}
            href={`/agents/${agent.id}`}
            className="flex flex-col items-center shrink-0"
          >
            <AgentAvatar state={avatarState} color={config.hex} size={40} icon={<Icon size={9} strokeWidth={2.5} />} />
            <span className="text-[9px] font-medium mt-0.5 truncate w-12 text-center">
              {agent.title.replace(' Agent', '').replace(' Bot', '')}
            </span>
          </Link>
        );
      })}
    </div>
  );
}

// =============================================================================
// Main IsometricRoom
// =============================================================================

interface IsometricRoomProps {
  agents: Agent[];
  tasks: Task[];
  loading: boolean;
}

export function IsometricRoom({ agents, tasks, loading }: IsometricRoomProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (agents.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="text-xs text-muted-foreground/30">Setting up your team...</p>
      </div>
    );
  }

  // Calculate room dimensions based on tile count
  const roomHeight = (TILE_POSITIONS.length > 3 ? 2 : 1) * TILE_HEIGHT + 120;

  return (
    <>
      {/* Desktop: Isometric room */}
      <div className="hidden md:block mb-4">
        <div
          className="relative mx-auto"
          style={{ height: roomHeight, maxWidth: 420 }}
        >
          {/* Floor tiles */}
          {TILE_POSITIONS.map(({ col, row }, i) => (
            <FloorTile
              key={`tile-${col}-${row}`}
              col={col}
              row={row}
              highlight={i < agents.length && agents[i]?.latest_version_status === 'generating'}
            />
          ))}

          {/* Agent sprites */}
          {agents.slice(0, 6).map((agent, i) => {
            const pos = TILE_POSITIONS[i];
            if (!pos) return null;
            return (
              <AgentSprite
                key={agent.id}
                agent={agent}
                tasks={tasks}
                col={pos.col}
                row={pos.row}
              />
            );
          })}
        </div>
      </div>

      {/* Mobile: Horizontal scroll strip */}
      <div className="md:hidden mb-3">
        <MobileAgentStrip agents={agents} tasks={tasks} />
      </div>
    </>
  );
}
