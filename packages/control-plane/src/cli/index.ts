#!/usr/bin/env bun
/**
 * `configs` CLI entry point. Dispatches the three read-only subcommands
 * this Story implements: `list`, `show <id>`, `compare <id...>`. No other
 * subcommand exists -- in particular there is no `configs sync`/`configs
 * import` (see `src/adapters/sources/cap-fs.ts` for why).
 */

import { SqliteConfigRevisionRepository } from '../adapters/sqlite/repository';
import {
  ConfigNotFoundError,
  ConfigUnsupportedError,
  compareConfigRevisions,
  getConfigRevisionDetail,
  listConfigRevisions,
  type ConfigQueryError,
} from '../application/queries';
import { defaultDbPath } from './db-path';
import { renderCompareResult, renderDetail, renderList, renderQueryFailure } from './render';

const USAGE = 'usage: configs <list|show <id>|compare <id> <id> [...ids]>';

function isConfigQueryError(error: unknown): error is ConfigQueryError {
  return error instanceof ConfigNotFoundError || error instanceof ConfigUnsupportedError;
}

/**
 * Validated ahead of opening the SQLite repository so a usage error (no
 * command, unknown command, missing `show` id, too few `compare` ids) never
 * has the side effect of creating/touching the database file.
 */
type ParsedCommand =
  | { readonly kind: 'usage-error'; readonly message: string }
  | { readonly kind: 'list' }
  | { readonly kind: 'show'; readonly id: string }
  | { readonly kind: 'compare'; readonly ids: readonly string[] };

function parseCommand(argv: readonly string[]): ParsedCommand {
  const [command, ...rest] = argv;
  switch (command) {
    case 'list':
      return { kind: 'list' };
    case 'show': {
      const id = rest[0];
      if (id === undefined) {
        return { kind: 'usage-error', message: `configs show <id>: missing <id>\n${USAGE}` };
      }
      return { kind: 'show', id };
    }
    case 'compare':
      if (rest.length < 2) {
        return { kind: 'usage-error', message: `configs compare <id> <id> [...ids]: requires at least 2 ids\n${USAGE}` };
      }
      return { kind: 'compare', ids: rest };
    default:
      return { kind: 'usage-error', message: `unknown command: ${command ?? '(none)'}\n${USAGE}` };
  }
}

export async function main(argv: readonly string[]): Promise<number> {
  const parsed = parseCommand(argv);
  if (parsed.kind === 'usage-error') {
    console.error(parsed.message);
    return 2;
  }

  let repository: SqliteConfigRevisionRepository;
  try {
    repository = new SqliteConfigRevisionRepository(defaultDbPath());
  } catch (error) {
    console.error(`configs: could not open configuration storage: ${(error as Error).message}`);
    return 1;
  }

  try {
    switch (parsed.kind) {
      case 'list': {
        const revisions = await listConfigRevisions(repository);
        console.log(renderList(revisions));
        return 0;
      }

      case 'show': {
        try {
          const revision = await getConfigRevisionDetail(repository, parsed.id);
          console.log(renderDetail(revision));
          return 0;
        } catch (error) {
          if (isConfigQueryError(error)) {
            console.log(renderQueryFailure(parsed.id, error));
            return 1;
          }
          throw error;
        }
      }

      case 'compare': {
        const result = await compareConfigRevisions(repository, parsed.ids);
        console.log(renderCompareResult(result));
        return result.resolved.length > 0 ? 0 : 1;
      }
    }
  } finally {
    repository.close();
  }
}

if (import.meta.main) {
  try {
    const exitCode = await main(process.argv.slice(2));
    process.exit(exitCode);
  } catch (error) {
    console.error(`configs: unexpected failure: ${(error as Error).message}`);
    process.exit(1);
  }
}
