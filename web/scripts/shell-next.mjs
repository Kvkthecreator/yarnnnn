// ADR-661 §7o — run Next for the desktop shell, on any OS.
//
//   node web/scripts/shell-next.mjs build   (tauri.conf.json beforeBuildCommand)
//   node web/scripts/shell-next.mjs dev     (tauri.conf.json beforeDevCommand)
//
// WHY A SCRIPT: the command used to be `YARNNN_SHELL=1 … npx next build`, and a
// leading `NAME=value` is POSIX shell syntax. Tauri runs these commands through
// `cmd` on Windows, which reads it as a program called `YARNNN_SHELL=1`, so the
// Windows build could not start. Node reads the same way on every platform, so
// the environment is set here and nowhere else.
//
// WHAT IT PINS:
//   YARNNN_SHELL=1        — switches next.config.js to the static export (§7b).
//   NEXT_PUBLIC_API_URL   — build only. A `NEXT_PUBLIC_*` value is frozen into
//                           the binary, and a developer's `.env.local` says
//                           `http://localhost:8000` — which shipped once
//                           (§7m). Process env outranks `.env.local`, and
//                           next.config.js refuses a loopback or plain-http
//                           origin if this pin is ever removed. `dev` is left
//                           alone: pointing a dev shell at a local API is the
//                           point of dev.

import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SHELL_API_ORIGIN = "https://yarnnn-api.onrender.com";

const mode = process.argv[2];
if (mode !== "build" && mode !== "dev") {
  console.error("usage: node web/scripts/shell-next.mjs build|dev");
  process.exit(2);
}

const web = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const env = { ...process.env, YARNNN_SHELL: "1" };
if (mode === "build") env.NEXT_PUBLIC_API_URL = SHELL_API_ORIGIN;

// Next's own entry point, run by this same Node — no `npx`, no shell, so
// nothing between here and Next parses the command line differently per OS.
const next = createRequire(resolve(web, "package.json")).resolve("next/dist/bin/next");
const args = mode === "dev" ? [next, "dev", "-p", "3000"] : [next, "build"];
const run = spawnSync(process.execPath, args, { cwd: web, env, stdio: "inherit" });
process.exit(run.status ?? 1);
