'use client';

/**
 * ADR-049: Platform Sync Status with Inline Connections
 *
 * Shows connected platforms and their sync freshness on the welcome screen.
 * Includes direct OAuth connection buttons for unconnected platforms.
 *
 * Key behaviors:
 * - Connected platforms: Show sync status with item counts
 * - Unconnected platforms: Show connect button that starts OAuth
 * - Manage sources: Navigate to /context/{platform} (singular selection UX)
 * - Document upload: Alternative entry point for users without platforms
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import {
  MessageSquare,
  Mail,
  FileText,
  Calendar,
  AlertCircle,
  CheckCircle2,
  Loader2,
  ExternalLink,
  Plus,
  Upload,
  File,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';
import { useRouter } from 'next/navigation';
import { useDocuments, UploadProgress } from '@/hooks/useDocuments';

type Provider = 'slack' | 'gmail' | 'notion' | 'calendar';

interface Integration {
  id: string;
  provider: string;
  status: string;
  workspace_name?: string | null;
  last_used_at?: string | null;
  created_at?: string;
}

interface SyncResource {
  resource_id: string;
  resource_name: string | null;
  last_synced: string | null;
  freshness_status: 'fresh' | 'recent' | 'stale' | 'unknown';
  items_synced: number;
}

interface SyncStatus {
  platform: string;
  synced_resources: SyncResource[];
  stale_count: number;
}

const PLATFORM_CONFIG: Record<string, {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  color: string;
  bgColor: string;
  connectLabel: string;
}> = {
  slack: {
    icon: MessageSquare,
    label: 'Slack',
    color: 'text-purple-600',
    bgColor: 'bg-purple-100 dark:bg-purple-900/30',
    connectLabel: 'channels',
  },
  gmail: {
    icon: Mail,
    label: 'Gmail',
    color: 'text-red-600',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
    connectLabel: 'inbox',
  },
  notion: {
    icon: FileText,
    label: 'Notion',
    color: 'text-gray-700 dark:text-gray-300',
    bgColor: 'bg-gray-100 dark:bg-gray-800',
    connectLabel: 'pages',
  },
  calendar: {
    icon: Calendar,
    label: 'Calendar',
    color: 'text-blue-600',
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
    connectLabel: 'schedule',
  },
};

// All available platforms in display order
const ALL_PLATFORMS: Provider[] = ['slack', 'gmail', 'notion', 'calendar'];

interface PlatformSyncStatusProps {
  className?: string;
}

// Allowed document types (matching backend)
const ALLOWED_DOC_TYPES = ['.pdf', '.docx', '.txt', '.md'];
const ALLOWED_MIME_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'text/markdown',
];

export function PlatformSyncStatus({ className }: PlatformSyncStatusProps) {
  const router = useRouter();

  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [syncStatuses, setSyncStatuses] = useState<Record<string, SyncStatus>>({});
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<string | null>(null);

  // Document upload state
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { documents, upload: uploadDocument, uploadProgress } = useDocuments();

  const loadIntegrations = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.integrations.list();
      const activeIntegrations = data.integrations.filter(
        (i: Integration) => i.status === 'active'
      );
      setIntegrations(activeIntegrations);

      // Load sync status for each platform
      for (const integration of activeIntegrations) {
        try {
          const status = await api.integrations.getSyncStatus(integration.provider);
          setSyncStatuses((prev) => ({
            ...prev,
            [integration.provider]: status,
          }));
        } catch (err) {
          console.error(`Failed to get sync status for ${integration.provider}:`, err);
        }
      }
    } catch (err) {
      console.error('Failed to load integrations:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadIntegrations();
  }, [loadIntegrations]);

  const handleConnect = async (provider: Provider) => {
    setConnecting(provider);
    try {
      // Calendar uses Google OAuth
      const authProvider = provider === 'calendar' ? 'google' : provider;
      const result = await api.integrations.getAuthorizationUrl(authProvider);
      // Redirect to OAuth — callback redirects to /context/{platform}?status=connected
      window.location.href = result.authorization_url;
    } catch (err) {
      console.error(`Failed to initiate ${provider} OAuth:`, err);
      setConnecting(null);
    }
  };

  // Check if a platform is connected
  const isConnected = (provider: Provider): boolean => {
    // Gmail and Calendar both use Google OAuth — check for gmail row
    if (provider === 'gmail' || provider === 'calendar') {
      return integrations.some(i => i.provider === 'gmail');
    }
    return integrations.some(i => i.provider === provider);
  };

  // Get integration for a provider
  const getIntegration = (provider: Provider): Integration | undefined => {
    if (provider === 'gmail' || provider === 'calendar') {
      return integrations.find(i => i.provider === 'gmail');
    }
    return integrations.find(i => i.provider === provider);
  };

  // Get sync status for a provider
  const getSyncStatus = (provider: Provider): SyncStatus | undefined => {
    if (provider === 'gmail' || provider === 'calendar') {
      return syncStatuses['gmail'];
    }
    return syncStatuses[provider];
  };

  if (loading) {
    return (
      <div className={cn('flex items-center justify-center gap-2 text-muted-foreground text-sm', className)}>
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>Loading platforms...</span>
      </div>
    );
  }

  const connectedPlatforms = ALL_PLATFORMS.filter(p => isConnected(p));
  const unconnectedPlatforms = ALL_PLATFORMS.filter(p => !isConnected(p));

  return (
    <div className={cn('max-w-lg mx-auto', className)}>
      {/* Connected Platforms */}
      {connectedPlatforms.length > 0 && (
        <div className="mb-4">
          <p className="text-xs text-muted-foreground mb-2 text-center">Connected platforms</p>
          <div className="space-y-2">
            {connectedPlatforms.map((provider) => {
              const config = PLATFORM_CONFIG[provider];
              const Icon = config.icon;
              const integration = getIntegration(provider);
              const status = getSyncStatus(provider);
              const hasStale = status?.stale_count ? status.stale_count > 0 : false;
              const resourceCount = status?.synced_resources?.length || 0;

              // Find most recent sync
              const mostRecentSync = status?.synced_resources?.reduce((latest, r) => {
                if (!r.last_synced) return latest;
                if (!latest) return r.last_synced;
                return new Date(r.last_synced) > new Date(latest) ? r.last_synced : latest;
              }, null as string | null);

              return (
                <div
                  key={provider}
                  className={cn(
                    'flex items-center gap-3 px-4 py-3 rounded-xl border',
                    hasStale ? 'border-amber-300 bg-amber-50/50 dark:bg-amber-950/20' : 'border-border bg-card'
                  )}
                >
                  <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center', config.bgColor)}>
                    <Icon className={cn('w-5 h-5', config.color)} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{config.label}</span>
                      {integration?.workspace_name && (
                        <span className="text-xs text-muted-foreground truncate">
                          {integration.workspace_name}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      {resourceCount > 0 ? (
                        <>
                          {hasStale ? (
                            <AlertCircle className="w-3 h-3 text-amber-500" />
                          ) : (
                            <CheckCircle2 className="w-3 h-3 text-green-500" />
                          )}
                          <span>
                            {resourceCount} source{resourceCount !== 1 ? 's' : ''}
                            {mostRecentSync && (
                              <> synced {formatDistanceToNow(new Date(mostRecentSync), { addSuffix: true })}</>
                            )}
                          </span>
                        </>
                      ) : (
                        <span className="text-amber-600">No sources selected</span>
                      )}
                    </div>
                  </div>
                  {/* Navigate to context page for source management */}
                  <button
                    onClick={() => router.push(`/context/${provider}`)}
                    className="p-1.5 hover:bg-muted rounded-md transition-colors"
                    title={`Manage ${config.connectLabel}`}
                  >
                    <Plus className="w-4 h-4 text-muted-foreground" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Unconnected Platforms */}
      {unconnectedPlatforms.length > 0 && (
        <div>
          {connectedPlatforms.length > 0 && (
            <p className="text-xs text-muted-foreground mb-2 text-center">Connect more</p>
          )}
          <div className="flex flex-wrap justify-center gap-2">
            {unconnectedPlatforms.map((provider) => {
              const config = PLATFORM_CONFIG[provider];
              const Icon = config.icon;
              const isConnecting = connecting === provider;

              return (
                <button
                  key={provider}
                  onClick={() => handleConnect(provider)}
                  disabled={isConnecting}
                  className={cn(
                    'flex items-center gap-2 px-4 py-2.5 rounded-xl border border-dashed border-border',
                    'hover:border-primary/50 hover:bg-primary/5 transition-colors',
                    'disabled:opacity-50 disabled:cursor-not-allowed'
                  )}
                >
                  {isConnecting ? (
                    <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                  ) : (
                    <Icon className={cn('w-4 h-4', config.color)} />
                  )}
                  <span className="text-sm">{config.label}</span>
                  {!isConnecting && (
                    <ExternalLink className="w-3 h-3 text-muted-foreground" />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Document Upload Section */}
      <div className="mt-4 pt-4 border-t border-border/50">
        <input
          ref={fileInputRef}
          type="file"
          accept={ALLOWED_DOC_TYPES.join(',')}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              // Validate file type
              const ext = '.' + file.name.split('.').pop()?.toLowerCase();
              if (ALLOWED_DOC_TYPES.includes(ext) || ALLOWED_MIME_TYPES.includes(file.type)) {
                uploadDocument(file);
              }
            }
            // Reset input
            if (fileInputRef.current) {
              fileInputRef.current.value = '';
            }
          }}
          className="hidden"
        />

        {/* Upload progress indicator */}
        {uploadProgress && (
          <div className="mb-3 flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/50 text-sm">
            {uploadProgress.status === 'uploading' || uploadProgress.status === 'processing' ? (
              <Loader2 className="w-4 h-4 animate-spin text-primary" />
            ) : uploadProgress.status === 'completed' ? (
              <CheckCircle2 className="w-4 h-4 text-green-500" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-500" />
            )}
            <span className="truncate flex-1">{uploadProgress.filename}</span>
            <span className="text-xs text-muted-foreground capitalize">{uploadProgress.status}</span>
          </div>
        )}

        {/* Show uploaded documents count if any */}
        {documents.length > 0 && (
          <div className="mb-3 flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/30 text-sm">
            <File className="w-4 h-4 text-muted-foreground" />
            <span>{documents.length} document{documents.length !== 1 ? 's' : ''} uploaded</span>
            <CheckCircle2 className="w-3 h-3 text-green-500 ml-auto" />
          </div>
        )}

        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploadProgress?.status === 'uploading' || uploadProgress?.status === 'processing'}
          className={cn(
            'w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl',
            'border border-dashed border-border text-sm',
            'hover:border-primary/50 hover:bg-primary/5 transition-colors',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          <Upload className="w-4 h-4 text-muted-foreground" />
          <span>Upload documents</span>
          <span className="text-xs text-muted-foreground">(PDF, DOCX, TXT, MD)</span>
        </button>
      </div>

      {/* No platforms at all - full onboarding prompt */}
      {connectedPlatforms.length === 0 && (
        <p className="text-xs text-muted-foreground text-center mt-3">
          Free plan: 2 sources per platform, syncs 2x daily
        </p>
      )}
    </div>
  );
}

export default PlatformSyncStatus;
