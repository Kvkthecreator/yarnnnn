"use client";

/**
 * AppShowcase — the feature-forward product chapter (CANON-LOCK-2026-07-30,
 * mocks rebuilt 2026-07-31 against the shipped surfaces).
 *
 * Four built-in apps rendered as miniature product mocks. Each mock mirrors
 * the REAL surface's structure and vocabulary (not an invented layout):
 *  - Chat: identity-first lane header ("Lisa" / "Critic · GPT-5"), assistant
 *    bubble, an ArtifactCard (replies land as files), "Message Lisa…" composer.
 *  - Studio: slide strip with position numbers + selection ring, canvas slide,
 *    the bound chat that lands revisions ("r7 · current").
 *  - Files: the Finder list — Name · Author · When columns, accent-dot +
 *    RESOLVED attribution labels ("You", "ChatGPT (via MCP)"), never raw
 *    substrate strings.
 *  - Agents: the real kernel roster (Thinker / Researcher / Designer, real
 *    blurbs), engine as the quiet third line, the "Make one" door.
 *
 * Roster-rule note (CANON-LOCK §5): app names are ALLOWED here — this is the
 * product chapter. They stay out of the hero/subhead/above-the-fold.
 * Honesty rule (ADR-460): desk agents work on your files as you — their edits
 * are attributed to you. Never presented as principals/colleagues-on-the-ledger.
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
          <span className="ml-auto text-[10px] font-mono uppercase tracking-wider text-[#de5a2b]/70 bg-[#de5a2b]/[0.07] rounded-full px-2 py-0.5 whitespace-nowrap">
            {badge}
          </span>
        )}
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

/* ── 1 · Chat — identity-first lane + a reply that lands as a file ─────── */

function ChatMock() {
  return (
    <WindowFrame title="Chat › Lisa" badge="replies land as files">
      <div className="space-y-3">
        {/* Conversation header — the real grammar: name leads, role · engine rides behind */}
        <div className="flex items-center gap-2.5 pb-2 border-b border-[#1a1a1a]/[0.05]">
          <span className="w-7 h-7 rounded-full bg-indigo-500/10 text-indigo-600 text-[11px] font-medium flex items-center justify-center shrink-0">
            L
          </span>
          <div className="min-w-0">
            <p className="text-xs font-medium text-[#1a1a1a]/85 leading-tight">Lisa</p>
            <p className="text-[10px] text-[#1a1a1a]/40 leading-tight">Critic · GPT-5</p>
          </div>
        </div>

        {/* Assistant bubble */}
        <p className="text-xs text-[#1a1a1a]/55 leading-relaxed rounded-xl rounded-tl-sm bg-[#1a1a1a]/[0.03] px-3 py-2 max-w-[92%]">
          The pricing section undercuts your own claim — I tightened it against the
          numbers in your metrics file and saved the memo.
        </p>

        {/* ArtifactCard — the landed file, the real grounding story */}
        <div className="rounded-xl border border-[#1a1a1a]/[0.08] bg-white overflow-hidden max-w-[92%]">
          <div className="flex items-center gap-2 px-3 py-2 bg-[#1a1a1a]/[0.02]">
            <span className="text-xs font-medium text-[#1a1a1a]/80 truncate">
              positioning-memo.md
            </span>
            <span className="text-[10px] text-[#1a1a1a]/35">revised · context/</span>
            <span className="ml-auto rounded-md border border-[#1a1a1a]/[0.1] px-2 py-0.5 text-[10px] font-medium text-[#1a1a1a]/60">
              Open
            </span>
          </div>
        </div>

        {/* Composer — the real placeholder grammar */}
        <div className="flex items-center gap-2 rounded-xl border border-[#1a1a1a]/[0.07] bg-white px-3 py-2">
          <span className="text-xs text-[#1a1a1a]/30 flex-1">Message Lisa…</span>
          <span className="w-5 h-5 rounded-full bg-[#1a1a1a] text-white text-[10px] flex items-center justify-center">
            ↑
          </span>
        </div>
      </div>
    </WindowFrame>
  );
}

/* ── 2 · Studio — slide strip + canvas + the bound chat landing revisions ── */

const SLIDES = [
  { n: "1", caption: "Traction", active: true },
  { n: "2", caption: "Model", active: false },
  { n: "3", caption: "The ask", active: false },
];

function StudioMock() {
  return (
    <WindowFrame title="Studio / investor-update · Deck" badge="every edit a revision">
      <div className="flex gap-3">
        {/* The slide strip — position number · thumbnail · caption, selection ring */}
        <div className="flex flex-col gap-2 shrink-0 w-[76px]">
          <span className="text-[8px] font-medium uppercase tracking-wide text-[#1a1a1a]/30">
            Slides
          </span>
          {SLIDES.map((s) => (
            <div key={s.n} className="flex items-stretch gap-1">
              <span className="w-3 text-[9px] font-medium text-[#1a1a1a]/35 text-right leading-none pt-1.5">
                {s.n}
              </span>
              <div className="flex-1">
                <div
                  className={`h-8 rounded-sm border bg-white ${
                    s.active
                      ? "border-indigo-400 ring-1 ring-indigo-400"
                      : "border-[#1a1a1a]/[0.1]"
                  }`}
                >
                  <div className="h-1 w-2/3 bg-[#1a1a1a]/[0.12] rounded-sm mt-1.5 ml-1.5" />
                  <div className="h-0.5 w-1/2 bg-[#1a1a1a]/[0.06] rounded-sm mt-1 ml-1.5" />
                </div>
                <p className="text-[8px] text-[#1a1a1a]/35 truncate mt-0.5">{s.caption}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Canvas + the bound chat */}
        <div className="flex-1 min-w-0">
          <div className="rounded-lg border border-[#1a1a1a]/[0.08] bg-white p-3">
            <p className="text-sm font-medium text-[#1a1a1a]/85 mb-1">Traction</p>
            <p className="text-xs text-[#1a1a1a]/50">3× retention vs. baseline</p>
          </div>
          <div className="rounded-lg bg-[#1a1a1a]/[0.03] px-2.5 py-2 mt-2">
            <p className="text-[10px] text-[#1a1a1a]/45 leading-relaxed">
              <span className="font-medium text-[#1a1a1a]/60">You:</span> lead this slide
              with the strongest number.
            </p>
            <p className="text-[10px] text-[#1a1a1a]/45 leading-relaxed mt-1">
              <span className="font-medium text-indigo-600/70">Lisa:</span> done — pulled
              &ldquo;3× retention&rdquo; from your metrics file.
            </p>
            <p className="mt-1.5 text-[9px] font-mono text-[#1a1a1a]/35">
              r7{" "}
              <span className="rounded bg-[#de5a2b]/[0.08] text-[#de5a2b]/70 px-1 py-px">
                current
              </span>{" "}
              · saved as a revision
            </p>
          </div>
        </div>
      </div>
    </WindowFrame>
  );
}

/* ── 3 · Files — the Finder list with resolved, signed attribution ─────── */

const FILE_ROWS = [
  { name: "positioning-memo.md", author: "You", dot: "bg-sky-500", when: "2h" },
  { name: "q3-pricing-note.md", author: "ChatGPT (via MCP)", dot: "bg-amber-400", when: "1d" },
  { name: "competitor-scan.md", author: "Claude (via MCP)", dot: "bg-amber-400", when: "2d" },
  { name: "launch-plan.md", author: "Mara", dot: "bg-teal-500", when: "5d" },
];

function FilesMock() {
  return (
    <WindowFrame title="Files › Context" badge="every write signed">
      <div className="rounded-lg border border-[#1a1a1a]/[0.07] bg-white overflow-hidden">
        <div className="grid grid-cols-[1fr_auto_auto] gap-3 px-3 py-1.5 border-b border-[#1a1a1a]/[0.06] text-[9px] font-medium uppercase tracking-wide text-[#1a1a1a]/30">
          <span>Name</span>
          <span>Author</span>
          <span className="text-right">When</span>
        </div>
        {FILE_ROWS.map((r) => (
          <div
            key={r.name}
            className="grid grid-cols-[1fr_auto_auto] gap-3 px-3 py-2 border-b border-[#1a1a1a]/[0.04] last:border-0 items-center"
          >
            <span className="text-xs text-[#1a1a1a]/70 font-mono truncate">{r.name}</span>
            <span className="flex items-center gap-1.5 text-[10px] font-medium text-[#1a1a1a]/60">
              <span className={`h-1.5 w-1.5 rounded-full ${r.dot}`} />
              {r.author}
            </span>
            <span className="text-[10px] font-mono text-[#1a1a1a]/30 text-right">{r.when}</span>
          </div>
        ))}
      </div>
      {/* The revision-history grammar, verbatim from the product */}
      <p className="mt-2.5 text-[10px] font-mono text-[#1a1a1a]/30">
        Revision history (12) · r12 current · revert · diff
      </p>
    </WindowFrame>
  );
}

/* ── 4 · Agents — the real kernel roster + the Make-one door ───────────── */

const AGENT_CARDS = [
  {
    initial: "T",
    name: "Thinker",
    desc: "Thinks a problem through with you — writing, judgment, hard calls.",
    engine: "GPT-5",
  },
  {
    initial: "R",
    name: "Researcher",
    desc: "Digs through material fast — the workspace and the web, with sources.",
    engine: "Gemini",
  },
  {
    initial: "D",
    name: "Designer",
    desc: "Makes the thing itself — decks, docs, the artifact in front of you.",
    engine: "Claude",
  },
];

function AgentsMock() {
  return (
    <WindowFrame title="Agents" badge="swap the engine, keep the name">
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
              <p className="text-[9px] text-[#1a1a1a]/30 mt-0.5">Runs on {a.engine}</p>
            </div>
          </div>
        ))}
        {/* The hire door — the real dashed affordance + name placeholder */}
        <div className="flex items-center gap-3 rounded-lg border border-dashed border-[#1a1a1a]/[0.15] px-3 py-2">
          <span className="w-7 h-7 rounded-full border border-dashed border-[#1a1a1a]/[0.2] text-[#1a1a1a]/35 text-xs flex items-center justify-center shrink-0">
            +
          </span>
          <p className="text-[10px] text-[#1a1a1a]/35 italic truncate">
            Name them — Lisa, Marcus, whoever
          </p>
        </div>
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
    body: "Conversation grounded in your workspace — with agents you name, on whichever engine suits the job. And what comes out of it doesn't die in the scroll: replies land as real files, saved where you and your team can find them.",
    Mock: ChatMock,
  },
  {
    id: "studio",
    kicker: "Make · Studio",
    title: "Shape documents, decks and pages — by hand and by AI.",
    body: "Compose directly on the canvas, or ask in the built-in chat — every reply becomes an edit to the artifact in front of you. Both land as the same signed revision, so the document carries its own history: who changed what, and why.",
    Mock: StudioMock,
  },
  {
    id: "files",
    kicker: "The record · Files",
    title: "One shared file system — every change signed.",
    body: "You, your people, and every AI you connect write into the same place. Every write carries a name — You, a teammate, ChatGPT — every version is kept, and any file can be walked back revision by revision.",
    Mock: FilesMock,
  },
  {
    id: "agents",
    kicker: "Intelligence · Agents",
    title: "Agents ready out of the box.",
    body: "A thinker, a researcher, a designer — ready to talk from the first minute. Hire one, give it a name and a manner, and it works on your files as you, with every edit kept in the file's history. Swap the engine any time; the name and the work stay.",
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
