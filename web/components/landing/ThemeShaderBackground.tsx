"use client";

import { ShaderBackground } from "./ShaderBackground";
import { ShaderBackgroundDark } from "./ShaderBackgroundDark";

export function ThemeShaderBackground() {
  return (
    <>
      <div className="dark:hidden">
        <ShaderBackground />
      </div>
      <div className="hidden dark:block">
        <ShaderBackgroundDark />
      </div>
    </>
  );
}
