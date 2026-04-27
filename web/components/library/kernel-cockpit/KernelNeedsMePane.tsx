'use client';

/**
 * KernelNeedsMePane — kernel-default cockpit pane (ADR-225 Phase 3).
 *
 * Wraps the existing NeedsMePane substrate component and threads the
 * chat-draft handler from CockpitContext. The substrate component
 * itself stays at web/components/work/briefing/ — it has substantive
 * logic; this wrapper is the registry-shaped facade.
 */

import { NeedsMePane } from '@/components/work/briefing/NeedsMePane';
import { useCockpit } from '../CockpitContext';

export function KernelNeedsMePane() {
  const { onOpenChatDraft } = useCockpit();
  return <NeedsMePane onOpenChatDraft={onOpenChatDraft} />;
}
