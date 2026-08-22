import { describe, expect, test } from 'bun:test';

import { SqliteConfigRevisionRepository } from '../../src/adapters/sqlite/repository';
import type { RevisionRow } from '../../src/adapters/sqlite/repository';
import { ConfigUnsupportedError } from '../../src/application/queries';
import { isKnown, isUnknown, known, unknown } from '../../src/domain/facts';
import type { StableConfigRevision } from '../../src/domain/config';

function sampleRevision(overrides: Partial<StableConfigRevision> & { configName: string; revisionId: string }): StableConfigRevision {
  return {
    configName: overrides.configName,
    revisionId: overrides.revisionId,
    defaultMarker: overrides.defaultMarker ?? known(false),
    scopeBoundary: overrides.scopeBoundary ?? known('a scope boundary'),
    availability: overrides.availability ?? known('resolved'),
    instructions: overrides.instructions ?? [],
    skills: overrides.skills ?? [],
    mcp: overrides.mcp ?? [],
    hooks: overrides.hooks ?? [],
    plugins: overrides.plugins ?? [],
  };
}

describe('SqliteConfigRevisionRepository (:memory:, STRICT)', () => {
  test('creates STRICT tables via a transactional migration and starts empty', async () => {
    const repo = new SqliteConfigRevisionRepository(':memory:');
    try {
      const revisions = await repo.listAll();
      expect(revisions).toEqual([]);
    } finally {
      repo.close();
    }
  });

  test('findById on an empty store returns null (not an exception)', async () => {
    const repo = new SqliteConfigRevisionRepository(':memory:');
    try {
      const result = await repo.findById('does-not-exist');
      expect(result).toBeNull();
    } finally {
      repo.close();
    }
  });

  test('seed() + listAll() round-trips known and unknown facts faithfully', async () => {
    const repo = new SqliteConfigRevisionRepository(':memory:');
    try {
      const revision = sampleRevision({
        configName: 'general',
        revisionId: 'rev-1',
        defaultMarker: known(true),
        scopeBoundary: known('Role `general`; prompt: .cap/prompts/general.md'),
        availability: unknown('not-resolved', '2026-08-22T00:00:00.000Z'),
        skills: [{ kind: 'skill', name: 'openspec-explore', sourceCategory: known('project-capability'), summary: known('skill reference: openspec-explore') }],
      });
      repo.seed([revision]);

      const all = await repo.listAll();
      expect(all).toHaveLength(1);
      const [got] = all;
      expect(got!.configName).toBe('general');
      expect(got!.revisionId).toBe('rev-1');
      expect(isKnown(got!.defaultMarker) && got!.defaultMarker.value).toBe(true);
      expect(isKnown(got!.scopeBoundary)).toBe(true);
      expect(isUnknown(got!.availability)).toBe(true);
      if (isUnknown(got!.availability)) {
        expect(got!.availability.reason).toBe('not-resolved');
      }
      expect(got!.skills).toHaveLength(1);
      expect(got!.skills[0]!.name).toBe('openspec-explore');
    } finally {
      repo.close();
    }
  });

  test('findById round-trips a seeded revision', async () => {
    const repo = new SqliteConfigRevisionRepository(':memory:');
    try {
      repo.seed([sampleRevision({ configName: 'general', revisionId: 'rev-1' })]);
      const found = await repo.findById('rev-1');
      expect(found?.revisionId).toBe('rev-1');
      const notFound = await repo.findById('missing');
      expect(notFound).toBeNull();
    } finally {
      repo.close();
    }
  });

  test('findById throws ConfigUnsupportedError for a row with an unsupported schema_version', async () => {
    const repo = new SqliteConfigRevisionRepository(':memory:');
    try {
      const row: RevisionRow = {
        revision_id: 'rev-bad-version',
        config_name: 'general',
        schema_version: 99,
        default_marker_status: 'known',
        default_marker_value: 'false',
        default_marker_reason: null,
        default_marker_observed_at: null,
        scope_boundary_status: 'known',
        scope_boundary_value: 'boundary',
        scope_boundary_reason: null,
        scope_boundary_observed_at: null,
        availability_status: 'known',
        availability_value: 'resolved',
        availability_reason: null,
        availability_observed_at: null,
        instructions_json: '[]',
        skills_json: '[]',
        mcp_json: '[]',
        hooks_json: '[]',
        plugins_json: '[]',
      };
      repo.insertRawRow(row);

      await expect(repo.findById('rev-bad-version')).rejects.toBeInstanceOf(ConfigUnsupportedError);
    } finally {
      repo.close();
    }
  });

  test('listAll degrades an unsupported-version row to Unknown instead of hiding or crashing the whole list', async () => {
    const repo = new SqliteConfigRevisionRepository(':memory:');
    try {
      repo.seed([sampleRevision({ configName: 'general', revisionId: 'rev-good' })]);
      const row: RevisionRow = {
        revision_id: 'rev-bad-version',
        config_name: 'general',
        schema_version: 99,
        default_marker_status: 'known',
        default_marker_value: 'false',
        default_marker_reason: null,
        default_marker_observed_at: null,
        scope_boundary_status: 'known',
        scope_boundary_value: 'boundary',
        scope_boundary_reason: null,
        scope_boundary_observed_at: null,
        availability_status: 'known',
        availability_value: 'resolved',
        availability_reason: null,
        availability_observed_at: null,
        instructions_json: '[]',
        skills_json: '[]',
        mcp_json: '[]',
        hooks_json: '[]',
        plugins_json: '[]',
      };
      repo.insertRawRow(row);

      const all = await repo.listAll();
      expect(all).toHaveLength(2);
      const bad = all.find((r) => r.revisionId === 'rev-bad-version')!;
      expect(isUnknown(bad.availability)).toBe(true);
      const good = all.find((r) => r.revisionId === 'rev-good')!;
      expect(isKnown(good.availability)).toBe(true);
    } finally {
      repo.close();
    }
  });

  test('findById throws ConfigUnsupportedError when stored capability JSON cannot be parsed', async () => {
    const repo = new SqliteConfigRevisionRepository(':memory:');
    try {
      const row: RevisionRow = {
        revision_id: 'rev-corrupt-json',
        config_name: 'general',
        schema_version: 1,
        default_marker_status: 'known',
        default_marker_value: 'false',
        default_marker_reason: null,
        default_marker_observed_at: null,
        scope_boundary_status: 'known',
        scope_boundary_value: 'boundary',
        scope_boundary_reason: null,
        scope_boundary_observed_at: null,
        availability_status: 'known',
        availability_value: 'resolved',
        availability_reason: null,
        availability_observed_at: null,
        instructions_json: 'not-json',
        skills_json: '[]',
        mcp_json: '[]',
        hooks_json: '[]',
        plugins_json: '[]',
      };
      repo.insertRawRow(row);

      await expect(repo.findById('rev-corrupt-json')).rejects.toBeInstanceOf(ConfigUnsupportedError);
    } finally {
      repo.close();
    }
  });
});
