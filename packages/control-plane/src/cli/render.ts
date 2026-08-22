/**
 * All text rendering for the three read-only views (list/detail/compare)
 * plus the shared empty-state and failure paths. Kept as pure
 * string-building functions over domain/application types so list, show
 * and compare can share the exact same formatting for common fields
 * (Code Map: "公共可导出视图共用同一渲染路径").
 */

import { isKnown } from '../domain/facts';
import type { Fact } from '../domain/facts';
import type {
  CapabilityComparisonEntry,
  CapabilityGroupComparison,
  CapabilityKind,
  CapabilityReference,
  ComparisonResult,
  ScalarFieldComparison,
  StableConfigRevision,
} from '../domain/config';
import type { CompareConfigRevisionsResult, ConfigQueryError } from '../application/queries';

const CAPABILITY_GROUP_LABELS: Record<CapabilityKind, string> = {
  instruction: 'Instructions',
  skill: 'Skills',
  mcp: 'MCP',
  hook: 'Hooks',
  plugin: 'Plugins',
};

function formatFact<T>(fact: Fact<T>, format: (value: T) => string = String): string {
  return isKnown(fact) ? format(fact.value) : `Unknown (${fact.reason}, observed ${fact.observedAt})`;
}

function formatAvailability(revision: StableConfigRevision): string {
  return isKnown(revision.availability) ? 'available' : formatFact(revision.availability);
}

function formatDefaultMarker(revision: StableConfigRevision): string {
  if (!isKnown(revision.defaultMarker)) {
    return formatFact(revision.defaultMarker);
  }
  return revision.defaultMarker.value ? 'default' : 'generic';
}

function formatCapabilityRef(ref: CapabilityReference): string {
  const source = formatFact(ref.sourceCategory);
  const summary = formatFact(ref.summary);
  return `    - ${ref.name} [source: ${source}] ${summary}`;
}

function formatCapabilityGroup(kind: CapabilityKind, refs: readonly CapabilityReference[]): string {
  const label = CAPABILITY_GROUP_LABELS[kind];
  if (refs.length === 0) {
    return `  ${label}: (none configured)`;
  }
  return [`  ${label}:`, ...refs.map(formatCapabilityRef)].join('\n');
}

/** MVP-FR1 empty state: honest, not a product failure. */
export function renderEmptyList(): string {
  return [
    'No saved configuration revisions found.',
    'This CLI only reads configuration revisions already stored in SQLite;',
    'it does not create, import or supply configuration on its own.',
  ].join('\n');
}

export function renderList(revisions: readonly StableConfigRevision[]): string {
  if (revisions.length === 0) {
    return renderEmptyList();
  }
  const lines = revisions.map((revision) => {
    const marker = formatDefaultMarker(revision);
    const boundary = formatFact(revision.scopeBoundary);
    return `- ${revision.configName}  revision=${revision.revisionId}  [${marker}]  status=${formatAvailability(revision)}\n    boundary: ${boundary}`;
  });
  return lines.join('\n');
}

export function renderDetail(revision: StableConfigRevision): string {
  const marker = formatDefaultMarker(revision);
  const lines = [
    `Configuration: ${revision.configName}`,
    `Revision: ${revision.revisionId}  [${marker}]`,
    `Status: ${formatAvailability(revision)}`,
    `Boundary: ${formatFact(revision.scopeBoundary)}`,
    '',
    formatCapabilityGroup('instruction', revision.instructions),
    formatCapabilityGroup('skill', revision.skills),
    formatCapabilityGroup('mcp', revision.mcp),
  ];
  if (revision.hooks.length > 0) {
    lines.push(formatCapabilityGroup('hook', revision.hooks));
  }
  if (revision.plugins.length > 0) {
    lines.push(formatCapabilityGroup('plugin', revision.plugins));
  }
  return lines.join('\n');
}

function formatErrorReason(error: ConfigQueryError): string {
  if (error.kind === 'config-not-found') {
    return `not found. Recovery: run \`configs list\` to see available revision ids.`;
  }
  return `unsupported (${error.reason}). Recovery: re-seed this revision or inspect its stored data; other configurations are unaffected.`;
}

/** Shared failure rendering for `show`/`compare`: identifier + typed reason + recovery entry. */
export function renderQueryFailure(revisionId: string, error: ConfigQueryError): string {
  return `Configuration "${revisionId}": ${formatErrorReason(error)}`;
}

function formatScalarField(field: ScalarFieldComparison): string {
  const header = `${field.field} [${field.status}]`;
  const rows = field.entries.map((entry) => `    ${entry.revisionId}: ${formatFact(entry.value)}`);
  return [header, ...rows].join('\n');
}

/**
 * When a capability's source category is `different`/`unknown` across the
 * compared revisions, print which revision has which value -- the
 * aggregate status alone ("different") does not say what the difference
 * actually is.
 */
function formatSourceCategoryBreakdown(entry: CapabilityComparisonEntry): string[] {
  if (entry.sourceCategoryStatus === 'same') {
    return [];
  }
  return entry.sourceCategoryByRevision
    .filter((byRevision) => byRevision.sourceCategory !== null)
    .map((byRevision) => `      ${byRevision.revisionId}: ${formatFact(byRevision.sourceCategory!)}`);
}

function formatCapabilityGroupComparison(group: CapabilityGroupComparison): string {
  const label = CAPABILITY_GROUP_LABELS[group.kind];
  if (group.entries.length === 0) {
    return `${label}: (none in any compared revision)`;
  }
  const rows = group.entries.flatMap((entry) => {
    const missing = entry.missingIn.length > 0 ? ` missing in: ${entry.missingIn.join(', ')}` : '';
    return [`    - ${entry.name} [source: ${entry.sourceCategoryStatus}]${missing}`, ...formatSourceCategoryBreakdown(entry)];
  });
  return [`${label}:`, ...rows].join('\n');
}

export function renderComparison(result: ComparisonResult): string {
  const lines = [
    `Comparing ${result.revisionIds.length} revision(s): ${result.revisionIds.join(', ')}`,
    '',
    ...result.scalarFields.map(formatScalarField),
    '',
    ...result.capabilities.map(formatCapabilityGroupComparison),
  ];
  return lines.join('\n');
}

export function renderCompareResult(result: CompareConfigRevisionsResult): string {
  const sections: string[] = [];

  if (result.comparison !== null) {
    sections.push(renderComparison(result.comparison));
  } else {
    sections.push('No valid configuration revisions were resolved to compare.');
  }

  if (result.failed.length > 0) {
    sections.push('');
    sections.push('Unresolved ids:');
    for (const failure of result.failed) {
      sections.push(`  ${renderQueryFailure(failure.revisionId, failure.error)}`);
    }
  }

  return sections.join('\n');
}
