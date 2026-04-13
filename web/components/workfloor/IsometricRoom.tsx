'use client';

/**
 * IsometricRoom — Habbo Hotel-inspired isometric agent display
 *
 * A proper isometric room with:
 * - Large tiled floor with depth and grid lines
 * - Agents spaced generously on tiles with ground shadows
 * - Clickable sprites with state-based animations (via AgentAvatar)
 * - Ambient floor effects: pulse wave + tile shimmer
 * - Mobile (<768px) falls back to horizontal scroll strip
 */

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { Loader2 } from 'lucide-react';
import {
  Brain,
  Bot,
  FlaskConical,
  FileText,
  FolderKanban,
  Layers3,
  Users,
  MessageCircle,
  TrendingUp,
} from 'lucide-react';
import type { Agent, Task } from '@/types';
import { AgentAvatar, TPAvatar } from '@/components/agents/AgentAvatar';
import { avatarColor, getAgentSlug, resolveRole } from '@/lib/agent-identity';
import { cn } from '@/lib/utils';

// =============================================================================
// Agent type → color + icon
// =============================================================================

const AGENT_ICON: Record<string, typeof FlaskConical> = {
  // v5 universal specialists (ADR-176)
  researcher: FlaskConical,
  analyst: TrendingUp,
  writer: FileText,
  tracker: FolderKanban,
  designer: Users,
  // synthesizer
  executive: Layers3,
  // platform bots
  slack_bot: MessageCircle,
  notion_bot: Bot,
  github_bot: Bot,
  // meta-cognitive
  thinking_partner: Brain,
  // v4 ICP legacy (backward compat)
  competitive_intel: FlaskConical,
  market_research: TrendingUp,
  business_dev: Users,
  operations: FolderKanban,
  marketing: FileText,
};

function getStyle(role: string) {
  const resolved = resolveRole(role);
  return {
    hex: avatarColor(resolved),
    icon: AGENT_ICON[resolved] || FolderKanban,
  };
}

// =============================================================================
// Isometric grid math
// =============================================================================

// Room is a 5×3 diamond grid — fills the left panel.
// screenWidth = (cols+rows) * tileW/2 = 8 * 100 = 800px
const GRID_COLS = 5;
const GRID_ROWS = 3;
const TILE_W = 200;
const TILE_H = 100;

function isoToScreen(col: number, row: number) {
  // Standard isometric: x = (col - row) * halfW, y = (col + row) * halfH
  const halfW = TILE_W / 2;
  const halfH = TILE_H / 2;
  return {
    x: (col - row) * halfW,
    y: (col + row) * halfH,
  };
}

// Agent positions on the grid — spread wide, TP gets center-front
const AGENT_TILES: [number, number][] = [
  [1, 0],
  [3, 0],
  [0, 1],
  [4, 1],
  [1, 2],
  [3, 2],
];
// TP position — center of middle row, slightly forward
const TP_TILE: [number, number] = [2, 1];

// Floor tiles: fill the full grid (including empty tiles for floor surface)
const FLOOR_TILES: [number, number][] = [];
for (let r = 0; r < GRID_ROWS; r++) {
  for (let c = 0; c < GRID_COLS; c++) {
    FLOOR_TILES.push([c, r]);
  }
}

// Room dimensions in screen space
const roomScreenHeight = (GRID_COLS + GRID_ROWS) * (TILE_H / 2);
const ROOM_PADDING_TOP = 80;
const ROOM_PADDING_BOTTOM = 50;
const ROOM_TOTAL_HEIGHT = roomScreenHeight + ROOM_PADDING_TOP + ROOM_PADDING_BOTTOM + 30;

// Center offset: compute from actual tile bounds to ensure visual centering
// Min x: tile (0, GRID_ROWS-1) = (0 - (GRID_ROWS-1)) * halfW
// Max x: tile (GRID_COLS-1, 0) = (GRID_COLS-1) * halfW + TILE_W
const halfW = TILE_W / 2;
const minScreenX = (0 - (GRID_ROWS - 1)) * halfW - halfW;
const maxScreenX = (GRID_COLS - 1) * halfW + halfW;
const centerX = -minScreenX; // shift so minScreenX maps to 0

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
      {/* Tile face with subtle shimmer */}
      <div
        className={cn(
          'w-full h-full border',
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

  const agentSlug = getAgentSlug(agent);
  const assignedTasks = tasks.filter(t => t.status !== 'archived' && t.agent_slugs?.includes(agentSlug));
  const activeTask = assignedTasks[0];

  const isRunning = agent.latest_version_status === 'generating';
  const isPaused = agent.status === 'paused';
  const hasFailed = agent.latest_version_status === 'failed';

  const avatarState: 'working' | 'ready' | 'paused' | 'idle' | 'error' =
    isRunning ? 'working' : isPaused ? 'paused' : hasFailed ? 'error' : activeTask ? 'ready' : 'idle';

  const Icon = style.icon;
  const AVATAR_SIZE = 80;
  const spriteWidth = 100;

  return (
    <Link
      href={`/agents?agent=${encodeURIComponent(agentSlug)}`}
      className="absolute flex flex-col items-center group z-10"
      style={{
        left: centerX + x - spriteWidth / 2,
        top: ROOM_PADDING_TOP + y - 68, // avatar stands above tile center
        width: spriteWidth,
      }}
    >
      {/* Ground shadow — ellipse on the floor */}
      <div
        className="absolute rounded-full blur-[5px]"
        style={{
          width: 50,
          height: 16,
          backgroundColor: style.hex,
          opacity: 0.15,
          bottom: 18,
          left: '50%',
          transform: 'translateX(-50%)',
        }}
      />

      {/* Role badge — small icon floating top-right */}
      <div
        className="absolute flex items-center justify-center rounded-full z-20 border-2 border-background"
        style={{
          width: 22,
          height: 22,
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
    <div className="flex gap-5 overflow-x-auto py-3 px-4 scrollbar-hide">
      {agents.map(agent => {
        const s = getStyle(agent.role);
        const agentSlug = getAgentSlug(agent);
        const assignedTasks = tasks.filter(t => t.status !== 'archived' && t.agent_slugs?.includes(agentSlug));
        const activeTask = assignedTasks[0];
        const isRunning = agent.latest_version_status === 'generating';
        const isPaused = agent.status === 'paused';
        const hasFailed = agent.latest_version_status === 'failed';
        const avatarState: 'working' | 'ready' | 'paused' | 'idle' | 'error' =
          isRunning ? 'working' : isPaused ? 'paused' : hasFailed ? 'error' : activeTask ? 'ready' : 'idle';

        // Short display name
        const shortName = agent.title
          .replace(' Agent', '')
          .replace(' Bot', '')
          .replace('Weekly ', '')
          .replace('Knowledge', 'Knowl.');

        return (
          <Link key={agent.id} href={`/agents?agent=${encodeURIComponent(agentSlug)}`} className="flex flex-col items-center shrink-0 w-16">
            <AgentAvatar state={avatarState} color={s.hex} size={48} />
            <span className="text-[10px] font-medium mt-1 truncate w-full text-center text-foreground/70">
              {shortName}
            </span>
            {activeTask && (
              <span className="text-[8px] text-muted-foreground/40 truncate w-full text-center">
                {activeTask.title.length > 12 ? activeTask.title.slice(0, 12) + '...' : activeTask.title}
              </span>
            )}
          </Link>
        );
      })}
    </div>
  );
}

// RoomActions removed (2026-03-30) — legacy pills replaced by panel-embedded action bar

// =============================================================================
// Main export
// =============================================================================

interface IsometricRoomProps {
  agents: Agent[];
  tasks: Task[];
  loading: boolean;
  collapsed?: boolean;
  onTPClick?: () => void;
  onAction?: (msg: string) => void;
}

export function IsometricRoom({ agents, tasks, loading, collapsed = false, onTPClick, onAction }: IsometricRoomProps) {
  // ALL hooks must be before any early return (React rules of hooks)
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  const ROOM_W = maxScreenX - minScreenX;
  const ROOM_H = ROOM_TOTAL_HEIGHT;

  useEffect(() => {
    const measure = () => {
      if (!containerRef.current) return;
      const available = containerRef.current.clientWidth;
      const s = Math.min(1.3, available / ROOM_W);
      setScale(s);
    };
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, [ROOM_W]);

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
  const occupiedSet = new Set([
    `${TP_TILE[0]},${TP_TILE[1]}`,
    ...agents.slice(0, 6).map((_, i) => {
      const t = AGENT_TILES[i];
      return t ? `${t[0]},${t[1]}` : '';
    }),
  ]);
  const workingSet = new Set(
    agents.slice(0, 6)
      .map((a, i) => a.latest_version_status === 'generating' ? AGENT_TILES[i] : null)
      .filter(Boolean)
      .map(t => `${t![0]},${t![1]}`)
  );

  const tpScreen = isoToScreen(TP_TILE[0], TP_TILE[1]);
  const tpSpriteW = 90;

  return (
    <>
      {/* Desktop: Isometric room — collapsible via parent, scales to fill */}
      <div ref={containerRef} className="hidden md:block overflow-hidden">
        {!collapsed && (
          <div
            style={{
              width: ROOM_W,
              height: ROOM_H,
              transform: `scale(${scale})`,
              transformOrigin: 'top center',
              marginLeft: 'auto',
              marginRight: 'auto',
              marginTop: 0,
              marginBottom: Math.min(0, -(ROOM_H * (1 - scale))),
            }}
            className="relative"
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

            {/* TP — center position, slightly distinct */}
            <button
              onClick={onTPClick}
              className="absolute flex flex-col items-center group z-10"
              style={{
                left: centerX + tpScreen.x - tpSpriteW / 2,
                top: ROOM_PADDING_TOP + tpScreen.y - 68,
                width: tpSpriteW,
              }}
            >
              {/* Ground shadow */}
              <div
                className="absolute rounded-full blur-[5px]"
                style={{
                  width: 50, height: 16,
                  backgroundColor: 'hsl(var(--primary))',
                  opacity: 0.12,
                  bottom: 18,
                  left: '50%',
                  transform: 'translateX(-50%)',
                }}
              />
              <div className="transition-transform duration-200 group-hover:-translate-y-2">
                <TPAvatar size={80} />
              </div>
              <span className="text-[10px] font-medium text-primary/70 group-hover:text-primary transition-colors">
                Orchestrator
              </span>
            </button>

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
        )}
      </div>

      {/* Mobile: Horizontal strip */}
      <div className="md:hidden border-b border-border/30">
        <MobileStrip agents={agents} tasks={tasks} />
      </div>
    </>
  );
}
