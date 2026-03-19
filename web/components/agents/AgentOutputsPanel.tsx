'use client';

/**
 * AgentOutputsPanel — ADR-119 Phase 4b
 *
 * Chronological output history for an agent, shown as a panel tab.
 * Each output folder: date, version, file list, delivery status, project badge.
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import {
  Loader2,
  Package,
  FileText,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  FolderKanban,
} from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import type { OutputManifest } from '@/types';

export function AgentOutputsPanel({ agentId }: { agentId: string }) {
  const [outputs, setOutputs] = useState<OutputManifest[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedFolder, setExpandedFolder] = useState<string | null>(null);

  useEffect(() => {
    api.agents.getOutputs(agentId).then((res) => {
      setOutputs(res.outputs);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [agentId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (outputs.length === 0) {
    return (
      <div className="text-center py-12 px-4">
        <Package className="w-8 h-8 text-muted-foreground/20 mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">No output folders yet — outputs appear after agent runs.</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-border">
      {outputs.map((o) => {
        const isExpanded = expandedFolder === o.folder;
        return (
          <div key={o.folder} className="px-4 py-3">
            <button
              onClick={() => setExpandedFolder(isExpanded ? null : o.folder)}
              className="w-full flex items-center gap-2 text-left group"
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
              ) : (
                <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <span className="text-sm font-medium group-hover:text-primary transition-colors">
                  v{o.version}
                </span>
                {o.created_at && (
                  <span className="text-xs text-muted-foreground ml-2">
                    {format(new Date(o.created_at), 'MMM d, yyyy h:mm a')}
                  </span>
                )}
              </div>
              <span className={cn(
                'text-xs px-2 py-0.5 rounded',
                o.status === 'delivered' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                o.status === 'active' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' :
                'bg-muted text-muted-foreground'
              )}>
                {o.status}
              </span>
            </button>

            {isExpanded && (
              <div className="mt-3 ml-6 space-y-2">
                {o.files.length > 0 && (
                  <div className="space-y-1">
                    {o.files.map((f, fi) => (
                      <div key={fi} className="flex items-center gap-2 text-xs text-muted-foreground">
                        <FileText className="w-3 h-3 shrink-0" />
                        <span className="truncate">{f.path}</span>
                        {f.content_url && (
                          <a
                            href={f.content_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline shrink-0"
                          >
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                {o.sources.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    Sources: {o.sources.join(', ')}
                  </p>
                )}
                {o.delivery && (
                  <p className="text-xs text-muted-foreground">
                    Delivery: {Object.entries(o.delivery).map(([k, v]) => `${k}: ${v}`).join(', ')}
                  </p>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
