"use client";

/**
 * ADR-033: Platform-First Onboarding Prompt
 *
 * Replaces the legacy WelcomePrompt with a platform-centric approach.
 * Guides users to connect their tools (Slack, Gmail, Notion) as the
 * primary way to build context with YARNNN.
 */

import { Loader2, CheckCircle2, ArrowRight, Settings } from "lucide-react";
import { SlackIcon, GmailIcon, NotionIcon } from "@/components/ui/PlatformIcons";

interface PlatformOnboardingPromptProps {
  /** Navigate to settings to connect platforms */
  onConnectPlatforms: () => void;
  /** Start chatting without connecting platforms */
  onSkip: () => void;
}

/**
 * Full onboarding prompt for new users with no platforms connected.
 * Shows the value of connecting platforms and provides CTAs.
 */
export function PlatformOnboardingPrompt({
  onConnectPlatforms,
  onSkip,
}: PlatformOnboardingPromptProps) {
  return (
    <div className="flex flex-col items-center justify-center py-8 px-4 max-w-2xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-xl font-semibold mb-2">
          Welcome to YARNNN
        </h2>
        <p className="text-muted-foreground">
          Connect your tools and I&apos;ll learn your context automatically.
          No manual uploads needed.
        </p>
      </div>

      {/* Platform Cards */}
      <div className="w-full grid grid-cols-3 gap-4 mb-8">
        <PlatformCard
          icon={<SlackIcon className="w-8 h-8" />}
          name="Slack"
          description="Learn from your conversations and communication style"
        />
        <PlatformCard
          icon={<GmailIcon className="w-8 h-8" />}
          name="Gmail"
          description="Draft emails in your voice and track important threads"
        />
        <PlatformCard
          icon={<NotionIcon className="w-8 h-8" />}
          name="Notion"
          description="Import context from your docs and knowledge base"
        />
      </div>

      {/* CTAs */}
      <div className="flex flex-col items-center gap-3 w-full max-w-sm">
        <button
          onClick={onConnectPlatforms}
          className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium"
        >
          <Settings className="w-4 h-4" />
          Connect Your First Platform
          <ArrowRight className="w-4 h-4" />
        </button>
        <button
          onClick={onSkip}
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          Skip for now and start chatting
        </button>
      </div>
    </div>
  );
}

/**
 * Platform card showing available integration.
 */
function PlatformCard({
  icon,
  name,
  description,
}: {
  icon: React.ReactNode;
  name: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center gap-2 p-5 rounded-2xl border border-border/50 bg-card">
      {icon}
      <span className="text-sm font-medium">{name}</span>
      <span className="text-xs text-muted-foreground text-center">
        {description}
      </span>
    </div>
  );
}

interface PlatformSyncingBannerProps {
  /** Number of platforms currently syncing */
  syncingCount: number;
  /** Callback to view sync progress */
  onViewProgress?: () => void;
}

/**
 * Banner shown when platforms are connected but still syncing.
 * Provides visual feedback that context is being built.
 */
export function PlatformSyncingBanner({
  syncingCount,
  onViewProgress,
}: PlatformSyncingBannerProps) {
  return (
    <div className="mb-4 p-4 bg-primary/5 border border-primary/20 rounded-2xl flex items-center justify-between">
      <div className="flex items-center gap-3">
        <Loader2 className="w-5 h-5 animate-spin text-primary" />
        <div>
          <p className="text-sm font-medium">
            Building your context...
          </p>
          <p className="text-xs text-muted-foreground">
            {syncingCount === 1
              ? "1 platform is syncing"
              : `${syncingCount} platforms are syncing`}
          </p>
        </div>
      </div>
      {onViewProgress && (
        <button
          onClick={onViewProgress}
          className="text-xs text-primary hover:underline"
        >
          View progress
        </button>
      )}
    </div>
  );
}

interface PlatformConnectedBannerProps {
  /** Number of connected platforms */
  platformCount: number;
  /** Total resources (channels, pages, etc.) */
  resourceCount: number;
  /** Callback to view platforms */
  onViewPlatforms?: () => void;
  /** Callback to dismiss the banner */
  onDismiss: () => void;
}

/**
 * Success banner shown after platforms are connected and synced.
 * Can be dismissed after the user acknowledges.
 */
export function PlatformConnectedBanner({
  platformCount,
  resourceCount,
  onViewPlatforms,
  onDismiss,
}: PlatformConnectedBannerProps) {
  return (
    <div className="mb-4 p-4 bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-900 rounded-2xl flex items-center justify-between">
      <div className="flex items-center gap-3">
        <CheckCircle2 className="w-5 h-5 text-green-600" />
        <div>
          <p className="text-sm font-medium text-green-800 dark:text-green-300">
            Context ready
          </p>
          <p className="text-xs text-green-600 dark:text-green-400">
            {platformCount} {platformCount === 1 ? "platform" : "platforms"} connected,{" "}
            {resourceCount} {resourceCount === 1 ? "resource" : "resources"} synced
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {onViewPlatforms && (
          <button
            onClick={onViewPlatforms}
            className="text-xs text-green-700 dark:text-green-400 hover:underline"
          >
            View platforms
          </button>
        )}
        <button
          onClick={onDismiss}
          className="text-xs text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-300 px-2 py-1 rounded-full hover:bg-green-100 dark:hover:bg-green-900/30 transition-colors"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}

interface NoPlatformsBannerProps {
  /** Navigate to settings to connect platforms */
  onConnect: () => void;
  /** Callback to dismiss the banner */
  onDismiss: () => void;
}

/**
 * Subtle banner for existing users who haven't connected platforms.
 * Less intrusive than the full onboarding prompt.
 */
export function NoPlatformsBanner({
  onConnect,
  onDismiss,
}: NoPlatformsBannerProps) {
  return (
    <div className="mb-4 p-4 bg-muted/50 rounded-2xl flex items-center justify-between">
      <p className="text-sm text-muted-foreground">
        Connect Slack, Gmail, or Notion to automatically build your context.
      </p>
      <div className="flex items-center gap-2">
        <button
          onClick={onConnect}
          className="text-xs text-primary hover:underline"
        >
          Connect
        </button>
        <button
          onClick={onDismiss}
          className="text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded-full hover:bg-muted transition-colors"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
