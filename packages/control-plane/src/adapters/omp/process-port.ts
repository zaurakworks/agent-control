import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { type Fact, known, unknown } from '../../domain/facts';
import type { StableConfigRevision } from '../../domain/config';
import type { OmpProcessPort, OmpSpawnParams, OmpSpawnResult } from '../../application/ports';

/**
 * Pure argv builder -- exported so tests can assert exact argv contents
 * without spawning a real process. `launchContextPath` is accepted for a
 * consistent call surface but intentionally never embedded in the
 * returned argv: it is delivered to OMP via the `AGENT_SYSTEM_LAUNCH_
 * CONTEXT` env var instead (Design Notes), so it needs no shell-unsafe
 * escaping here regardless of spaces/non-ASCII characters.
 *
 * Never emits anything that clears, rewrites or restores the user's real
 * global OMP configuration directory -- only `--profile`/`--no-extensions
 * -e <path>`/`--skills`|`--no-skills` plus the caller's opaque forwarded
 * args.
 */
export function buildOmpArgv(
  revision: StableConfigRevision,
  launchContextPath: string,
  extensionPath: string | null,
  forwardedArgs: readonly string[],
): string[] {
  void launchContextPath;

  const argv: string[] = ['--profile', sanitizeProfileName(revision.configName)];

  if (extensionPath !== null) {
    // `--no-extensions` disables auto-discovery of the user's own
    // extensions so only the extension file we explicitly pass via `-e`
    // loads -- this is what keeps "current config/status" to a single
    // fact source (Design Notes).
    argv.push('--no-extensions', '-e', extensionPath);
  }

  const skillNames = revision.skills.map((skill) => skill.name);
  if (skillNames.length > 0) {
    argv.push('--skills', skillNames.join(','));
  } else {
    argv.push('--no-skills');
  }

  argv.push(...forwardedArgs);
  return argv;
}

/**
 * Forwarded-arg (`-- <args>`) tokens that would defeat this Story's own
 * safety guarantees if let through to the real `omp` binary -- verified
 * against this machine's real `omp --help` output (18.0.0), matching the
 * Design Notes' "OMP 真实调用面" section:
 *  - extension loading: `-e, --extension=<value>` is documented and
 *    verified repeatable ("Load an extension file (can be used multiple
 *    times)"), so a forwarded `-e <path>` would add an *extra* extension
 *    on top of the `--no-extensions -e <thin-extension>` this module
 *    already emits -- breaking the "single fact source" guarantee
 *    (`buildOmpArgv`'s own docstring above).
 *  - profile selection: `--profile=<value>` is the exact flag
 *    `buildOmpArgv` uses to isolate auth/session/settings/cache per
 *    config; a forwarded `--profile` would override that computed value,
 *    breaking config/OMP-profile isolation.
 *  - resume/continue/session-dir: `-c, --continue`, `-r, --resume=<value>`
 *    and `--session-dir=<value>` all let OMP auto-resume a prior session
 *    or redirect where sessions are discovered, breaking "resume 完全不
 *    拦截" (Boundaries & Constraints) that this Story/AD-7/AD-13/AD-19
 *    rely on -- Agent System must never intercept or bias OMP's own
 *    resume UI.
 *
 * This is a narrow, exact-token denylist -- it never inspects, parses or
 * classifies the *content* of a forwarded arg (still forbidden by
 * Boundaries & Constraints), it only rejects a small fixed set of flag
 * spellings that specifically undermine the three guarantees above.
 */
export const DENYLISTED_FORWARDED_ARG_TOKENS: readonly string[] = [
  '-e',
  '--extension',
  '--profile',
  '-c',
  '--continue',
  '-r',
  '--resume',
  '--session-dir',
];

/**
 * Returns the first forwarded arg whose flag token (the part before `=`,
 * for `--flag=value` forms) matches `DENYLISTED_FORWARDED_ARG_TOKENS`, or
 * `null` if none match. Only compares the exact token -- never inspects
 * the value that follows it.
 */
export function findDenylistedForwardedArg(forwardedArgs: readonly string[]): string | null {
  for (const arg of forwardedArgs) {
    const eqIndex = arg.indexOf('=');
    const token = eqIndex === -1 ? arg : arg.slice(0, eqIndex);
    if (DENYLISTED_FORWARDED_ARG_TOKENS.includes(token)) {
      return arg;
    }
  }
  return null;
}

/**
 * Deterministic, non-cryptographic short hash of the *original* (pre-
 * sanitization) `configName` -- same collision-resistance philosophy as
 * `domain/activation.ts`'s `computePlanHash`. Appended as a suffix so two
 * distinct config names that sanitize to the same readable prefix (e.g.
 * `"my config"` and `"my/config"`, which both collapse disallowed
 * characters to `-`) can never collide onto the same `--profile` value --
 * `--profile` isolates OMP auth/session/settings/cache, so a collision
 * here would mean two different Agent System configs silently sharing
 * OMP profile state.
 */
function shortHash(input: string): string {
  let hash = 0;
  for (let i = 0; i < input.length; i += 1) {
    hash = (Math.imul(31, hash) + input.charCodeAt(i)) | 0;
  }
  return (hash >>> 0).toString(16);
}

function sanitizeProfileName(configName: string): string {
  const sanitized = configName.trim().replace(/[^a-zA-Z0-9_.-]+/g, '-');
  const base = sanitized.length > 0 ? sanitized : 'agent-system-default';
  return `${base}-${shortHash(configName)}`;
}

/** Resolves the on-disk path of the thin status/switch extension shipped with this package. */
export function defaultExtensionPath(): string {
  const here = path.dirname(fileURLToPath(import.meta.url));
  return path.join(here, 'extensions', 'agent-status-extension.ts');
}

const OMP_VERSION_PATTERN = /^omp\/(\S+)/;

/**
 * Spawns the real `omp` binary directly via an argv array (`Bun.spawn`) --
 * never through a shell or string-concatenated command line.
 */
export class BunOmpProcessPort implements OmpProcessPort {
  async detectVersion(): Promise<Fact<string>> {
    const binaryPath = Bun.which('omp');
    if (binaryPath === null) {
      return unknown('omp-binary-not-found', new Date().toISOString());
    }

    try {
      const proc = Bun.spawn([binaryPath, '--version'], { stdout: 'pipe', stderr: 'pipe' });
      const [output, exitCode] = await Promise.all([new Response(proc.stdout).text(), proc.exited]);
      if (exitCode !== 0) {
        return unknown(`omp --version exited with code ${exitCode}`, new Date().toISOString());
      }
      const match = OMP_VERSION_PATTERN.exec(output.trim());
      if (match === null || match[1] === undefined) {
        return unknown(`unrecognized omp --version output: ${output.trim()}`, new Date().toISOString());
      }
      return known(match[1]);
    } catch (error) {
      return unknown(`failed to run omp --version: ${(error as Error).message}`, new Date().toISOString());
    }
  }

  async spawn(params: OmpSpawnParams): Promise<OmpSpawnResult> {
    const binaryPath = Bun.which('omp');
    if (binaryPath === null) {
      throw new Error('omp-binary-not-found');
    }

    const argv = [binaryPath, ...buildOmpArgv(params.revision, params.launchContextPath, params.extensionPath, params.forwardedArgs)];
    const proc = Bun.spawn(argv, {
      cwd: params.cwd,
      // Only ever *adds* AGENT_SYSTEM_LAUNCH_CONTEXT on top of the
      // caller's existing environment -- never strips or rewrites
      // anything else (Boundaries & Constraints).
      env: { ...process.env, AGENT_SYSTEM_LAUNCH_CONTEXT: params.launchContextPath },
      stdio: ['inherit', 'inherit', 'inherit'],
    });

    const exitCode = await proc.exited;
    return { exitCode, signal: proc.signalCode ?? null };
  }
}
