"use client";

import { Shader, Swirl, ChromaFlow } from "shaders/react";

export function ShaderBackground() {
  return (
    <div
      className="fixed inset-0 z-0"
      style={{
        contain: "strict",
      }}
    >
      <Shader className="h-full w-full">
        {/* Base fluid animation - warm light tones with orange */}
        <Swirl
          colorA="#f5ebe0"
          colorB="#edd9c4"
          speed={0.8}
          detail={0.8}
          blend={50}
        />
        {/* Mouse-reactive color flow - brand orange hints */}
        <ChromaFlow
          baseColor="#f8f4ef"
          upColor="#f0e0d0"
          downColor="#faf6f2"
          leftColor="#e8d4c0"
          rightColor="#f5e8da"
          intensity={0.7}
          radius={1.8}
          momentum={25}
          maskType="alpha"
          opacity={0.95}
        />
      </Shader>
      {/* Subtle light overlay for text readability */}
      <div className="absolute inset-0 bg-white/10" />
    </div>
  );
}
