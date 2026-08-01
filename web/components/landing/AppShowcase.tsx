"use client";

/**
 * AppShowcase — the feature-forward product chapter (CANON-LOCK-2026-07-30).
 *
 * As of 2026-08-01 the four apps render as PRODUCT REPLICAS
 * (components/landing/product/*) — pixel-faithful, animated recreations of
 * the shipped surfaces built from the same design tokens the authenticated
 * app uses, each mirroring the real chrome, layout, and vocabulary
 * (see the replica files for the fidelity notes). No screenshots to go
 * stale; no invented UI.
 *
 * Roster-rule note (CANON-LOCK §5): app names are ALLOWED here — this is the
 * product chapter. They stay out of the hero/subhead/above-the-fold.
 * Honesty rule (ADR-460): desk agents work on your files as you — their edits
 * are attributed to you. Never presented as principals/colleagues-on-the-ledger.
 */

import { ScrollReveal } from "@/components/landing/ScrollReveal";
import { ChatReplica } from "@/components/landing/product/ChatReplica";
import { StudioReplica } from "@/components/landing/product/StudioReplica";
import { FilesReplica } from "@/components/landing/product/FilesReplica";
import { AgentsReplica } from "@/components/landing/product/AgentsReplica";

const SECTIONS = [
  {
    id: "chat",
    kicker: "Think · Chat",
    title: "Think out loud, over your own files.",
    body: "Conversation grounded in your workspace — with agents you name, on whichever engine suits the job. And what comes out of it doesn't die in the scroll: replies land as real files, saved where you and your team can find them.",
    Mock: ChatReplica,
  },
  {
    id: "studio",
    kicker: "Make · Studio",
    title: "Shape documents, decks and pages — by hand and by AI.",
    body: "Compose directly on the canvas, or ask in the built-in chat — every reply becomes an edit to the artifact in front of you. Both land as the same signed revision, so the document carries its own history: who changed what, and why.",
    Mock: StudioReplica,
  },
  {
    id: "files",
    kicker: "The record · Files",
    title: "One shared file system — every change signed.",
    body: "You, your people, and every AI you connect write into the same place. Every write carries a name — You, a teammate, ChatGPT — every version is kept, and any file can be walked back revision by revision.",
    Mock: FilesReplica,
  },
  {
    id: "agents",
    kicker: "Intelligence · Agents",
    title: "Agents ready out of the box.",
    body: "A thinker, a researcher, a designer — ready to talk from the first minute. Hire one, give it a name and a manner, and it works on your files as you, with every edit kept in the file's history. Swap the engine any time; the name and the work stay.",
    Mock: AgentsReplica,
  },
];

export function AppShowcase() {
  return (
    <div className="space-y-20 md:space-y-28">
      {SECTIONS.map((s, i) => (
        <ScrollReveal key={s.id}>
          <div
            className={`flex flex-col gap-8 lg:gap-14 lg:items-center ${
              i % 2 === 1 ? "lg:flex-row-reverse" : "lg:flex-row"
            }`}
          >
            <div className="flex-1 max-w-xl">
              <div className="text-xs font-mono text-[#de5a2b]/70 uppercase tracking-wider mb-3">
                {s.kicker}
              </div>
              <h3 className="text-xl md:text-2xl font-medium mb-4 text-[#1a1a1a] leading-snug">
                {s.title}
              </h3>
              <p className="text-[#1a1a1a]/50 leading-relaxed font-light">{s.body}</p>
            </div>
            <div className="flex-1 w-full max-w-xl">
              <s.Mock />
            </div>
          </div>
        </ScrollReveal>
      ))}
    </div>
  );
}
