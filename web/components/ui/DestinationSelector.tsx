'use client';

/**
 * DestinationSelector - ADR-032 Phase 2
 *
 * Platform-first destination picker. Shows connected integrations
 * and allows selecting where deliverables should be sent.
 *
 * This is step 1 in the platform-first flow:
 * Destination → Type → Sources → Schedule
 */

import { useState, useEffect } from 'react';
import {
  Mail,
  Slack,
  FileCode,
  Download,
  Calendar,
  ChevronRight,
  Check,
  Loader2,
  ExternalLink,
  AlertCircle,
} from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type { Destination, IntegrationProvider } from '@/types';

interface Integration {
  id: string;
  provider: string;
  status: string;
  workspace_name: string | null;
  last_used_at: string | null;
  created_at: string;
}

interface DestinationSelectorProps {
  value: Destination | undefined;
  onChange: (destination: Destination | undefined) => void;
  onClose?: () => void;
}

const PLATFORM_CONFIG: Record<string, {
  icon: React.ReactNode;
  label: string;
  color: string;
  formats: { value: string; label: string; description: string }[];
}> = {
  gmail: {
    icon: <Mail className="w-5 h-5" />,
    label: 'Gmail',
    color: 'text-red-500',
    formats: [
      { value: 'draft', label: 'Draft', description: 'Creates a draft in your Gmail' },
      { value: 'send', label: 'Send directly', description: 'Sends email immediately' },
    ],
  },
  slack: {
    icon: <Slack className="w-5 h-5" />,
    label: 'Slack',
    color: 'text-purple-500',
    formats: [
      { value: 'dm_draft', label: 'Draft (DM)', description: 'Sends you a DM with content to copy' },
      { value: 'message', label: 'Post to channel', description: 'Posts directly to channel' },
    ],
  },
  notion: {
    icon: <FileCode className="w-5 h-5" />,
    label: 'Notion',
    color: 'text-gray-700',
    formats: [
      { value: 'draft', label: 'Draft page', description: 'Creates draft in your YARNNN Drafts' },
      { value: 'page', label: 'Create page', description: 'Creates page directly in target' },
    ],
  },
  download: {
    icon: <Download className="w-5 h-5" />,
    label: 'Download',
    color: 'text-blue-500',
    formats: [
      { value: 'markdown', label: 'Markdown', description: 'Download as .md file' },
    ],
  },
  google: {
    icon: <Calendar className="w-5 h-5" />,
    label: 'Google',
    color: 'text-blue-500',
    formats: [
      { value: 'draft', label: 'Draft', description: 'Creates a draft in your Gmail' },
    ],
  },
  calendar: {
    icon: <Calendar className="w-5 h-5" />,
    label: 'Calendar',
    color: 'text-blue-500',
    formats: [
      { value: 'markdown', label: 'Download', description: 'Download as markdown file' },
    ],
  },
};

export function DestinationSelector({
  value,
  onChange,
  onClose,
}: DestinationSelectorProps) {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selection state
  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(
    value?.platform || null
  );
  const [selectedFormat, setSelectedFormat] = useState<string | null>(
    value?.format || null
  );
  const [target, setTarget] = useState(value?.target || '');

  // Slack channels for picker
  const [slackChannels, setSlackChannels] = useState<Array<{
    id: string;
    name: string;
    is_private: boolean;
  }>>([]);
  const [loadingChannels, setLoadingChannels] = useState(false);

  // Load integrations
  useEffect(() => {
    const loadIntegrations = async () => {
      try {
        const result = await api.integrations.list();
        setIntegrations(result.integrations.filter(i => i.status === 'connected'));
      } catch (err) {
        console.error('Failed to load integrations:', err);
        setError('Failed to load integrations');
      } finally {
        setLoading(false);
      }
    };
    loadIntegrations();
  }, []);

  // Load Slack channels when Slack is selected
  useEffect(() => {
    if (selectedPlatform === 'slack') {
      const loadChannels = async () => {
        setLoadingChannels(true);
        try {
          const result = await api.integrations.listSlackChannels();
          setSlackChannels(result.channels || []);
        } catch (err) {
          console.error('Failed to load Slack channels:', err);
        } finally {
          setLoadingChannels(false);
        }
      };
      loadChannels();
    }
  }, [selectedPlatform]);

  // Update parent when selection changes
  useEffect(() => {
    if (selectedPlatform && selectedFormat) {
      const destination: Destination = {
        platform: selectedPlatform as IntegrationProvider | 'download',
        format: selectedFormat,
        target: target || undefined,
      };
      onChange(destination);
    }
  }, [selectedPlatform, selectedFormat, target, onChange]);

  const isConnected = (platform: string) => {
    if (platform === 'download') return true;
    return integrations.some(i => i.provider === platform);
  };

  const getIntegration = (platform: string) => {
    return integrations.find(i => i.provider === platform);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Step 1: Select platform
  if (!selectedPlatform) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Where should this deliverable appear?
        </p>

        <div className="grid grid-cols-2 gap-2">
          {Object.entries(PLATFORM_CONFIG).map(([platform, config]) => {
            const connected = isConnected(platform);
            const integration = getIntegration(platform);

            return (
              <button
                key={platform}
                onClick={() => connected && setSelectedPlatform(platform)}
                disabled={!connected}
                className={cn(
                  "p-4 rounded-lg border text-left transition-all",
                  connected
                    ? "border-border hover:border-primary hover:bg-primary/5 cursor-pointer"
                    : "border-dashed border-border/50 opacity-50 cursor-not-allowed"
                )}
              >
                <div className="flex items-center gap-3">
                  <div className={cn("shrink-0", config.color)}>
                    {config.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm">{config.label}</div>
                    {connected ? (
                      <div className="text-xs text-muted-foreground truncate">
                        {integration?.workspace_name || 'Connected'}
                      </div>
                    ) : (
                      <div className="text-xs text-amber-600">
                        Not connected
                      </div>
                    )}
                  </div>
                  {connected && (
                    <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {integrations.length === 0 && (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-md text-sm text-amber-800">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <div>
                <p className="font-medium">No integrations connected</p>
                <p className="text-xs mt-1">
                  Connect Gmail, Slack, or Notion to enable platform delivery.
                </p>
                <Link
                  href="/settings?tab=integrations"
                  className="text-xs text-amber-700 hover:underline inline-flex items-center gap-1 mt-2"
                  onClick={onClose}
                >
                  Connect integrations
                  <ExternalLink className="w-3 h-3" />
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  const platformConfig = PLATFORM_CONFIG[selectedPlatform];

  // Step 2: Select format and target
  return (
    <div className="space-y-4">
      {/* Platform header */}
      <div className="flex items-center gap-3 pb-3 border-b border-border">
        <button
          onClick={() => {
            setSelectedPlatform(null);
            setSelectedFormat(null);
            setTarget('');
          }}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Back
        </button>
        <div className={cn("shrink-0", platformConfig.color)}>
          {platformConfig.icon}
        </div>
        <span className="font-medium">{platformConfig.label}</span>
      </div>

      {/* Format selection */}
      <div>
        <label className="block text-sm font-medium mb-2">Delivery mode</label>
        <div className="space-y-2">
          {platformConfig.formats.map((format) => (
            <button
              key={format.value}
              onClick={() => setSelectedFormat(format.value)}
              className={cn(
                "w-full p-3 rounded-md border text-left transition-colors",
                selectedFormat === format.value
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-muted-foreground/50"
              )}
            >
              <div className="flex items-center gap-2">
                {selectedFormat === format.value && (
                  <Check className="w-4 h-4 text-primary shrink-0" />
                )}
                <div className="flex-1">
                  <div className="text-sm font-medium">{format.label}</div>
                  <div className="text-xs text-muted-foreground">
                    {format.description}
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Target input (platform-specific) */}
      {selectedFormat && selectedPlatform === 'gmail' && (
        <div>
          <label className="block text-sm font-medium mb-1.5">
            Recipient email
          </label>
          <input
            type="email"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="recipient@example.com"
            className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
          <p className="text-xs text-muted-foreground mt-1">
            The email address this will be sent to
          </p>
        </div>
      )}

      {selectedFormat && selectedPlatform === 'slack' && (
        <div>
          <label className="block text-sm font-medium mb-1.5">
            {selectedFormat === 'dm_draft' ? 'Target channel' : 'Channel'}
          </label>
          {loadingChannels ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading channels...
            </div>
          ) : slackChannels.length > 0 ? (
            <select
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="">Select a channel...</option>
              {slackChannels.map((channel) => (
                <option key={channel.id} value={`#${channel.name}`}>
                  #{channel.name} {channel.is_private && '(private)'}
                </option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="#channel-name or C123456"
              className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          )}
          {selectedFormat === 'dm_draft' && (
            <p className="text-xs text-muted-foreground mt-1">
              You'll receive a DM with content to copy to this channel
            </p>
          )}
        </div>
      )}

      {selectedFormat && selectedPlatform === 'notion' && (
        <div>
          <label className="block text-sm font-medium mb-1.5">
            Target page
          </label>
          <input
            type="text"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="Page name or ID"
            className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
          <p className="text-xs text-muted-foreground mt-1">
            {selectedFormat === 'draft'
              ? 'Target for reference (draft will be in YARNNN Drafts)'
              : 'The page this will be created under'}
          </p>
        </div>
      )}

      {/* Summary */}
      {selectedFormat && (
        <div className="p-3 bg-muted/50 rounded-md">
          <div className="text-sm">
            <span className="font-medium">Summary: </span>
            {selectedPlatform === 'gmail' && selectedFormat === 'draft' && (
              <span>Draft will appear in your Gmail Drafts folder</span>
            )}
            {selectedPlatform === 'gmail' && selectedFormat === 'send' && (
              <span>Email will be sent to {target || '(enter email)'}</span>
            )}
            {selectedPlatform === 'slack' && selectedFormat === 'dm_draft' && (
              <span>You'll receive a DM with content for {target || '(select channel)'}</span>
            )}
            {selectedPlatform === 'slack' && selectedFormat === 'message' && (
              <span>Message will post to {target || '(select channel)'}</span>
            )}
            {selectedPlatform === 'notion' && selectedFormat === 'draft' && (
              <span>Draft page will be created in YARNNN Drafts</span>
            )}
            {selectedPlatform === 'notion' && selectedFormat === 'page' && (
              <span>Page will be created under {target || '(enter target)'}</span>
            )}
            {selectedPlatform === 'download' && (
              <span>File will be available for download</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
