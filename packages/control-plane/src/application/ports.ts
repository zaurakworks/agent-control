import type { Fact } from '../domain/facts';
import type { StableConfigRevision } from '../domain/config';
import type { ClientId } from '../domain/client';
import type { LaunchPlan } from '../domain/activation';

/**
 * Read-only persistence port. Adapters implement this against whatever
 * storage backs it (SQLite in production); they must not make product
 * decisions -- e.g. "not found" is represented as `null`, and the
 * application layer is the one that turns that into a typed error.
 */
export interface ConfigRevisionRepository {
  listAll(): Promise<readonly StableConfigRevision[]>;
  findById(revisionId: string): Promise<StableConfigRevision | null>;
}

/**
 * Persistence port for `LaunchPlan`s. Like `ConfigRevisionRepository`,
 * adapters must not make product decisions -- "not found" is `null`; the
 * application layer turns that into a typed error.
 */
export interface LaunchPlanRepository {
  save(plan: LaunchPlan): Promise<void>;
  findById(planId: string): Promise<LaunchPlan | null>;
  /**
   * The most recently created plan for `client`, regardless of phase.
   * Used both to detect "is there something to switch away from" and to
   * resolve `configs status` when no explicit plan id is given.
   */
  findActiveForClient(client: ClientId): Promise<LaunchPlan | null>;
}

export interface OmpSpawnParams {
  readonly revision: StableConfigRevision;
  /** Path to the version-1 launch context JSON file (delivered to OMP via env, not argv). */
  readonly launchContextPath: string;
  /** Path to the thin status/switch extension file, or `null` to not load one. */
  readonly extensionPath: string | null;
  /** Opaque user-provided argv tail, passed through unparsed. */
  readonly forwardedArgs: readonly string[];
  readonly cwd: string;
}

export interface OmpSpawnResult {
  readonly exitCode: number | null;
  readonly signal: string | null;
}

/**
 * The only way this package ever starts or inspects the OMP binary.
 * Adapters must spawn it directly via an argv array (never a shell) --
 * see Boundaries & Constraints.
 */
export interface OmpProcessPort {
  detectVersion(): Promise<Fact<string>>;
  spawn(params: OmpSpawnParams): Promise<OmpSpawnResult>;
}

export type CapabilityProbeLevel = 'supported' | 'degraded' | 'unsupported' | 'unknown';

export interface CapabilityProbeResult {
  readonly level: CapabilityProbeLevel;
  readonly reason: string;
}

/**
 * A real, one-time detection of whether OMP's *native* interface already
 * satisfies the current-configuration/launch-status viewing contract.
 * Must never be hardcoded to skip straight to "install the extension" nor
 * to claim native support without actually probing -- see Boundaries &
 * Constraints.
 */
export interface OmpCapabilityProbePort {
  probeStatusViewingCapability(): Promise<CapabilityProbeResult>;
}

/**
 * The one-time, versioned file the thin OMP extension reads on
 * `session_start` (delivered via `AGENT_SYSTEM_LAUNCH_CONTEXT`). Never a
 * vehicle for task content -- see Design Notes.
 */
export interface LaunchContext {
  readonly version: 1;
  readonly planId: string;
  readonly configName: string;
  readonly revisionId: string;
  readonly client: ClientId;
  readonly launchedAt: string;
  readonly applyResult: 'applied' | 'degraded';
  readonly knownDifferences: readonly string[];
  readonly switchEntryPointHint: string;
}

export interface LaunchContextWriter {
  /** Writes the context and returns the path it was written to. */
  write(context: LaunchContext): Promise<string>;
}
