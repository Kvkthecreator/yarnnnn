'use client';

/**
 * ADR-091: Agent Workspace
 *
 * Chat-first layout with persistent right panel:
 * - Main: scoped TP chat (left, full height)
 * - Panel: persistent right panel (≥lg) with tabs: Versions | Instructions | Memory | Sessions | Settings
 * - Header: breadcrumb + identity chip (platform icon) + schedule subtitle + active/paused toggle + panel toggle
 *
 * Versions display has moved from inline (above chat) to the panel.
 * Panel defaults to open with Versions tab showing the latest version preview.
 *
 * Chat is scoped via surface_context { type: 'agent-detail', agentId }
 * which sets agent_id on the chat_sessions row (ADR-087).
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import {
  Loader2,
  Play,
  Pause,
  ChevronLeft,
  FileText,
  Globe,
  Brain,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { getPlatformIcon } from '@/components/ui/PlatformIcons';
import { SKILL_LABELS } from '@/lib/constants/agents';
import { AgentSettingsPanel } from '@/components/agents/AgentSettingsPanel';
import { WorkspaceLayout, WorkspacePanelTab } from '@/components/desk/WorkspaceLayout';
import { RunsPanel } from '@/components/agents/AgentRunDisplay';
import { MemoryPanel, InstructionsPanel, SessionsPanel } from '@/components/agents/AgentDrawerPanels';
import { AgentChatArea } from '@/components/agents/AgentChatArea';
import type { Agent, AgentRun, AgentSession, RenderedOutput } from '@/types';

// =============================================================================
// Helpers: platform icon (source-first, AGENT-PRESENTATION-PRINCIPLES.md)
// =============================================================================

function getAgentPlatformIcon(agent: Agent): React.ReactNode {
  const providers: Record<string, true> = {};
  for (const s of agent.sources ?? []) {
    const p = s.provider as string | undefined;
    if (p) {
      if (p === 'google') {
        const rid = s.resource_id;
        if (rid && (['INBOX', 'SENT', 'IMPORTANT', 'STARRED'].includes(rid.toUpperCase()) || rid.startsWith('label:'))) {
          providers['gmail'] = true;
        } else {
          providers['calendar'] = true;
        }
      } else {
        providers[p] = true;
      }
    }
  }
  const keys = Object.keys(providers);
  if (keys.length === 0) {
    if (agent.skill === 'research') return <Globe className="w-4 h-4" />;
    return <Brain className="w-4 h-4" />;
  }
  if (keys.length === 1) return getPlatformIcon(keys[0], 'w-4 h-4');
  return (
    <div className="flex items-center -space-x-1">
      {keys.slice(0, 2).map((p) => (
        <span key={p} className="inline-block">{getPlatformIcon(p, 'w-3.5 h-3.5')}</span>
      ))}
    </div>
  );
}

function getScheduleSummary(agent: Agent): string | null {
  const s = agent.schedule;
  if (!s?.frequency) return null;
  const time = s.time || '09:00';
  let timeStr = time;
  try {
    const [hour, minute] = time.split(':').map(Number);
    const ampm = hour >= 12 ? 'pm' : 'am';
    const h12 = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour;
    timeStr = `${h12}:${minute.toString().padStart(2, '0')}${ampm}`;
  } catch { /* keep original */ }
  const skillLabel = SKILL_LABELS[agent.skill] || agent.skill;
  switch (s.frequency) {
    case 'daily': return `${skillLabel} · Daily ${timeStr}`;
    case 'weekly': {
      const day = s.day ? s.day.charAt(0).toUpperCase() + s.day.slice(1, 3) : 'Mon';
      return `${skillLabel} · ${day} ${timeStr}`;
    }
    case 'biweekly': return `${skillLabel} · Biweekly`;
    case 'monthly': return `${skillLabel} · Monthly`;
    default: return skillLabel;
  }
}

// =============================================================================
// Main Component
// =============================================================================

export default function AgentWorkspacePage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();

  // Data
  const [loading, setLoading] = useState(true);
  const [agent, setAgent] = useState<Agent | null>(null);
  const [versions, setVersions] = useState<AgentRun[]>([]);
  const [sessions, setSessions] = useState<AgentSession[]>([]);
  const [renderedOutputs, setRenderedOutputs] = useState<RenderedOutput[]>([]);

  // UI
  const [running, setRunning] = useState(false);

  // Ref for prefilling chat input from drawer (e.g. "Edit in chat" button)
  const prefillChatRef = useRef<((text: string) => void) | null>(null);

  const loadAgent = useCallback(async () => {
    try {
      const [detail, sessionData] = await Promise.all([
        api.agents.get(id),
        api.agents.listSessions(id).catch(() => []),
      ]);
      setAgent(detail.agent);
      setVersions(detail.versions);
      setSessions(sessionData);
      setRenderedOutputs(detail.rendered_outputs || []);
    } catch (err) {
      console.error('Failed to load agent:', err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadAgent();
  }, [loadAgent]);

  // Lightweight sessions refresh — called after each TP turn completes
  const refreshSessions = useCallback(async () => {
    try {
      const sessionData = await api.agents.listSessions(id).catch(() => []);
      setSessions(sessionData);
    } catch { /* silent */ }
  }, [id]);

  const handleTogglePause = async () => {
    if (!agent) return;
    try {
      const newStatus = agent.status === 'paused' ? 'active' : 'paused';
      await api.agents.update(id, { status: newStatus });
      setAgent({ ...agent, status: newStatus });
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const handleRunNow = async () => {
    if (!agent) return;
    setRunning(true);

    // Optimistic: show a "generating" placeholder immediately
    const nextVersion = (versions[0]?.version_number ?? 0) + 1;
    const placeholder: AgentRun = {
      id: `generating-${Date.now()}`,
      agent_id: id,
      version_number: nextVersion,
      status: 'generating',
      created_at: new Date().toISOString(),
    };
    setVersions((prev) => [placeholder, ...prev]);

    try {
      await api.agents.run(id);
      await loadAgent();
    } catch (err) {
      console.error('Failed to run agent:', err);
      // Remove optimistic placeholder on failure
      setVersions((prev) => prev.filter((v) => v.id !== placeholder.id));
    } finally {
      setRunning(false);
    }
  };

  // ==========================================================================
  // Loading / Not found
  // ==========================================================================

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4">
        <FileText className="w-8 h-8 text-muted-foreground" />
        <p className="text-muted-foreground">Agent not found</p>
        <button onClick={() => router.push('/agents')} className="text-sm text-primary hover:underline">
          Back to Agents
        </button>
      </div>
    );
  }

  const memory = agent.agent_memory;
  const observations = memory?.observations || [];
  const reviewLog = memory?.review_log || [];
  const memoryCount = observations.length + reviewLog.length
    + (memory?.preferences ? 1 : 0) + (memory?.supervisor_notes ? 1 : 0);

  // ==========================================================================
  // Panel tabs
  // ==========================================================================

  const panelTabs: WorkspacePanelTab[] = [
    {
      id: 'runs',
      label: `Runs${versions.length > 0 ? ` (${versions.length})` : ''}`,
      content: (
        <RunsPanel
          versions={versions}
          agent={agent}
          onRunNow={handleRunNow}
          running={running}
          renderedOutputs={renderedOutputs}
        />
      ),
    },
    {
      id: 'instructions',
      label: 'Instructions',
      content: (
        <InstructionsPanel
          agent={agent}
          onEditInChat={() => prefillChatRef.current?.('I want to update the instructions for this agent')}
        />
      ),
    },
    {
      id: 'memory',
      label: `Memory${memoryCount > 0 ? ` (${memoryCount})` : ''}`,
      content: <MemoryPanel agent={agent} />,
    },
    {
      id: 'sessions',
      label: 'Sessions',
      content: <SessionsPanel sessions={sessions} />,
    },
    {
      id: 'settings',
      label: 'Settings',
      content: (
        <AgentSettingsPanel
          agent={agent}
          onSaved={(updated) => setAgent(updated)}
          onArchived={() => router.push('/agents')}
        />
      ),
    },
  ];

  // ==========================================================================
  // Header pieces
  // ==========================================================================

  const scheduleSummary = getScheduleSummary(agent);

  const inlineMeta = (
    <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
      {scheduleSummary && (
        <>
          <span>{scheduleSummary}</span>
          <span className="select-none">·</span>
        </>
      )}
      <button
        onClick={handleTogglePause}
        className={cn(
          'inline-flex items-center gap-1 hover:underline transition-colors',
          agent.status === 'paused'
            ? 'text-amber-600 dark:text-amber-400'
            : 'text-green-600 dark:text-green-400'
        )}
        title={agent.status === 'paused' ? 'Resume' : 'Pause'}
      >
        {agent.status === 'paused' ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
        {agent.status === 'paused' ? 'Paused' : 'Active'}
      </button>
    </span>
  );

  const breadcrumb = (
    <Link
      href="/agents"
      className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
    >
      <ChevronLeft className="w-4 h-4" />
      Agents
    </Link>
  );

  return (
    <WorkspaceLayout
        identity={{
          icon: getAgentPlatformIcon(agent),
          label: agent.title,
          badge: inlineMeta,
        }}
        breadcrumb={breadcrumb}
        panelTabs={panelTabs}
        panelDefaultOpen={true}
      >
        <AgentChatArea
          agentId={id}
          agentTitle={agent.title}
          onRunNow={handleRunNow}
          running={running}
          prefillChatRef={prefillChatRef}
          onTurnComplete={refreshSessions}
        />
    </WorkspaceLayout>
  );
}
