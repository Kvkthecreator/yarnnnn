/**
 * ProductDemo — 30s product explainer.
 *
 * Uses shared design system (fonts, colors, platform SVGs, yarn ball).
 * Minimal and punchy — closer to ad style than a tutorial.
 *
 * Scenes:
 *   1. Logo reveal (3s)
 *   2. Hook — "Your AI forgot everything. Again." (4s)
 *   3. Connect platforms — 4 icons animate in (5s)
 *   4. Agents at work — mock cards (6s)
 *   5. Compounding — quality rises (5s)
 *   6. CTA (4s)
 */

import React from "react";
import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
} from "remotion";
import {
  COLOR,
  FONT,
  YarnBall,
  Watermark,
  PlatformSVG,
  useFadeIn,
  useSlideUp,
  useSpring,
} from "../design";

// ── Scene 1: Logo ──
const SceneLogo: React.FC = () => {
  const scale = useSpring(0, { damping: 15, stiffness: 80 });
  const tagOpacity = useFadeIn(25, 20);
  const tagY = useSlideUp(25);

  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.bg, justifyContent: "center", alignItems: "center" }}>
      <div style={{ transform: `scale(${scale})`, fontFamily: FONT.brand, fontSize: 140, color: COLOR.fg }}>
        yarnnn
      </div>
      <div
        style={{
          opacity: tagOpacity,
          transform: `translateY(${tagY}px)`,
          fontFamily: FONT.body,
          fontSize: 32,
          color: COLOR.muted,
          marginTop: 20,
          fontWeight: 400,
        }}
      >
        Autonomous AI that already knows your work.
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 2: Hook ──
const SceneHook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const lineOneScale = useSpring(0, { damping: 15, stiffness: 120 });
  const ballScale = useSpring(Math.round(0.5 * fps), { damping: 12 });
  const lineTwoDelay = Math.round(0.9 * fps);
  const lineTwoOpacity = interpolate(frame, [lineTwoDelay, lineTwoDelay + 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const lineTwoY = interpolate(frame, [lineTwoDelay, lineTwoDelay + 12], [50, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });

  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <div style={{ transform: `scale(${lineOneScale})`, textAlign: "center", marginBottom: 40 }}>
        <div style={{ fontFamily: FONT.body, fontSize: 80, fontWeight: 900, color: COLOR.fg, lineHeight: 1.15, letterSpacing: "-0.03em" }}>
          Your AI forgot
        </div>
        <div style={{ fontFamily: FONT.body, fontSize: 80, fontWeight: 900, color: COLOR.fg, lineHeight: 1.15, letterSpacing: "-0.03em" }}>
          everything.
        </div>
      </div>
      <div style={{ transform: `scale(${ballScale})` }}>
        <YarnBall size={56} />
      </div>
      <div style={{ opacity: lineTwoOpacity, transform: `translateY(${lineTwoY}px)`, marginTop: 40, textAlign: "center" }}>
        <div style={{ fontFamily: FONT.body, fontSize: 80, fontWeight: 900, color: COLOR.fg, lineHeight: 1.15, letterSpacing: "-0.03em" }}>
          Again.
        </div>
      </div>
      <Watermark />
    </AbsoluteFill>
  );
};

// ── Scene 3: Connect ──
const SceneConnect: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const titleScale = useSpring(0, { damping: 200 });
  const platforms = [
    { name: "Slack", color: COLOR.slack, delay: Math.round(0.4 * fps) },
    { name: "Gmail", color: COLOR.gmail, delay: Math.round(0.6 * fps) },
    { name: "Notion", color: COLOR.notion, delay: Math.round(0.8 * fps) },
    { name: "Calendar", color: COLOR.calendar, delay: Math.round(1.0 * fps) },
  ];
  const subDelay = Math.round(1.5 * fps);
  const subOpacity = interpolate(frame, [subDelay, subDelay + 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.bg, justifyContent: "center", alignItems: "center" }}>
      <div style={{ transform: `scale(${titleScale})`, fontFamily: FONT.body, fontSize: 56, fontWeight: 900, color: COLOR.fg, marginBottom: 56, letterSpacing: "-0.02em" }}>
        Connect once.
      </div>
      <div style={{ display: "flex", gap: 48 }}>
        {platforms.map(({ name, color, delay }) => {
          const s = useSpring(delay, { damping: 12, stiffness: 120 });
          return (
            <div key={name} style={{ transform: `scale(${s})`, display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
              <PlatformSVG name={name} color={color} size={100} iconSize={36} />
              <span style={{ fontFamily: FONT.body, fontSize: 18, color: COLOR.muted, fontWeight: 400 }}>{name}</span>
            </div>
          );
        })}
      </div>
      <div style={{ opacity: subOpacity, fontFamily: FONT.body, fontSize: 28, color: COLOR.muted, marginTop: 48, fontWeight: 400 }}>
        Agents appear automatically.
      </div>
      <Watermark />
    </AbsoluteFill>
  );
};

// ── Scene 4: Dashboard ──
const AgentCard: React.FC<{
  title: string;
  platform: string;
  platformColor: string;
  skill: string;
  runs: number;
  delay: number;
}> = ({ title, platform, platformColor, skill, runs, delay }) => {
  const scale = useSpring(delay, { damping: 200 });

  return (
    <div style={{ opacity: scale, transform: `scale(${scale})`, backgroundColor: "#fff", borderRadius: 16, padding: "24px 28px", width: 340, boxShadow: "0 2px 12px rgba(0,0,0,0.06)", border: "1px solid rgba(0,0,0,0.06)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
        <PlatformSVG name={platform} color={platformColor} size={36} iconSize={16} />
        <div>
          <div style={{ fontSize: 17, fontWeight: 700, color: COLOR.fg, fontFamily: FONT.body }}>{title}</div>
          <div style={{ fontSize: 12, color: COLOR.muted, fontFamily: FONT.body }}>{skill}</div>
        </div>
        <div style={{ marginLeft: "auto", width: 10, height: 10, borderRadius: "50%", backgroundColor: COLOR.green }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: COLOR.muted, fontFamily: FONT.body }}>
        <span>{runs} runs</span>
        <span style={{ color: COLOR.green, fontWeight: 600 }}>Active</span>
      </div>
    </div>
  );
};

const SceneDashboard: React.FC = () => {
  const { fps } = useVideoConfig();
  const titleScale = useSpring(0, { damping: 200 });
  const subOpacity = useFadeIn(12, 15);

  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <div style={{ transform: `scale(${titleScale})`, fontFamily: FONT.body, fontSize: 52, fontWeight: 900, color: COLOR.fg, marginBottom: 8, textAlign: "center", letterSpacing: "-0.02em" }}>
        Agents run in the background.
      </div>
      <div style={{ opacity: subOpacity, fontFamily: FONT.body, fontSize: 24, color: COLOR.muted, marginBottom: 44, fontWeight: 400 }}>
        You supervise outcomes.
      </div>
      <div style={{ display: "flex", gap: 20, justifyContent: "center" }}>
        <AgentCard title="Slack Recap" platform="Slack" platformColor={COLOR.slack} skill="Digest · Daily 9am" runs={14} delay={Math.round(0.5 * fps)} />
        <AgentCard title="Gmail Digest" platform="Gmail" platformColor={COLOR.gmail} skill="Digest · Daily 8am" runs={12} delay={Math.round(0.7 * fps)} />
        <AgentCard title="Meeting Prep" platform="Calendar" platformColor={COLOR.calendar} skill="Prepare · Daily 7am" runs={10} delay={Math.round(0.9 * fps)} />
      </div>
      <Watermark />
    </AbsoluteFill>
  );
};

// ── Scene 5: Compounding ──
const SceneCompound: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const headScale = useSpring(0, { damping: 200 });
  const ballScale = useSpring(Math.round(0.4 * fps), { damping: 12 });
  const bottomDelay = Math.round(0.8 * fps);
  const bottomOpacity = interpolate(frame, [bottomDelay, bottomDelay + 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const bottomY = interpolate(frame, [bottomDelay, bottomDelay + 15], [50, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });

  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <div style={{ transform: `scale(${headScale})`, textAlign: "center", marginBottom: 40 }}>
        <div style={{ fontFamily: FONT.body, fontSize: 80, fontWeight: 900, color: COLOR.fg, lineHeight: 1.15, letterSpacing: "-0.03em" }}>
          context
        </div>
        <div style={{ fontFamily: FONT.body, fontSize: 80, fontWeight: 900, color: COLOR.fg, lineHeight: 1.15, letterSpacing: "-0.03em" }}>
          compounds
        </div>
      </div>
      <div style={{ transform: `scale(${ballScale})` }}>
        <YarnBall size={56} />
      </div>
      <div style={{ opacity: bottomOpacity, transform: `translateY(${bottomY}px)`, marginTop: 40, textAlign: "center" }}>
        <div style={{ fontFamily: FONT.body, fontSize: 80, fontWeight: 900, color: COLOR.fg, lineHeight: 1.15, letterSpacing: "-0.03em" }}>
          every cycle
        </div>
        <div style={{ fontFamily: FONT.body, fontSize: 80, fontWeight: 900, color: COLOR.fg, lineHeight: 1.15, letterSpacing: "-0.03em" }}>
          gets better
        </div>
      </div>
      <Watermark />
    </AbsoluteFill>
  );
};

// ── Scene 6: CTA ──
const SceneCTA: React.FC = () => {
  const logoScale = useSpring(0, { damping: 15, stiffness: 80 });
  const ballScale = useSpring(15, { damping: 12 });
  const ctaOpacity = useFadeIn(25, 15);
  const ctaY = useSlideUp(25);

  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.bg, justifyContent: "center", alignItems: "center" }}>
      <div style={{ transform: `scale(${logoScale})`, fontFamily: FONT.brand, fontSize: 120, color: COLOR.fg }}>
        yarnnn
      </div>
      <div style={{ transform: `scale(${ballScale})`, marginTop: 24 }}>
        <YarnBall size={48} />
      </div>
      <div
        style={{
          opacity: ctaOpacity,
          transform: `translateY(${ctaY}px)`,
          marginTop: 36,
          fontFamily: FONT.body,
          fontSize: 28,
          color: COLOR.muted,
          fontWeight: 400,
        }}
      >
        Connect once. Supervise from there.
      </div>
      <Watermark />
    </AbsoluteFill>
  );
};

// ── Main composition ──
export const ProductDemo: React.FC = () => {
  const { fps } = useVideoConfig();

  const scenes = [
    { seconds: 3, Component: SceneLogo },
    { seconds: 4, Component: SceneHook },
    { seconds: 5, Component: SceneConnect },
    { seconds: 6, Component: SceneDashboard },
    { seconds: 5, Component: SceneCompound },
    { seconds: 4, Component: SceneCTA },
  ];

  let offset = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.bg }}>
      {scenes.map(({ seconds, Component }, i) => {
        const from = offset;
        const dur = seconds * fps;
        offset += dur;
        return (
          <Sequence key={i} from={from} durationInFrames={dur} premountFor={fps}>
            <Component />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
