'use client';

/**
 * SourcePicker - Platform source selection for create wizard
 *
 * Step 3 in the destination-first flow:
 * Destination → Type → Sources → Schedule
 *
 * Shows connected platform resources that can be selected as sources.
 */

import { useState, useEffect } from 'react';
import { Loader2, Check, Mail, Slack, FileCode, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type { DataSource, IntegrationProvider } from '@/types';

interface PlatformResource {
  id: string;
  name: string;
  type: string;
  provider: IntegrationProvider;
}

interface SourcePickerProps {
  value: DataSource[];
  onChange: (sources: DataSource[]) => void;
  /** Suggested platform based on destination */
  suggestedPlatform?: IntegrationProvider;
}

const PLATFORM_CONFIG: Record<
  string,
  {
    icon: React.ReactNode;
    label: string;
    color: string;
  }
> = {
  slack: {
    icon: <Slack className="w-4 h-4" />,
    label: 'Slack',
    color: 'text-purple-500',
  },
  gmail: {
    icon: <Mail className="w-4 h-4" />,
    label: 'Gmail',
    color: 'text-red-500',
  },
  notion: {
    icon: <FileCode className="w-4 h-4" />,
    label: 'Notion',
    color: 'text-gray-700',
  },
};

export function SourcePicker({ value, onChange, suggestedPlatform }: SourcePickerProps) {
  const [loading, setLoading] = useState(true);
  const [resources, setResources] = useState<PlatformResource[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadResources();
  }, []);

  const loadResources = async () => {
    setLoading(true);
    setError(null);
    try {
      // Load all available platform resources
      const allResources: PlatformResource[] = [];

      // Try to load Slack channels
      try {
        const slackResult = await api.integrations.listSlackChannels();
        if (slackResult.channels) {
          allResources.push(
            ...slackResult.channels.map((ch: { id: string; name: string }) => ({
              id: ch.id,
              name: `#${ch.name}`,
              type: 'channel',
              provider: 'slack' as IntegrationProvider,
            }))
          );
        }
      } catch {
        // Slack not connected, ignore
      }

      // Try to load Notion pages
      try {
        const notionResult = await api.integrations.listNotionPages();
        if (notionResult.pages) {
          allResources.push(
            ...notionResult.pages.slice(0, 10).map((p: { id: string; title: string }) => ({
              id: p.id,
              name: p.title,
              type: 'page',
              provider: 'notion' as IntegrationProvider,
            }))
          );
        }
      } catch {
        // Notion not connected, ignore
      }

      // Add Gmail inbox as a default option if Gmail is connected
      try {
        const integrations = await api.integrations.list();
        const hasGmail = integrations.integrations?.some(
          (i) => i.provider === 'gmail' && i.status === 'connected'
        );
        if (hasGmail) {
          allResources.push({
            id: 'inbox',
            name: 'Inbox',
            type: 'label',
            provider: 'gmail' as IntegrationProvider,
          });
        }
      } catch {
        // Ignore
      }

      // Sort suggested platform first
      if (suggestedPlatform) {
        allResources.sort((a, b) => {
          if (a.provider === suggestedPlatform && b.provider !== suggestedPlatform) return -1;
          if (a.provider !== suggestedPlatform && b.provider === suggestedPlatform) return 1;
          return 0;
        });
      }

      setResources(allResources);
    } catch (err) {
      console.error('Failed to load resources:', err);
      setError('Failed to load platform resources');
    } finally {
      setLoading(false);
    }
  };

  const isSelected = (resource: PlatformResource) => {
    return value.some(
      (s) =>
        s.type === 'integration_import' &&
        s.provider === resource.provider &&
        s.source === resource.id
    );
  };

  const toggleResource = (resource: PlatformResource) => {
    if (isSelected(resource)) {
      // Remove
      onChange(
        value.filter(
          (s) =>
            !(
              s.type === 'integration_import' &&
              s.provider === resource.provider &&
              s.source === resource.id
            )
        )
      );
    } else {
      // Add
      const newSource: DataSource = {
        type: 'integration_import',
        value: `${resource.provider}:${resource.id}`,
        label: `${PLATFORM_CONFIG[resource.provider]?.label || resource.provider} - ${resource.name}`,
        provider: resource.provider,
        source: resource.id,
        scope: {
          mode: 'delta',
          fallback_days: 7,
          max_items: 200,
        },
      };
      onChange([...value, newSource]);
    }
  };

  // Group resources by platform
  const groupedResources = resources.reduce(
    (acc, resource) => {
      if (!acc[resource.provider]) {
        acc[resource.provider] = [];
      }
      acc[resource.provider].push(resource);
      return acc;
    },
    {} as Record<string, PlatformResource[]>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center gap-2">
        <AlertCircle className="w-4 h-4 shrink-0" />
        {error}
      </div>
    );
  }

  if (resources.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <p className="text-sm">No platform resources available</p>
        <p className="text-xs mt-1">Connect platforms in Settings to add sources</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Select sources to inform this deliverable. Content from these sources will be used to
        generate your output.
      </p>

      {Object.entries(groupedResources).map(([provider, providerResources]) => {
        const config = PLATFORM_CONFIG[provider];
        if (!config) return null;

        return (
          <div key={provider} className="space-y-2">
            <div className={cn('flex items-center gap-2 text-sm font-medium', config.color)}>
              {config.icon}
              {config.label}
            </div>

            <div className="grid grid-cols-2 gap-2">
              {providerResources.map((resource) => {
                const selected = isSelected(resource);
                return (
                  <button
                    key={`${resource.provider}-${resource.id}`}
                    type="button"
                    onClick={() => toggleResource(resource)}
                    className={cn(
                      'p-2.5 rounded-md border text-left transition-all text-sm',
                      selected
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-muted-foreground/50'
                    )}
                  >
                    <div className="flex items-center gap-2">
                      {selected && <Check className="w-3.5 h-3.5 text-primary shrink-0" />}
                      <span className={cn('truncate', !selected && 'ml-5.5')}>
                        {resource.name}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}

      {value.length > 0 && (
        <div className="pt-2 border-t border-border">
          <p className="text-xs text-muted-foreground">
            {value.length} source{value.length !== 1 ? 's' : ''} selected
          </p>
        </div>
      )}
    </div>
  );
}
