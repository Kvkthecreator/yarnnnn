"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Shader } from "shaders/react";

// One-shot probe: try to acquire a WebGL2 (preferred) or WebGL context on
// a throwaway canvas. Returns false when the GL context is null — Chrome
// returns null when hardware acceleration is off, GPU process has crashed,
// or the user is in a sandboxed/headless context. Mounting <Shader> in that
// state crashes inside three.webgpu.js → WebGLExtensions(null).getSupportedExtensions().
function probeWebGLSupport(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    const gl =
      canvas.getContext("webgl2") ||
      canvas.getContext("webgl") ||
      canvas.getContext("experimental-webgl");
    return gl !== null;
  } catch {
    return false;
  }
}

export function ShaderCanvas({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  // The probe can only run in the browser, so it MUST NOT decide the first
  // render: the server renders null, and a lazy useState initialiser would
  // make the client's first render disagree with it — React #418/#423 on
  // every WebGL-capable visitor. Probing in an effect keeps hydration
  // byte-identical to SSR and mounts the shader on the commit after.
  const [supported, setSupported] = useState(false);
  useEffect(() => {
    setSupported(probeWebGLSupport());
  }, []);
  if (!supported) return null;
  return <Shader className={className}>{children}</Shader>;
}
