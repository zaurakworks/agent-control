import { describe, expect, test } from 'bun:test';
import path from 'node:path';

import { loadCapConfigRevisions } from '../../src/adapters/sources/cap-fs';
import { isKnown, isUnknown } from '../../src/domain/facts';

const FIXTURE_ROOT = path.join(import.meta.dir, '..', 'fixtures', 'cap-sample');

describe('loadCapConfigRevisions (fixture, not the real repo .cap/)', () => {
  test('maps one StableConfigRevision per declared profile role', async () => {
    const revisions = await loadCapConfigRevisions(FIXTURE_ROOT);
    expect(revisions.map((r) => r.configName).sort()).toEqual(['general', 'reviewer']);
  });

  test('defaultMarker is Unknown for every profile -- manifest.defaults is a policy-overlay path, not a per-profile role marker', async () => {
    const revisions = await loadCapConfigRevisions(FIXTURE_ROOT);
    for (const revision of revisions) {
      expect(isUnknown(revision.defaultMarker)).toBe(true);
    }
  });

  test('a role resolved in lock.json gets revisionId = layer_digest and Known("resolved") availability', async () => {
    const revisions = await loadCapConfigRevisions(FIXTURE_ROOT);
    const general = revisions.find((r) => r.configName === 'general')!;
    expect(general.revisionId).toBe('sha256:general-fixture-digest');
    expect(isKnown(general.availability)).toBe(true);
  });

  test('a role absent from lock.json.profiles gets Unknown("not-resolved", ...) availability', async () => {
    const revisions = await loadCapConfigRevisions(FIXTURE_ROOT);
    const reviewer = revisions.find((r) => r.configName === 'reviewer')!;
    expect(isUnknown(reviewer.availability)).toBe(true);
    if (isUnknown(reviewer.availability)) {
      expect(reviewer.availability.reason).toBe('not-resolved');
    }
  });

  test('skills/mcps from lock.json inventory map to typed Skill/MCP references', async () => {
    const revisions = await loadCapConfigRevisions(FIXTURE_ROOT);
    const general = revisions.find((r) => r.configName === 'general')!;
    const names = general.skills.map((s) => s.name).sort();
    expect(names).toEqual(['grilling', 'openspec-explore']);
    expect(general.mcp).toEqual([]);
  });

  test('a plugin-imported skill (declared in project_skill_imports) is tagged project-skill-import; a plain project skill is tagged project-capability', async () => {
    const revisions = await loadCapConfigRevisions(FIXTURE_ROOT);
    const general = revisions.find((r) => r.configName === 'general')!;
    const grilling = general.skills.find((s) => s.name === 'grilling')!;
    const openspecExplore = general.skills.find((s) => s.name === 'openspec-explore')!;
    expect(isKnown(grilling.sourceCategory) && grilling.sourceCategory.value).toBe('project-skill-import');
    expect(isKnown(openspecExplore.sourceCategory) && openspecExplore.sourceCategory.value).toBe('project-capability');
  });

  test('the prompt path becomes a typed Instruction reference -- the prompt file content is never read', async () => {
    const revisions = await loadCapConfigRevisions(FIXTURE_ROOT);
    const general = revisions.find((r) => r.configName === 'general')!;
    expect(general.instructions).toHaveLength(1);
    expect(general.instructions[0]!.kind).toBe('instruction');
    expect(general.instructions[0]!.name).toBe('.cap/prompts/general.md');
    const summary = general.instructions[0]!.summary;
    expect(isKnown(summary) && summary.value.includes('general.md')).toBe(true);
    // The mapped summary must only ever reference the path, never contain
    // arbitrary prose that could only come from reading the .md body.
    expect(isKnown(summary) && summary.value).not.toContain('\n');
  });

  test('scopeBoundary never embeds prompt body content, only path/counts', async () => {
    const revisions = await loadCapConfigRevisions(FIXTURE_ROOT);
    for (const revision of revisions) {
      expect(isKnown(revision.scopeBoundary)).toBe(true);
      if (isKnown(revision.scopeBoundary)) {
        expect(revision.scopeBoundary.value).toContain('prompt:');
      }
    }
  });

  test('an unresolved profile\'s capability arrays come from lock.json inventory (empty), never from the profile TOML allow list', async () => {
    // reviewer.toml declares skills.allow = ["review-checklist"], but the
    // `reviewer` role has no entry under lock.json.profiles -- it is
    // unresolved. The allow list is a *request*, not an *inventory*; only
    // lock.json's resolved inventory may populate skills/mcp/hooks/plugins.
    // If this ever starts reading `review-checklist` out of the profile
    // TOML's allow list, that is a silent-fabrication regression.
    const revisions = await loadCapConfigRevisions(FIXTURE_ROOT);
    const reviewer = revisions.find((r) => r.configName === 'reviewer')!;
    expect(isUnknown(reviewer.availability)).toBe(true);
    expect(reviewer.skills).toEqual([]);
    expect(reviewer.mcp).toEqual([]);
    expect(reviewer.hooks).toEqual([]);
    expect(reviewer.plugins).toEqual([]);
    expect(reviewer.skills.map((s) => s.name)).not.toContain('review-checklist');
  });
});
