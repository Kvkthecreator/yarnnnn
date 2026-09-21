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
import { useTranslations } from "next-intl";
import { ChatReplica } from "@/components/landing/product/ChatReplica";
import { StudioReplica } from "@/components/landing/product/StudioReplica";
import { FilesReplica } from "@/components/landing/product/FilesReplica";
import { AgentsReplica } from "@/components/landing/product/AgentsReplica";

// ADR-660 D3 — a module-level roster holds catalog KEYS, worded at render.
// The prose here is the product chapter every visitor reads, so it cannot be
// English literals baked into a table evaluated at import.
const SECTIONS = [
  { id: "chat", Mock: ChatReplica },
  { id: "slides", Mock: StudioReplica },
  { id: "files", Mock: FilesReplica },
  { id: "agents", Mock: AgentsReplica },
] as const;

export function AppShowcase() {
  const t = useTranslations("marketing.apps");
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
                {t(`${s.id}.kicker`)}
              </div>
              <h3 className="text-xl md:text-2xl font-medium mb-4 text-[#1a1a1a] leading-snug">
                {t(`${s.id}.title`)}
              </h3>
              <p className="text-[#1a1a1a]/50 leading-relaxed font-light">{t(`${s.id}.body`)}</p>
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
