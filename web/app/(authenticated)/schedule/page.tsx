'use client';

/**
 * Schedule Page — Cadence-framed list surface (ADR-243).
 *
 * Sibling of /work. Same recurrence substrate, different framing:
 *   /work     answers "what does my work produce?" (output kind)
 *   /schedule answers "what's on my schedule?" (cadence)
 *
 * List mode only; click any row → /work?task={slug} (canonical detail
 * surface, ADR-241). No detail mode here — keeps the framing pure
 * and avoids divergent detail UIs.
 *
 * Phase 2 (deferred): Calendar/timeline view as a toggle on this same
 * page. List ships first; calendar awaits an alpha operator with 5+
 * recurrences explicitly requesting cadence-grid visualization.
 */

import { useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, MessageCircle } from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useBreadcrumb } from '@/contexts/BreadcrumbContext';
import { useAgentsAndRecurrences } from '@/hooks/useAgentsAndRecurrences';
import { ScheduleListSurface } from '@/components/schedule/ScheduleListSurface';
import { ThreePanelLayout } from '@/components/shell/ThreePanelLayout';
import { PageHeader } from '@/components/shell/PageHeader';

export default function SchedulePage() {
  const router = useRouter();
  const { loadScopedHistory } = useTP();
  const { clearBreadcrumb } = useBreadcrumb();
  const { tasks: recurrences, loading } = useAgentsAndRecurrences();

  // Load chat history (unified session — once)
  useEffect(() => { loadScopedHistory(); }, [loadScopedHistory]);

  // Schedule is list-only — no detail mode means breadcrumb stays clear
  useEffect(() => {
    clearBreadcrumb();
    return () => clearBreadcrumb();
  }, [clearBreadcrumb]);

  // ADR-243 Decision 3: row click hands off to /work?task=, the canonical
  // detail surface. /schedule never owns recurrence detail.
  const handleSelect = useCallback((slug: string) => {
    router.push(`/work?task=${encodeURIComponent(slug)}`);
  }, [router]);

  const chatEmptyState = (
    <div className="py-2 text-center">
      <MessageCircle className="mx-auto mb-1.5 h-5 w-5 text-muted-foreground/15" />
      <p className="text-[11px] text-muted-foreground/40">
        Ask anything about your schedule
      </p>
    </div>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <ThreePanelLayout
      chat={{
        placeholder: 'Ask about your schedule…',
        emptyState: chatEmptyState,
        defaultOpen: false,
      }}
    >
      <PageHeader defaultLabel="Schedule" />
      <ScheduleListSurface
        recurrences={recurrences}
        onSelect={handleSelect}
      />
    </ThreePanelLayout>
  );
}
