/**
 * Read-only adapter over `.cap/manifest.toml` + `.cap/profiles/*.toml` +
 * `.cap/lock.json`. This is NOT a product CLI capability -- per epics.md
 * AR16, "configuration supply" is out of this Story's scope. It exists
 * only to feed `scripts/seed-from-cap.ts` (developer-run, manual
 * verification) and test fixture generation. `configs list/show/compare`
 * never import from this module.
 *
 * It never reads prompt file *contents* -- only the path string declared
 * in the profile TOML -- and it never reads credentials.
 */

import path from 'node:path';

import { known, unknown } from '../../domain/facts';
import type { CapabilityKind, CapabilityReference, SourceCategory, StableConfigRevision } from '../../domain/config';

interface CapManifest {
  version: number;
  defaults?: string;
  profiles: Record<string, string>;
}

interface CapAllowDenyOverride {
  allow?: string[];
  deny?: string[];
  override?: string[];
}

interface CapProfileToml {
  version: number;
  prompt: string;
  skills?: CapAllowDenyOverride;
  mcps?: CapAllowDenyOverride;
  hooks?: CapAllowDenyOverride;
  plugins?: CapAllowDenyOverride;
}

interface CapLockProfileInventory {
  skills: string[];
  mcps: string[];
  hooks: string[];
  plugins: string[];
}

interface CapLockProfile {
  layer_digest: string;
  inventory: CapLockProfileInventory;
}

interface CapLock {
  profiles: Record<string, CapLockProfile>;
  project_skill_imports?: Array<{ name: string; source: string }>;
}

/**
 * Declared paths inside `manifest.toml` are repo-root-relative and
 * conventionally carry a leading `.cap/` (e.g. `.cap/profiles/general.toml`)
 * even though the manifest itself lives inside `.cap/`. Resolve them
 * against `capRoot` regardless of whether that prefix is present, so this
 * works unchanged against the real repo's `.cap/` and against a
 * self-contained fixture directory that omits the prefix.
 */
function resolveCapRelativePath(capRoot: string, declaredPath: string): string {
  const normalized = declaredPath.startsWith('.cap/') ? declaredPath.slice('.cap/'.length) : declaredPath;
  return path.join(capRoot, normalized);
}

async function readToml<T>(absPath: string): Promise<T> {
  const text = await Bun.file(absPath).text();
  return Bun.TOML.parse(text) as T;
}

async function readJson<T>(absPath: string): Promise<T> {
  const text = await Bun.file(absPath).text();
  return JSON.parse(text) as T;
}

/**
 * Only ever called with a non-empty `names` array when the profile actually
 * resolved in `lock.json` (see call sites: `inventory?.skills ?? []` is `[]`
 * whenever the profile is unresolved). There is therefore no "unresolved
 * capability name" case to represent here -- an unresolved profile's
 * unavailability is already carried by its `availability: Unknown(...)`.
 */
function mapCapabilityNames(
  names: readonly string[],
  kind: CapabilityKind,
  importNames: ReadonlySet<string>,
): CapabilityReference[] {
  return names.map((name) => {
    const sourceCategory: SourceCategory = importNames.has(name) ? 'project-skill-import' : 'project-capability';
    return {
      kind,
      name,
      sourceCategory: known(sourceCategory),
      summary: known(`${kind} reference: ${name}`),
    };
  });
}

function buildScopeBoundary(role: string, profile: CapProfileToml): string {
  const allow = profile.skills?.allow?.length ?? 0;
  const deny = profile.skills?.deny?.length ?? 0;
  const override = profile.skills?.override?.length ?? 0;
  return `Role \`${role}\`; prompt: ${profile.prompt}; skills allow=${allow} deny=${deny} override=${override}.`;
}

/**
 * Maps `.cap/` (or an equivalently-shaped fixture directory) into
 * immutable `StableConfigRevision[]`, one per declared profile role. Field
 * mapping is fixed by the Story's frozen Design Notes and must not diverge
 * without a human renegotiating the spec.
 */
export async function loadCapConfigRevisions(capRoot: string): Promise<StableConfigRevision[]> {
  const manifest = await readToml<CapManifest>(resolveCapRelativePath(capRoot, 'manifest.toml'));
  const lock = await readJson<CapLock>(resolveCapRelativePath(capRoot, 'lock.json'));
  const importNames = new Set((lock.project_skill_imports ?? []).map((entry) => entry.name));
  const observedAt = new Date().toISOString();

  const revisions: StableConfigRevision[] = [];

  for (const role of Object.keys(manifest.profiles)) {
    const profilePath = manifest.profiles[role];
    if (profilePath === undefined) {
      continue;
    }
    const profile = await readToml<CapProfileToml>(resolveCapRelativePath(capRoot, profilePath));
    const lockProfile = lock.profiles[role];
    const inventory = lockProfile?.inventory;
    const resolved = inventory !== undefined;

    revisions.push({
      configName: role,
      revisionId: resolved ? lockProfile!.layer_digest : `unresolved:${role}`,
      // `manifest.defaults` (e.g. ".cap/project-defaults.toml") is a path to
      // a project-level capability-policy overlay, NOT a per-profile "this
      // role is the default/generic one" marker -- there is no such role
      // identifier anywhere in declared `.cap/` data today. Per AD-8,
      // uncertain values must never be represented as `Known(false)`; this
      // must be `Unknown` for every profile until a real signal exists.
      defaultMarker: unknown('cap-manifest-defaults-field-is-not-a-per-profile-role-marker', observedAt),
      scopeBoundary: known(buildScopeBoundary(role, profile)),
      availability: resolved ? known('resolved') : unknown('not-resolved', observedAt),
      instructions: [
        {
          kind: 'instruction',
          name: profile.prompt,
          sourceCategory: known<SourceCategory>('project-prompt'),
          summary: known(`prompt file reference: ${profile.prompt}`),
        },
      ],
      skills: mapCapabilityNames(inventory?.skills ?? [], 'skill', importNames),
      mcp: mapCapabilityNames(inventory?.mcps ?? [], 'mcp', importNames),
      hooks: mapCapabilityNames(inventory?.hooks ?? [], 'hook', importNames),
      plugins: mapCapabilityNames(inventory?.plugins ?? [], 'plugin', importNames),
    });
  }

  return revisions;
}
