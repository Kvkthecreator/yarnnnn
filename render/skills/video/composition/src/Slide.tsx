import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import type { Slide as SlideType } from "./types";
import { useTheme } from "./theme";
import { CenterLayout } from "./layouts/Center";
import { StackLayout } from "./layouts/Stack";
import { SplitLayout } from "./layouts/Split";

type Props = {
  slide: SlideType;
};

const LayoutRouter: React.FC<{ layout: string; elements: SlideType["elements"] }> = ({
  layout,
  elements,
}) => {
  switch (layout) {
    case "split":
      return <SplitLayout elements={elements} />;
    case "stack":
      return <StackLayout elements={elements} />;
    case "center":
    default:
      return <CenterLayout elements={elements} />;
  }
};

export const Slide: React.FC<Props> = ({ slide }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = useTheme();
  const totalFrames = slide.duration * fps;

  // Entrance transition
  const transition = slide.transition || "fade";
  let enterOpacity = 1;
  let enterTransform = "none";

  const transitionDuration = fps * 0.4; // 0.4 seconds

  if (transition === "fade") {
    enterOpacity = interpolate(frame, [0, transitionDuration], [0, 1], {
      extrapolateRight: "clamp",
    });
  } else if (transition === "slide-left") {
    enterOpacity = interpolate(frame, [0, transitionDuration], [0, 1], {
      extrapolateRight: "clamp",
    });
    const translateX = interpolate(frame, [0, transitionDuration], [100, 0], {
      extrapolateRight: "clamp",
    });
    enterTransform = `translateX(${translateX}px)`;
  } else if (transition === "slide-up") {
    enterOpacity = interpolate(frame, [0, transitionDuration], [0, 1], {
      extrapolateRight: "clamp",
    });
    const translateY = interpolate(frame, [0, transitionDuration], [60, 0], {
      extrapolateRight: "clamp",
    });
    enterTransform = `translateY(${translateY}px)`;
  }
  // "cut" = no transition animation

  // Exit fade (last 0.3 seconds)
  const exitStart = totalFrames - fps * 0.3;
  const exitOpacity =
    frame > exitStart
      ? interpolate(frame, [exitStart, totalFrames], [1, 0], {
          extrapolateRight: "clamp",
        })
      : 1;

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        backgroundColor: theme.background,
        opacity: enterOpacity * exitOpacity,
        transform: enterTransform,
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      }}
    >
      <LayoutRouter layout={slide.layout} elements={slide.elements} />
    </div>
  );
};
