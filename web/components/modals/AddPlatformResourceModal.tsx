'use client';

/**
 * ADR-032 Phase 3: Add Platform Resource Modal
 *
 * Modal for linking a platform resource (Slack channel, Gmail label, Notion page)
 * to a project for cross-platform context gathering.
 */

import { useState, useEffect } from 'react';
import {
  X,
  Mail,
  Slack,
  FileText,
  Calendar,
  Loader2,
  Check,
  Sparkles,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import type { ProjectResourceCreate, ResourceSuggestion } from '@/types';

interface AddPlatformResourceModalProps {
  projectId: string;
  open: boolean;
  onClose: () => void;
  onAdded: () => void;
}

type Platform = 'slack' | 'gmail' | 'notion' | 'calendar';

const PLATFORM_CONFIG: Record<Platform, {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  color: string;
  bgColor: string;
  resourceTypes: { value: string; label: string }[];
  idPlaceholder: string;
  idHelp: string;
}> = {
  slack: {
    icon: Slack,
    label: 'Slack',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    resourceTypes: [
      { value: 'channel', label: 'Channel' },
    ],
    idPlaceholder: 'C01234567',
    idHelp: 'The Slack channel ID (starts with C)',
  },
  gmail: {
    icon: Mail,
    label: 'Gmail',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    resourceTypes: [
      { value: 'label', label: 'Label' },
    ],
    idPlaceholder: 'Label_123 or INBOX',
    idHelp: 'Gmail label ID or name',
  },
  notion: {
    icon: FileText,
    label: 'Notion',
    color: 'text-gray-700',
    bgColor: 'bg-gray-100',
    resourceTypes: [
      { value: 'page', label: 'Page' },
      { value: 'database', label: 'Database' },
    ],
    idPlaceholder: 'abc123def456...',
    idHelp: 'Notion page or database ID',
  },
  calendar: {
    icon: Calendar,
    label: 'Calendar',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    resourceTypes: [
      { value: 'calendar', label: 'Calendar' },
    ],
    idPlaceholder: 'primary or calendar@group.calendar.google.com',
    idHelp: 'Google Calendar ID',
  },
};

export function AddPlatformResourceModal({
  projectId,
  open,
  onClose,
  onAdded,
}: AddPlatformResourceModalProps) {
  const [step, setStep] = useState<'platform' | 'details'>('platform');
  const [selectedPlatform, setSelectedPlatform] = useState<Platform | null>(null);
  const [resourceType, setResourceType] = useState('');
  const [resourceId, setResourceId] = useState('');
  const [resourceName, setResourceName] = useState('');
  const [isPrimary, setIsPrimary] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Suggestions
  const [suggestions, setSuggestions] = useState<ResourceSuggestion[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);

  // Load suggestions when modal opens
  useEffect(() => {
    if (open && projectId) {
      loadSuggestions();
    }
  }, [open, projectId]);

  // Reset form when modal closes
  useEffect(() => {
    if (!open) {
      setStep('platform');
      setSelectedPlatform(null);
      setResourceType('');
      setResourceId('');
      setResourceName('');
      setIsPrimary(false);
      setError(null);
    }
  }, [open]);

  // Set default resource type when platform changes
  useEffect(() => {
    if (selectedPlatform) {
      const config = PLATFORM_CONFIG[selectedPlatform];
      setResourceType(config.resourceTypes[0]?.value || '');
    }
  }, [selectedPlatform]);

  const loadSuggestions = async () => {
    setLoadingSuggestions(true);
    try {
      const data = await api.projects.resources.suggest(projectId);
      setSuggestions(data);
    } catch (err) {
      console.error('Failed to load suggestions:', err);
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const handleSelectPlatform = (platform: Platform) => {
    setSelectedPlatform(platform);
    setStep('details');
  };

  const handleSelectSuggestion = (suggestion: ResourceSuggestion) => {
    setSelectedPlatform(suggestion.platform as Platform);
    setResourceId(suggestion.resource_id);
    setResourceName(suggestion.resource_name || '');
    setStep('details');
  };

  const handleSave = async () => {
    if (!selectedPlatform || !resourceId.trim()) {
      setError('Please fill in the resource ID');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const data: ProjectResourceCreate = {
        platform: selectedPlatform,
        resource_type: resourceType,
        resource_id: resourceId.trim(),
        resource_name: resourceName.trim() || undefined,
        is_primary: isPrimary,
      };

      await api.projects.resources.create(projectId, data);
      onAdded();
      onClose();
    } catch (err) {
      console.error('Failed to add resource:', err);
      if (err instanceof Error && err.message.includes('409')) {
        setError('This resource is already linked to the project');
      } else {
        setError('Failed to add resource. Please try again.');
      }
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;

  const config = selectedPlatform ? PLATFORM_CONFIG[selectedPlatform] : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-background rounded-lg shadow-lg w-full max-w-md mx-4 max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
          <h2 className="font-medium">
            {step === 'platform' ? 'Add Platform Resource' : `Add ${config?.label} Resource`}
          </h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-muted rounded"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {step === 'platform' ? (
            <div className="space-y-4">
              {/* Platform selection */}
              <div>
                <label className="block text-sm font-medium mb-2">Select Platform</label>
                <div className="grid grid-cols-2 gap-2">
                  {(Object.entries(PLATFORM_CONFIG) as [Platform, typeof PLATFORM_CONFIG[Platform]][]).map(
                    ([platform, platformConfig]) => {
                      const Icon = platformConfig.icon;
                      return (
                        <button
                          key={platform}
                          onClick={() => handleSelectPlatform(platform)}
                          className={cn(
                            "flex items-center gap-3 p-3 rounded-lg border text-left transition-colors",
                            "border-border hover:border-primary hover:bg-primary/5"
                          )}
                        >
                          <div className={cn("shrink-0", platformConfig.color)}>
                            <Icon className="w-5 h-5" />
                          </div>
                          <span className="text-sm font-medium">{platformConfig.label}</span>
                          <ChevronRight className="w-4 h-4 text-muted-foreground ml-auto" />
                        </button>
                      );
                    }
                  )}
                </div>
              </div>

              {/* Suggestions */}
              {suggestions.length > 0 && (
                <div>
                  <label className="block text-sm font-medium mb-2 flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-amber-500" />
                    Suggested Resources
                  </label>
                  <div className="space-y-2">
                    {suggestions.slice(0, 5).map((suggestion, index) => {
                      const sugConfig = PLATFORM_CONFIG[suggestion.platform as Platform];
                      if (!sugConfig) return null;
                      const Icon = sugConfig.icon;

                      return (
                        <button
                          key={index}
                          onClick={() => handleSelectSuggestion(suggestion)}
                          className="w-full flex items-center gap-3 p-3 rounded-lg border border-border hover:border-primary hover:bg-primary/5 text-left transition-colors"
                        >
                          <div className={cn("shrink-0", sugConfig.color)}>
                            <Icon className="w-4 h-4" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">
                              {suggestion.resource_name || suggestion.resource_id}
                            </p>
                            <p className="text-xs text-muted-foreground">{suggestion.reason}</p>
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {Math.round(suggestion.confidence * 100)}%
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {loadingSuggestions && (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                  <span className="ml-2 text-sm text-muted-foreground">Loading suggestions...</span>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {/* Back button */}
              <button
                onClick={() => setStep('platform')}
                className="text-sm text-muted-foreground hover:text-foreground"
              >
                ← Back to platforms
              </button>

              {/* Platform indicator */}
              {config && (
                <div className={cn("flex items-center gap-2 p-3 rounded-lg", config.bgColor)}>
                  <config.icon className={cn("w-5 h-5", config.color)} />
                  <span className="font-medium">{config.label}</span>
                </div>
              )}

              {/* Resource type */}
              {config && config.resourceTypes.length > 1 && (
                <div>
                  <label className="block text-sm font-medium mb-1.5">Resource Type</label>
                  <select
                    value={resourceType}
                    onChange={(e) => setResourceType(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    {config.resourceTypes.map((type) => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Resource ID */}
              <div>
                <label className="block text-sm font-medium mb-1.5">Resource ID</label>
                <input
                  type="text"
                  value={resourceId}
                  onChange={(e) => setResourceId(e.target.value)}
                  placeholder={config?.idPlaceholder}
                  className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
                <p className="text-xs text-muted-foreground mt-1">{config?.idHelp}</p>
              </div>

              {/* Resource name (optional) */}
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  Display Name <span className="text-muted-foreground">(optional)</span>
                </label>
                <input
                  type="text"
                  value={resourceName}
                  onChange={(e) => setResourceName(e.target.value)}
                  placeholder="e.g., #team-updates"
                  className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>

              {/* Primary checkbox */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isPrimary}
                  onChange={(e) => setIsPrimary(e.target.checked)}
                  className="w-4 h-4 rounded border-border"
                />
                <span className="text-sm">Set as primary resource for this platform</span>
              </label>

              {/* Error */}
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700">
                  {error}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        {step === 'details' && (
          <div className="flex items-center justify-end gap-3 px-4 py-3 border-t border-border shrink-0">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm hover:bg-muted rounded-md"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !resourceId.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90 disabled:opacity-50"
            >
              {saving ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Check className="w-4 h-4" />
              )}
              Add Resource
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
