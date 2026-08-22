import { describe, expect, test } from 'bun:test';

import { DENYLISTED_FORWARDED_ARG_TOKENS, buildOmpArgv, findDenylistedForwardedArg } from '../../src/adapters/omp/process-port';
import { known } from '../../src/domain/facts';
import type { CapabilityReference, StableConfigRevision } from '../../src/domain/config';

function ref(kind: CapabilityReference['kind'], name: string): CapabilityReference {
  return { kind, name, sourceCategory: known('project-capability'), summary: known(`${kind}: ${name}`) };
}

function revision(overrides: Partial<StableConfigRevision> & { configName: string; revisionId: string }): StableConfigRevision {
  return {
    configName: overrides.configName,
    revisionId: overrides.revisionId,
    defaultMarker: known(false),
    scopeBoundary: known('a scope boundary'),
    availability: known('resolved'),
    instructions: overrides.instructions ?? [],
    skills: overrides.skills ?? [],
    mcp: overrides.mcp ?? [],
    hooks: overrides.hooks ?? [],
    plugins: overrides.plugins ?? [],
  };
}

describe('buildOmpArgv', () => {
  test('always sets --profile to a sanitized configName (with a disambiguating suffix)', () => {
    const argv = buildOmpArgv(revision({ configName: 'general', revisionId: 'rev-1' }), '/tmp/ctx.json', null, []);
    expect(argv).toContain('--profile');
    const profileValue = argv[argv.indexOf('--profile') + 1]!;
    expect(profileValue).toMatch(/^general-[0-9a-f]+$/);
  });

  test('sanitizes profile names containing spaces/slashes/other unsafe characters', () => {
    const argv = buildOmpArgv(revision({ configName: 'my config/team ☺', revisionId: 'rev-1' }), '/tmp/ctx.json', null, []);
    const profileValue = argv[argv.indexOf('--profile') + 1]!;
    expect(profileValue).not.toMatch(/[\s/☺]/);
    expect(profileValue.length).toBeGreaterThan(0);
  });

  test('two distinct configNames that sanitize to the same readable prefix never collide onto the same --profile value', () => {
    const argvA = buildOmpArgv(revision({ configName: 'my config', revisionId: 'rev-a' }), '/tmp/ctx.json', null, []);
    const argvB = buildOmpArgv(revision({ configName: 'my/config', revisionId: 'rev-b' }), '/tmp/ctx.json', null, []);
    const profileA = argvA[argvA.indexOf('--profile') + 1]!;
    const profileB = argvB[argvB.indexOf('--profile') + 1]!;
    expect(profileA).not.toBe(profileB);
  });

  test('the same configName always sanitizes to the same --profile value (deterministic)', () => {
    const argvA = buildOmpArgv(revision({ configName: 'general', revisionId: 'rev-a' }), '/tmp/ctx.json', null, []);
    const argvB = buildOmpArgv(revision({ configName: 'general', revisionId: 'rev-b' }), '/tmp/ctx.json', null, []);
    expect(argvA[argvA.indexOf('--profile') + 1]).toBe(argvB[argvB.indexOf('--profile') + 1]);
  });

  test('when extensionPath is provided, emits --no-extensions -e <path> to guarantee a single fact source', () => {
    const argv = buildOmpArgv(revision({ configName: 'general', revisionId: 'rev-1' }), '/tmp/ctx.json', '/path/to/ext.ts', []);
    expect(argv).toContain('--no-extensions');
    const eIndex = argv.indexOf('-e');
    expect(eIndex).toBeGreaterThan(-1);
    expect(argv[eIndex + 1]).toBe('/path/to/ext.ts');
  });

  test('when extensionPath is null, no extension-related flags are emitted', () => {
    const argv = buildOmpArgv(revision({ configName: 'general', revisionId: 'rev-1' }), '/tmp/ctx.json', null, []);
    expect(argv).not.toContain('--no-extensions');
    expect(argv).not.toContain('-e');
  });

  test('non-empty skills produce a comma-separated --skills list of names only', () => {
    const rev = revision({
      configName: 'general',
      revisionId: 'rev-1',
      skills: [ref('skill', 'openspec-explore'), ref('skill', 'grilling')],
    });
    const argv = buildOmpArgv(rev, '/tmp/ctx.json', null, []);
    const skillsIndex = argv.indexOf('--skills');
    expect(skillsIndex).toBeGreaterThan(-1);
    expect(argv[skillsIndex + 1]).toBe('openspec-explore,grilling');
    expect(argv).not.toContain('--no-skills');
  });

  test('empty skills produce --no-skills, not an empty --skills value', () => {
    const argv = buildOmpArgv(revision({ configName: 'general', revisionId: 'rev-1' }), '/tmp/ctx.json', null, []);
    expect(argv).toContain('--no-skills');
    expect(argv).not.toContain('--skills');
  });

  test('forwarded args are appended verbatim and last, as opaque values', () => {
    const argv = buildOmpArgv(revision({ configName: 'general', revisionId: 'rev-1' }), '/tmp/ctx.json', null, ['do the thing', '--not-a-real-flag']);
    expect(argv.slice(-2)).toEqual(['do the thing', '--not-a-real-flag']);
  });

  test('non-ASCII / spaced paths in extensionPath pass through untouched -- argv array, no shell escaping needed', () => {
    const weirdPath = 'C:/Users/名前 with spaces/ext ①.ts';
    const argv = buildOmpArgv(revision({ configName: 'general', revisionId: 'rev-1' }), '/tmp/ctx.json', weirdPath, []);
    expect(argv).toContain(weirdPath);
  });

  test('never emits any flag that clears/rewrites/restores the global OMP config directory', () => {
    const argv = buildOmpArgv(
      revision({ configName: 'general', revisionId: 'rev-1', skills: [ref('skill', 's')] }),
      '/tmp/ctx.json',
      '/ext.ts',
      ['--print'],
    );
    const forbidden = ['--session-dir', '-r', '--resume', '-c', '--continue', '--config'];
    for (const flag of forbidden) {
      expect(argv).not.toContain(flag);
    }
  });

  test('never embeds the launch context path in argv -- delivered via env var only', () => {
    const argv = buildOmpArgv(revision({ configName: 'general', revisionId: 'rev-1' }), '/tmp/some-launch-context.json', null, []);
    expect(argv).not.toContain('/tmp/some-launch-context.json');
  });
});

describe('findDenylistedForwardedArg', () => {
  test('returns null when no forwarded arg matches the denylist', () => {
    expect(findDenylistedForwardedArg([])).toBeNull();
    expect(findDenylistedForwardedArg(['do the task', '--not-a-real-flag', '--model=opus'])).toBeNull();
  });

  for (const token of DENYLISTED_FORWARDED_ARG_TOKENS) {
    test(`flags exact token "${token}"`, () => {
      expect(findDenylistedForwardedArg([token])).toBe(token);
      expect(findDenylistedForwardedArg(['harmless', token, 'trailing'])).toBe(token);
    });
  }

  test('flags "--flag=value" forms by matching the token before "="', () => {
    expect(findDenylistedForwardedArg(['--profile=work'])).toBe('--profile=work');
    expect(findDenylistedForwardedArg(['--resume=abc123'])).toBe('--resume=abc123');
    expect(findDenylistedForwardedArg(['--session-dir=/tmp/x'])).toBe('--session-dir=/tmp/x');
  });

  test('does not flag unrelated flags that merely contain a denylisted substring', () => {
    expect(findDenylistedForwardedArg(['--session-dirs', '--profiles', '--extensions'])).toBeNull();
  });
});
