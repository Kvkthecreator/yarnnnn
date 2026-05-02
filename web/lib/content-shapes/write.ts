/**
 * writeShape() — ADR-245 Phase 4 typed write helper.
 *
 * Routes operator-initiated writes to the correct primitive based on the
 * shape's WRITE_CONTRACT (per ADR-245 D5):
 *
 *   - `authored_prose`  → WriteFile(scope='workspace')   via api.workspace.editFile
 *   - `configuration`   → WriteFile(scope='workspace')   via api.workspace.editFile
 *   - `declaration`     → ManageRecurrence (FE editor deferred — throws today)
 *   - `narrative`       → never (system writers append-only — throws)
 *   - `live_aggregate`  → never (system-owned — throws)
 *   - `composed_artifact` → never (system-derived — throws)
 *   - `system_owned`    → never (broad sentinel — throws)
 *
 * Singular Implementation: every operator-initiated mutation of a
 * registry-covered shape routes through this helper. Callers do NOT call
 * api.workspace.editFile directly for substrate covered by a content
 * shape — they call writeShape so write-contract is enforced.
 *
 * ADR-209 attribution: the backend defaults `authored_by="operator"` for
 * operator-session writes. opts.message is forwarded verbatim as the
 * revision commit message.
 */

import { CONTENT_SHAPES, type WriteContract } from './index';
import { api } from '@/lib/api/client';

const WRITABLE_CONTRACTS: ReadonlySet<WriteContract> = new Set<WriteContract>([
  'authored_prose',
  'configuration',
  // declaration is "writable" but routes elsewhere; checked separately
]);

const DECLARATION_CONTRACT: WriteContract = 'declaration';

export class WriteContractViolation extends Error {
  readonly shapeKey: string;
  readonly contract: WriteContract;

  constructor(shapeKey: string, contract: WriteContract) {
    super(
      `writeShape('${shapeKey}'): WRITE_CONTRACT='${contract}' is not ` +
        `operator-writable. ${describeContract(contract)}`,
    );
    this.name = 'WriteContractViolation';
    this.shapeKey = shapeKey;
    this.contract = contract;
  }
}

function describeContract(c: WriteContract): string {
  switch (c) {
    case 'narrative':
      return 'Narrative substrate is append-only by system writers per ADR-245 D5.';
    case 'live_aggregate':
      return 'Live aggregates are system-owned per ADR-245 D5; operator interacts via outcome → feedback path.';
    case 'composed_artifact':
      return 'Composed artifacts are system-derived (ADR-213 surface-pull pipeline).';
    case 'system_owned':
      return 'system_owned is the broad sentinel — only system writers may mutate.';
    default:
      return '';
  }
}

export interface WriteShapeOpts {
  /**
   * Optional commit message for the ADR-209 revision. The backend sets
   * `authored_by` from the operator session by default; this helper does
   * not override it.
   */
  message?: string;
}

/**
 * Write serialized shape content to a workspace path through the
 * primitive matched by the shape's WRITE_CONTRACT.
 *
 * Callers are expected to have invoked the shape's `serialize(data, body)`
 * function before calling this helper — `writeShape` itself is content-
 * agnostic so the same helper handles every writable shape uniformly.
 */
export async function writeShape(
  shapeKey: string,
  path: string,
  serializedContent: string,
  opts: WriteShapeOpts = {},
): Promise<void> {
  const shape = CONTENT_SHAPES[shapeKey];
  if (!shape) {
    throw new Error(`writeShape: unknown shape '${shapeKey}'`);
  }

  if (shape.WRITE_CONTRACT === DECLARATION_CONTRACT) {
    // Declaration shapes (`_spec.yaml`, `_recurring.yaml`, `_action.yaml`)
    // route through ManageRecurrence per ADR-235 D1.c, NOT WriteFile. The
    // FE editor for declaration shapes is deferred — see ADR-245 §Phase 4
    // deferrals. When the editor lands, this branch wires up the
    // ManageRecurrence call.
    throw new Error(
      `writeShape: declaration shape '${shapeKey}' routes through ` +
        `ManageRecurrence (ADR-235 D1.c), not WriteFile. The FE editor ` +
        `for declaration shapes is deferred — see ADR-245 §Phase 4.`,
    );
  }

  if (!WRITABLE_CONTRACTS.has(shape.WRITE_CONTRACT)) {
    throw new WriteContractViolation(shapeKey, shape.WRITE_CONTRACT);
  }

  // configuration + authored_prose: WriteFile(scope='workspace') per
  // ADR-235 D1.b. api.workspace.editFile is the existing surface; the
  // backend records ADR-209 attribution from the operator session.
  await api.workspace.editFile(path, serializedContent, undefined, opts.message);
}
