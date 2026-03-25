'use client';

/**
 * Workspace sidebar — file browser for outputs and uploads.
 */

import { useState, useEffect } from 'react';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import {
  FileText,
  FolderTree,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';

export function ContextSidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [knowledgeCounts, setKnowledgeCounts] = useState<Record<string, number>>({});

  useEffect(() => {
    api.knowledge.summary().catch(() => ({ classes: [] })).then((knowledge) => {
      const nextCounts: Record<string, number> = {};
      for (const item of knowledge.classes || []) {
        nextCounts[item.content_class] = item.count;
      }
      setKnowledgeCounts(nextCounts);
    }).catch(() => {});
  }, []);

  const isOnContextRoot = pathname === '/context';
  const activeSection = searchParams.get('section') || 'knowledge';
  const totalKnowledge = Object.values(knowledgeCounts).reduce((sum, count) => sum + count, 0);

  return (
    <nav className="h-full min-h-0 border-r border-border bg-muted/50 flex flex-col">
      <div className="p-4 space-y-1 flex-1 min-h-0 overflow-y-auto">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-3 pt-4 pb-2">
          Workspace
        </div>

        {/* Outputs — agent-produced files */}
        <button
          onClick={() => router.push('/context?section=knowledge')}
          className={cn(
            "w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors",
            activeSection === 'knowledge'
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <span className="flex items-center gap-2">
            <FolderTree className="w-4 h-4" />
            Outputs
          </span>
          {totalKnowledge > 0 && (
            <span className="text-muted-foreground text-xs">{totalKnowledge}</span>
          )}
        </button>

        {/* Documents */}
        <button
          onClick={() => router.push('/context?section=documents')}
          className={cn(
            "w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors mt-1",
            isOnContextRoot && activeSection === 'documents'
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <FileText className="w-4 h-4" />
          Uploads
        </button>
      </div>
    </nav>
  );
}
