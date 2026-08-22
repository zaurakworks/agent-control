import { describe, expect, test } from 'bun:test';

import { resolveClientSupport } from '../../src/domain/client';

describe('resolveClientSupport', () => {
  test('omp is supported', () => {
    const result = resolveClientSupport('omp');
    expect(result.supported).toBe(true);
    expect(result.reason).toBeUndefined();
  });

  test('claude-code is not supported and names the future adapter boundary', () => {
    const result = resolveClientSupport('claude-code');
    expect(result.supported).toBe(false);
    expect(result.reason).toBeDefined();
    expect(result.reason).toContain('claude-code');
    expect(result.reason).toMatch(/future adapter boundary/);
  });

  test('codex-cli is not supported and names the future adapter boundary', () => {
    const result = resolveClientSupport('codex-cli');
    expect(result.supported).toBe(false);
    expect(result.reason).toContain('codex-cli');
    expect(result.reason).toMatch(/future adapter boundary/);
  });
});
