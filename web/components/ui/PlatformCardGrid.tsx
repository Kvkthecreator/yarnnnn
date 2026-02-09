'use client';

import * as React from 'react';
import { useState, useEffect, useCallback } from 'react';
import { PlatformCard, type PlatformSummary } from './PlatformCard';
import { Loader2, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import api from '@/lib/api/client';

/**
 * ADR-033: Platform Card Grid for Dashboard
 *
 * Fetches integration summary and renders platform cards.
 * Shows loading, error, and empty states appropriately.
 */

interface PlatformCardGridProps {
  onPlatformClick?: (platform: PlatformSummary) => void;
  className?: string;
}

export function PlatformCardGrid({
  onPlatformClick,
  className,
}: PlatformCardGridProps) {
  const [platforms, setPlatforms] = useState<PlatformSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchSummary = useCallback(async (showRefreshState = false) => {
    try {
      if (showRefreshState) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const result = await api.integrations.getSummary();
      setPlatforms(result.platforms);
    } catch (err) {
      console.error('Failed to fetch integrations summary:', err);
      setError('Failed to load integrations');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  const handleRefresh = () => {
    fetchSummary(true);
  };

  if (loading) {
    return (
      <div className={cn('flex items-center justify-center py-8', className)}>
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn('text-center py-8', className)}>
        <p className="text-sm text-muted-foreground mb-2">{error}</p>
        <button
          onClick={() => fetchSummary()}
          className="text-sm text-primary hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-foreground">Platforms</h2>
        {platforms.length > 0 && (
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className={cn(
              'text-xs text-muted-foreground hover:text-foreground',
              'flex items-center gap-1 transition-colors',
              refreshing && 'opacity-50 cursor-not-allowed'
            )}
          >
            <RefreshCw className={cn('w-3 h-3', refreshing && 'animate-spin')} />
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        )}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {platforms.map((platform) => (
          <PlatformCard
            key={platform.provider}
            platform={platform}
            onClick={onPlatformClick ? () => onPlatformClick(platform) : undefined}
          />
        ))}
      </div>

      {/* Empty state message when no platforms connected */}
      {platforms.length === 0 && (
        <p className="text-xs text-muted-foreground text-center mt-4">
          Connect your first platform to see activity and manage deliverables.
        </p>
      )}
    </div>
  );
}

/**
 * Compact version for smaller spaces
 */
interface PlatformCardListProps {
  onPlatformClick?: (platform: PlatformSummary) => void;
  className?: string;
}

export function PlatformCardList({
  onPlatformClick,
  className,
}: PlatformCardListProps) {
  const [platforms, setPlatforms] = useState<PlatformSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const result = await api.integrations.getSummary();
        setPlatforms(result.platforms);
      } catch (err) {
        console.error('Failed to fetch integrations summary:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchSummary();
  }, []);

  if (loading) {
    return (
      <div className={cn('flex items-center gap-2 py-2', className)}>
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
        <span className="text-xs text-muted-foreground">Loading platforms...</span>
      </div>
    );
  }

  if (platforms.length === 0) {
    return (
      <div className={cn('text-xs text-muted-foreground py-2', className)}>
        No platforms connected
      </div>
    );
  }

  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {platforms.map((platform) => (
        <button
          key={platform.provider}
          onClick={onPlatformClick ? () => onPlatformClick(platform) : undefined}
          className={cn(
            'flex items-center gap-2 px-3 py-1.5 rounded-full',
            'bg-muted/50 hover:bg-muted text-xs transition-colors',
            'border border-border/50'
          )}
        >
          <span className="font-medium capitalize">{platform.provider}</span>
          <span className="text-muted-foreground">
            {platform.resource_count} {platform.resource_type}
          </span>
        </button>
      ))}
    </div>
  );
}
