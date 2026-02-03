'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * DomainBrowser - Escape hatch to browse all data domains
 */

import { useState, useEffect } from 'react';
import { X, Loader2, AlertCircle, FileText, Folder, Brain, Briefcase, Plus } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import { DeskSurface, BrowserData, AttentionItem } from '@/types/desk';
import { formatDistanceToNow } from 'date-fns';

interface DomainBrowserProps {
  isOpen: boolean;
  onClose: () => void;
}

export function DomainBrowser({ isOpen, onClose }: DomainBrowserProps) {
  const { setSurface, attention } = useDesk();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<BrowserData | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadBrowserData();
    }
  }, [isOpen]);

  const loadBrowserData = async () => {
    setLoading(true);
    try {
      // Fetch all data in parallel
      const [deliverables, workResult, memories, documentsResult] = await Promise.all([
        api.deliverables.list().catch(() => []),
        api.work.listAll({ limit: 5 }).catch(() => ({ work: [] })),
        api.userMemories.list().catch(() => []),
        api.documents.list().catch(() => ({ documents: [] })),
      ]);

      setData({
        deliverables: (deliverables || []).slice(0, 10).map((d) => ({
          id: d.id,
          title: d.title,
          status: d.status,
          scheduleDescription: formatSchedule(d.schedule),
          nextRunAt: d.next_run_at,
        })),
        recentWork: (workResult.work || []).slice(0, 5).map((w) => ({
          id: w.id,
          title: w.task,
          status: w.status || 'completed',
          agentType: w.agent_type,
          completedAt: w.created_at,
        })),
        userMemoryCount: memories.length,
        deliverableContexts: [], // TODO: Aggregate from deliverables
        recentDocuments: (documentsResult.documents || []).slice(0, 3).map((d) => ({
          id: d.id,
          filename: d.filename,
          uploadedAt: d.created_at,
        })),
      });
    } catch (err) {
      console.error('Failed to load browser data:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatSchedule = (schedule: { frequency?: string; day?: string; time?: string } | undefined) => {
    if (!schedule) return 'No schedule';
    const { frequency, day, time } = schedule;
    if (frequency === 'weekly') return `${day || 'Weekly'} ${time || ''}`.trim();
    if (frequency === 'daily') return `Daily ${time || ''}`.trim();
    if (frequency === 'monthly') return `Monthly ${day || ''} ${time || ''}`.trim();
    return frequency || 'Custom';
  };

  const handleItemClick = (surface: DeskSurface) => {
    setSurface(surface);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <div className="absolute right-0 top-0 h-full w-80 bg-background border-l border-border shadow-xl overflow-y-auto">
        <div className="p-4">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="font-semibold">Browse</h2>
            <button onClick={onClose} className="p-1.5 hover:bg-muted rounded">
              <X className="w-4 h-4" />
            </button>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="space-y-6">
              {/* Needs Attention */}
              {attention.length > 0 && (
                <BrowserSection
                  icon={<AlertCircle className="w-4 h-4 text-amber-500" />}
                  title={`Needs Attention (${attention.length})`}
                >
                  {attention.map((item) => (
                    <BrowserItem
                      key={item.versionId}
                      title={item.title}
                      subtitle={`staged ${formatDistanceToNow(new Date(item.stagedAt), { addSuffix: false })} ago`}
                      onClick={() =>
                        handleItemClick({
                          type: 'deliverable-review',
                          deliverableId: item.deliverableId,
                          versionId: item.versionId,
                        })
                      }
                    />
                  ))}
                </BrowserSection>
              )}

              {/* Deliverables */}
              <BrowserSection
                icon={<Briefcase className="w-4 h-4" />}
                title="Deliverables"
              >
                {data?.deliverables.map((d) => (
                  <BrowserItem
                    key={d.id}
                    title={d.title}
                    subtitle={d.scheduleDescription}
                    badge={d.status === 'paused' ? 'Paused' : undefined}
                    onClick={() =>
                      handleItemClick({ type: 'deliverable-detail', deliverableId: d.id })
                    }
                  />
                ))}
                <BrowserAction
                  icon={<Plus className="w-3.5 h-3.5" />}
                  label="Create new deliverable"
                  onClick={() => {
                    onClose();
                    // Focus TP input - will be handled by idle state
                  }}
                />
              </BrowserSection>

              {/* Recent Work */}
              {data?.recentWork && data.recentWork.length > 0 && (
                <BrowserSection
                  icon={<Briefcase className="w-4 h-4" />}
                  title="Recent Work"
                >
                  {data.recentWork.slice(0, 3).map((w) => (
                    <BrowserItem
                      key={w.id}
                      title={w.title}
                      subtitle={`${w.agentType} • ${w.status}`}
                      onClick={() =>
                        handleItemClick({ type: 'work-output', workId: w.id })
                      }
                    />
                  ))}
                  <BrowserAction
                    label="View all work"
                    onClick={() => handleItemClick({ type: 'work-list' })}
                  />
                </BrowserSection>
              )}

              {/* Context */}
              <BrowserSection
                icon={<Brain className="w-4 h-4" />}
                title="Context"
              >
                <BrowserItem
                  title="About Me"
                  subtitle={`${data?.userMemoryCount || 0} memories`}
                  onClick={() =>
                    handleItemClick({ type: 'context-browser', scope: 'user' })
                  }
                />
              </BrowserSection>

              {/* Documents */}
              {data?.recentDocuments && data.recentDocuments.length > 0 && (
                <BrowserSection
                  icon={<FileText className="w-4 h-4" />}
                  title="Documents"
                >
                  {data.recentDocuments.map((doc) => (
                    <BrowserItem
                      key={doc.id}
                      title={doc.filename}
                      subtitle={`uploaded ${formatDistanceToNow(new Date(doc.uploadedAt), { addSuffix: false })} ago`}
                      onClick={() =>
                        handleItemClick({ type: 'document-viewer', documentId: doc.id })
                      }
                    />
                  ))}
                  <BrowserAction
                    label="View all documents"
                    onClick={() => handleItemClick({ type: 'document-list' })}
                  />
                </BrowserSection>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Sub-components
// =============================================================================

function BrowserSection({
  icon,
  title,
  children,
}: {
  icon?: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-2">
        {icon}
        {title}
      </h3>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

function BrowserItem({
  title,
  subtitle,
  badge,
  onClick,
}: {
  title: string;
  subtitle?: string;
  badge?: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full px-3 py-2 text-left rounded-md hover:bg-muted transition-colors"
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium truncate">{title}</span>
        {badge && (
          <span className="text-[10px] px-1.5 py-0.5 bg-muted rounded text-muted-foreground">
            {badge}
          </span>
        )}
      </div>
      {subtitle && <p className="text-xs text-muted-foreground truncate">{subtitle}</p>}
    </button>
  );
}

function BrowserAction({
  icon,
  label,
  onClick,
}: {
  icon?: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full px-3 py-2 text-left text-xs text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors flex items-center gap-2"
    >
      {icon}
      {label}
    </button>
  );
}
