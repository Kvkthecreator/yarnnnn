/**
 * Entity Cache
 *
 * Simple in-memory cache for entity names (deliverables, projects).
 * Surfaces populate this cache when loading data, TPBar reads from it
 * to display actual names instead of generic labels.
 */

interface CachedEntity {
  name: string;
  type: 'deliverable' | 'project';
  cachedAt: number;
}

const entityCache = new Map<string, CachedEntity>();

// Cache TTL: 5 minutes (entities don't change names often)
const CACHE_TTL_MS = 5 * 60 * 1000;

/**
 * Cache an entity's name for display in TPBar
 */
export function cacheEntity(
  id: string,
  name: string,
  type: 'deliverable' | 'project'
): void {
  entityCache.set(id, {
    name,
    type,
    cachedAt: Date.now(),
  });
}

/**
 * Get a cached entity name, or undefined if not cached/expired
 */
export function getEntityName(id: string): string | undefined {
  const cached = entityCache.get(id);
  if (!cached) return undefined;

  // Check if expired
  if (Date.now() - cached.cachedAt > CACHE_TTL_MS) {
    entityCache.delete(id);
    return undefined;
  }

  return cached.name;
}

/**
 * Get cached entity with type info
 */
export function getCachedEntity(id: string): CachedEntity | undefined {
  const cached = entityCache.get(id);
  if (!cached) return undefined;

  // Check if expired
  if (Date.now() - cached.cachedAt > CACHE_TTL_MS) {
    entityCache.delete(id);
    return undefined;
  }

  return cached;
}

/**
 * Clear a specific entity from cache (e.g., after rename)
 */
export function invalidateEntity(id: string): void {
  entityCache.delete(id);
}

/**
 * Clear all cached entities (e.g., on logout)
 */
export function clearEntityCache(): void {
  entityCache.clear();
}
