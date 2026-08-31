import type { ComponentType } from "react";

import { TraceCard } from "@/components/landing/TraceCard";
import { CompoundsStepper } from "@/components/landing/CompoundsStepper";
import { IntegrationHub } from "@/components/landing/IntegrationHub";
import { ChatReplica } from "@/components/landing/product/ChatReplica";
import { StudioReplica } from "@/components/landing/product/StudioReplica";
import { FilesReplica } from "@/components/landing/product/FilesReplica";
import { AgentsReplica } from "@/components/landing/product/AgentsReplica";
import { ConnectReplica } from "@/components/landing/product/ConnectReplica";

/**
 * blog-embeds — lets a plain-markdown blog post render one of the landing
 * page's proof components inline.
 *
 * Why a sentinel and not MDX: posts in `content/posts/` are plain `.md` read by
 * `lib/blog.ts` and rendered through ReactMarkdown. Introducing MDX would mean
 * migrating 100+ existing posts and changing the loader. A sentinel that is a
 * valid HTML comment keeps every file valid markdown, so the RSS route, the
 * word count, the Medium import and the X Article cross-post all keep working —
 * they see a comment and drop it.
 *
 * Author a post with the sentinel alone on its own line:
 *
 *     <!-- embed:TraceCard -->
 *
 * An unknown name renders nothing rather than throwing, so a typo degrades to
 * an omission and never breaks a build.
 *
 * Surfaces:
 *  - "cream"  — the component hardcodes the landing palette (#1a1a1a on the
 *               #faf8f5 ground). It gets a fixed light card so it renders as
 *               designed under both blog themes.
 *  - "token"  — the component is built from the shared design tokens
 *               (bg-background / border-border / text-foreground) and is
 *               already theme-correct. It is rendered bare.
 */

type EmbedSurface = "cream" | "token";

interface EmbedEntry {
  Component: ComponentType<{ className?: string }>;
  surface: EmbedSurface;
  /** Caption printed under the figure. Every embed is illustrative, not live data. */
  caption: string;
  /** Extra classes on the <figure>, e.g. to hide a fixed-width component on small screens. */
  wrapperClass?: string;
}

export const BLOG_EMBEDS: Record<string, EmbedEntry> = {
  TraceCard: {
    Component: TraceCard,
    surface: "cream",
    caption: "A revision chain, illustrative — the shape the workspace records for every file.",
  },
  CompoundsStepper: {
    Component: CompoundsStepper,
    surface: "cream",
    caption: "Day 1 to day 90 — select a stage, or let it advance.",
  },
  IntegrationHub: {
    Component: IntegrationHub,
    surface: "cream",
    // Fixed 500px canvas, authored as `hidden lg:block`. Hide the figure too so
    // small screens get no empty card.
    wrapperClass: "hidden lg:block",
    caption: "Your sources on the left, the AI you use on the right, one workspace between them.",
  },
  ChatReplica: {
    Component: ChatReplica,
    surface: "token",
    caption: "Chat — a reply that lands as a file, not as scrollback.",
  },
  StudioReplica: {
    Component: StudioReplica,
    surface: "token",
    caption: "Studio — the same deck edited by hand and by AI, into one signed revision.",
  },
  FilesReplica: {
    Component: FilesReplica,
    surface: "token",
    caption: "Files — one shared file system, every write carrying a name.",
  },
  AgentsReplica: {
    Component: AgentsReplica,
    surface: "token",
    caption: "Agents — named, and working on your files as you.",
  },
  ConnectReplica: {
    Component: ConnectReplica,
    surface: "token",
    caption: "Connect an AI, and its first write arrives in the ledger already signed.",
  },
};

const SENTINEL = /^[ \t]*<!--[ \t]*embed:([A-Za-z0-9_-]+)[ \t]*-->[ \t]*$/m;

export type PostBlock =
  | { type: "markdown"; value: string }
  | { type: "embed"; name: string };

/**
 * Split a post body into markdown runs and embed markers.
 *
 * `String.split` with a capturing regex interleaves the captures into the
 * result, so even indices are markdown and odd indices are embed names.
 */
export function splitPostContent(content: string): PostBlock[] {
  const parts = content.split(SENTINEL);

  return parts
    .map((part, i): PostBlock | null => {
      if (i % 2 === 1) {
        return part in BLOG_EMBEDS ? { type: "embed", name: part } : null;
      }
      return part.trim() ? { type: "markdown", value: part } : null;
    })
    .filter((block): block is PostBlock => block !== null);
}

export function BlogEmbed({ name }: { name: string }) {
  const entry = BLOG_EMBEDS[name];
  if (!entry) return null;

  const { Component, surface, caption, wrapperClass = "" } = entry;

  return (
    <figure className={`my-12 ${wrapperClass}`.trim()}>
      {surface === "cream" ? (
        <div className="rounded-2xl border border-black/[0.08] bg-[#faf8f5] p-4 md:p-6 text-[#1a1a1a] shadow-sm">
          <Component />
        </div>
      ) : (
        <Component className="w-full" />
      )}
      <figcaption className="mt-3 text-xs text-muted-foreground/60 leading-relaxed">
        {caption}
      </figcaption>
    </figure>
  );
}
