"use client";

import { Shader, Swirl, ChromaFlow } from "shaders/react";

export function ShaderBackgroundDark() {
  return (
    <div className="fixed inset-0 z-0" style={{ contain: "strict" }}>
      <Shader className="h-full w-full">
        {/* Base fluid animation - dark with cyan/teal hints (matching icon) */}
        <Swirl
          colorA="#080f0f"
          colorB="#081218"
          speed={0.6}
          detail={0.7}
          blend={45}
        />
        {/* Mouse-reactive color flow - subtle cyan/teal accents */}
        <ChromaFlow
          baseColor="#0a0a0a"
          upColor="#0a1a2a"
          downColor="#051a1a"
          leftColor="#102030"
          rightColor="#081520"
          intensity={0.8}
          radius={3.5}
          momentum={25}
          maskType="alpha"
          opacity={0.9}
        />
      </Shader>
      {/* Slight overlay to blend */}
      <div className="absolute inset-0 bg-black/10" />
    </div>
  );
}
