'use client';

/**
 * ADR-032 Phase 3: Platform Resources List
 *
 * Shows platform resources linked to a project (Slack channels, Gmail labels, Notion pages).
 * Enables cross-platform context gathering for deliverables.
 */

import { useState } from 'react';
import {
  Mail,
  Slack,
  FileText,
  Calendar,
  Trash2,
  Plus,
  Loader2,
  AlertCircle,
  Hash,
  Tag,
  Database,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ProjectResource } from '@/types';

interface PlatformResourcesListProps {
  resources: ProjectResource[];
  isLoading?: boolean;
  onRemove?: (resourceId: string) => Promise<void>;
  onAdd?: () => void;
  compact?: boolean;
}

const PLATFORM_CONFIG: Record<string, {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  color: string;
  bgColor: string;
}> = {
  slack: {
    icon: Slack,
    label: 'Slack',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
  },
  gmail: {
    icon: Mail,
    label: 'Gmail',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
  },
  notion: {
    icon: FileText,
    label: 'Notion',
    color: 'text-gray-700',
    bgColor: 'bg-gray-100',
  },
  calendar: {
    icon: Calendar,
    label: 'Calendar',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
  },
};

const RESOURCE_TYPE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  channel: Hash,
  label: Tag,
  page: FileText,
  database: Database,
  calendar: Calendar,
};

export function PlatformResourcesList({
  resources,
  isLoading,
  onRemove,
  onAdd,
  compact = false,
}: PlatformResourcesListProps) {
  const [removingId, setRemovingId] = useState<string | null>(null);

  const handleRemove = async (resourceId: string) => {
    if (!onRemove) return;
    setRemovingId(resourceId);
    try {
      await onRemove(resourceId);
    } finally {
      setRemovingId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (resources.length === 0) {
    return (
      <div className={cn(
        "text-center py-6 border border-dashed border-border rounded-lg",
        compact && "py-4"
      )}>
        <AlertCircle className="w-8 h-8 mx-auto mb-2 text-muted-foreground/50" />
        <p className="text-sm text-muted-foreground">No platform resources linked</p>
        <p className="text-xs text-muted-foreground mt-1">
          Link Slack channels, Gmail labels, or Notion pages to enable cross-platform context
        </p>
        {onAdd && (
          <button
            onClick={onAdd}
            className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/5 rounded-md"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Resource
          </button>
        )}
      </div>
    );
  }

  // Group resources by platform
  const grouped = resources.reduce((acc, resource) => {
    const platform = resource.platform;
    if (!acc[platform]) acc[platform] = [];
    acc[platform].push(resource);
    return acc;
  }, {} as Record<string, ProjectResource[]>);

  return (
    <div className="space-y-3">
      {Object.entries(grouped).map(([platform, platformResources]) => {
        const config = PLATFORM_CONFIG[platform];
        if (!config) return null;

        const PlatformIcon = config.icon;

        return (
          <div key={platform} className="border border-border rounded-lg overflow-hidden">
            {/* Platform header */}
            <div className={cn(
              "flex items-center gap-2 px-3 py-2",
              config.bgColor
            )}>
              <PlatformIcon className={cn("w-4 h-4", config.color)} />
              <span className="text-sm font-medium">{config.label}</span>
              <span className="text-xs text-muted-foreground">
                ({platformResources.length})
              </span>
            </div>

            {/* Resources list */}
            <div className="divide-y divide-border">
              {platformResources.map((resource) => {
                const TypeIcon = RESOURCE_TYPE_ICONS[resource.resource_type] || FileText;
                const isRemoving = removingId === resource.id;

                return (
                  <div
                    key={resource.id}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2 bg-background",
                      isRemoving && "opacity-50"
                    )}
                  >
                    <TypeIcon className="w-4 h-4 text-muted-foreground shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {resource.resource_name || resource.resource_id}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {resource.resource_type}
                        {resource.is_primary && (
                          <span className="ml-1.5 text-primary">(primary)</span>
                        )}
                      </p>
                    </div>
                    {onRemove && (
                      <button
                        onClick={() => handleRemove(resource.id)}
                        disabled={isRemoving}
                        className="p-1 text-muted-foreground hover:text-red-600 hover:bg-red-50 rounded"
                        title="Remove resource"
                      >
                        {isRemoving ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

      {/* Add button */}
      {onAdd && (
        <button
          onClick={onAdd}
          className="w-full flex items-center justify-center gap-1.5 py-2 border border-dashed border-border rounded-lg text-sm text-muted-foreground hover:text-foreground hover:border-muted-foreground/50 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Platform Resource
        </button>
      )}
    </div>
  );
}
