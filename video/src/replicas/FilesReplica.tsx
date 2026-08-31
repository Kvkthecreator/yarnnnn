/**
 * FilesReplica — the landing page's Files mockup
 * (web/components/landing/product/FilesReplica.tsx), ported to Remotion.
 *
 * The port is a FAITHFUL RE-EXPRESSION, not a rewrite: same rows, same
 * attribution labels, same revision-panel grammar (r{N} + the "current"
 * pill), same staged beats. Two things necessarily change:
 *
 *   1. Timing. The web replica is wall-clock driven (useStagedLoop's
 *      setTimeout) and therefore not seekable. Here the same three beats are
 *      derived from useCurrentFrame(), so any frame can be rendered
 *      independently — which is what makes deterministic video export
 *      possible at all.
 *   2. Styling. Tailwind token classes (bg-background, border-border…) become
 *      explicit values from ./chrome, resolved from the same globals.css
 *      :root the web replica reads through the shared stylesheet.
 *
 * The beats, unchanged from the web replica:
 *   a connected AI writes in → the row lands at the top, signed
 *   "ChatGPT (via MCP)" → the revision count ticks 11 → 12.
 */

import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, Easing } from "remotion";
import { ProductWindow, UI, fg, mutedFg, borderAlpha } from "./chrome";

const BASE_ROWS = [
  { name: "positioning-memo.md", author: "You", dot: UI.blue, when: "2h" },
  { name: "competitor-scan.md", author: "Claude (via MCP)", dot: UI.amber, when: "2d" },
  { name: "launch-plan.md", author: "Mara", dot: UI.teal, when: "5d" },
];

const TREE = ["Identity", "Context", "Reports", "Uploads"];

/** Beat timings, in seconds from the composition's start. */
export const FILES_BEATS = { land: 1.1, revision: 2.3 };

/** A 0→1 ease for a beat starting at `atSec`, over `durSec`. */
const useBeat = (atSec: number, durSec = 0.45) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return interpolate(frame, [atSec * fps, (atSec + durSec) * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });
};

export const FilesReplica: React.FC<{ scale?: number }> = ({ scale = 2 }) => {
  const landed = useBeat(FILES_BEATS.land);
  const revealed = useBeat(FILES_BEATS.revision);
  const s = (n: number) => n * scale;

  // Shared column geometry — the replica's grid-cols-[1fr_auto_44px].
  const row: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: `minmax(0,1fr) auto ${s(44)}px`,
    alignItems: "center",
    gap: s(12),
    paddingLeft: s(12),
    paddingRight: s(12),
  };
  const mono = "ui-monospace, SFMono-Regular, Menlo, monospace";

  const AuthorCell: React.FC<{ dot: string; label: string }> = ({ dot, label }) => (
    <span style={{ display: "flex", alignItems: "center", gap: s(6), fontSize: s(10), fontWeight: 500, color: fg(0.7), whiteSpace: "nowrap" }}>
      <span style={{ height: s(6), width: s(6), borderRadius: "50%", backgroundColor: dot }} />
      {label}
    </span>
  );

  return (
    <ProductWindow title="Files" width={s(560)} scale={scale}>
      <div style={{ display: "flex",  fontFamily: "system-ui, sans-serif" }}>
        {/* Tree rail */}
        <div style={{ width: s(136), flexShrink: 0, alignSelf: "stretch", borderRight: `${Math.max(1, scale)}px solid ${UI.border}`, padding: s(8), display: "flex", flexDirection: "column" }}>
          <span style={{ display: "flex", alignItems: "center", gap: s(6), borderRadius: s(6), backgroundColor: UI.muted, paddingLeft: s(8), paddingRight: s(8), paddingTop: s(4), paddingBottom: s(4), fontSize: s(12), fontWeight: 500, color: UI.foreground }}>
            Recents
          </span>
          <span style={{ paddingLeft: s(8), paddingTop: s(4), paddingBottom: s(4), fontSize: s(12), color: UI.mutedForeground }}>
            Trash
          </span>
          <div style={{ marginTop: s(6), marginBottom: s(6), borderTop: `${Math.max(1, scale)}px solid ${borderAlpha(0.6)}` }} />
          {TREE.map((t) => (
            <span
              key={t}
              style={{
                display: "flex", alignItems: "center", gap: s(6),
                paddingLeft: s(8), paddingTop: s(4), paddingBottom: s(4),
                fontSize: s(12),
                fontWeight: t === "Context" ? 500 : 400,
                color: t === "Context" ? UI.foreground : UI.mutedForeground,
              }}
            >
              <svg width={s(12)} height={s(12)} viewBox="0 0 24 24" fill="none" stroke="#0284c7" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
              </svg>
              {t}
            </span>
          ))}
        </div>

        {/* List + revision panel */}
        <div style={{ display: "flex", minWidth: 0, flex: 1, flexDirection: "column" }}>
          {/* Column headers */}
          <div style={{ ...row, borderBottom: `${Math.max(1, scale)}px solid ${UI.border}`, paddingTop: s(6), paddingBottom: s(6), fontSize: s(10), fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em", color: UI.mutedForeground }}>
            <span>Name</span>
            <span>Author</span>
            <span style={{ textAlign: "right" }}>When</span>
          </div>

          {/* The landing MCP row — beat 1. Height animates so the list below
              is pushed down, exactly as the web replica's max-h transition. */}
          <div
            style={{
              ...row,
              height: interpolate(landed, [0, 1], [0, s(37)]),
              opacity: landed,
              overflow: "hidden",
              backgroundColor: UI.amberBg,
              borderBottom: landed > 0 ? `${Math.max(1, scale)}px solid ${borderAlpha(0.5)}` : "none",
            }}
          >
            <span style={{ fontFamily: mono, fontSize: s(12), color: fg(0.8), whiteSpace: "nowrap" }}>
              q3-pricing-note.md
            </span>
            <AuthorCell dot={UI.amber} label="ChatGPT (via MCP)" />
            <span style={{ textAlign: "right", fontFamily: mono, fontSize: s(10), color: mutedFg(0.7) }}>now</span>
          </div>

          {BASE_ROWS.map((r) => (
            <div key={r.name} style={{ ...row, paddingTop: s(8), paddingBottom: s(8), borderBottom: `${Math.max(1, scale)}px solid ${borderAlpha(0.5)}` }}>
              <span style={{ fontFamily: mono, fontSize: s(12), color: fg(0.8), whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {r.name}
              </span>
              <AuthorCell dot={r.dot} label={r.author} />
              <span style={{ textAlign: "right", fontFamily: mono, fontSize: s(10), color: mutedFg(0.7) }}>{r.when}</span>
            </div>
          ))}

          {/* Revision history — the product's exact grammar */}
          <div style={{ margin: s(12), marginTop: s(10), marginBottom: s(12), borderRadius: s(8), border: `${Math.max(1, scale)}px solid ${UI.border}` }}>
            <div style={{ display: "flex", alignItems: "center", gap: s(6), borderBottom: `${Math.max(1, scale)}px solid ${borderAlpha(0.6)}`, padding: `${s(6)}px ${s(10)}px` }}>
              <span style={{ fontSize: s(11), fontWeight: 500, color: fg(0.8) }}>
                Revision history{" "}
                <span style={{ color: UI.mutedForeground }}>({revealed > 0.5 ? "12" : "11"})</span>
              </span>
              <span style={{ marginLeft: "auto", fontSize: s(10), color: mutedFg(0.6) }}>hide</span>
            </div>

            {/* r12 — beat 2 */}
            <div
              style={{
                display: "flex", alignItems: "center", gap: s(8),
                padding: `${s(6)}px ${s(10)}px`,
                opacity: revealed,
                transform: `translateY(${interpolate(revealed, [0, 1], [s(6), 0])}px)`,
              }}
            >
              <span style={{ fontFamily: mono, fontSize: s(10), color: UI.mutedForeground }}>r12</span>
              <span style={{ borderRadius: s(3), border: `${Math.max(1, scale)}px solid ${UI.amberBorder}`, backgroundColor: "#fffbeb", padding: `${s(2)}px ${s(6)}px`, fontSize: s(9), color: UI.amberText, whiteSpace: "nowrap" }}>
                ChatGPT (via MCP)
              </span>
              <span style={{ fontSize: s(10), color: fg(0.8), whiteSpace: "nowrap" }}>Added the Q3 numbers</span>
              <span style={{ marginLeft: "auto", borderRadius: s(3), border: `${Math.max(1, scale)}px solid hsla(240,5.9%,10%,0.25)`, backgroundColor: "hsla(240,5.9%,10%,0.06)", padding: `${s(2)}px ${s(6)}px`, fontSize: s(9), color: UI.primary }}>
                current
              </span>
            </div>

            {/* r11 — always present */}
            <div style={{ display: "flex", alignItems: "center", gap: s(8), padding: `0 ${s(10)}px ${s(6)}px` }}>
              <span style={{ fontFamily: mono, fontSize: s(10), color: UI.mutedForeground }}>r11</span>
              <span style={{ borderRadius: s(3), border: `${Math.max(1, scale)}px solid ${UI.blueBorder}`, backgroundColor: UI.blueBg, padding: `${s(2)}px ${s(6)}px`, fontSize: s(9), color: UI.blueText }}>
                You
              </span>
              <span style={{ fontSize: s(10), color: fg(0.8), whiteSpace: "nowrap" }}>Tightened the pricing section</span>
            </div>
          </div>
        </div>
      </div>
    </ProductWindow>
  );
};
