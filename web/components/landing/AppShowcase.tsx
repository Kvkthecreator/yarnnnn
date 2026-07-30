"use client";

/**
 * AppShowcase — the feature-forward product chapter (CANON-LOCK-2026-07-30).
 *
 * Four built-in apps rendered as miniature product mocks, modeled on the IR
 * deck's product chapter (slides 7–10): Chat · Studio · Files · Agents.
 *
 * Roster-rule note (CANON-LOCK §5): app names are ALLOWED here — this is the
 * product chapter. They stay out of the hero/subhead/above-the-fold.
 * Honesty rule (ADR-460): desk agents are presented as things you hire that
 * work under your name — never as "colleagues on the ledger" / principals.
 */

import { ScrollReveal } from "@/components/landing/ScrollReveal";

/* ── shared chrome ─────────────────────────────────────────────────────── */

function WindowFrame({
  title,
  badge,
  children,
}: {
  title: string;
  badge?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-[#1a1a1a]/[0.08] bg-white/70 shadow-[0_8px_40px_rgba(26,26,26,0.06)] overflow-hidden backdrop-blur-sm">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-[#1a1a1a]/[0.06] bg-white/60">
        <span className="flex gap-1.5">
          <i className="w-2.5 h-2.5 rounded-full bg-[#1a1a1a]/10 block" />
          <i className="w-2.5 h-2.5 rounded-full bg-[#1a1a1a]/10 block" />
          <i className="w-2.5 h-2.5 rounded-full bg-[#1a1a1a]/10 block" />
        </span>
        <span className="text-xs font-mono text-[#1a1a1a]/40 ml-2">{title}</span>
        {badge && (
          <span className="ml-auto text-[10px] font-mono uppercase tracking-wider text-[#de5a2b]/70 bg-[#de5a2b]/[0.07] rounded-full px-2 py-0.5">
            {badge}
          </span>
        )}
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function EngineChip({ name }: { name: string }) {
  return (
    <span className="inline-flex items-center rounded-full border border-[#1a1a1a]/[0.08] bg-white/80 px-2 py-0.5 text-[10px] font-mono text-[#1a1a1a]/50">
      {name}
    </span>
  );
}

/* ── 1 · Chat ──────────────────────────────────────────────────────────── */

function ChatMock() {
  return (
    <WindowFrame title="Chat › positioning memo" badge="every reply grounded">
      <div className="space-y-3">
        <div className="flex items-start gap-2.5">
          <span className="w-6 h-6 rounded-full bg-indigo-500/10 text-indigo-600 text-[10px] font-medium flex items-center justify-center shrink-0">
            L
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-medium text-[#1a1a1a]/80">Lisa · Critic</span>
              <EngineChip name="GPT-5" />
            </div>
            <p className="text-xs text-[#1a1a1a]/55 leading-relaxed rounded-xl rounded-tl-sm bg-[#1a1a1a]/[0.03] px-3 py-2">
              Their memory is inferred and locked to one model. Yours is authored and
              portable — that&apos;s the line that survives. I pulled your own framing to check.
            </p>
            <p className="mt-1.5 text-[10px] font-mono text-emerald-700/60">
              grounded in 4 workspace files
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-xl border border-[#1a1a1a]/[0.07] bg-white px-3 py-2">
          <span className="text-xs text-[#1a1a1a]/30 flex-1">Ask over your workspace…</span>
          <span className="text-[10px] font-mono text-[#1a1a1a]/25">⏎</span>
        </div>
      </div>
    </WindowFrame>
  );
}

/* ── 2 · Studio ────────────────────────────────────────────────────────── */

function StudioMock() {
  return (
    <WindowFrame title="Studio › investor update · deck" badge="every edit a revision">
      <div className="flex gap-3">
        <div className="flex flex-col gap-1.5 shrink-0">
          {["01", "02", "03"].map((n, i) => (
            <span
              key={n}
              className={`w-10 h-7 rounded border text-[9px] font-mono flex items-center justify-center ${
                i === 0
                  ? "border-[#de5a2b]/40 bg-[#de5a2b]/[0.06] text-[#de5a2b]/70"
                  : "border-[#1a1a1a]/[0.08] bg-white text-[#1a1a1a]/30"
              }`}
            >
              {n}
            </span>
          ))}
        </div>
        <div className="flex-1 rounded-lg border border-[#1a1a1a]/[0.08] bg-white p-3">
          <p className="text-sm font-medium text-[#1a1a1a]/85 mb-1">Traction</p>
          <p className="text-xs text-[#1a1a1a]/50 mb-3">3× retention vs. baseline</p>
          <div className="rounded-lg bg-[#1a1a1a]/[0.03] px-2.5 py-2">
            <p className="text-[10px] text-[#1a1a1a]/45 leading-relaxed">
              <span className="font-medium text-[#1a1a1a]/60">You:</span> lead this slide with
              the strongest number.
            </p>
            <p className="text-[10px] text-[#1a1a1a]/45 leading-relaxed mt-1">
              <span className="font-medium text-indigo-600/70">Lane:</span> done — pulled
              &ldquo;3× retention&rdquo; from your metrics file. Revision saved.
            </p>
          </div>
        </div>
      </div>
    </WindowFrame>
  );
}

/* ── 3 · Files ─────────────────────────────────────────────────────────── */

const FILE_ROWS = [
  { name: "wedge.md", author: "you", meta: "v12 · 2h", tone: "text-[#1a1a1a]/70" },
  { name: "competitor-scan.md", author: "Sana · your agent", meta: "v4 · 1d", tone: "text-indigo-600/80" },
  { name: "pricing-decision.md", author: "Claude", meta: "v7 · 2d", tone: "text-[#de5a2b]/80" },
  { name: "market-read.md", author: "GPT-5", meta: "v2 · 5d", tone: "text-emerald-700/80" },
];

function FilesMock() {
  return (
    <WindowFrame title="Files › documents / positioning" badge="every write signed">
      <div className="rounded-lg border border-[#1a1a1a]/[0.07] bg-white overflow-hidden">
        <div className="grid grid-cols-[1fr_auto_auto] gap-3 px-3 py-1.5 border-b border-[#1a1a1a]/[0.06] text-[9px] font-mono uppercase tracking-wider text-[#1a1a1a]/30">
          <span>Name</span>
          <span>Last authored by</span>
          <span>Version</span>
        </div>
        {FILE_ROWS.map((r) => (
          <div
            key={r.name}
            className="grid grid-cols-[1fr_auto_auto] gap-3 px-3 py-2 border-b border-[#1a1a1a]/[0.04] last:border-0 items-center"
          >
            <span className="text-xs text-[#1a1a1a]/70 font-mono truncate">{r.name}</span>
            <span className={`text-[10px] font-medium ${r.tone}`}>{r.author}</span>
            <span className="text-[10px] font-mono text-[#1a1a1a]/30">{r.meta}</span>
          </div>
        ))}
      </div>
      <p className="mt-2.5 text-[10px] font-mono text-[#1a1a1a]/30">
        every version kept · walk any line back to who decided it
      </p>
    </WindowFrame>
  );
}

/* ── 4 · Agents ────────────────────────────────────────────────────────── */

const AGENT_CARDS = [
  { initial: "T", name: "Thinker", desc: "Reasons over your files, argues back", engine: "GPT-5" },
  { initial: "R", name: "Researcher", desc: "Goes and finds out, brings sources", engine: "Gemini" },
  { initial: "D", name: "Designer", desc: "Makes the artifact — decks, docs, pages", engine: "Claude" },
];

function AgentsMock() {
  return (
    <WindowFrame title="Agents › set up an agent" badge="swap the engine, keep the name">
      <div className="space-y-2">
        {AGENT_CARDS.map((a) => (
          <div
            key={a.name}
            className="flex items-center gap-3 rounded-lg border border-[#1a1a1a]/[0.07] bg-white px-3 py-2"
          >
            <span className="w-7 h-7 rounded-full bg-[#1a1a1a]/[0.05] text-[#1a1a1a]/60 text-xs font-medium flex items-center justify-center shrink-0">
              {a.initial}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-[#1a1a1a]/80">{a.name}</p>
              <p className="text-[10px] text-[#1a1a1a]/45 truncate">{a.desc}</p>
            </div>
            <EngineChip name={a.engine} />
          </div>
        ))}
      </div>
    </WindowFrame>
  );
}

/* ── the chapter ───────────────────────────────────────────────────────── */

const SECTIONS = [
  {
    id: "chat",
    kicker: "Think · Chat",
    title: "Think out loud, over your own files.",
    body: "Grounded, multi-engine conversation over your shared workspace. Ask a named agent you set up once; the best engine for the job rides behind the name — and what you decide lands in the record, not in a scroll you'll never find again.",
    Mock: ChatMock,
  },
  {
    id: "studio",
    kicker: "Make · Studio",
    title: "Shape documents, decks and pages — by hand and by AI.",
    body: "Compose directly, or ask the lane bound to the artifact. Both land as the same signed revision, and every figure you cite carries its source — the artifact knows where every claim came from.",
    Mock: StudioMock,
  },
  {
    id: "files",
    kicker: "The record · Files",
    title: "One shared file system — every change signed.",
    body: "You, your people, and your AIs all write into the same place. Every version is kept, every write carries a name — human or not — and you can walk any file back to who decided what, and why.",
    Mock: FilesMock,
  },
  {
    id: "agents",
    kicker: "Intelligence · Agents",
    title: "Set up an agent in a click.",
    body: "Three starting points — a thinker, a researcher, a designer. Name one, give it a manner, and it works on your files under your name, on whichever engine suits the job. Swap the engine any time; the agent and its work stay.",
    Mock: AgentsMock,
  },
];

export function AppShowcase() {
  return (
    <div className="space-y-20 md:space-y-28">
      {SECTIONS.map((s, i) => (
        <ScrollReveal key={s.id}>
          <div
            className={`flex flex-col gap-8 lg:gap-16 lg:items-center ${
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
            <div className="flex-1 w-full max-w-lg">
              <s.Mock />
            </div>
          </div>
        </ScrollReveal>
      ))}
    </div>
  );
}
