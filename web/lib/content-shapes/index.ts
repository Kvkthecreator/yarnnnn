/**
 * Content-Shape Registry — ADR-244 Frontend Kernel L2 home.
 *
 * Each entry under web/lib/content-shapes/ owns one content shape (autonomy,
 * decisions, performance, principles, recurrence-spec, etc.). Phase 1 ships
 * the directory + this stub index; Phase 2 migrates existing parsers in
 * web/lib/{autonomy,reviewer-decisions,recurrence-shapes,inference-meta,
 * snapshot-meta}.ts into this directory and populates CONTENT_SHAPES.
 *
 * Schema: per ADR-244 D3, every shape exports SHAPE_KEY, PATH_GLOB, parse(),
 * serialize() (when WRITE_CONTRACT permits), WRITE_CONTRACT (D5), and
 * CANONICAL_L3 (D4). The `writeShape` helper added in Phase 4 routes to the
 * correct primitive based on WRITE_CONTRACT.
 */

export type WriteContract =
  | "narrative"
  | "authored_prose"
  | "configuration"
  | "live_aggregate"
  | "declaration"
  | "composed_artifact"
  | "system_owned";

export type ContentShape = {
  SHAPE_KEY: string;
  PATH_GLOB: string;
  WRITE_CONTRACT: WriteContract;
  CANONICAL_L3: string;
};

export const CONTENT_SHAPES: Readonly<Record<string, ContentShape>> = {};

export function shapeForPath(_path: string): ContentShape | null {
  return null;
}
