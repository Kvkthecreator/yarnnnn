'use client';

/**
 * ADR-013: Conversation + Surfaces
 * Output Surface - displays work results, documents with export options
 */

import { useEffect, useState } from 'react';
import {
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Lightbulb,
  FileEdit,
  FileText,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Download,
  Mail,
  Briefcase,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { useSurface } from '@/contexts/SurfaceContext';
import type { SurfaceData } from '@/types/surfaces';
import type { WorkTicket, WorkOutput } from '@/types';

interface OutputSurfaceProps {
  data: SurfaceData | null;
}

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  pending: { icon: <Clock className="w-3 h-3" />, color: 'text-yellow-600 bg-yellow-50', label: 'Pending' },
  running: { icon: <Loader2 className="w-3 h-3 animate-spin" />, color: 'text-blue-600 bg-blue-50', label: 'Running' },
  completed: { icon: <CheckCircle2 className="w-3 h-3" />, color: 'text-green-600 bg-green-50', label: 'Completed' },
  failed: { icon: <XCircle className="w-3 h-3" />, color: 'text-red-600 bg-red-50', label: 'Failed' },
};

const OUTPUT_TYPE_ICONS: Record<string, React.ReactNode> = {
  finding: <CheckCircle2 className="w-4 h-4 text-blue-500" />,
  recommendation: <AlertTriangle className="w-4 h-4 text-amber-500" />,
  insight: <Lightbulb className="w-4 h-4 text-purple-500" />,
  draft: <FileEdit className="w-4 h-4 text-green-500" />,
  report: <FileText className="w-4 h-4 text-indigo-500" />,
};

export function OutputSurface({ data }: OutputSurfaceProps) {
  const [ticket, setTicket] = useState<WorkTicket | null>(null);
  const [outputs, setOutputs] = useState<WorkOutput[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { openSurface } = useSurface();

  useEffect(() => {
    if (data?.ticketId) {
      loadTicket(data.ticketId);
    } else {
      setLoading(false);
      setError('No ticket specified');
    }
  }, [data?.ticketId]);

  const loadTicket = async (ticketId: string) => {
    setLoading(true);
    setError(null);
    try {
      const detail = await api.work.get(ticketId);
      setTicket(detail.ticket);
      setOutputs(detail.outputs);
    } catch (err) {
      console.error('Failed to load ticket:', err);
      setError('Failed to load work details');
    } finally {
      setLoading(false);
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
        <Briefcase className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p>{error || 'No work found'}</p>
      </div>
    );
  }

  const statusConfig = STATUS_CONFIG[ticket.status] || STATUS_CONFIG.pending;

  return (
    <div className="p-4">
      {/* Header */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusConfig.color}`}>
            {statusConfig.icon}
            {statusConfig.label}
          </span>
          <span className="text-xs text-muted-foreground capitalize">
            {ticket.agent_type} agent
          </span>
        </div>
        <h2 className="font-medium">{ticket.task}</h2>
        <p className="text-xs text-muted-foreground mt-1">
          {new Date(ticket.created_at).toLocaleString()}
          {ticket.completed_at && ` • Completed ${new Date(ticket.completed_at).toLocaleString()}`}
        </p>
      </div>

      {/* Export actions - at top for easy access */}
      {outputs.length > 0 && ticket.status === 'completed' && (
        <div className="mb-4 pb-4 border-b border-border">
          <p className="text-xs text-muted-foreground mb-3">Export this work</p>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => handleExport('pdf')}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-full font-medium"
            >
              <Download className="w-4 h-4" />
              PDF
            </button>
            <button
              onClick={() => handleExport('docx')}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm border border-border rounded-full hover:bg-muted"
            >
              <FileText className="w-4 h-4" />
              DOCX
            </button>
            <button
              onClick={() => handleExport('email')}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm border border-border rounded-full hover:bg-muted"
            >
              <Mail className="w-4 h-4" />
              Email
            </button>
          </div>
        </div>
      )}

      {/* Error message */}
      {ticket.error_message && (
        <div className="mb-4 p-3 bg-destructive/10 text-destructive text-sm rounded-2xl">
          {ticket.error_message}
        </div>
      )}

      {/* Outputs */}
      {outputs.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-muted-foreground">
            Outputs ({outputs.length})
          </h3>
          {outputs.map((output) => (
            <OutputCard key={output.id} output={output} />
          ))}
        </div>
      )}
    </div>
  );
}

function OutputCard({ output }: { output: WorkOutput }) {
  const [isExpanded, setIsExpanded] = useState(true);

  // Parse content JSON
  let body: { summary?: string; details?: string; evidence?: string[]; implications?: string[] } | null = null;
  try {
    if (output.content) {
      body = JSON.parse(output.content);
    }
  } catch {
    // Content might be plain text
  }

  return (
    <div className="p-3 bg-muted/30 border border-border/50 rounded-2xl">
      <div
        className="flex items-start gap-2 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {OUTPUT_TYPE_ICONS[output.output_type] || <FileText className="w-4 h-4" />}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm truncate">{output.title}</span>
            <span className="text-xs text-muted-foreground capitalize shrink-0">
              {output.output_type}
            </span>
          </div>
          {body?.summary && !isExpanded && (
            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{body.summary}</p>
          )}
        </div>
        <span className="text-muted-foreground shrink-0">
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </span>
      </div>

      {isExpanded && body && (
        <div className="mt-3 pl-6 space-y-3 text-sm">
          {body.summary && (
            <div>
              <span className="font-medium text-muted-foreground">Summary:</span>
              <p className="mt-1">{body.summary}</p>
            </div>
          )}
          {body.details && (
            <div>
              <span className="font-medium text-muted-foreground">Details:</span>
              <p className="mt-1 whitespace-pre-wrap">{body.details}</p>
            </div>
          )}
          {body.evidence && body.evidence.length > 0 && (
            <div>
              <span className="font-medium text-muted-foreground">Evidence:</span>
              <ul className="list-disc list-inside ml-2 mt-1">
                {body.evidence.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </div>
          )}
          {body.implications && body.implications.length > 0 && (
            <div>
              <span className="font-medium text-muted-foreground">Implications:</span>
              <ul className="list-disc list-inside ml-2 mt-1">
                {body.implications.map((imp, i) => <li key={i}>{imp}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {isExpanded && !body && output.content && (
        <div className="mt-3 pl-6 text-sm whitespace-pre-wrap">
          {output.content}
        </div>
      )}
    </div>
  );
}
