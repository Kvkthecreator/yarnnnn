'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * WorkListSurface - List of work items
 */

import { useState, useEffect } from 'react';
import { Loader2, Search, CheckCircle2, XCircle, Clock, Play } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import { formatDistanceToNow } from 'date-fns';
import type { Work } from '@/types';

interface WorkListSurfaceProps {
  filter?: 'active' | 'completed' | 'all';
}

export function WorkListSurface({ filter = 'all' }: WorkListSurfaceProps) {
  const { setSurface } = useDesk();
  const [loading, setLoading] = useState(true);
  const [work, setWork] = useState<Work[]>([]);
  const [currentFilter, setCurrentFilter] = useState(filter);

  useEffect(() => {
    loadWork();
  }, [currentFilter]);

  const loadWork = async () => {
    setLoading(true);
    try {
      const response = await api.work.listAll();
      let filtered = response.work;

      if (currentFilter === 'completed') {
        filtered = filtered.filter((w) => w.status === 'completed');
      } else if (currentFilter === 'active') {
        filtered = filtered.filter((w) => w.status === 'running' || w.status === 'pending');
      }

      setWork(filtered);
    } catch (err) {
      console.error('Failed to load work:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-green-600" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-600" />;
      case 'running':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'pending':
        return <Clock className="w-4 h-4 text-amber-500" />;
      default:
        return <Play className="w-4 h-4 text-muted-foreground" />;
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 h-14 border-b border-border flex items-center justify-between px-4">
        <h1 className="font-medium">Work</h1>

        <div className="flex items-center gap-2">
          {(['all', 'active', 'completed'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setCurrentFilter(f)}
              className={`px-3 py-1.5 text-xs rounded-full border ${
                currentFilter === f
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'border-border hover:bg-muted'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto px-6 py-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : work.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No work items found</p>
            </div>
          ) : (
            <div className="space-y-2">
              {work.map((w) => (
                <button
                  key={w.id}
                  onClick={() =>
                    w.status === 'completed'
                      ? setSurface({ type: 'work-output', workId: w.id })
                      : undefined
                  }
                  disabled={w.status !== 'completed'}
                  className={`w-full p-4 border border-border rounded-lg text-left ${
                    w.status === 'completed'
                      ? 'hover:bg-muted cursor-pointer'
                      : 'opacity-60 cursor-default'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(w.status)}
                      <div>
                        <span className="text-sm font-medium">{w.task}</span>
                        <p className="text-xs text-muted-foreground">
                          {w.agent_type} • {w.project_name}
                        </p>
                      </div>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(w.created_at), { addSuffix: true })}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
