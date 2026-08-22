/**
 * `domain/` must not import Bun, SQLite, the filesystem, or the process
 * environment. Only pure types and functions live here.
 */

/**
 * The three client identifiers this Story's CLI can be asked to launch.
 * Only `'omp'` has a working adapter in this Story -- `'claude-code'` and
 * `'codex-cli'` are named here so callers get a typed, honest "not
 * supported yet" answer instead of an unhandled string.
 */
export type ClientId = 'omp' | 'claude-code' | 'codex-cli';

export interface ClientSupport {
  readonly supported: boolean;
  /** Present iff `supported` is `false`. Never a placeholder/shim excuse. */
  readonly reason?: string;
}

/**
 * MVP-FR10: only `'omp'` is supported. `'claude-code'`/`'codex-cli'` must
 * resolve to `supported: false` with a typed reason naming this as a
 * future adapter boundary -- never a placeholder implementation,
 * configuration translation or compatibility shim.
 */
export function resolveClientSupport(clientId: ClientId): ClientSupport {
  if (clientId === 'omp') {
    return { supported: true };
  }
  return {
    supported: false,
    reason: `client "${clientId}" is not supported yet -- this is a future adapter boundary, not a placeholder implementation, configuration translation or compatibility shim`,
  };
}
