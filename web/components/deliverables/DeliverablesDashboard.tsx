'use client';

/**
 * ADR-018: Deliverables Dashboard
 *
 * Primary landing view for authenticated users.
 * Shows deliverable cards, staged items requiring review, and empty state.
 *
 * For cold-start users (no deliverables), shows OnboardingChatView
 * which provides a conversation-first onboarding experience.
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Loader2, RefreshCw, Filter } from 'lucide-react';
import { api } from '@/lib/api/client';
import { DeliverableCard } from './DeliverableCard';
import { OnboardingChatView } from './OnboardingChatView';
import type { Deliverable } from '@/types';

interface DeliverablesDashboardProps {
  onCreateNew: () => void;
}

export function DeliverablesDashboard({ onCreateNew }: DeliverablesDashboardProps) {
  const router = useRouter();
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'active' | 'paused'>('all');

  useEffect(() => {
    loadDeliverables();
  }, []);

  const loadDeliverables = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.deliverables.list();
      setDeliverables(data);
    } catch (err) {
      console.error('Failed to load deliverables:', err);
      setError('Failed to load deliverables');
    } finally {
      setLoading(false);
    }
  };

  const handleView = (id: string) => {
    router.push(`/dashboard/deliverable/${id}`);
  };

  const handleReview = (id: string) => {
    // Find the deliverable to get the latest staged version
    const deliverable = deliverables.find(d => d.id === id);
    if (deliverable) {
      router.push(`/dashboard/deliverable/${id}/review`);
    }
  };

  const handlePause = async (id: string) => {
    try {
      await api.deliverables.update(id, { status: 'paused' });
      setDeliverables(prev =>
        prev.map(d => d.id === id ? { ...d, status: 'paused' } : d)
      );
    } catch (err) {
      console.error('Failed to pause deliverable:', err);
    }
  };

  const handleResume = async (id: string) => {
    try {
      await api.deliverables.update(id, { status: 'active' });
      setDeliverables(prev =>
        prev.map(d => d.id === id ? { ...d, status: 'active' } : d)
      );
    } catch (err) {
      console.error('Failed to resume deliverable:', err);
    }
  };

  const handleRunNow = async (id: string) => {
    try {
      await api.deliverables.run(id);
      // Refresh to get updated status
      loadDeliverables();
    } catch (err) {
      console.error('Failed to run deliverable:', err);
    }
  };

  // Filter deliverables
  const filteredDeliverables = deliverables.filter(d => {
    if (filter === 'active') return d.status === 'active';
    if (filter === 'paused') return d.status === 'paused';
    return d.status !== 'archived';
  });

  // Separate staged items for attention banner
  const stagedDeliverables = filteredDeliverables.filter(
    d => d.latest_version_status === 'staged'
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <p className="text-muted-foreground mb-4">{error}</p>
        <button
          onClick={loadDeliverables}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm border border-border rounded-md hover:bg-muted"
        >
          <RefreshCw className="w-4 h-4" />
          Retry
        </button>
      </div>
    );
  }

  // Empty state - conversation-first onboarding
  if (deliverables.length === 0) {
    return (
      <OnboardingChatView
        onDeliverableCreated={(deliverableId) => {
          // Refresh dashboard to show new deliverable
          loadDeliverables();
        }}
        onUseWizard={onCreateNew}
      />
    );
  }

  return (
    <div className="h-full overflow-auto">
      {/* Staged banner */}
      {stagedDeliverables.length > 0 && (
        <div className="bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 px-4 py-3">
          <div className="container mx-auto flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center justify-center w-5 h-5 bg-amber-500 text-white text-xs font-bold rounded-full">
                {stagedDeliverables.length}
              </span>
              <span className="text-sm font-medium text-amber-800 dark:text-amber-200">
                {stagedDeliverables.length === 1
                  ? 'deliverable ready for review'
                  : 'deliverables ready for review'}
              </span>
            </div>
            {stagedDeliverables.length === 1 && (
              <button
                onClick={() => handleReview(stagedDeliverables[0].id)}
                className="text-sm font-medium text-amber-700 dark:text-amber-300 hover:underline"
              >
                Review now
              </button>
            )}
          </div>
        </div>
      )}

      <div className="container mx-auto px-4 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-semibold">Deliverables</h1>
            <p className="text-sm text-muted-foreground">
              {filteredDeliverables.length} {filteredDeliverables.length === 1 ? 'deliverable' : 'deliverables'}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Filter */}
            <div className="flex items-center border border-border rounded-md overflow-hidden text-sm">
              <button
                onClick={() => setFilter('all')}
                className={`px-3 py-1.5 ${filter === 'all' ? 'bg-muted font-medium' : 'hover:bg-muted/50'}`}
              >
                All
              </button>
              <button
                onClick={() => setFilter('active')}
                className={`px-3 py-1.5 border-l border-border ${filter === 'active' ? 'bg-muted font-medium' : 'hover:bg-muted/50'}`}
              >
                Active
              </button>
              <button
                onClick={() => setFilter('paused')}
                className={`px-3 py-1.5 border-l border-border ${filter === 'paused' ? 'bg-muted font-medium' : 'hover:bg-muted/50'}`}
              >
                Paused
              </button>
            </div>

            {/* Refresh */}
            <button
              onClick={loadDeliverables}
              className="p-2 text-muted-foreground hover:text-foreground border border-border rounded-md hover:bg-muted"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>

            {/* Create new */}
            <button
              onClick={onCreateNew}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90 transition-colors"
            >
              <Plus className="w-4 h-4" />
              New
            </button>
          </div>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredDeliverables.map(deliverable => (
            <DeliverableCard
              key={deliverable.id}
              deliverable={deliverable}
              onView={handleView}
              onReview={handleReview}
              onPause={handlePause}
              onResume={handleResume}
              onRunNow={handleRunNow}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
