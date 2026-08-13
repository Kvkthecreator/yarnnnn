/** Node resolve hook so gates can execute the app's OWN TypeScript modules
 *  (extensionless relative imports, as the bundler resolves them) under
 *  node's native type stripping. Registered via:
 *    node --import ./web/scripts/gates/_ts_register.mjs <gate>
 */
import { existsSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

/** `@/*` → `web/*`, mirroring web/tsconfig.json's `paths`. Without this a gate
 *  importing any module that uses the app's own alias dies at resolve time. */
const WEB_ROOT = path.resolve(fileURLToPath(import.meta.url), '../../..');

export async function resolve(specifier, context, nextResolve) {
  const isRelative = specifier.startsWith('./') || specifier.startsWith('../');
  const isAliased = specifier.startsWith('@/');
  if (isRelative || isAliased) {
    const parent = context.parentURL ? fileURLToPath(context.parentURL) : null;
    const base = isAliased
      ? path.join(WEB_ROOT, specifier.slice(2))
      : parent
        ? path.resolve(path.dirname(parent), specifier)
        : null;
    if (base) {
      // An extensionless specifier resolves as the bundler does; an aliased one
      // may already carry its extension, so try the bare path too.
      const candidates = path.extname(base)
        ? [base]
        : ['.ts', '.tsx'].map((ext) => base + ext);
      for (const candidate of candidates) {
        if (existsSync(candidate)) {
          return nextResolve(pathToFileURL(candidate).href, context);
        }
      }
    }
  }
  return nextResolve(specifier, context);
}
