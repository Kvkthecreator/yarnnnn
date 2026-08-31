/**
 * CarouselFiles — the Files proof slide for the ad carousel (1080×1080, 8s).
 *
 * COMPOSED, not captured. content/_creatives/_reference/claude-linkedin-
 * carousel.md records the rule this follows: "Text lives in the image —
 * carousel cards carry their own headline + subhead inside the image." On the
 * landing page the headline lives in an HTML column beside the mockup
 * (AppShowcase.tsx); cropped out of that context a bare window states no
 * claim. So the slide re-unites them: kicker + headline above, product
 * replica below, on the brand ground.
 *
 * Copy is VERBATIM from AppShowcase.tsx's `files` section — the canon-locked
 * marketing copy, not a paraphrase.
 *
 * The mockup keeps its own light ground (it is a window, and the product's
 * chrome only reads correctly against its real tokens) while the card sits on
 * COLOR.bg peach — the same figure-on-brand relationship the static ad frames
 * use.
 */

import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Easing } from "remotion";
import { COLOR, FONT, Watermark, useSpring } from "../design";
import { FilesReplica } from "../replicas/FilesReplica";

/** Verbatim from web/components/landing/AppShowcase.tsx → SECTIONS.files */
const KICKER = "The record · Files";
const TITLE = "One shared file system — every change signed.";

export const CarouselFiles: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Kicker, then headline, then the window rises in.
  const kicker = interpolate(frame, [0, 0.4 * fps], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.quad),
  });
  const title = interpolate(frame, [0.15 * fps, 0.45 * fps], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.quad),
  });
  const windowIn = useSpring(Math.round(0.4 * fps), { damping: 200 });

  // Fade the last 0.4s to black-free cream so a looping carousel card doesn't
  // hard-cut on the seam.
  const outro = interpolate(
    frame,
    [durationInFrames - 0.4 * fps, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.bg, opacity: outro }}>
      <AbsoluteFill
        style={{
          padding: 72,
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        {/* Kicker — the mono uppercase eyebrow, orange, as on the page */}
        <div
          style={{
            opacity: kicker,
            fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
            fontSize: 26,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
            color: COLOR.orange,
            marginBottom: 20,
            alignSelf: "flex-start",
          }}
        >
          {KICKER}
        </div>

        {/* Headline — the claim the slide has to make on its own */}
        <div
          style={{
            opacity: title,
            transform: `translateY(${interpolate(title, [0, 1], [16, 0])}px)`,
            fontFamily: FONT.body,
            fontSize: 62,
            fontWeight: 700,
            letterSpacing: "-0.025em",
            lineHeight: 1.12,
            color: COLOR.fg,
            alignSelf: "flex-start",
            marginBottom: 56,
          }}
        >
          {TITLE}
        </div>

        {/* The product replica */}
        <div
          style={{
            opacity: windowIn,
            transform: `translateY(${interpolate(windowIn, [0, 1], [40, 0])}px)`,
          }}
        >
          <FilesReplica scale={1.75} />
        </div>
      </AbsoluteFill>

      <Watermark opacity={interpolate(frame, [1.2 * fps, 1.6 * fps], [0, 1], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      })} />
    </AbsoluteFill>
  );
};
