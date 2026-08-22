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
import type { LaunchPlan, LaunchStatus } from '../domain/activation';
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

/**
 * MVP-FR5: the one-time confirmation summary shown before a launch plan is
 * confirmed. Shows configuration name/revision, the client, the client's
 * OMP version (a `Fact` -- may be `Unknown`), the Instructions/Skills/MCP
 * that will be enabled, any known differences/degradations, and any
 * `-- <args>` that will be forwarded verbatim to the real `omp` invocation
 * -- so the user sees exactly what will be appended *before* they confirm,
 * not just after. Forwarded args are echoed opaquely (never parsed or
 * classified, per Boundaries & Constraints) -- nothing about tasks/
 * prompts/conversation content is shown beyond the raw tokens themselves.
 */
export function renderConfirmationSummary(
  plan: LaunchPlan,
  revision: StableConfigRevision,
  clientVersion: Fact<string>,
  knownDifferences: readonly string[],
  forwardedArgs: readonly string[],
): string {
  const lines = [
    `About to launch OMP with configuration "${revision.configName}" (revision ${revision.revisionId}).`,
    `Client: ${plan.client}  version: ${formatFact(clientVersion)}`,
    '',
    formatCapabilityGroup('instruction', revision.instructions),
    formatCapabilityGroup('skill', revision.skills),
    formatCapabilityGroup('mcp', revision.mcp),
  ];
  if (knownDifferences.length > 0) {
    lines.push('', 'Known differences (will not be fully applied in this MVP):');
    for (const reason of knownDifferences) {
      lines.push(`  - ${reason}`);
    }
  }
  if (forwardedArgs.length > 0) {
    lines.push('', 'Forwarded to `omp` verbatim after `--`:', `  ${forwardedArgs.join(' ')}`);
  }
  lines.push('', 'This is a one-time confirmation for this launch plan -- nothing else will ask again.');
  return lines.join('\n');
}

/**
 * MVP-FR6: launch status view. Only revision/client/version/phase/apply
 * result/known differences -- never task goals, conversation, tool calls,
 * task progress or results (Boundaries & Constraints).
 */
export function renderLaunchStatus(status: LaunchStatus): string {
  const lines = [
    `Revision: ${status.revisionId}`,
    `Client: ${status.client}`,
    `Client version: ${formatFact(status.clientVersion)}`,
    `Phase: ${status.phase}`,
    `Apply result: ${formatFact(status.applyResult)}`,
  ];
  if (status.knownDifferences.length > 0) {
    lines.push('Known differences:');
    for (const reason of status.knownDifferences) {
      lines.push(`  - ${reason}`);
    }
  } else {
    lines.push('Known differences: (none)');
  }
  return lines.join('\n');
}

/** MVP-FR10: immediate, typed "not supported yet" response -- no placeholder, translation or shim. */
export function renderUnsupportedClient(clientId: string, reason: string): string {
  return `Client "${clientId}" is not supported yet: ${reason}`;
}

/**
 * Shared failure/terminal-with-reason rendering for a launch plan --
 * covers both `cancelled` (user rejected the confirmation) and any other
 * failure phase (`failed`/`incomplete`). Never fabricates success and
 * never hides which phase the plan stopped in.
 */
export function renderLaunchFailure(plan: LaunchPlan): string {
  const reason = isKnown(plan.failureReason) ? plan.failureReason.value : formatFact(plan.failureReason);

  if (plan.phase === 'cancelled') {
    return [`Launch plan ${plan.planId} was cancelled: ${reason}.`, 'OMP was not started.'].join('\n');
  }

  // `incomplete` is a domain-distinct terminal state from `failed`
  // (`deriveOutcome` in `application/launch.ts`: the OMP process ended
  // without a determinable exit code, e.g. killed by a signal) -- it must
  // not be reported with the same "failed" wording as an actual non-zero
  // exit.
  const leadingSentence =
    plan.phase === 'incomplete' ? `Launch plan ${plan.planId} did not complete.` : `Launch plan ${plan.planId} failed.`;

  return [
    leadingSentence,
    `Phase: ${plan.phase}`,
    `Reason: ${reason}`,
    `Recovery: inspect the reason above; run \`configs show ${plan.revisionId}\` to re-check the configuration, then \`configs use ${plan.revisionId}\` to retry once resolved.`,
  ].join('\n');
}

/** MVP-FR8: switching never hot-reloads the current process -- it requires a restart and a fresh confirmation. */
export function renderSwitchAccepted(previousPlan: LaunchPlan, newPlan: LaunchPlan): string {
  return [
    `Current OMP process (plan ${previousPlan.planId}) now requires a restart to use a new configuration.`,
    `A new launch plan (${newPlan.planId}) was created for revision ${newPlan.revisionId} and awaits a fresh confirmation.`,
    'The current process is not modified in place and will not auto-resume.',
  ].join('\n');
}
