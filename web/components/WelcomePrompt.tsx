"use client";

import { Upload, ClipboardPaste, MessageSquare } from "lucide-react";

const STARTER_PROMPTS = [
  "I'm working on...",
  "Help me think through a decision",
];

interface WelcomePromptProps {
  /** Callback when user clicks "Upload a document" */
  onUpload: () => void;
  /** Callback when user clicks "Paste some text" */
  onPaste: () => void;
  /** Callback when user clicks "Just start" */
  onStart: () => void;
  /** Callback when user selects a starter prompt */
  onSelectPrompt: (prompt: string) => void;
}

/**
 * Cold start welcome UI for new users.
 *
 * Shows three equal CTAs (Upload, Paste, Just Start) and two starter prompts.
 * Based on ONBOARDING_STARTER_PROMPTS.md design spec.
 */
export function WelcomePrompt({
  onUpload,
  onPaste,
  onStart,
  onSelectPrompt,
}: WelcomePromptProps) {
  return (
    <div className="flex flex-col items-center justify-center py-8 px-4 max-w-2xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-xl font-semibold mb-2">
          Welcome! I&apos;m your Thinking Partner.
        </h2>
        <p className="text-muted-foreground">
          The more I know about you and your work, the better I can help you think.
        </p>
      </div>

      {/* Three CTAs */}
      <div className="grid grid-cols-3 gap-4 w-full mb-8">
        <button
          onClick={onUpload}
          className="flex flex-col items-center gap-2 p-5 rounded-2xl border border-border/50 bg-card hover:bg-muted hover:border-border transition-all hover:shadow-sm"
        >
          <Upload className="w-6 h-6 text-primary" />
          <span className="text-sm font-medium">Upload</span>
          <span className="text-xs text-muted-foreground">a document</span>
        </button>

        <button
          onClick={onPaste}
          className="flex flex-col items-center gap-2 p-5 rounded-2xl border border-border/50 bg-card hover:bg-muted hover:border-border transition-all hover:shadow-sm"
        >
          <ClipboardPaste className="w-6 h-6 text-primary" />
          <span className="text-sm font-medium">Paste</span>
          <span className="text-xs text-muted-foreground">some text</span>
        </button>

        <button
          onClick={onStart}
          className="flex flex-col items-center gap-2 p-5 rounded-2xl border border-border/50 bg-card hover:bg-muted hover:border-border transition-all hover:shadow-sm"
        >
          <MessageSquare className="w-6 h-6 text-primary" />
          <span className="text-sm font-medium">Just</span>
          <span className="text-xs text-muted-foreground">start</span>
        </button>
      </div>

      {/* Starter Prompts */}
      <div className="w-full">
        <p className="text-sm text-muted-foreground mb-3 text-center">
          Or try a conversation starter:
        </p>
        <div className="space-y-2">
          {STARTER_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              onClick={() => onSelectPrompt(prompt)}
              className="w-full p-4 text-left text-sm rounded-2xl border border-border/50 bg-card hover:bg-muted hover:border-border transition-all hover:shadow-sm"
            >
              &ldquo;{prompt}&rdquo;
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

interface MinimalContextBannerProps {
  memoryCount: number;
  onDismiss: () => void;
}

/**
 * Subtle banner for users with minimal context.
 * Shown when state is "minimal_context" (< 3 memories, no recent chat).
 */
export function MinimalContextBanner({
  memoryCount,
  onDismiss,
}: MinimalContextBannerProps) {
  return (
    <div className="mb-4 p-4 bg-muted/50 rounded-2xl flex items-center justify-between">
      <p className="text-sm text-muted-foreground">
        I don&apos;t know much about you yet ({memoryCount} {memoryCount === 1 ? "memory" : "memories"}).
        Share more context to get better help.
      </p>
      <button
        onClick={onDismiss}
        className="text-xs text-muted-foreground hover:text-foreground ml-4 px-3 py-1.5 rounded-full hover:bg-background transition-colors"
      >
        Dismiss
      </button>
    </div>
  );
}
