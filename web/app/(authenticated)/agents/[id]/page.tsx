'use client';

/**
 * Agent Identity Page — ADR-139
 *
 * Reference surface for agent identity and development. Not a working surface.
 * Left: AGENT.md content + memory browser
 * Right: archetype, assigned tasks, development stats, actions
 *
 * No dedicated chat — agent steering happens via workfloor TP or task-scoped TP.
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import {
  Loader2,
  ChevronLeft,
  FileText,
  Play,
  Pause,
  Archive,
  FlaskConical,
  TrendingUp,
  Users,
  MessageCircle,
  BookOpen,
  ChevronRight,
  ChevronDown,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import ReactMarkdown from 'react-markdown';
import type { Agent, AgentRun, AgentMemory } from '@/types';

// =============================================================================
// Archetype mapping (shared with workfloor + agents list)
// =============================================================================

const ARCHETYPE_CONFIG: Record<string, { icon: typeof FlaskConical; color: string; label: string }> = {
  // Primary ADR-140 types
  research:   { icon: FlaskConical,   color: 'text-blue-500',   label: 'Research Agent' },
  content:    { icon: FileText,       color: 'text-purple-500', label: 'Content Agent' },
  marketing:  { icon: TrendingUp,     color: 'text-pink-500',   label: 'Marketing Agent' },
  crm:        { icon: Users,          color: 'text-orange-500', label: 'CRM Agent' },
  slack_bot:  { icon: MessageCircle,  color: 'text-teal-500',   label: 'Slack Bot' },
  notion_bot: { icon: BookOpen,       color: 'text-indigo-500', label: 'Notion Bot' },
  // Legacy → new type mappings
  briefer:    { icon: FlaskConical,   color: 'text-blue-500',   label: 'Research Agent' },
  monitor:    { icon: FlaskConical,   color: 'text-blue-500',   label: 'Research Agent' },
  scout:      { icon: FlaskConical,   color: 'text-blue-500',   label: 'Research Agent' },
  digest:     { icon: FlaskConical,   color: 'text-blue-500',   label: 'Research Agent' },
  researcher: { icon: FlaskConical,   color: 'text-blue-500',   label: 'Research Agent' },
  analyst:    { icon: FlaskConical,   color: 'text-blue-500',   label: 'Research Agent' },
  synthesize: { icon: FlaskConical,   color: 'text-blue-500',   label: 'Research Agent' },
  custom:     { icon: FlaskConical,   color: 'text-blue-500',   label: 'Research Agent' },
  drafter:    { icon: FileText,       color: 'text-purple-500', label: 'Content Agent' },
  writer:     { icon: FileText,       color: 'text-purple-500', label: 'Content Agent' },
  planner:    { icon: FileText,       color: 'text-purple-500', label: 'Content Agent' },
  prepare:    { icon: FileText,       color: 'text-purple-500', label: 'Content Agent' },
};

function getArchetype(role: string) {
  return ARCHETYPE_CONFIG[role] || ARCHETYPE_CONFIG.research;
}

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

// =============================================================================
// Memory Section (expandable)
// =============================================================================

function MemorySection({ title, content }: { title: string; content: string | null | undefined }) {
  const [open, setOpen] = useState(false);
  if (!content?.trim()) return null;

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-muted-foreground hover:bg-muted/50 transition-colors"
      >
        <span>{title}</span>
        <ChevronDown className={cn('w-3.5 h-3.5 transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="px-3 pb-3 text-xs text-muted-foreground/80">
          <div className="prose prose-xs dark:prose-invert max-w-none">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Main Page
// =============================================================================

export default function AgentIdentityPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [agent, setAgent] = useState<Agent | null>(null);
  const [versions, setVersions] = useState<AgentRun[]>([]);

  const loadAgent = useCallback(async () => {
    try {
      const detail = await api.agents.get(id);
      setAgent(detail.agent);
      setVersions(detail.versions);
    } catch (err) {
      console.error('Failed to load agent:', err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadAgent();
  }, [loadAgent]);

  const handleTogglePause = async () => {
    if (!agent) return;
    const newStatus = agent.status === 'paused' ? 'active' : 'paused';
    try {
      await api.agents.update(id, { status: newStatus });
      setAgent({ ...agent, status: newStatus });
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const handleArchive = async () => {
    if (!agent) return;
    try {
      await api.agents.delete(id);
      router.push('/agents');
    } catch (err) {
      console.error('Failed to archive agent:', err);
    }
  };

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
        <Link href="/agents" className="text-sm text-primary hover:underline">
          Back to Agents
        </Link>
      </div>
    );
  }

  const archetype = getArchetype(agent.role);
  const Icon = archetype.icon;
  const memory = agent.agent_memory;
  const totalRuns = versions.length;
  const deliveredRuns = versions.filter(v => v.status === 'delivered').length;
  const approvalRate = totalRuns > 0 ? Math.round((deliveredRuns / totalRuns) * 100) : 0;

  return (
    <div className="h-full flex flex-col lg:flex-row overflow-hidden">
      {/* Left: Identity + Memory */}
      <div className="flex-1 overflow-y-auto">
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-border">
          <Link
            href="/workfloor"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
          >
            <ChevronLeft className="w-4 h-4" />
            Workfloor
          </Link>

          <div className="flex items-center gap-4">
            <div className={cn(
              'w-12 h-12 rounded-xl flex items-center justify-center border',
              'bg-background',
            )}>
              <Icon className={cn('w-6 h-6', archetype.color)} />
            </div>
            <div>
              <h1 className="text-xl font-medium">{agent.title}</h1>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span>{archetype.label}</span>
                <span className="text-muted-foreground/30">|</span>
                <span className={cn(
                  agent.status === 'paused' ? 'text-amber-500' : 'text-green-500'
                )}>
                  {agent.status === 'paused' ? 'Paused' : 'Active'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Agent instructions / description */}
        <div className="px-6 py-6 space-y-6">
          {agent.agent_instructions && (
            <div>
              <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Instructions</h2>
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown>{agent.agent_instructions}</ReactMarkdown>
              </div>
            </div>
          )}

          {agent.description && (
            <div>
              <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Description</h2>
              <p className="text-sm text-muted-foreground">{agent.description}</p>
            </div>
          )}

          {/* Memory browser */}
          <div>
            <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">Memory</h2>
            <div className="space-y-2">
              {memory?.observations && memory.observations.length > 0 && (
                <MemorySection
                  title={`Observations (${memory.observations.length})`}
                  content={memory.observations.map(o => `- **${o.date}**: ${o.note}`).join('\n')}
                />
              )}
              <MemorySection title="Preferences" content={memory?.preferences} />
              <MemorySection title="Supervisor Notes" content={memory?.supervisor_notes} />
              {memory?.review_log && memory.review_log.length > 0 && (
                <MemorySection
                  title={`Review Log (${memory.review_log.length})`}
                  content={memory.review_log.map(r => `- **${r.date}** [${r.action}]: ${r.note}`).join('\n')}
                />
              )}
              {!memory?.observations?.length && !memory?.preferences && !memory?.supervisor_notes && !memory?.review_log?.length && (
                <p className="text-xs text-muted-foreground/50">No memory accumulated yet.</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Right: Identity card + tasks + stats + actions */}
      <div className="w-full lg:w-[360px] border-t lg:border-t-0 lg:border-l border-border overflow-y-auto bg-muted/20">
        <div className="p-5 space-y-6">
          {/* Identity card */}
          <div>
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">Agent Identity</h3>
            <div className="flex items-center gap-3 p-3 rounded-lg border border-border bg-background">
              <Icon className={cn('w-5 h-5', archetype.color)} />
              <div>
                <div className="text-sm font-medium">{agent.title}</div>
                <div className="text-[11px] text-muted-foreground">{archetype.label}</div>
              </div>
            </div>
          </div>

          {/* Development stats */}
          <div>
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">Development</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-lg border border-border bg-background">
                <div className="text-lg font-medium">{totalRuns}</div>
                <div className="text-[11px] text-muted-foreground">Total runs</div>
              </div>
              <div className="p-3 rounded-lg border border-border bg-background">
                <div className="text-lg font-medium">{approvalRate}%</div>
                <div className="text-[11px] text-muted-foreground">Delivery rate</div>
              </div>
              <div className="p-3 rounded-lg border border-border bg-background col-span-2">
                <div className="text-sm font-medium">
                  {agent.created_at ? `Since ${new Date(agent.created_at).toLocaleDateString()}` : 'Unknown'}
                </div>
                <div className="text-[11px] text-muted-foreground">
                  {agent.last_run_at ? `Last run: ${formatRelativeTime(agent.last_run_at)}` : 'Never run'}
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div>
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">Actions</h3>
            <div className="space-y-2">
              <button
                onClick={handleTogglePause}
                className={cn(
                  'w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg border transition-colors',
                  agent.status === 'paused'
                    ? 'border-green-500/30 text-green-600 hover:bg-green-500/10'
                    : 'border-amber-500/30 text-amber-600 hover:bg-amber-500/10'
                )}
              >
                {agent.status === 'paused' ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
                {agent.status === 'paused' ? 'Resume Agent' : 'Pause Agent'}
              </button>
              <button
                onClick={handleArchive}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-red-500/20 text-red-500 hover:bg-red-500/10 transition-colors"
              >
                <Archive className="w-4 h-4" />
                Archive Agent
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
