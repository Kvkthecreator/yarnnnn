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
import type { Deliverable, DeliverableVersion, DeliverableSession, RecipientContext, TemplateStructure } from '@/types';

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

  // Instructions panel fields (unified save: instructions + recipient + template)
  const [instructions, setInstructions] = useState('');
  const [recipientContext, setRecipientContext] = useState<RecipientContext>({});
  const [templateStructure, setTemplateStructure] = useState<TemplateStructure | undefined>(undefined);
  const [instructionsSaving, setInstructionsSaving] = useState(false);
  const [instructionsSaved, setInstructionsSaved] = useState(false);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Refs for latest values to avoid stale closures in debounced save
  const instructionsRef = useRef(instructions);
  const recipientRef = useRef(recipientContext);
  const templateRef = useRef(templateStructure);
  instructionsRef.current = instructions;
  recipientRef.current = recipientContext;
  templateRef.current = templateStructure;

  const loadDeliverable = useCallback(async () => {
    try {
      const [detail, sessionData] = await Promise.all([
        api.deliverables.get(id),
        api.deliverables.listSessions(id).catch(() => []),
      ]);
      setDeliverable(detail.deliverable);
      setVersions(detail.versions);
      setInstructions(detail.deliverable.deliverable_instructions || '');
      setRecipientContext(detail.deliverable.recipient_context || {});
      setTemplateStructure(detail.deliverable.template_structure);
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

  // Unified save for all instruction panel fields
  const saveInstructionFields = useCallback(async () => {
    if (!deliverable) return;
    setInstructionsSaving(true);
    try {
      const update = {
        deliverable_instructions: instructionsRef.current,
        recipient_context: recipientRef.current,
        template_structure: templateRef.current,
      };
      await api.deliverables.update(id, update);
      setDeliverable((prev) => prev ? { ...prev, ...update } : prev);
      setInstructionsSaved(true);
      setTimeout(() => setInstructionsSaved(false), 3000);
    } catch (err) {
      console.error('Failed to save instruction fields:', err);
    } finally {
      setInstructionsSaving(false);
    }
  }, [deliverable, id]);

  const scheduleSave = useCallback(() => {
    setInstructionsSaved(false);
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => saveInstructionFields(), 2000);
  }, [saveInstructionFields]);

  const handleInstructionsChange = (value: string) => {
    setInstructions(value);
    scheduleSave();
  };

  const handleRecipientChange = (value: RecipientContext) => {
    setRecipientContext(value);
    scheduleSave();
  };

  const handleTemplateChange = (value: TemplateStructure) => {
    setTemplateStructure(value);
    scheduleSave();
  };

  const handleInstructionFieldsBlur = () => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    // Save if any field has changed
    const instrChanged = instructionsRef.current !== (deliverable?.deliverable_instructions || '');
    const recipientChanged = JSON.stringify(recipientRef.current) !== JSON.stringify(deliverable?.recipient_context || {});
    const templateChanged = JSON.stringify(templateRef.current) !== JSON.stringify(deliverable?.template_structure);
    if (instrChanged || recipientChanged || templateChanged) {
      saveInstructionFields();
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
      id: 'settings',
      label: 'Settings',
      content: (
        <DeliverableSettingsPanel
          deliverable={deliverable}
          onSaved={(updated) => {
            // Preserve instruction panel fields — Settings no longer manages them
            setDeliverable({
              ...updated,
              deliverable_instructions: instructionsRef.current,
              recipient_context: recipientRef.current,
              template_structure: templateRef.current,
            });
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
      label: `Memory${memoryCount > 0 ? ` (${memoryCount})` : ''}`,
      content: <MemoryPanel deliverable={deliverable} />,
    },
    {
      id: 'instructions',
      label: 'Instructions',
      content: (
        <InstructionsPanel
          instructions={instructions}
          onInstructionsChange={handleInstructionsChange}
          onBlur={handleInstructionFieldsBlur}
          recipientContext={recipientContext}
          onRecipientChange={handleRecipientChange}
          templateStructure={templateStructure}
          onTemplateChange={handleTemplateChange}
          deliverableType={deliverable.deliverable_type}
          deliverableMemory={deliverable.deliverable_memory}
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
