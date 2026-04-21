'use client';

/**
 * OverviewEmptyState — semantic-day-zero cockpit greeting (ADR-203 §4a).
 *
 * Rendered by OverviewSurface when `detectSemanticDayZero()` returns true.
 * That means: no operator-authored agents (scaffolded YARNNN + specialists
 * + platform bots don't count), no non-essential active tasks (back-office
 * + daily-update don't count), no pending proposals.
 *
 * Replaces the pre-ADR-203 two-CTA empty state. Structured four-section
 * introduction that teaches the operator what the cockpit is, what they
 * already have, what's missing, and three concrete first moves. Each first
 * move seeds the ambient YARNNN rail with a purpose-specific prompt
 * (not a generic CTA) — the rail is already open by default on cold-start
 * (Overview page wires this via onDayZeroResolved).
 *
 * Per ADR-161 heartbeat discipline: never silent, always a path forward.
 */

import { Sparkles, Users, FolderOpen, Plug, Compass, MessageCircle } from 'lucide-react';

export interface OverviewEmptyStateProps {
  onOpenChatDraft: (prompt: string) => void;
}

export function OverviewEmptyState({ onOpenChatDraft }: OverviewEmptyStateProps) {
  return (
    <div className="flex flex-1 flex-col gap-6 overflow-y-auto px-6 py-8">
      {/* Section 1 — Welcome */}
      <section className="max-w-3xl">
        <div className="flex items-center gap-2 text-muted-foreground/70">
          <Sparkles className="h-4 w-4" />
          <span className="text-xs font-medium uppercase tracking-wide">Welcome</span>
        </div>
        <h1 className="mt-2 text-xl font-semibold text-foreground">
          This is your workforce control surface.
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Your agents live here; you supervise them from here. YARNNN sits in
          the rail on the right — talk to it any time to describe work, adjust
          your team, or ask what&apos;s going on.
        </p>
      </section>

      {/* Section 2 — What's already scaffolded */}
      <section className="rounded-md border border-border bg-card p-4">
        <div className="flex items-center gap-2 text-muted-foreground/70">
          <Users className="h-4 w-4" />
          <span className="text-xs font-medium uppercase tracking-wide">
            What&apos;s already here
          </span>
        </div>
        <p className="mt-2 text-sm text-foreground">
          Your workspace is provisioned.{' '}
          <strong className="font-medium">YARNNN</strong> (your meta-cognitive
          partner) + six Specialists (Researcher, Analyst, Writer, Tracker,
          Designer, Reporting) are ready. Platform bots (Slack, Notion, GitHub,
          Alpaca, Commerce) will activate when you connect the corresponding
          platform.
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          A daily-update email arrives every morning, even before you&apos;ve
          authored anything — that&apos;s the system telling you it&apos;s
          alive. As you add work, the email gets richer.
        </p>
      </section>

      {/* Section 3 — What's missing */}
      <section className="rounded-md border border-dashed border-border bg-muted/20 p-4">
        <div className="flex items-center gap-2 text-muted-foreground/70">
          <FolderOpen className="h-4 w-4" />
          <span className="text-xs font-medium uppercase tracking-wide">
            What&apos;s missing
          </span>
        </div>
        <p className="mt-2 text-sm text-foreground">
          You haven&apos;t described your work yet. Without that, we
          haven&apos;t authored any domain-specific agents or tasks.
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          Tell YARNNN what you want to track, produce, or monitor — it will
          propose the agents and tasks that fit, and you approve each one.
          The cockpit fills in from that conversation.
        </p>
      </section>

      {/* Section 4 — Three concrete first moves */}
      <section>
        <div className="mb-3 flex items-center gap-2 text-muted-foreground/70">
          <Compass className="h-4 w-4" />
          <span className="text-xs font-medium uppercase tracking-wide">
            Three concrete first moves
          </span>
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          <FirstMoveCard
            icon={<MessageCircle className="h-4 w-4" />}
            title="Tell YARNNN about your work"
            description="Describe what you do, what matters, what you want tracked. YARNNN will propose the right agents."
            ctaLabel="Start describing"
            onClick={() =>
              onOpenChatDraft(
                "I want to describe my work so you can help me set up the right agents and tasks. Here's what I do: ",
              )
            }
          />
          <FirstMoveCard
            icon={<Plug className="h-4 w-4" />}
            title="Connect a platform first"
            description="Already running on Slack, Notion, GitHub, Alpaca, or Lemon Squeezy? Connect and the matching platform bot activates."
            ctaLabel="See integrations"
            href="/integrations"
          />
          <FirstMoveCard
            icon={<Compass className="h-4 w-4" />}
            title="Walk me through the cockpit"
            description="Want a quick orientation? YARNNN can tour Overview, Work, Team, Context, and Review — one surface at a time."
            ctaLabel="Take the tour"
            onClick={() =>
              onOpenChatDraft(
                "Walk me through the cockpit surfaces one at a time — Overview, Work, Team, Context, Review. Explain what each is for and when I'd use it.",
              )
            }
          />
        </div>
      </section>

      {/* Footer hint */}
      <p className="mt-2 text-xs text-muted-foreground/60">
        Tip: YARNNN is open in the rail. Type there anytime — or click a card
        above to get started.
      </p>
    </div>
  );
}

function FirstMoveCard({
  icon,
  title,
  description,
  ctaLabel,
  onClick,
  href,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  ctaLabel: string;
  onClick?: () => void;
  href?: string;
}) {
  const body = (
    <>
      <div className="flex items-center gap-1.5 text-muted-foreground/80">
        {icon}
        <span className="text-xs font-medium">{title}</span>
      </div>
      <p className="mt-1.5 text-[13px] text-foreground/90">{description}</p>
      <div className="mt-2 text-xs font-medium text-foreground underline-offset-4 group-hover:underline">
        {ctaLabel} →
      </div>
    </>
  );

  const className =
    'group flex flex-col rounded-md border border-border bg-card p-3 text-left transition-colors hover:bg-muted/40';

  if (href) {
    return (
      <a href={href} className={className}>
        {body}
      </a>
    );
  }

  return (
    <button type="button" onClick={onClick} className={className}>
      {body}
    </button>
  );
}
