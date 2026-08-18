#!/usr/bin/env node

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { verifyEvidence } from '../scripts/verify-three-party-review.ts';

const here = dirname(fileURLToPath(import.meta.url));
const fixtures = join(here, 'fixtures');
const cli = join(here, '..', 'scripts', 'verify-three-party-review.ts');
const stub = join(here, 'evidence-stub.ts');
const fixedTime = '2026-08-12T01:00:00.000Z';
const readFixture = (name: string) => JSON.parse(readFileSync(join(fixtures, name), 'utf8'));
const clone = <T>(value: T): T => structuredClone(value);
const codes = (result: ReturnType<typeof verifyEvidence>) => new Set(result.failures.map((failure) => failure.code));

const compliant = readFixture('three-party-review-compliant.json');
const positive = verifyEvidence(compliant.input, compliant.first, compliant.second ?? compliant.first, fixedTime);
assert.equal(positive.verified, true, JSON.stringify(positive.failures));
assert.deepEqual(positive.mapping.map((row) => row.role_id), ['R1', 'R2', 'R3']);
assert.ok(positive.mapping_markdown.includes('run_example+generation:4'));
assert.ok(positive.mapping_markdown.includes('task_r2+ctx_r2'));

function mutated(
  change: (input: any, first: any, second: any) => void,
): ReturnType<typeof verifyEvidence> {
  const input = clone(compliant.input);
  const first = clone(compliant.first);
  const second = clone(compliant.second ?? compliant.first);
  change(input, first, second);
  return verifyEvidence(input, first, second, fixedTime);
}

let result = mutated((input) => { input.seats.pop(); });
assert.ok(codes(result).has('seat_count'), '少票必须拒绝');
result = mutated((input) => { input.seats[0].role_id = 'R2'; });
assert.ok(codes(result).has('role_ids'), '重复 role_id 必须拒绝');
result = mutated((input) => { input.seats[0].comment_url = input.seats[1].comment_url; });
assert.ok(codes(result).has('comment_urls'), '重复评论 URL 必须拒绝');
result = mutated((input) => {
  const r2 = input.seats.find((seat: any) => seat.role_id === 'R2');
  const r3 = input.seats.find((seat: any) => seat.role_id === 'R3');
  [r2.task_id, r3.task_id] = [r3.task_id, r2.task_id];
});
assert.ok(codes(result).has('runtime_identity_mismatch'), 'Task／Dispatch 对调必须拒绝');
result = mutated((input) => { input.target_issue.number = 121; });
assert.ok(codes(result).has('comment_issue_mismatch'), '错误 Issue 必须拒绝');
result = mutated((_input, first, second) => {
  const url = compliant.input.seats[0].comment_url;
  first.comments[url].user.type = 'Bot';
  second.comments[url].user.type = 'Bot';
});
assert.ok(codes(result).has('comment_author_type'), '错误作者类型必须拒绝');
result = mutated((input) => { input.seats.find((seat: any) => seat.seat_kind === 'coordinator').consumer_generation = 3; });
assert.ok(codes(result).has('coordinator_generation_stale'), '过期 consumer_generation 必须拒绝');
result = mutated((_input, _first, second) => {
  second.workers.ctx_r2.result.dispatch.assignee_handle = 'term_changed';
  second.workers.ctx_r2.result.worker.agent_terminal_handle = 'term_changed';
});
assert.ok(codes(result).has('dispatch_changed'), 'terminal 变化必须拒绝');
result = mutated((input) => { input.seats.find((seat: any) => seat.role_id === 'R2').seal_sha256 = 'c'.repeat(64); });
assert.ok(codes(result).has('seal_hash_mismatch'), '公开判定与密封哈希不一致必须拒绝');
result = mutated((_input, first, second) => {
  const url = compliant.input.seats.find((seat: any) => seat.role_id === 'R2').comment_url;
  first.comments[url].updated_at = '2026-08-12T00:05:00Z';
  second.comments[url].updated_at = '2026-08-12T00:05:00Z';
});
assert.ok(codes(result).has('comment_edit_unverified'), '编辑后未重新捕获水位必须拒绝');
result = mutated((_input, first, second) => {
  const url = compliant.input.seats.find((seat: any) => seat.role_id === 'R3').comment_url;
  first.comments[url].body = first.comments[url].body.replaceAll('"verdict":"approve"', '"verdict":"uncertain"');
  second.comments[url].body = first.comments[url].body;
});
assert.ok(codes(result).has('verdict_not_approve'), '否决或存疑必须拒绝');

const historical = readFixture('issue-90-reverse-binding.json');
const historicalResult = verifyEvidence(historical.input, historical.first, historical.second ?? historical.first, fixedTime);
assert.equal(historicalResult.verified, false, '#90 反向绑定样本不得通过');
assert.ok(codes(historicalResult).has('comment_mapping_mismatch'), '#90 必须因评论与运行身份反向绑定而失败');

const temporary = mkdtempSync(join(tmpdir(), 'cf6-validator-'));
process.on('exit', () => rmSync(temporary, { recursive: true, force: true }));
const inputPath = join(temporary, 'input.json');
writeFileSync(inputPath, JSON.stringify(compliant.input), 'utf8');
const cliResult = spawnSync(process.execPath, [cli, 'verify', '--input', inputPath, '--json', '--orca-command', stub, '--gh-command', stub], {
  encoding: 'utf8',
  env: { ...process.env, CF6_STUB_FIXTURE: join(fixtures, 'three-party-review-compliant.json') },
  timeout: 10_000,
});
assert.equal(cliResult.status, 0, cliResult.stderr || cliResult.stdout);
assert.equal(JSON.parse(cliResult.stdout).verified, true);

writeFileSync(inputPath, JSON.stringify(historical.input), 'utf8');
const historicalCli = spawnSync(process.execPath, [cli, 'verify', '--input', inputPath, '--json', '--orca-command', stub, '--gh-command', stub], {
  encoding: 'utf8',
  env: { ...process.env, CF6_STUB_FIXTURE: join(fixtures, 'issue-90-reverse-binding.json') },
  timeout: 10_000,
});
assert.equal(historicalCli.status, 3, historicalCli.stderr || historicalCli.stdout);
assert.ok(JSON.parse(historicalCli.stdout).failures.some((failure: any) => failure.code === 'comment_mapping_mismatch'));

console.log('PASS: CF-6 三方审阅验证器合同');
