'use client';

import * as React from 'react';
import { Mail, Slack, FileCode, Calendar, AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card, CardContent } from './card';

/**
 * ADR-033: Platform Card for Dashboard
 *
 * Shows summary of a single platform integration:
 * - Connection status
 * - Resource count (channels, labels, pages)
 * - Deliverable count targeting this platform
 * - Recent activity stats
 */

export interface PlatformSummary {
  provider: string;
  status: string; // active, error, expired
  workspace_name: string | null;
  connected_at: string;
  resource_count: number;
  resource_type: string; // channels, labels, pages
  deliverable_count: number;
  activity_7d: number;
}

interface PlatformCardProps {
  platform: PlatformSummary;
  onClick?: () => void;
  className?: string;
}

const PLATFORM_CONFIG: Record<string, {
  icon: React.ReactNode;
  label: string;
  color: string;
  bgColor: string;
}> = {
  gmail: {
    icon: <Mail className="w-6 h-6" />,
    label: 'Gmail',
    color: 'text-red-500',
    bgColor: 'bg-red-50 dark:bg-red-950/30',
  },
  slack: {
    icon: <Slack className="w-6 h-6" />,
    label: 'Slack',
    color: 'text-purple-500',
    bgColor: 'bg-purple-50 dark:bg-purple-950/30',
  },
  notion: {
    icon: <FileCode className="w-6 h-6" />,
    label: 'Notion',
    color: 'text-gray-700 dark:text-gray-300',
    bgColor: 'bg-gray-50 dark:bg-gray-800/50',
  },
  google: {
    icon: <Calendar className="w-6 h-6" />,
    label: 'Calendar',
    color: 'text-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-950/30',
  },
};

function StatusBadge({ status }: { status: string }) {
  if (status === 'active') {
    return (
      <div className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
        <CheckCircle2 className="w-3 h-3" />
        <span>Connected</span>
      </div>
    );
  }
  if (status === 'error') {
    return (
      <div className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400">
        <AlertCircle className="w-3 h-3" />
        <span>Error</span>
      </div>
    );
  }
  if (status === 'expired') {
    return (
      <div className="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
        <Clock className="w-3 h-3" />
        <span>Expired</span>
      </div>
    );
  }
  return null;
}

function formatActivityCount(count: number): string {
  if (count === 0) return 'No activity';
  if (count === 1) return '1 item';
  if (count < 100) return `${count} items`;
  if (count < 1000) return `${count} items`;
  return `${(count / 1000).toFixed(1)}k items`;
}

export function PlatformCard({ platform, onClick, className }: PlatformCardProps) {
  const config = PLATFORM_CONFIG[platform.provider] || {
    icon: <FileCode className="w-6 h-6" />,
    label: platform.provider,
    color: 'text-gray-500',
    bgColor: 'bg-gray-50 dark:bg-gray-800/50',
  };

  const isClickable = !!onClick;

  return (
    <Card
      className={cn(
        'overflow-hidden transition-all duration-200',
        isClickable && 'cursor-pointer hover:border-primary/50 hover:shadow-md',
        className
      )}
      onClick={onClick}
    >
      <CardContent className="p-4">
        {/* Header: Icon + Name + Status */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={cn(
              'p-2 rounded-lg',
              config.bgColor,
              config.color
            )}>
              {config.icon}
            </div>
            <div>
              <h3 className="font-semibold text-sm">{config.label}</h3>
              {platform.workspace_name && (
                <p className="text-xs text-muted-foreground truncate max-w-[120px]">
                  {platform.workspace_name}
                </p>
              )}
            </div>
          </div>
          <StatusBadge status={platform.status} />
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3 text-xs">
          {/* Resources */}
          <div className="bg-muted/50 rounded-lg p-2">
            <div className="text-muted-foreground">{platform.resource_type}</div>
            <div className="font-semibold text-foreground">
              {platform.resource_count}
            </div>
          </div>

          {/* Deliverables */}
          <div className="bg-muted/50 rounded-lg p-2">
            <div className="text-muted-foreground">deliverables</div>
            <div className="font-semibold text-foreground">
              {platform.deliverable_count}
            </div>
          </div>
        </div>

        {/* Activity indicator */}
        {platform.activity_7d > 0 && (
          <div className="mt-3 pt-3 border-t border-border/50">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Last 7 days</span>
              <span className="font-medium text-foreground">
                {formatActivityCount(platform.activity_7d)}
              </span>
            </div>
          </div>
        )}

        {/* View prompt */}
        {isClickable && (
          <div className="mt-3 text-xs text-primary font-medium">
            View details →
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Empty state card for connecting a new platform
 */
interface AddPlatformCardProps {
  onClick?: () => void;
  className?: string;
}

export function AddPlatformCard({ onClick, className }: AddPlatformCardProps) {
  return (
    <Card
      className={cn(
        'overflow-hidden border-dashed cursor-pointer',
        'hover:border-primary/50 hover:bg-muted/50 transition-all duration-200',
        className
      )}
      onClick={onClick}
    >
      <CardContent className="p-4 flex flex-col items-center justify-center min-h-[140px] text-center">
        <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center mb-2">
          <span className="text-2xl text-muted-foreground">+</span>
        </div>
        <p className="text-sm font-medium text-muted-foreground">
          Connect Platform
        </p>
        <p className="text-xs text-muted-foreground/70 mt-1">
          Slack, Gmail, Notion
        </p>
      </CardContent>
    </Card>
  );
}
