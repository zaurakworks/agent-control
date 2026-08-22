#!/usr/bin/env bun
/**
 * Developer-only script: reads the repo's real `.cap/` and writes the
 * resulting `StableConfigRevision[]` into a local SQLite file so the CLI
 * (`configs list/show/compare`) can be exercised against real data.
 *
 * This is intentionally NOT a CLI subcommand -- per epics.md AR16,
 * "configuration supply" is not a user-facing capability in this Story.
 *
 * Usage:
 *   bun scripts/seed-from-cap.ts [--cap-root <path>] [--db <path>]
 */

import path from 'node:path';

import { loadCapConfigRevisions } from '../src/adapters/sources/cap-fs';
import { SqliteConfigRevisionRepository } from '../src/adapters/sqlite/repository';
import { defaultDbPath } from '../src/cli/db-path';

function parseArgs(argv: readonly string[]): { capRoot: string; dbPath: string } {
  let capRoot = path.resolve(import.meta.dir, '..', '..', '..', '.cap');
  let dbPath = defaultDbPath();

  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--cap-root' && argv[i + 1] !== undefined) {
      capRoot = path.resolve(argv[i + 1]!);
      i += 1;
    } else if (argv[i] === '--db' && argv[i + 1] !== undefined) {
      dbPath = path.resolve(argv[i + 1]!);
      i += 1;
    }
  }

  return { capRoot, dbPath };
}

async function main(): Promise<void> {
  const { capRoot, dbPath } = parseArgs(process.argv.slice(2));

  console.log(`reading .cap fixture data from: ${capRoot}`);
  const revisions = await loadCapConfigRevisions(capRoot);

  console.log(`writing ${revisions.length} revision(s) to: ${dbPath}`);
  const repository = new SqliteConfigRevisionRepository(dbPath);
  try {
    repository.seed(revisions);
  } finally {
    repository.close();
  }

  for (const revision of revisions) {
    console.log(`  - ${revision.configName} (${revision.revisionId})`);
  }
  console.log('done.');
}

if (import.meta.main) {
  await main();
}
