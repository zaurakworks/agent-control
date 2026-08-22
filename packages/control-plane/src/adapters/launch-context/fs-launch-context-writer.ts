import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

import { defaultDbPath } from '../../cli/db-path';
import type { LaunchContext, LaunchContextWriter } from '../../application/ports';

/**
 * Writes under the same state root the SQLite database lives under
 * (`cli/db-path.ts`'s convention), in a sibling `launch-context/`
 * directory -- so overriding `CONTROL_PLANE_DB_PATH` (as tests already do)
 * moves both together without a second env var to keep in sync.
 */
export function launchContextDir(): string {
  return path.join(path.dirname(defaultDbPath()), 'launch-context');
}

export class FsLaunchContextWriter implements LaunchContextWriter {
  async write(context: LaunchContext): Promise<string> {
    const dir = launchContextDir();
    mkdirSync(dir, { recursive: true });
    const filePath = path.join(dir, `${context.planId}.json`);
    writeFileSync(filePath, JSON.stringify(context, null, 2), 'utf8');
    return filePath;
  }
}
