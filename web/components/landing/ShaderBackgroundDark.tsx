"use client";

import { Shader, Swirl, ChromaFlow } from "shaders/react";

export function ShaderBackgroundDark() {
  return (
    <div className="fixed inset-0 z-0" style={{ contain: "strict" }}>
      <Shader className="h-full w-full">
        {/* Base fluid animation - deep dark tones */}
        <Swirl
          colorA="#0a0a0a"
          colorB="#1a1510"
          speed={0.6}
          detail={0.7}
          blend={40}
        />
        {/* Mouse-reactive color flow - subtle warm undertones */}
        <ChromaFlow
          baseColor="#0d0d0d"
          upColor="#151210"
          downColor="#0a0a0a"
          leftColor="#12100d"
          rightColor="#0f0d0a"
          intensity={0.5}
          radius={1.6}
          momentum={20}
          maskType="alpha"
          opacity={0.9}
        />
      </Shader>
      {/* Subtle dark overlay */}
      <div className="absolute inset-0 bg-black/20" />
    </div>
  );
}
