/**
 * `domain/` must not import Bun, SQLite, the filesystem, or the process
 * environment. Only pure types and functions live here.
 */

import { type Fact, factsEqual, isUnknown, known } from './facts';

/**
 * The three capability groups required by MVP-FR2. `hook` and `plugin` are
 * carried too (Design Notes: hooks/plugins are out of AC scope but, when
 * present, must not be dropped -- they are surfaced as sibling groupings
 * alongside Skills rather than folded into it).
 */
export type CapabilityKind = 'instruction' | 'skill' | 'mcp' | 'hook' | 'plugin';

/**
 * Where a capability reference is provably sourced from. Never inferred
 * from "file exists" / "installed" -- only from declarations this Story is
 * allowed to read (see Design Notes field mapping).
 */
export type SourceCategory =
  | 'project-capability'
  | 'project-skill-import'
  | 'project-prompt'
  | 'unknown-source';

/**
 * A typed reference to one Instruction/Skill/MCP/Hook/Plugin. Only the
 * identifier, its source category and an allowed-public summary are ever
 * carried -- never private prompt text, credentials, transcripts or tool
 * payloads.
 */
export interface CapabilityReference {
  readonly kind: CapabilityKind;
  readonly name: string;
  readonly sourceCategory: Fact<SourceCategory>;
  readonly summary: Fact<string>;
}

/**
 * Whether this revision's configuration could be mechanically resolved
 * against its lock data. `'resolved'` is the only known value; anything
 * else must be represented as `Unknown(reason, observedAt)`.
 */
export type ConfigAvailability = Fact<'resolved'>;

/**
 * An immutable, fully-identified configuration revision. Comparisons,
 * detail views and list rows are always bound to a specific revision --
 * nothing here is mutated in place.
 */
export interface StableConfigRevision {
  readonly configName: string;
  readonly revisionId: string;
  readonly defaultMarker: Fact<boolean>;
  readonly scopeBoundary: Fact<string>;
  readonly availability: ConfigAvailability;
  readonly instructions: readonly CapabilityReference[];
  readonly skills: readonly CapabilityReference[];
  readonly mcp: readonly CapabilityReference[];
  readonly hooks: readonly CapabilityReference[];
  readonly plugins: readonly CapabilityReference[];
}

export type ScalarFieldName =
  | 'configName'
  | 'revisionId'
  | 'defaultMarker'
  | 'scopeBoundary'
  | 'availability';

export type ComparisonStatus = 'same' | 'different' | 'unknown';

export interface ScalarFieldEntry {
  readonly revisionId: string;
  readonly value: Fact<string | boolean>;
}

/** One field, laid out side by side across every compared revision. */
export interface ScalarFieldComparison {
  readonly field: ScalarFieldName;
  readonly entries: readonly ScalarFieldEntry[];
  readonly status: ComparisonStatus;
}

export interface CapabilitySourceEntry {
  readonly revisionId: string;
  /** `null` when the capability is absent from this revision. */
  readonly sourceCategory: Fact<SourceCategory> | null;
}

export interface CapabilityComparisonEntry {
  readonly name: string;
  readonly presentIn: readonly string[];
  readonly missingIn: readonly string[];
  readonly sourceCategoryStatus: ComparisonStatus;
  readonly sourceCategoryByRevision: readonly CapabilitySourceEntry[];
}

/** Mechanical composition/source comparison for one capability kind. */
export interface CapabilityGroupComparison {
  readonly kind: CapabilityKind;
  readonly entries: readonly CapabilityComparisonEntry[];
}

/**
 * Pure, mechanical side-by-side comparison. Never produces a score,
 * ranking, recommendation or automatic candidate -- only same/different/
 * unknown per field, and presence/absence per capability.
 */
export interface ComparisonResult {
  readonly revisionIds: readonly string[];
  readonly scalarFields: readonly ScalarFieldComparison[];
  readonly capabilities: readonly CapabilityGroupComparison[];
}

const CAPABILITY_KINDS: readonly CapabilityKind[] = ['instruction', 'skill', 'mcp', 'hook', 'plugin'];

function scalarStatus(entries: readonly ScalarFieldEntry[]): ComparisonStatus {
  if (entries.some((entry) => isUnknown(entry.value))) {
    return 'unknown';
  }
  const first = entries[0];
  if (first === undefined) {
    return 'same';
  }
  const allEqual = entries.every((entry) => factsEqual(entry.value, first.value));
  return allEqual ? 'same' : 'different';
}

function compareScalarField(
  field: ScalarFieldName,
  revisions: readonly StableConfigRevision[],
  select: (revision: StableConfigRevision) => Fact<string | boolean>,
): ScalarFieldComparison {
  const entries = revisions.map((revision) => ({
    revisionId: revision.revisionId,
    value: select(revision),
  }));
  return { field, entries, status: scalarStatus(entries) };
}

function capabilitiesOfKind(
  revision: StableConfigRevision,
  kind: CapabilityKind,
): readonly CapabilityReference[] {
  switch (kind) {
    case 'instruction':
      return revision.instructions;
    case 'skill':
      return revision.skills;
    case 'mcp':
      return revision.mcp;
    case 'hook':
      return revision.hooks;
    case 'plugin':
      return revision.plugins;
    default:
      return [];
  }
}

function compareCapabilityGroup(
  kind: CapabilityKind,
  revisions: readonly StableConfigRevision[],
): CapabilityGroupComparison {
  const byRevision = revisions.map((revision) => ({
    revisionId: revision.revisionId,
    refs: new Map(capabilitiesOfKind(revision, kind).map((ref) => [ref.name, ref])),
  }));

  const allNames = new Set<string>();
  for (const { refs } of byRevision) {
    for (const name of refs.keys()) {
      allNames.add(name);
    }
  }

  const entries: CapabilityComparisonEntry[] = [...allNames].sort().map((name) => {
    const presentIn: string[] = [];
    const missingIn: string[] = [];
    const sourceCategoryByRevision: CapabilitySourceEntry[] = [];

    for (const { revisionId, refs } of byRevision) {
      const ref = refs.get(name);
      if (ref === undefined) {
        missingIn.push(revisionId);
        sourceCategoryByRevision.push({ revisionId, sourceCategory: null });
      } else {
        presentIn.push(revisionId);
        sourceCategoryByRevision.push({ revisionId, sourceCategory: ref.sourceCategory });
      }
    }

    const knownCategories = sourceCategoryByRevision
      .map((entry) => entry.sourceCategory)
      .filter((fact): fact is Fact<SourceCategory> => fact !== null);
    let sourceCategoryStatus: ComparisonStatus;
    if (knownCategories.some((fact) => isUnknown(fact))) {
      sourceCategoryStatus = 'unknown';
    } else if (knownCategories.length === 0) {
      sourceCategoryStatus = 'same';
    } else {
      const first = knownCategories[0]!;
      sourceCategoryStatus = knownCategories.every((fact) => factsEqual(fact, first)) ? 'same' : 'different';
    }

    return { name, presentIn, missingIn, sourceCategoryStatus, sourceCategoryByRevision };
  });

  return { kind, entries };
}

/**
 * Mechanically lays the same fields side by side for every revision.
 * `differences` = a field whose comparable values are not all equal.
 * `Unknown` on either side makes the whole field `unknown` -- it is never
 * guessed to be equal or different (Design Notes: 比较的"差异"定义).
 */
export function compareRevisions(revisions: readonly StableConfigRevision[]): ComparisonResult {
  const revisionIds = revisions.map((revision) => revision.revisionId);

  const scalarFields: ScalarFieldComparison[] = [
    compareScalarField('configName', revisions, (r) => known(r.configName)),
    compareScalarField('revisionId', revisions, (r) => known(r.revisionId)),
    compareScalarField('defaultMarker', revisions, (r) => r.defaultMarker),
    compareScalarField('scopeBoundary', revisions, (r) => r.scopeBoundary),
    compareScalarField('availability', revisions, (r) => r.availability),
  ];

  const capabilities = CAPABILITY_KINDS.map((kind) => compareCapabilityGroup(kind, revisions));

  return { revisionIds, scalarFields, capabilities };
}
