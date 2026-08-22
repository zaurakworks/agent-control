import { describe, expect, test } from 'bun:test';

import { compareRevisions } from '../../src/domain/config';
import type { CapabilityReference, StableConfigRevision } from '../../src/domain/config';
import { known, unknown } from '../../src/domain/facts';

function ref(kind: CapabilityReference['kind'], name: string, source: CapabilityReference['sourceCategory'] = known('project-capability')): CapabilityReference {
  return { kind, name, sourceCategory: source, summary: known(`${kind} reference: ${name}`) };
}

function revision(overrides: Partial<StableConfigRevision> & { configName: string; revisionId: string }): StableConfigRevision {
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

describe('compareRevisions', () => {
  test('same scalar values across revisions are marked "same"', () => {
    const a = revision({ configName: 'general', revisionId: 'rev-a', scopeBoundary: known('shared boundary') });
    const b = revision({ configName: 'general', revisionId: 'rev-b', scopeBoundary: known('shared boundary') });
    const result = compareRevisions([a, b]);
    const boundaryField = result.scalarFields.find((f) => f.field === 'scopeBoundary')!;
    expect(boundaryField.status).toBe('same');
  });

  test('different scalar values are marked "different" and listed per revision', () => {
    const a = revision({ configName: 'general', revisionId: 'rev-a' });
    const b = revision({ configName: 'reviewer', revisionId: 'rev-b' });
    const result = compareRevisions([a, b]);
    const nameField = result.scalarFields.find((f) => f.field === 'configName')!;
    expect(nameField.status).toBe('different');
    expect(nameField.entries).toEqual([
      { revisionId: 'rev-a', value: known('general') },
      { revisionId: 'rev-b', value: known('reviewer') },
    ]);
  });

  test('a field is "unknown" as a whole when either side is unknown -- never guessed same/different', () => {
    const a = revision({ configName: 'general', revisionId: 'rev-a', scopeBoundary: known('boundary') });
    const b = revision({ configName: 'general', revisionId: 'rev-b', scopeBoundary: unknown('not-resolved', 'now') });
    const result = compareRevisions([a, b]);
    const boundaryField = result.scalarFields.find((f) => f.field === 'scopeBoundary')!;
    expect(boundaryField.status).toBe('unknown');
  });

  test('defaultMarker Unknown makes that field "unknown" in comparison, never guessed as same/different', () => {
    const a = revision({ configName: 'general', revisionId: 'rev-a', defaultMarker: unknown('cap-manifest-defaults-field-is-not-a-per-profile-role-marker', 'now') });
    const b = revision({ configName: 'general', revisionId: 'rev-b', defaultMarker: unknown('cap-manifest-defaults-field-is-not-a-per-profile-role-marker', 'now') });
    const result = compareRevisions([a, b]);
    const markerField = result.scalarFields.find((f) => f.field === 'defaultMarker')!;
    expect(markerField.status).toBe('unknown');
  });

  test('capability composition reports presence, missing-in and source category status', () => {
    const a = revision({
      configName: 'general',
      revisionId: 'rev-a',
      skills: [ref('skill', 'shared-skill'), ref('skill', 'only-in-a')],
    });
    const b = revision({
      configName: 'general',
      revisionId: 'rev-b',
      skills: [ref('skill', 'shared-skill')],
    });
    const result = compareRevisions([a, b]);
    const skillGroup = result.capabilities.find((g) => g.kind === 'skill')!;

    const shared = skillGroup.entries.find((e) => e.name === 'shared-skill')!;
    expect(shared.presentIn).toEqual(['rev-a', 'rev-b']);
    expect(shared.missingIn).toEqual([]);
    expect(shared.sourceCategoryStatus).toBe('same');

    const onlyInA = skillGroup.entries.find((e) => e.name === 'only-in-a')!;
    expect(onlyInA.presentIn).toEqual(['rev-a']);
    expect(onlyInA.missingIn).toEqual(['rev-b']);
  });

  test('differing source categories for the same capability name are marked "different"', () => {
    const a = revision({
      configName: 'general',
      revisionId: 'rev-a',
      skills: [ref('skill', 'shared-skill', known('project-capability'))],
    });
    const b = revision({
      configName: 'general',
      revisionId: 'rev-b',
      skills: [ref('skill', 'shared-skill', known('project-skill-import'))],
    });
    const result = compareRevisions([a, b]);
    const skillGroup = result.capabilities.find((g) => g.kind === 'skill')!;
    const shared = skillGroup.entries.find((e) => e.name === 'shared-skill')!;
    expect(shared.sourceCategoryStatus).toBe('different');
  });

  test('unknown source category for a present capability marks that capability "unknown", not guessed', () => {
    const a = revision({
      configName: 'general',
      revisionId: 'rev-a',
      skills: [ref('skill', 'shared-skill', unknown('not-resolved', 'now'))],
    });
    const b = revision({
      configName: 'general',
      revisionId: 'rev-b',
      skills: [ref('skill', 'shared-skill', known('project-capability'))],
    });
    const result = compareRevisions([a, b]);
    const skillGroup = result.capabilities.find((g) => g.kind === 'skill')!;
    const shared = skillGroup.entries.find((e) => e.name === 'shared-skill')!;
    expect(shared.sourceCategoryStatus).toBe('unknown');
  });

  test('comparison never produces a score, ranking or recommendation field', () => {
    const a = revision({ configName: 'general', revisionId: 'rev-a' });
    const b = revision({ configName: 'reviewer', revisionId: 'rev-b' });
    const result = compareRevisions([a, b]);
    const serialized = JSON.stringify(result);
    expect(serialized).not.toMatch(/score|rank|recommend/i);
  });

  test('a single revision can still be "compared" (used by detail view logic) without requiring a second', () => {
    const a = revision({ configName: 'general', revisionId: 'rev-a' });
    const result = compareRevisions([a]);
    expect(result.revisionIds).toEqual(['rev-a']);
    expect(result.scalarFields.every((f) => f.status === 'same')).toBe(true);
  });
});
