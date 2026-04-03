import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useTheme, FONT_SIZES, resolveColor } from "../theme";

type Props = {
  items: string[];
  delay?: number;
};

const STAGGER_FRAMES = 6;

export const List: React.FC<Props> = ({ items, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = useTheme();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {items.map((item, i) => {
        const itemDelay = delay + i * STAGGER_FRAMES;
        const opacity = interpolate(
          frame - itemDelay,
          [0, fps * 0.3],
          [0, 1],
          { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
        );
        const x = spring({
          frame: frame - itemDelay,
          fps,
          config: { damping: 200, stiffness: 100 },
        });
        const translateX = interpolate(x, [0, 1], [30, 0]);

        return (
          <div
            key={i}
            style={{
              opacity,
              transform: `translateX(${translateX}px)`,
              display: "flex",
              alignItems: "flex-start",
              gap: 12,
              fontSize: FONT_SIZES.md,
              color: resolveColor("foreground", theme),
              lineHeight: 1.4,
            }}
          >
            <span
              style={{
                color: theme.accent,
                fontSize: 20,
                marginTop: 4,
                flexShrink: 0,
              }}
            >
              {"\u25CF"}
            </span>
            <span>{item}</span>
          </div>
        );
      })}
    </div>
  );
};
