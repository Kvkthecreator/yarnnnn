'use client';

/**
 * ADR-013: Output Detail View
 *
 * Shows a single output in full detail within the workspace panel.
 * Replaces the separate OutputSurface drawer.
 */

import { useEffect, useState } from 'react';
import {
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Download,
  Mail,
  FileText,
  Copy,
  Check,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { useSurface } from '@/contexts/SurfaceContext';
import type { WorkTicket, WorkOutput } from '@/types';

interface OutputDetailViewProps {
  workId: string;
  onBack: () => void;
}

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  pending: { icon: <Clock className="w-3 h-3" />, color: 'text-yellow-600 bg-yellow-50', label: 'Pending' },
  running: { icon: <Loader2 className="w-3 h-3 animate-spin" />, color: 'text-blue-600 bg-blue-50', label: 'Running' },
  completed: { icon: <CheckCircle2 className="w-3 h-3" />, color: 'text-green-600 bg-green-50', label: 'Completed' },
  failed: { icon: <XCircle className="w-3 h-3" />, color: 'text-red-600 bg-red-50', label: 'Failed' },
};

const AGENT_COLORS: Record<string, string> = {
  research: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  content: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  reporting: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
};

export function OutputDetailView({ workId, onBack }: OutputDetailViewProps) {
  const [ticket, setTicket] = useState<WorkTicket | null>(null);
  const [outputs, setOutputs] = useState<WorkOutput[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const { openSurface } = useSurface();

  useEffect(() => {
    loadWork();
  }, [workId]);

  const loadWork = async () => {
    setLoading(true);
    setError(null);
    try {
      const detail = await api.work.get(workId);
      setTicket(detail.ticket);
      setOutputs(detail.outputs);
    } catch (err) {
      console.error('Failed to load work:', err);
      setError('Failed to load work details');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (outputs.length > 0 && outputs[0].content) {
      await navigator.clipboard.writeText(outputs[0].content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleExport = (type: 'pdf' | 'docx' | 'email') => {
    openSurface('export', {
      exportType: type,
      content: outputs,
      title: ticket?.task,
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !ticket) {
    return (
      <div className="p-6 text-center text-muted-foreground">
        <p>{error || 'Work not found'}</p>
        <button
          onClick={onBack}
          className="mt-2 text-xs text-primary hover:underline"
        >
          Go back
        </button>
      </div>
    );
  }

  const statusConfig = STATUS_CONFIG[ticket.status] || STATUS_CONFIG.pending;
  const output = outputs[0]; // ADR-016: single output per work

  return (
    <div className="p-4">
      {/* Header */}
      <div className="mb-4 pb-4 border-b border-border">
        <div className="flex items-center gap-2 mb-2">
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusConfig.color}`}>
            {statusConfig.icon}
            {statusConfig.label}
          </span>
          <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${AGENT_COLORS[ticket.agent_type] || 'bg-gray-100 text-gray-700'}`}>
            {ticket.agent_type}
          </span>
        </div>
        <h2 className="font-medium text-sm">{ticket.task}</h2>
        <p className="text-xs text-muted-foreground mt-1">
          {new Date(ticket.created_at).toLocaleString()}
        </p>
      </div>

      {/* Actions */}
      {output && ticket.status === 'completed' && (
        <div className="mb-4 pb-4 border-b border-border">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-full hover:bg-muted transition-colors"
            >
              {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button
              onClick={() => handleExport('pdf')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-full hover:bg-muted transition-colors"
            >
              <Download className="w-3 h-3" />
              PDF
            </button>
            <button
              onClick={() => handleExport('docx')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-full hover:bg-muted transition-colors"
            >
              <FileText className="w-3 h-3" />
              DOCX
            </button>
            <button
              onClick={() => handleExport('email')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-full hover:bg-muted transition-colors"
            >
              <Mail className="w-3 h-3" />
              Email
            </button>
          </div>
        </div>
      )}

      {/* Error message */}
      {ticket.error_message && (
        <div className="mb-4 p-3 bg-destructive/10 text-destructive text-sm rounded-lg">
          {ticket.error_message}
        </div>
      )}

      {/* Output content */}
      {output ? (
        <div>
          <h3 className="text-sm font-medium mb-3">{output.title}</h3>
          <div className="text-sm whitespace-pre-wrap leading-relaxed">
            {output.content}
          </div>
        </div>
      ) : ticket.status === 'completed' ? (
        <div className="text-center py-4 text-muted-foreground text-sm">
          No output generated
        </div>
      ) : null}
    </div>
  );
}
