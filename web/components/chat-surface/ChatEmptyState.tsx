'use client';

/**
 * ChatEmptyState — YARNNN's deterministic first-turn welcome surface (ADR-190).
 *
 * Rendered by ChatPanel when messages.length === 0. Replaces the prior
 * silent-canvas empty state. Zero LLM cost — this is hardcoded client-side
 * copy that establishes the authored-team frame before the user types.
 *
 * Four chips prompt high-density input behaviors:
 *   1. Upload a doc — rich input (file drop)
 *   2. Paste a URL — rich input (link paste)
 *   3. Track something recurring — text-intent seed
 *   4. Build a recurring report — text-intent seed
 *
 * Chips 3 and 4 seed composer text via onChipClick. Chips 1 and 2 currently
 * seed an instructional prompt; they will rewire to native file/URL
 * affordances in a later commit (ADR-190 commit 2) when the composer gains
 * rich-input richness. For now, seeding text is the minimum wiring.
 */

import { FileUp, Link2, Eye, FileText } from 'lucide-react';

interface ChatEmptyStateProps {
  /** Called when a text-seed chip is clicked. */
  onChipClick: (text: string) => void;
  /** Opens the composer's file picker. Wired from ChatPanel.fileInputRef. */
  onUploadClick: () => void;
}

type Chip =
  | {
      icon: React.ComponentType<{ className?: string }>;
      label: string;
      /** Rich affordance chips trigger a helper instead of seeding text. */
      action: 'upload';
    }
  | {
      icon: React.ComponentType<{ className?: string }>;
      label: string;
      /** Text-seed chips seed this string into the composer. */
      action: 'seed';
      seed: string;
    };

const CHIPS: Chip[] = [
  {
    icon: FileUp,
    label: 'Upload a doc',
    action: 'upload',
  },
  {
    icon: Link2,
    label: 'Paste a URL',
    action: 'seed',
    seed: 'Here is a URL that describes my work or company: ',
  },
  {
    icon: Eye,
    label: 'Track something recurring',
    action: 'seed',
    seed: 'I want to track ',
  },
  {
    icon: FileText,
    label: 'Build a recurring report',
    action: 'seed',
    seed: 'I want a recurring report on ',
  },
];

export function ChatEmptyState({ onChipClick, onUploadClick }: ChatEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-10 sm:py-16 px-4">
      <img
        src="/assets/logos/circleonly_yarnnn_1.svg"
        alt=""
        className="w-10 h-10 mb-5 opacity-80"
      />

      <h2 className="text-xl sm:text-2xl font-medium text-foreground mb-2 text-center">
        What are you working on?
      </h2>

      <p className="text-sm text-muted-foreground text-center max-w-md mb-8 leading-relaxed">
        Upload a doc, paste a link, or tell me in your own words. The more you share,
        the sharper the team I build you.
      </p>

      <div className="flex flex-wrap gap-2 justify-center max-w-2xl">
        {CHIPS.map((chip) => {
          const Icon = chip.icon;
          const handleClick =
            chip.action === 'upload'
              ? onUploadClick
              : () => onChipClick(chip.seed);
          return (
            <button
              key={chip.label}
              type="button"
              onClick={handleClick}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-full border border-border/60 bg-background hover:bg-muted/40 hover:border-border transition-colors text-sm text-foreground"
            >
              <Icon className="w-3.5 h-3.5 text-muted-foreground" />
              <span>{chip.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
