#!/usr/bin/env node

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { delimiter, dirname, join } from 'node:path';
import { tmpdir } from 'node:os';

const here = dirname(fileURLToPath(import.meta.url));
const cli = join(here, '..', 'scripts', 'resource-observability.ts');
const stub = join(here, 'ccusage-stub.ts');
const temporaryRoot = mkdtempSync(join(tmpdir(), 'resource-observability test '));
const temporaryStub = join(temporaryRoot, 'ccusage-stub.ts');
const cmdStub = join(temporaryRoot, 'ccusage-stub.cmd');
const npmShimDirectory = join(temporaryRoot, 'npm shim');
const spacedCmdStub = join(npmShimDirectory, 'ccusage-stub.cmd');
const codexId = '019f1234-5678-79d1-8abc-0123456789ab';
const pluginRoot = join(here, '..');
const cmdBody = `@echo off\r\n"${process.execPath}" "${temporaryStub}" %*\r\n`;
mkdirSync(npmShimDirectory);
writeFileSync(temporaryStub, readFileSync(stub));
writeFileSync(cmdStub, cmdBody, 'utf8');
writeFileSync(spacedCmdStub, cmdBody, 'utf8');
writeFileSync(join(npmShimDirectory, 'ccusage.cmd'), cmdBody, 'utf8');
writeFileSync(join(npmShimDirectory, 'ccusage'), '# npm POSIX shim: Windows must select ccusage.cmd.\n', 'utf8');
process.on('exit', () => rmSync(temporaryRoot, { recursive: true, force: true }));

function run(provider: string, id: string, scenario = 'codex_ok', format = '--json', extras: string[] = []) {
  const result = spawnSync(process.execPath, [cli, 'session', '--provider', provider, '--id', id, format, '--ccusage-command', stub, ...extras], { encoding: 'utf8', env: { ...process.env, CCUSAGE_STUB_SCENARIO: scenario }, timeout: 8_000 });
  assert.equal(result.error, undefined, result.error?.message);
  return result;
}
function json(...args: Parameters<typeof run>) { const result = run(...args); return { result, value: JSON.parse(result.stdout) }; }

let { result, value } = json('codex', codexId);
assert.equal(result.status, 0); assert.equal(value.schema, 'resource-observability.session/v1'); assert.equal(value.source_session_id, `workspace/${codexId}`); assert.equal(value.tokens.total, 37); assert.deepEqual(value.models, ['gpt-5.6']); assert.ok(!JSON.stringify(value).includes('secret'));
({ result, value } = json('claude', 'claude-session-1', 'claude_ok'));
assert.equal(result.status, 0); assert.equal(value.last_activity, '2026-08-10T12:01:00.000Z'); assert.equal(value.tokens.total, 37);
({ result, value } = json('claude', 'claude-session-1', 'claude_unknown'));
assert.equal(result.status, 0); assert.equal(value.models, null); assert.ok(value.summary_zh.includes('模型：未知'));
({ result, value } = json('claude', 'claude-session-1', 'claude_mixed_models'));
assert.equal(result.status, 0); assert.deepEqual(value.models, ['claude-sonnet-4']); assert.equal(value.tokens.total, 74);
for (const [provider, id, scenario, code, exit] of [
  ['codex', codexId, 'bad_version', 'dependency_version_mismatch', 2],
  ['codex', codexId, 'codex_not_found', 'session_not_found', 2],
  ['codex', codexId, 'codex_ambiguous', 'session_ambiguous', 2],
  ['claude', 'claude-session-1', 'claude_not_found', 'session_not_found', 2],
  ['claude', 'claude-session-1', 'protocol', 'upstream_protocol_unrecognized', 1],
  ['codex', codexId, 'failed', 'upstream_failed', 1],
  ['codex', codexId, 'timeout', 'upstream_timeout', 1],
  ['codex', codexId, 'large', 'upstream_output_too_large', 1],
]) { ({ result, value } = json(provider, id, scenario, '--json', scenario === 'timeout' ? ['--timeout-ms', '50'] : [])); assert.equal(result.status, exit); assert.equal(value.error.code, code); assert.equal(value.tokens.total, null); }
result = run('codex', '../unsafe', 'codex_ok'); value = JSON.parse(result.stdout); assert.equal(result.status, 2); assert.equal(value.error.code, 'invalid_usage');
result = spawnSync(process.execPath, [cli, 'session', '--provider', 'codex', '--id', codexId, '--json', '--ccusage-command', join(here, 'missing-ccusage')], { encoding: 'utf8' }); value = JSON.parse(result.stdout); assert.equal(result.status, 2); assert.equal(value.error.code, 'dependency_missing');
if (process.platform === 'win32') {
  const shim = spawnSync(process.execPath, [cli, 'session', '--provider', 'codex', '--id', codexId, '--json', '--ccusage-command', cmdStub], { encoding: 'utf8', env: { ...process.env, CCUSAGE_STUB_SCENARIO: 'codex_ok' } });
  assert.equal(shim.status, 0, shim.stderr); assert.equal(JSON.parse(shim.stdout).source_session_id, `workspace/${codexId}`);
  const spacedShim = spawnSync(process.execPath, [cli, 'session', '--provider', 'codex', '--id', codexId, '--json', '--ccusage-command', spacedCmdStub], { encoding: 'utf8', env: { ...process.env, CCUSAGE_STUB_SCENARIO: 'codex_ok' } });
  assert.equal(spacedShim.status, 0, spacedShim.stderr); assert.equal(JSON.parse(spacedShim.stdout).source_session_id, `workspace/${codexId}`);
  const npmShim = spawnSync(process.execPath, [cli, 'session', '--provider', 'codex', '--id', codexId, '--json'], { encoding: 'utf8', env: { ...process.env, PATH: `${npmShimDirectory}${delimiter}${process.env.PATH ?? ''}`, CCUSAGE_STUB_SCENARIO: 'codex_ok' } });
  assert.equal(npmShim.status, 0, npmShim.stderr); assert.equal(JSON.parse(npmShim.stdout).source_session_id, `workspace/${codexId}`);
}
result = run('codex', codexId, 'codex_ok', '--summary'); assert.equal(result.status, 0); assert.ok(result.stdout.includes('Token')); assert.ok(result.stdout.includes('已消耗'));

const skill = readFileSync(join(pluginRoot, 'skills', 'resource-observability', 'SKILL.md'), 'utf8');
const naturalDecisionLoop = readFileSync(join(pluginRoot, 'skills', 'resource-observability', 'references', 'natural-decision-loop.md'), 'utf8');
assert.ok(skill.includes('orca account list --json'));
assert.ok(skill.includes('result.rateLimits.claude'));
assert.ok(skill.includes('result.rateLimits.codex'));
assert.ok(skill.includes('不得输出或转述原始 JSON 中的邮箱'));
assert.ok(skill.includes('不自动启动任务、扩大并发、消费重置券或停止 Agent'));
assert.ok(skill.includes('resource-observability.ts'));
assert.ok(skill.includes('./references/natural-decision-loop.md'));
for (const marker of [
  '无资源数据时会怎样决定',
  '同一 Provider、同一窗口',
  '`updatedAt` 确实前进',
  '每个实际参与 Session',
  '未知值是否正确阻止了错误理由',
  '稳定交付与验收情况',
  '负责人打扰',
  '超过 5 分钟',
  '不为实验制造任务',
  '不得据此声称产品采用、长期依赖或自动化授权',
]) {
  assert.ok(naturalDecisionLoop.includes(marker), `自然资源决定闭环缺少：${marker}`);
}
for (const manifest of ['.claude-plugin', '.codex-plugin']) {
  const metadata = JSON.parse(readFileSync(join(pluginRoot, manifest, 'plugin.json'), 'utf8'));
  assert.equal(metadata.version, '0.2.3');
}

const persistentFiles = (root: string): string[] => readdirSync(root, { recursive: true, encoding: 'utf8' })
  .map((entry) => String(entry).replaceAll('\\', '/'));
const forbiddenExtensions = /\.(?:mjs|ps1|cmd|bat|sh)$/iu;
for (const entry of persistentFiles(pluginRoot)) {
  assert.ok(!forbiddenExtensions.test(entry), `白名单语言迁移后仍有持久脚本资产：${entry}`);
}
console.log('PASS: resource observability contracts');
