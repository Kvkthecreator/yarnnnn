/** Node resolve hook so gates can execute the app's OWN TypeScript modules
 *  (extensionless relative imports, as the bundler resolves them) under
 *  node's native type stripping. Registered via:
 *    node --import ./web/scripts/gates/_ts_register.mjs <gate>
 */
import { existsSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

export async function resolve(specifier, context, nextResolve) {
  if (specifier.startsWith('./') || specifier.startsWith('../')) {
    const parent = context.parentURL ? fileURLToPath(context.parentURL) : null;
    if (parent && !path.extname(specifier)) {
      const base = path.resolve(path.dirname(parent), specifier);
      for (const ext of ['.ts', '.tsx']) {
        if (existsSync(base + ext)) {
          return nextResolve(pathToFileURL(base + ext).href, context);
        }
      }
    }
  }
  return nextResolve(specifier, context);
}
