'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * WorkOutputSurface - View work output content
 */

import { useState, useEffect } from 'react';
import { Loader2, Copy, Download, CheckCircle2, ArrowLeft } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import { format } from 'date-fns';
import type { WorkOutput, WorkTicketDetail } from '@/types';

interface WorkOutputSurfaceProps {
  workId: string;
  outputId?: string;
}

export function WorkOutputSurface({ workId, outputId }: WorkOutputSurfaceProps) {
  const { setSurface } = useDesk();
  const [loading, setLoading] = useState(true);
  const [workDetail, setWorkDetail] = useState<WorkTicketDetail | null>(null);
  const [output, setOutput] = useState<WorkOutput | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadWork();
  }, [workId, outputId]);

  const loadWork = async () => {
    setLoading(true);
    try {
      const detail = await api.work.get(workId);
      setWorkDetail(detail);

      // Find the specific output or use the first one
      if (outputId) {
        const found = detail.outputs.find((o) => o.id === outputId);
        setOutput(found || detail.outputs[0] || null);
      } else {
        setOutput(detail.outputs[0] || null);
      }
    } catch (err) {
      console.error('Failed to load work:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!output?.content) return;
    try {
      const parsed = JSON.parse(output.content);
      await navigator.clipboard.writeText(parsed.body || output.content);
    } catch {
      await navigator.clipboard.writeText(output.content);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getContent = (): string => {
    if (!output?.content) return '';
    try {
      const parsed = JSON.parse(output.content);
      return parsed.body || output.content;
    } catch {
      return output.content;
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!workDetail) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        Work not found
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 h-14 border-b border-border flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSurface({ type: 'work-list' })}
            className="p-1.5 hover:bg-muted rounded"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="font-medium">{output?.title || workDetail.ticket.task}</h1>
            <p className="text-xs text-muted-foreground">
              {workDetail.ticket.agent_type} • {workDetail.ticket.status}
              {workDetail.ticket.completed_at &&
                ` • ${format(new Date(workDetail.ticket.completed_at), 'MMM d, h:mm a')}`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted"
          >
            {copied ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-green-600" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
            {copied ? 'Copied' : 'Copy'}
          </button>
          {output?.file_url && (
            <a
              href={output.file_url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 border border-border rounded-md hover:bg-muted"
            >
              <Download className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto px-6 py-6">
          {output ? (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <pre className="whitespace-pre-wrap font-sans bg-muted/30 p-4 rounded-lg border border-border">
                {getContent()}
              </pre>
            </div>
          ) : (
            <p className="text-muted-foreground">No output available</p>
          )}

          {/* Other outputs */}
          {workDetail.outputs.length > 1 && (
            <div className="mt-6 pt-6 border-t border-border">
              <h3 className="text-sm font-medium mb-3">All outputs ({workDetail.output_count})</h3>
              <div className="space-y-2">
                {workDetail.outputs.map((o) => (
                  <button
                    key={o.id}
                    onClick={() =>
                      setSurface({ type: 'work-output', workId, outputId: o.id })
                    }
                    className={`w-full p-3 border rounded-lg text-left ${
                      o.id === output?.id
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:bg-muted'
                    }`}
                  >
                    <span className="text-sm font-medium">{o.title}</span>
                    <span className="text-xs text-muted-foreground ml-2 capitalize">
                      {o.output_type}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
