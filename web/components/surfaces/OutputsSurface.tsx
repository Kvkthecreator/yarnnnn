'use client';

/**
 * ADR-013: Outputs Surface
 *
 * Shows all work outputs directly (not nested under work items).
 * Users can see their outputs without navigating through Schedule first.
 */

import { useEffect, useState, useCallback } from 'react';
import {
  Loader2,
  FileText,
  CheckCircle2,
  Lightbulb,
  FileEdit,
  AlertTriangle,
  Calendar,
} from 'lucide-react';
import { useProjectContext } from '@/contexts/ProjectContext';
import { api } from '@/lib/api/client';

interface OutputWithWork {
  id: string;
  title: string;
  output_type: string;
  content: string | undefined;
  created_at: string;
  work_id: string;
  work_task: string;
  agent_type: string;
}

interface OutputsSurfaceProps {
  onViewOutput?: (workId: string) => void;
}

const OUTPUT_TYPE_ICONS: Record<string, React.ReactNode> = {
  finding: <CheckCircle2 className="w-4 h-4 text-blue-500" />,
  recommendation: <AlertTriangle className="w-4 h-4 text-amber-500" />,
  insight: <Lightbulb className="w-4 h-4 text-purple-500" />,
  draft: <FileEdit className="w-4 h-4 text-green-500" />,
  report: <FileText className="w-4 h-4 text-indigo-500" />,
  markdown: <FileText className="w-4 h-4 text-gray-500" />,
};

const AGENT_COLORS: Record<string, string> = {
  research: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  content: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  reporting: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
};

export function OutputsSurface({ onViewOutput }: OutputsSurfaceProps) {
  const { activeProject } = useProjectContext();
  const [outputs, setOutputs] = useState<OutputWithWork[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadOutputs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch completed work with outputs
      const result = await api.work.listAll({
        projectId: activeProject?.id,
        activeOnly: false,
        includeCompleted: true,
        limit: 50,
      });

      // For each completed work, get its outputs
      const workWithOutputs = (result.work || []).filter(w => w.status === 'completed');

      // Fetch outputs for completed work
      const outputPromises = workWithOutputs.map(async (work) => {
        try {
          const detail = await api.work.get(work.id);
          return (detail.outputs || []).map((output): OutputWithWork => ({
            id: output.id,
            title: output.title,
            output_type: output.output_type,
            content: output.content,
            created_at: output.created_at,
            work_id: work.id,
            work_task: work.task,
            agent_type: work.agent_type,
          }));
        } catch {
          return [] as OutputWithWork[];
        }
      });

      const outputArrays = await Promise.all(outputPromises);
      const allOutputs: OutputWithWork[] = outputArrays.flat();

      // Sort by created_at descending
      allOutputs.sort((a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );

      setOutputs(allOutputs);
    } catch (err) {
      console.error('Failed to load outputs:', err);
      setError('Failed to load outputs');
    } finally {
      setLoading(false);
    }
  }, [activeProject?.id]);

  useEffect(() => {
    loadOutputs();
  }, [loadOutputs]);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const getContentPreview = (content: string | undefined) => {
    if (!content) return 'No content';

    // Try to extract summary or first paragraph
    try {
      const parsed = JSON.parse(content);
      if (parsed.summary) return parsed.summary;
    } catch {
      // Not JSON, treat as plain text/markdown
    }

    // Get first non-header line
    const lines = content.split('\n').filter(l => l.trim() && !l.startsWith('#'));
    const preview = lines[0] || '';
    return preview.length > 150 ? preview.slice(0, 150) + '...' : preview;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center text-muted-foreground">
        <p className="text-sm">{error}</p>
        <button
          onClick={loadOutputs}
          className="mt-2 text-xs text-primary hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  if (outputs.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground px-4">
        <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p className="text-sm font-medium">No outputs yet</p>
        <p className="text-xs mt-1">
          Outputs will appear here when your work is completed.
        </p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-muted-foreground">
          Recent Outputs ({outputs.length})
        </h3>
      </div>

      <div className="space-y-3">
        {outputs.map((output) => (
          <div
            key={output.id}
            onClick={() => onViewOutput?.(output.work_id)}
            className="p-3 border border-border rounded-lg hover:border-muted-foreground/30 hover:bg-muted/20 transition-colors cursor-pointer group"
          >
            <div className="flex items-start gap-3">
              {OUTPUT_TYPE_ICONS[output.output_type] || <FileText className="w-4 h-4 text-gray-400" />}

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-sm truncate">{output.title}</span>
                </div>

                <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
                  {getContentPreview(output.content)}
                </p>

                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <span
                    className={`px-1.5 py-0.5 rounded font-medium ${
                      AGENT_COLORS[output.agent_type] || 'bg-gray-100 text-gray-700'
                    }`}
                  >
                    {output.agent_type}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {formatDate(output.created_at)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
