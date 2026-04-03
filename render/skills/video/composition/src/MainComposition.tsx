import React from "react";
import { Series } from "remotion";
import type { VideoProps } from "./types";
import { ThemeProvider } from "./theme";
import { Slide } from "./Slide";

export const MainComposition: React.FC<VideoProps> = ({
  slides,
  theme,
  fps = 30,
}) => {
  return (
    <ThemeProvider theme={theme}>
      <Series>
        {slides.map((slide, i) => (
          <Series.Sequence
            key={i}
            durationInFrames={slide.duration * fps}
            premountFor={fps}
          >
            <Slide slide={slide} />
          </Series.Sequence>
        ))}
      </Series>
    </ThemeProvider>
  );
};
