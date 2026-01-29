"use client";

import { Shader, Swirl, ChromaFlow } from "shaders/react";

export function ShaderBackgroundDark() {
  return (
    <div className="fixed inset-0 z-0" style={{ contain: "strict" }}>
      <Shader className="h-full w-full">
        {/* Base fluid animation - dark with orange hints */}
        <Swirl
          colorA="#0f0a08"
          colorB="#1a1008"
          speed={0.6}
          detail={0.7}
          blend={45}
        />
        {/* Mouse-reactive color flow - visible orange accents */}
        <ChromaFlow
          baseColor="#0a0a0a"
          upColor="#2a1a0a"
          downColor="#1a0f05"
          leftColor="#3a2010"
          rightColor="#2a1508"
          intensity={0.7}
          radius={1.8}
          momentum={25}
          maskType="alpha"
          opacity={0.85}
        />
      </Shader>
      {/* Slight overlay to blend */}
      <div className="absolute inset-0 bg-black/10" />
    </div>
  );
}
