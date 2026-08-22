import type { StableConfigRevision } from '../domain/config';

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
