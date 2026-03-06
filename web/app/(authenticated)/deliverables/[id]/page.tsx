'use client';

/**
 * ADR-091: Deliverable Workspace
 *
 * Chat-first layout with drawer overlay:
 * - Main: scoped TP chat (full width) with inline version preview
 * - Drawer: Settings | Versions | Memory | Instructions | Sessions tabs
 * - Header: breadcrumb + identity chip + mode badge + active/paused toggle + drawer trigger
 *
 * Chat is scoped via surface_context { type: 'deliverable-detail', deliverableId }
 * which sets deliverable_id on the chat_sessions row (ADR-087).
 *
 * Sub-components extracted to web/components/deliverables/:
 * - DeliverableVersionDisplay.tsx (VersionsPanel, InlineVersionCard, VersionPreview, SourcePills)
 * - DeliverableDrawerPanels.tsx (MemoryPanel, InstructionsPanel, SessionsPanel)
 * - DeliverableChatArea.tsx (DeliverableChatArea)
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
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [running, setRunning] = useState(false);

  // Instructions editor
  const [instructions, setInstructions] = useState('');
  const [instructionsSaving, setInstructionsSaving] = useState(false);
  const [instructionsSaved, setInstructionsSaved] = useState(false);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadDeliverable = useCallback(async () => {
    try {
      const [detail, sessionData] = await Promise.all([
        api.deliverables.get(id),
        api.deliverables.listSessions(id).catch(() => []),
      ]);
      setDeliverable(detail.deliverable);
      setVersions(detail.versions);
      setInstructions(detail.deliverable.deliverable_instructions || '');
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
    try {
      await api.deliverables.run(id);
      await loadDeliverable();
      setSelectedIdx(0);
    } catch (err) {
      console.error('Failed to run deliverable:', err);
    } finally {
      setRunning(false);
    }
  };

  const handleInstructionsChange = (value: string) => {
    setInstructions(value);
    setInstructionsSaved(false);
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => saveInstructions(value), 2000);
  };

  const saveInstructions = async (value: string) => {
    if (!deliverable) return;
    setInstructionsSaving(true);
    try {
      await api.deliverables.update(id, { deliverable_instructions: value });
      setDeliverable({ ...deliverable, deliverable_instructions: value });
      setInstructionsSaved(true);
      setTimeout(() => setInstructionsSaved(false), 3000);
    } catch (err) {
      console.error('Failed to save instructions:', err);
    } finally {
      setInstructionsSaving(false);
    }
  };

  const handleInstructionsBlur = () => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    if (instructions !== (deliverable?.deliverable_instructions || '')) {
      saveInstructions(instructions);
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

  // ==========================================================================
  // Panel tabs
  // ==========================================================================

  const panelTabs: WorkspacePanelTab[] = [
    {
      id: 'settings',
      label: 'Settings',
      content: (
        <DeliverableSettingsPanel
          deliverable={deliverable}
          onSaved={(updated) => {
            setDeliverable(updated);
            setInstructions(updated.deliverable_instructions || '');
          }}
          onArchived={() => router.push('/deliverables')}
        />
      ),
    },
    {
      id: 'versions',
      label: `Versions${versions.length > 0 ? ` (${versions.length})` : ''}`,
      content: (
        <VersionsPanel
          versions={versions}
          selectedIdx={selectedIdx}
          onSelect={setSelectedIdx}
        />
      ),
    },
    {
      id: 'memory',
      label: `Memory${observations.length > 0 ? ` (${observations.length})` : ''}`,
      content: <MemoryPanel deliverable={deliverable} />,
    },
    {
      id: 'instructions',
      label: 'Instructions',
      content: (
        <InstructionsPanel
          instructions={instructions}
          onChange={handleInstructionsChange}
          onBlur={handleInstructionsBlur}
          saving={instructionsSaving}
          saved={instructionsSaved}
        />
      ),
    },
    {
      id: 'sessions',
      label: 'Sessions',
      content: <SessionsPanel sessions={sessions} />,
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
        panelDefaultOpen={false}
      >
        <DeliverableChatArea
          deliverableId={id}
          deliverableTitle={deliverable.title}
          versions={versions}
          selectedIdx={selectedIdx}
          onSelectIdx={setSelectedIdx}
          deliverable={deliverable}
          onRunNow={handleRunNow}
          running={running}
        />
    </WorkspaceLayout>
  );
}
