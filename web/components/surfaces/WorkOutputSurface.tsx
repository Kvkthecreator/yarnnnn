'use client';

/**
 * ADR-090 Phase 2: work_tickets removed — redirected to Deliverables.
 */

import { useRouter } from 'next/navigation';
import { FileText } from 'lucide-react';

interface WorkOutputSurfaceProps {
  workId: string;
  outputId?: string;
}

export function WorkOutputSurface({ workId: _, outputId: _2 }: WorkOutputSurfaceProps) {
  const router = useRouter();
  return (
    <div className="h-full flex flex-col items-center justify-center gap-4 text-center px-6">
      <FileText className="w-8 h-8 text-muted-foreground" />
      <p className="text-sm text-muted-foreground">Work output history has moved to Deliverables.</p>
      <button
        onClick={() => router.push('/deliverables')}
        className="text-sm text-primary hover:underline"
      >
        View Deliverables
      </button>
    </div>
  );
}
