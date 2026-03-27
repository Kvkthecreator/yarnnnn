'use client';

/**
 * IsometricRoom — Habbo Hotel-inspired isometric agent display
 *
 * A proper isometric room with:
 * - Large tiled floor with depth and grid lines
 * - Agents spaced generously on tiles with ground shadows
 * - Clickable sprites with state-based animations (via AgentAvatar)
 * - Mobile (<768px) falls back to horizontal scroll strip
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
// Agent type → color + icon
// =============================================================================

const AGENT_STYLE: Record<string, { hex: string; icon: typeof FlaskConical }> = {
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

function getStyle(role: string) {
  return AGENT_STYLE[role] || AGENT_STYLE.custom;
}

// =============================================================================
// Isometric grid math
// =============================================================================

// Room is a 4×3 diamond grid (wider than tall). Agents on inner tiles.
const GRID_COLS = 4;
const GRID_ROWS = 3;
const TILE_W = 130; // px width of one tile — generous spacing for characters
const TILE_H = 65;  // px height (half width for true isometric)

function isoToScreen(col: number, row: number) {
  // Standard isometric: x = (col - row) * halfW, y = (col + row) * halfH
  const halfW = TILE_W / 2;
  const halfH = TILE_H / 2;
  return {
    x: (col - row) * halfW,
    y: (col + row) * halfH,
  };
}

// Agent positions on the grid (spread across inner tiles)
// 6 agents arranged in a staggered pattern for visual interest
const AGENT_TILES: [number, number][] = [
  [0, 0],
  [2, 0],
  [1, 1],
  [3, 1],
  [0, 2],
  [2, 2],
];

// Floor tiles: fill the full grid (including empty tiles for floor surface)
const FLOOR_TILES: [number, number][] = [];
for (let r = 0; r < GRID_ROWS; r++) {
  for (let c = 0; c < GRID_COLS; c++) {
    FLOOR_TILES.push([c, r]);
  }
}

// Room dimensions in screen space
const roomScreenWidth = (GRID_COLS + GRID_ROWS) * (TILE_W / 2);
const roomScreenHeight = (GRID_COLS + GRID_ROWS) * (TILE_H / 2);
const ROOM_PADDING_TOP = 70; // space above for avatars that stick up
const ROOM_PADDING_BOTTOM = 40;
const ROOM_TOTAL_HEIGHT = roomScreenHeight + ROOM_PADDING_TOP + ROOM_PADDING_BOTTOM + 30;

// Center offset: shift so the (0,0) tile's center is at the visual center-top
const centerX = roomScreenWidth / 2;

// =============================================================================
// Floor tile
// =============================================================================

function FloorTile({ col, row, occupied, working }: { col: number; row: number; occupied: boolean; working: boolean }) {
  const { x, y } = isoToScreen(col, row);

  const isLight = (col + row) % 2 === 0;

  return (
    <div
      className="absolute pointer-events-none"
      style={{
        left: centerX + x - TILE_W / 2,
        top: ROOM_PADDING_TOP + y,
        width: TILE_W,
        height: TILE_H,
      }}
    >
      {/* Tile face */}
      <div
        className={cn(
          'w-full h-full border transition-colors duration-500',
          working
            ? 'bg-primary/12 border-primary/20 dark:bg-primary/15 dark:border-primary/25'
            : occupied
              ? isLight
                ? 'bg-muted/50 border-border/30 dark:bg-muted/25 dark:border-border/20'
                : 'bg-muted/35 border-border/20 dark:bg-muted/18 dark:border-border/15'
              : isLight
                ? 'bg-muted/30 border-border/15 dark:bg-muted/12 dark:border-border/10'
                : 'bg-muted/20 border-border/10 dark:bg-muted/8 dark:border-border/8'
        )}
        style={{
          clipPath: 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)',
        }}
      />
    </div>
  );
}

// =============================================================================
// Agent on a tile
// =============================================================================

function AgentOnTile({ agent, tasks, col, row }: {
  agent: Agent;
  tasks: Task[];
  col: number;
  row: number;
}) {
  const style = getStyle(agent.role);
  const { x, y } = isoToScreen(col, row);

  const agentSlug = agent.slug || agent.title.toLowerCase().replace(/\s+/g, '-');
  const assignedTasks = tasks.filter(t => t.status !== 'archived' && t.agent_slugs?.includes(agentSlug));
  const activeTask = assignedTasks[0];

  const isRunning = agent.latest_version_status === 'generating';
  const isPaused = agent.status === 'paused';
  const hasFailed = agent.latest_version_status === 'failed';

  const avatarState: 'working' | 'ready' | 'paused' | 'idle' | 'error' =
    isRunning ? 'working' : isPaused ? 'paused' : hasFailed ? 'error' : activeTask ? 'ready' : 'idle';

  const Icon = style.icon;
  const AVATAR_SIZE = 72;
  const spriteWidth = 90;

  return (
    <Link
      href={`/agents/${agent.id}`}
      className="absolute flex flex-col items-center group z-10"
      style={{
        left: centerX + x - spriteWidth / 2,
        top: ROOM_PADDING_TOP + y - 62, // avatar stands above tile center
        width: spriteWidth,
      }}
    >
      {/* Ground shadow — ellipse on the floor */}
      <div
        className="absolute rounded-full blur-[4px]"
        style={{
          width: 44,
          height: 14,
          backgroundColor: style.hex,
          opacity: 0.15,
          bottom: 16,
          left: '50%',
          transform: 'translateX(-50%)',
        }}
      />

      {/* Role badge — small icon floating top-right */}
      <div
        className="absolute flex items-center justify-center rounded-full z-20 border-2 border-background"
        style={{
          width: 20,
          height: 20,
          backgroundColor: style.hex,
          top: 0,
          right: 6,
          opacity: isPaused ? 0.3 : 0.85,
        }}
      >
        <Icon size={9} strokeWidth={2.5} color="white" />
      </div>

      {/* Character avatar — eyes mode (no icon = shows eyes) */}
      <div className="transition-transform duration-200 group-hover:-translate-y-2">
        <AgentAvatar
          state={avatarState}
          color={style.hex}
          size={AVATAR_SIZE}
        />
      </div>

      {/* Name */}
      <span className="text-[10px] font-medium text-center truncate w-full text-foreground/70 group-hover:text-foreground transition-colors">
        {agent.title.replace(' Agent', '').replace(' Bot', '')}
      </span>

      {/* Active task */}
      {activeTask && (
        <span className="text-[8px] text-muted-foreground/40 truncate w-full text-center leading-tight">
          {activeTask.title}
        </span>
      )}
    </Link>
  );
}

// =============================================================================
// Mobile fallback
// =============================================================================

function MobileStrip({ agents, tasks }: { agents: Agent[]; tasks: Task[] }) {
  return (
    <div className="flex gap-4 overflow-x-auto pb-2 px-1 scrollbar-hide">
      {agents.map(agent => {
        const s = getStyle(agent.role);
        const agentSlug = agent.slug || agent.title.toLowerCase().replace(/\s+/g, '-');
        const assignedTasks = tasks.filter(t => t.status !== 'archived' && t.agent_slugs?.includes(agentSlug));
        const activeTask = assignedTasks[0];
        const isRunning = agent.latest_version_status === 'generating';
        const isPaused = agent.status === 'paused';
        const hasFailed = agent.latest_version_status === 'failed';
        const avatarState: 'working' | 'ready' | 'paused' | 'idle' | 'error' =
          isRunning ? 'working' : isPaused ? 'paused' : hasFailed ? 'error' : activeTask ? 'ready' : 'idle';
        const Icon = s.icon;

        return (
          <Link key={agent.id} href={`/agents/${agent.id}`} className="flex flex-col items-center shrink-0">
            <AgentAvatar state={avatarState} color={s.hex} size={40} icon={<Icon size={9} strokeWidth={2.5} />} />
            <span className="text-[9px] font-medium mt-0.5 truncate w-14 text-center">
              {agent.title.replace(' Agent', '').replace(' Bot', '')}
            </span>
          </Link>
        );
      })}
    </div>
  );
}

// =============================================================================
// Main export
// =============================================================================

interface IsometricRoomProps {
  agents: Agent[];
  tasks: Task[];
  loading: boolean;
}

export function IsometricRoom({ agents, tasks, loading }: IsometricRoomProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ height: ROOM_TOTAL_HEIGHT }}>
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (agents.length === 0) {
    return (
      <div className="flex items-center justify-center py-10">
        <p className="text-xs text-muted-foreground/30">Setting up your team...</p>
      </div>
    );
  }

  // Build set of occupied tile positions for floor highlighting
  const occupiedSet = new Set(
    agents.slice(0, 6).map((_, i) => {
      const t = AGENT_TILES[i];
      return t ? `${t[0]},${t[1]}` : '';
    })
  );
  const workingSet = new Set(
    agents.slice(0, 6)
      .map((a, i) => a.latest_version_status === 'generating' ? AGENT_TILES[i] : null)
      .filter(Boolean)
      .map(t => `${t![0]},${t![1]}`)
  );

  return (
    <>
      {/* Desktop: Isometric room — fills available width, centered */}
      <div className="hidden md:block mb-2 px-4">
        <div
          className="relative mx-auto"
          style={{
            width: '100%',
            maxWidth: roomScreenWidth + 40,
            height: ROOM_TOTAL_HEIGHT,
          }}
        >
          {/* Floor tiles */}
          {FLOOR_TILES.map(([c, r]) => (
            <FloorTile
              key={`${c}-${r}`}
              col={c}
              row={r}
              occupied={occupiedSet.has(`${c},${r}`)}
              working={workingSet.has(`${c},${r}`)}
            />
          ))}

          {/* Agents on tiles */}
          {agents.slice(0, 6).map((agent, i) => {
            const tile = AGENT_TILES[i];
            if (!tile) return null;
            return (
              <AgentOnTile
                key={agent.id}
                agent={agent}
                tasks={tasks}
                col={tile[0]}
                row={tile[1]}
              />
            );
          })}
        </div>
      </div>

      {/* Mobile: Horizontal strip */}
      <div className="md:hidden mb-3">
        <MobileStrip agents={agents} tasks={tasks} />
      </div>
    </>
  );
}
