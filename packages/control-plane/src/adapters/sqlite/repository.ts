import { Database } from 'bun:sqlite';
import { mkdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { type Fact, isKnown, known, unknown } from '../../domain/facts';
import type { CapabilityReference, StableConfigRevision } from '../../domain/config';
import type { ConfigRevisionRepository } from '../../application/ports';
import { ConfigUnsupportedError } from '../../application/queries';

/** The only `stable_config_revision.schema_version` this Story can read. */
const SUPPORTED_SCHEMA_VERSION = 1;

export interface RevisionRow {
  revision_id: string;
  config_name: string;
  schema_version: number;
  default_marker_status: string;
  default_marker_value: string | null;
  default_marker_reason: string | null;
  default_marker_observed_at: string | null;
  scope_boundary_status: string;
  scope_boundary_value: string | null;
  scope_boundary_reason: string | null;
  scope_boundary_observed_at: string | null;
  availability_status: string;
  availability_value: string | null;
  availability_reason: string | null;
  availability_observed_at: string | null;
  instructions_json: string;
  skills_json: string;
  mcp_json: string;
  hooks_json: string;
  plugins_json: string;
}

function migrationSqlPath(): string {
  const here = path.dirname(fileURLToPath(import.meta.url));
  return path.join(here, '..', '..', '..', 'migrations', '0001_init.sql');
}

function factColumnToFact<T>(
  status: string,
  value: T | null,
  reason: string | null,
  observedAt: string | null,
  parseValue: (raw: T) => unknown,
): Fact<unknown> {
  if (status === 'known' && value !== null) {
    return known(parseValue(value));
  }
  return unknown(reason ?? 'unspecified', observedAt ?? new Date(0).toISOString());
}

function parseCapabilityJson(raw: string): CapabilityReference[] {
  const parsed = JSON.parse(raw) as unknown;
  if (!Array.isArray(parsed)) {
    throw new Error('capability column did not contain a JSON array');
  }
  return parsed as CapabilityReference[];
}

/** Strict mapping used by `findById`: throws a typed error rather than guessing. */
function mapRowStrict(row: RevisionRow): StableConfigRevision {
  if (row.schema_version !== SUPPORTED_SCHEMA_VERSION) {
    throw new ConfigUnsupportedError(
      row.revision_id,
      `unsupported schema_version ${row.schema_version} (expected ${SUPPORTED_SCHEMA_VERSION})`,
    );
  }

  let instructions: CapabilityReference[];
  let skills: CapabilityReference[];
  let mcp: CapabilityReference[];
  let hooks: CapabilityReference[];
  let plugins: CapabilityReference[];
  try {
    instructions = parseCapabilityJson(row.instructions_json);
    skills = parseCapabilityJson(row.skills_json);
    mcp = parseCapabilityJson(row.mcp_json);
    hooks = parseCapabilityJson(row.hooks_json);
    plugins = parseCapabilityJson(row.plugins_json);
  } catch (error) {
    throw new ConfigUnsupportedError(
      row.revision_id,
      `stored capability data could not be parsed: ${(error as Error).message}`,
    );
  }

  return {
    configName: row.config_name,
    revisionId: row.revision_id,
    defaultMarker: factColumnToFact(
      row.default_marker_status,
      row.default_marker_value,
      row.default_marker_reason,
      row.default_marker_observed_at,
      (v) => v === 'true',
    ) as Fact<boolean>,
    scopeBoundary: factColumnToFact(
      row.scope_boundary_status,
      row.scope_boundary_value,
      row.scope_boundary_reason,
      row.scope_boundary_observed_at,
      (v) => v,
    ) as Fact<string>,
    availability: factColumnToFact(
      row.availability_status,
      row.availability_value,
      row.availability_reason,
      row.availability_observed_at,
      () => 'resolved' as const,
    ) as Fact<'resolved'>,
    instructions,
    skills,
    mcp,
    hooks,
    plugins,
  };
}

/**
 * Lenient mapping used by `listAll`: one malformed revision must not hide
 * the rest of the list. Unsupported schema/unparseable capability data
 * degrades that revision's affected fields to `Unknown` instead of
 * throwing.
 */
function mapRowLenient(row: RevisionRow): StableConfigRevision {
  const now = new Date().toISOString();

  if (row.schema_version !== SUPPORTED_SCHEMA_VERSION) {
    return {
      configName: row.config_name,
      revisionId: row.revision_id,
      defaultMarker: unknown(`unsupported schema_version ${row.schema_version}`, now),
      scopeBoundary: unknown(`unsupported schema_version ${row.schema_version}`, now),
      availability: unknown(`unsupported schema_version ${row.schema_version}`, now),
      instructions: [],
      skills: [],
      mcp: [],
      hooks: [],
      plugins: [],
    };
  }

  const parseLenient = (raw: string): CapabilityReference[] => {
    try {
      return parseCapabilityJson(raw);
    } catch {
      return [];
    }
  };

  return {
    configName: row.config_name,
    revisionId: row.revision_id,
    defaultMarker: factColumnToFact(
      row.default_marker_status,
      row.default_marker_value,
      row.default_marker_reason,
      row.default_marker_observed_at,
      (v) => v === 'true',
    ) as Fact<boolean>,
    scopeBoundary: factColumnToFact(
      row.scope_boundary_status,
      row.scope_boundary_value,
      row.scope_boundary_reason,
      row.scope_boundary_observed_at,
      (v) => v,
    ) as Fact<string>,
    availability: factColumnToFact(
      row.availability_status,
      row.availability_value,
      row.availability_reason,
      row.availability_observed_at,
      () => 'resolved' as const,
    ) as Fact<'resolved'>,
    instructions: parseLenient(row.instructions_json),
    skills: parseLenient(row.skills_json),
    mcp: parseLenient(row.mcp_json),
    hooks: parseLenient(row.hooks_json),
    plugins: parseLenient(row.plugins_json),
  };
}

function factColumns(fact: Fact<unknown>): {
  status: 'known' | 'unknown';
  value: string | null;
  reason: string | null;
  observedAt: string | null;
} {
  if (isKnown(fact)) {
    const value = typeof fact.value === 'string' ? fact.value : JSON.stringify(fact.value);
    return { status: 'known', value, reason: null, observedAt: null };
  }
  return { status: 'unknown', value: null, reason: fact.reason, observedAt: fact.observedAt };
}

const REVISION_COLUMNS = [
  'revision_id',
  'config_name',
  'schema_version',
  'default_marker_status',
  'default_marker_value',
  'default_marker_reason',
  'default_marker_observed_at',
  'scope_boundary_status',
  'scope_boundary_value',
  'scope_boundary_reason',
  'scope_boundary_observed_at',
  'availability_status',
  'availability_value',
  'availability_reason',
  'availability_observed_at',
  'instructions_json',
  'skills_json',
  'mcp_json',
  'hooks_json',
  'plugins_json',
  'created_at',
].join(', ');

/**
 * `bun:sqlite` STRICT repository. Every query uses parameterized SQL and
 * explicit columns; no `SELECT *`. Runs the migration inside a transaction
 * on construction so the schema is always present before use.
 */
export class SqliteConfigRevisionRepository implements ConfigRevisionRepository {
  private readonly db: Database;

  constructor(dbPath: string) {
    if (dbPath !== ':memory:') {
      mkdirSync(path.dirname(dbPath), { recursive: true });
    }
    this.db = new Database(dbPath, { create: true });
    this.db.exec('PRAGMA journal_mode = WAL;');
    // SQLite disables foreign key enforcement by default per connection --
    // without this, `stable_config_revision`'s `REFERENCES stable_config`
    // is decorative only.
    this.db.exec('PRAGMA foreign_keys = ON;');
    this.runMigration();
  }

  private runMigration(): void {
    const sql = readFileSync(migrationSqlPath(), 'utf8');
    this.db.transaction(() => {
      this.db.exec(sql);
    })();
  }

  async listAll(): Promise<readonly StableConfigRevision[]> {
    const rows = this.db
      .query<RevisionRow, []>(`SELECT ${REVISION_COLUMNS} FROM stable_config_revision ORDER BY config_name, revision_id`)
      .all();
    return rows.map(mapRowLenient);
  }

  async findById(revisionId: string): Promise<StableConfigRevision | null> {
    const row = this.db
      .query<RevisionRow, [string]>(`SELECT ${REVISION_COLUMNS} FROM stable_config_revision WHERE revision_id = ?`)
      .get(revisionId);
    if (row === null) {
      return null;
    }
    return mapRowStrict(row);
  }

  /**
   * Development-only seed helper (not part of the read-only port). Used by
   * `scripts/seed-from-cap.ts` and tests to populate SQLite fixtures.
   * Replaces the full contents of both tables inside one transaction.
   */
  seed(revisions: readonly StableConfigRevision[]): void {
    const insertConfig = this.db.query<unknown, [string]>(
      'INSERT OR IGNORE INTO stable_config (config_name) VALUES (?)',
    );
    const insertRevision = this.db.query<
      unknown,
      [
        string,
        string,
        number,
        string,
        string | null,
        string | null,
        string | null,
        string,
        string | null,
        string | null,
        string | null,
        string,
        string | null,
        string | null,
        string | null,
        string,
        string,
        string,
        string,
        string,
        string,
      ]
    >(
      `INSERT OR REPLACE INTO stable_config_revision (${REVISION_COLUMNS})
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    );

    this.db.transaction(() => {
      this.db.exec('DELETE FROM stable_config_revision');
      this.db.exec('DELETE FROM stable_config');
      for (const revision of revisions) {
        insertConfig.run(revision.configName);

        const defaultMarker = factColumns(revision.defaultMarker);
        const scopeBoundary = factColumns(revision.scopeBoundary);
        const availability = factColumns(revision.availability);

        insertRevision.run(
          revision.revisionId,
          revision.configName,
          SUPPORTED_SCHEMA_VERSION,
          defaultMarker.status,
          defaultMarker.value,
          defaultMarker.reason,
          defaultMarker.observedAt,
          scopeBoundary.status,
          scopeBoundary.value,
          scopeBoundary.reason,
          scopeBoundary.observedAt,
          availability.status,
          availability.value,
          availability.reason,
          availability.observedAt,
          JSON.stringify(revision.instructions),
          JSON.stringify(revision.skills),
          JSON.stringify(revision.mcp),
          JSON.stringify(revision.hooks),
          JSON.stringify(revision.plugins),
          new Date().toISOString(),
        );
      }
    })();
  }

  /** Test-only escape hatch: insert a row without going through `seed()`'s validation. */
  insertRawRow(row: RevisionRow): void {
    const insertConfig = this.db.query<unknown, [string]>(
      'INSERT OR IGNORE INTO stable_config (config_name) VALUES (?)',
    );
    const insertRevision = this.db.query<
      unknown,
      [
        string,
        string,
        number,
        string,
        string | null,
        string | null,
        string | null,
        string,
        string | null,
        string | null,
        string | null,
        string,
        string | null,
        string | null,
        string | null,
        string,
        string,
        string,
        string,
        string,
        string,
      ]
    >(
      `INSERT OR REPLACE INTO stable_config_revision (${REVISION_COLUMNS})
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    );
    this.db.transaction(() => {
      insertConfig.run(row.config_name);
      insertRevision.run(
        row.revision_id,
        row.config_name,
        row.schema_version,
        row.default_marker_status,
        row.default_marker_value,
        row.default_marker_reason,
        row.default_marker_observed_at,
        row.scope_boundary_status,
        row.scope_boundary_value,
        row.scope_boundary_reason,
        row.scope_boundary_observed_at,
        row.availability_status,
        row.availability_value,
        row.availability_reason,
        row.availability_observed_at,
        row.instructions_json,
        row.skills_json,
        row.mcp_json,
        row.hooks_json,
        row.plugins_json,
        new Date().toISOString(),
      );
    })();
  }

  close(): void {
    this.db.close();
  }
}
