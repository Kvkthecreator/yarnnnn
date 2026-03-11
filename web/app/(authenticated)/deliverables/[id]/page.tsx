'use client';

/**
 * ADR-091: Deliverable Workspace
 *
 * Chat-first layout with persistent right panel:
 * - Main: scoped TP chat (left, full height)
 * - Panel: persistent right panel (≥lg) with tabs: Versions | Instructions | Memory | Sessions | Settings
 * - Header: breadcrumb + identity chip + mode badge + active/paused toggle + panel toggle
 *
 * Versions display has moved from inline (above chat) to the panel.
 * Panel defaults to open with Versions tab showing the latest version preview.
 *
 * Chat is scoped via surface_context { type: 'deliverable-detail', deliverableId }
 * which sets deliverable_id on the chat_sessions row (ADR-087).
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
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { DeliverableSettingsPanel } from '@/components/deliverables/DeliverableSettingsPanel';
import { WorkspaceLayout, WorkspacePanelTab } from '@/components/desk/WorkspaceLayout';
import { DeliverableModeBadge } from '@/components/deliverables/DeliverableModeBadge';
import { VersionsPanel } from '@/components/deliverables/DeliverableVersionDisplay';
import { MemoryPanel, InstructionsPanel, SessionsPanel } from '@/components/deliverables/DeliverableDrawerPanels';
import { DeliverableChatArea } from '@/components/deliverables/DeliverableChatArea';
import type { Deliverable, DeliverableVersion, DeliverableSession } from '@/types';

// =============================================================================
// Main Component
// =============================================================================

export default function DeliverableWorkspacePage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();

  // Data
  const [loading, setLoading] = useState(true);
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [versions, setVersions] = useState<DeliverableVersion[]>([]);
  const [sessions, setSessions] = useState<DeliverableSession[]>([]);

  // UI
  const [running, setRunning] = useState(false);

  // Ref for prefilling chat input from drawer (e.g. "Edit in chat" button)
  const prefillChatRef = useRef<((text: string) => void) | null>(null);

  const loadDeliverable = useCallback(async () => {
    try {
      const [detail, sessionData] = await Promise.all([
        api.deliverables.get(id),
        api.deliverables.listSessions(id).catch(() => []),
      ]);
      setDeliverable(detail.deliverable);
      setVersions(detail.versions);
      setSessions(sessionData);
    } catch (err) {
      console.error('Failed to load deliverable:', err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadDeliverable();
  }, [loadDeliverable]);

  const handleTogglePause = async () => {
    if (!deliverable) return;
    try {
      const newStatus = deliverable.status === 'paused' ? 'active' : 'paused';
      await api.deliverables.update(id, { status: newStatus });
      setDeliverable({ ...deliverable, status: newStatus });
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const handleRunNow = async () => {
    if (!deliverable) return;
    setRunning(true);

    // Optimistic: show a "generating" placeholder immediately
    const nextVersion = (versions[0]?.version_number ?? 0) + 1;
    const placeholder: DeliverableVersion = {
      id: `generating-${Date.now()}`,
      deliverable_id: id,
      version_number: nextVersion,
      status: 'generating',
      created_at: new Date().toISOString(),
    };
    setVersions((prev) => [placeholder, ...prev]);

    try {
      await api.deliverables.run(id);
      await loadDeliverable();
    } catch (err) {
      console.error('Failed to run deliverable:', err);
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

  if (!deliverable) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4">
        <FileText className="w-8 h-8 text-muted-foreground" />
        <p className="text-muted-foreground">Deliverable not found</p>
        <button onClick={() => router.push('/deliverables')} className="text-sm text-primary hover:underline">
          Back to Deliverables
        </button>
      </div>
    );
  }

  const memory = deliverable.deliverable_memory;
  const observations = memory?.observations || [];
  const reviewLog = memory?.review_log || [];
  const memoryCount = observations.length + reviewLog.length;

  // ==========================================================================
  // Panel tabs
  // ==========================================================================

  const panelTabs: WorkspacePanelTab[] = [
    {
      id: 'versions',
      label: `Versions${versions.length > 0 ? ` (${versions.length})` : ''}`,
      content: (
        <VersionsPanel
          versions={versions}
          deliverable={deliverable}
          onRunNow={handleRunNow}
          running={running}
        />
      ),
    },
    {
      id: 'instructions',
      label: 'Instructions',
      content: (
        <InstructionsPanel
          deliverable={deliverable}
          onEditInChat={() => prefillChatRef.current?.('I want to update the instructions for this deliverable')}
        />
      ),
    },
    {
      id: 'memory',
      label: `Memory${memoryCount > 0 ? ` (${memoryCount})` : ''}`,
      content: <MemoryPanel deliverable={deliverable} />,
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
        <DeliverableSettingsPanel
          deliverable={deliverable}
          onSaved={(updated) => setDeliverable(updated)}
          onArchived={() => router.push('/deliverables')}
        />
      ),
    },
  ];

  // ==========================================================================
  // Header pieces
  // ==========================================================================

  const inlineMeta = (
    <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <DeliverableModeBadge mode={deliverable.mode} variant="inline" />
      <span className="select-none">·</span>
      <button
        onClick={handleTogglePause}
        className={cn(
          'inline-flex items-center gap-1 hover:underline transition-colors',
          deliverable.status === 'paused'
            ? 'text-amber-600 dark:text-amber-400'
            : 'text-green-600 dark:text-green-400'
        )}
        title={deliverable.status === 'paused' ? 'Resume' : 'Pause'}
      >
        {deliverable.status === 'paused' ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
        {deliverable.status === 'paused' ? 'Paused' : 'Active'}
      </button>
    </span>
  );

  const breadcrumb = (
    <Link
      href="/deliverables"
      className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
    >
      <ChevronLeft className="w-4 h-4" />
      Deliverables
    </Link>
  );

  return (
    <WorkspaceLayout
        identity={{
          icon: <DeliverableModeBadge mode={deliverable.mode} variant="icon" />,
          label: deliverable.title,
          badge: inlineMeta,
        }}
        breadcrumb={breadcrumb}
        panelTabs={panelTabs}
        panelDefaultOpen={true}
      >
        <DeliverableChatArea
          deliverableId={id}
          deliverableTitle={deliverable.title}
          onRunNow={handleRunNow}
          running={running}
          prefillChatRef={prefillChatRef}
        />
    </WorkspaceLayout>
  );
}
