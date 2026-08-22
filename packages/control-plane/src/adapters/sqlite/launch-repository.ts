import { Database } from 'bun:sqlite';
import { mkdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { type Fact, isKnown, known, unknown } from '../../domain/facts';
import type { ClientId } from '../../domain/client';
import type { LaunchPhase, LaunchPlan, ObservedOutcome } from '../../domain/activation';
import type { LaunchPlanRepository } from '../../application/ports';

export interface LaunchPlanRow {
  plan_id: string;
  operation_id: string;
  revision_id: string;
  config_name: string;
  client: string;
  plan_hash: string;
  phase: string;
  created_at: string;
  confirmed_at_status: string;
  confirmed_at_value: string | null;
  confirmed_at_reason: string | null;
  confirmed_at_observed_at: string | null;
  failure_reason_status: string;
  failure_reason_value: string | null;
  failure_reason_reason: string | null;
  failure_reason_observed_at: string | null;
  observed_outcome_status: string;
  observed_outcome_value: string | null;
  observed_outcome_reason: string | null;
  observed_outcome_observed_at: string | null;
}

function migrationSqlPath(): string {
  const here = path.dirname(fileURLToPath(import.meta.url));
  return path.join(here, '..', '..', '..', 'migrations', '0002_launch.sql');
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

function factFromColumns<T>(
  status: string,
  value: string | null,
  reason: string | null,
  observedAt: string | null,
  parseValue: (raw: string) => T,
): Fact<T> {
  if (status === 'known' && value !== null) {
    return known(parseValue(value));
  }
  return unknown(reason ?? 'unspecified', observedAt ?? new Date(0).toISOString());
}

function rowToPlan(row: LaunchPlanRow): LaunchPlan {
  return {
    planId: row.plan_id,
    operationId: row.operation_id,
    revisionId: row.revision_id,
    configName: row.config_name,
    client: row.client as ClientId,
    planHash: row.plan_hash,
    phase: row.phase as LaunchPhase,
    createdAt: row.created_at,
    confirmedAt: factFromColumns(
      row.confirmed_at_status,
      row.confirmed_at_value,
      row.confirmed_at_reason,
      row.confirmed_at_observed_at,
      (v) => v,
    ),
    failureReason: factFromColumns(
      row.failure_reason_status,
      row.failure_reason_value,
      row.failure_reason_reason,
      row.failure_reason_observed_at,
      (v) => v,
    ),
    observedOutcome: factFromColumns(
      row.observed_outcome_status,
      row.observed_outcome_value,
      row.observed_outcome_reason,
      row.observed_outcome_observed_at,
      (v) => v as ObservedOutcome,
    ),
  };
}

const PLAN_COLUMNS = [
  'plan_id',
  'operation_id',
  'revision_id',
  'config_name',
  'client',
  'plan_hash',
  'phase',
  'created_at',
  'confirmed_at_status',
  'confirmed_at_value',
  'confirmed_at_reason',
  'confirmed_at_observed_at',
  'failure_reason_status',
  'failure_reason_value',
  'failure_reason_reason',
  'failure_reason_observed_at',
  'observed_outcome_status',
  'observed_outcome_value',
  'observed_outcome_reason',
  'observed_outcome_observed_at',
].join(', ');

/**
 * `bun:sqlite` STRICT repository for `launch_plan`. Independent of
 * `sqlite/repository.ts` -- separate migration file, separate connection
 * -- both are free to share the same `.sqlite3` file path.
 */
export class SqliteLaunchPlanRepository implements LaunchPlanRepository {
  private readonly db: Database;

  constructor(dbPath: string) {
    if (dbPath !== ':memory:') {
      mkdirSync(path.dirname(dbPath), { recursive: true });
    }
    this.db = new Database(dbPath, { create: true });
    this.db.exec('PRAGMA journal_mode = WAL;');
    this.db.exec('PRAGMA foreign_keys = ON;');
    this.runMigration();
  }

  private runMigration(): void {
    const sql = readFileSync(migrationSqlPath(), 'utf8');
    this.db.transaction(() => {
      this.db.exec(sql);
    })();
  }

  async save(plan: LaunchPlan): Promise<void> {
    const confirmedAt = factColumns(plan.confirmedAt);
    const failureReason = factColumns(plan.failureReason);
    const observedOutcome = factColumns(plan.observedOutcome);

    this.db
      .query<
        unknown,
        [
          string,
          string,
          string,
          string,
          string,
          string,
          string,
          string,
          'known' | 'unknown',
          string | null,
          string | null,
          string | null,
          'known' | 'unknown',
          string | null,
          string | null,
          string | null,
          'known' | 'unknown',
          string | null,
          string | null,
          string | null,
        ]
      >(
        `INSERT INTO launch_plan (${PLAN_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
         ON CONFLICT(plan_id) DO UPDATE SET
           operation_id = excluded.operation_id,
           revision_id = excluded.revision_id,
           config_name = excluded.config_name,
           client = excluded.client,
           plan_hash = excluded.plan_hash,
           phase = excluded.phase,
           confirmed_at_status = excluded.confirmed_at_status,
           confirmed_at_value = excluded.confirmed_at_value,
           confirmed_at_reason = excluded.confirmed_at_reason,
           confirmed_at_observed_at = excluded.confirmed_at_observed_at,
           failure_reason_status = excluded.failure_reason_status,
           failure_reason_value = excluded.failure_reason_value,
           failure_reason_reason = excluded.failure_reason_reason,
           failure_reason_observed_at = excluded.failure_reason_observed_at,
           observed_outcome_status = excluded.observed_outcome_status,
           observed_outcome_value = excluded.observed_outcome_value,
           observed_outcome_reason = excluded.observed_outcome_reason,
           observed_outcome_observed_at = excluded.observed_outcome_observed_at`,
      )
      .run(
        plan.planId,
        plan.operationId,
        plan.revisionId,
        plan.configName,
        plan.client,
        plan.planHash,
        plan.phase,
        plan.createdAt,
        confirmedAt.status,
        confirmedAt.value,
        confirmedAt.reason,
        confirmedAt.observedAt,
        failureReason.status,
        failureReason.value,
        failureReason.reason,
        failureReason.observedAt,
        observedOutcome.status,
        observedOutcome.value,
        observedOutcome.reason,
        observedOutcome.observedAt,
      );
  }

  async findById(planId: string): Promise<LaunchPlan | null> {
    const row = this.db.query<LaunchPlanRow, [string]>(`SELECT ${PLAN_COLUMNS} FROM launch_plan WHERE plan_id = ?`).get(planId);
    return row === null ? null : rowToPlan(row);
  }

  async findActiveForClient(client: ClientId): Promise<LaunchPlan | null> {
    const row = this.db
      .query<
        LaunchPlanRow,
        [string]
      >(`SELECT ${PLAN_COLUMNS} FROM launch_plan WHERE client = ? ORDER BY created_at DESC, rowid DESC LIMIT 1`)
      .get(client);
    return row === null ? null : rowToPlan(row);
  }

  close(): void {
    this.db.close();
  }
}
