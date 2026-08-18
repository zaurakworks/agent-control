#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { extname, resolve } from 'node:path';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const execute = promisify(execFile);
const INPUT = 'orchestrated-collaboration.three-party-review-input/v1';
const VERDICT = 'orchestrated-collaboration.three-party-verdict/v1';
const SEALED = 'orchestrated-collaboration.sealed-verdict/v1';
const RESULT = 'orchestrated-collaboration.three-party-review-result/v1';
const ROLES = ['R1', 'R2', 'R3'];
const COUNTERCASES = { R1: '授权与边界', R2: '执行与身份', R3: 'ROI 与维持现状' };
const SHA = /^[0-9a-f]{64}$/u;

function object(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (object(value)) return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}
export function sha256Canonical(value) { return createHash('sha256').update(canonical(value)).digest('hex'); }
function same(left, right) { return canonical(left) === canonical(right); }
function runOf(raw) { return object(raw?.result?.run) ? raw.result.run : object(raw?.run) ? raw.run : null; }
function workerOf(raw) {
  const root = object(raw?.result) ? raw.result : raw;
  return object(root?.dispatch) ? { dispatch: root.dispatch, worker: object(root.worker) ? root.worker : null } : null;
}
function commentOf(raw) { return object(raw?.comment) ? raw.comment : object(raw) && !raw.fetch_error ? raw : null; }
function manifestOf(body) {
  if (typeof body !== 'string') return null;
  const matches = [...body.matchAll(/<!--\s*CF6-VERDICT-V1\s*\n([\s\S]*?)\n-->/gu)];
  if (matches.length !== 1) return null;
  try { const value = JSON.parse(matches[0][1]); return object(value) ? value : null; } catch { return null; }
}
function commentId(url) {
  const match = typeof url === 'string' && url.match(/^https:\/\/github\.com\/([^/]+)\/([^/]+)\/issues\/(\d+)#issuecomment-(\d+)$/u);
  return match ? { owner: match[1], repo: match[2], issue: Number(match[3]), id: match[4] } : null;
}
function markdown(rows) {
  const columns = ['comment_url', 'role_id', 'seat_kind', 'stable_runtime_key', 'observed_terminal_handle', 'seal_message_id', 'seal_sha256', 'verdict', 'verified_at'];
  const escape = (value) => String(value).replaceAll('|', '\\|').replaceAll('\n', ' ');
  return `${[`| ${columns.join(' | ')} |`, `| ${columns.map(() => '---').join(' | ')} |`, ...rows.map((row) => `| ${columns.map((key) => escape(row[key])).join(' | ')} |`)].join('\n')}\n`;
}
function runView(raw) {
  const run = runOf(raw);
  return run && { id: run.id, consumer_generation: run.consumer_generation, coordinator_handle: run.coordinator_handle };
}
function workerView(raw) {
  const item = workerOf(raw);
  return item && { id: item.dispatch.id, task_id: item.dispatch.task_id, run_id: item.dispatch.run_id, assignee_handle: item.dispatch.assignee_handle, worker_handle: item.worker?.agent_terminal_handle ?? null };
}
function commentView(raw) {
  const comment = commentOf(raw);
  return comment && { html_url: comment.html_url, issue_url: comment.issue_url, login: comment.user?.login, type: comment.user?.type, created_at: comment.created_at, updated_at: comment.updated_at, body: comment.body };
}

export function verifyEvidence(input, first, second, verifiedAt = new Date().toISOString()) {
  const failures = [];
  const keys = new Set();
  const fail = (code, role_id = null) => {
    const key = `${code}:${role_id ?? ''}`;
    if (!keys.has(key)) { keys.add(key); failures.push({ code, role_id }); }
  };
  const base = { schema: RESULT, verified: false, decision_id: null, target_issue: null, run_id: null, verified_at: verifiedAt, failures, mapping: [], mapping_markdown: '' };
  if (!object(input) || input.schema !== INPUT || !object(input.target_issue) || !Array.isArray(input.seats) || !SHA.test(input.decision_packet_sha256 ?? '') || !Array.isArray(input.trusted_github_users)) {
    fail('invalid_input'); base.mapping_markdown = markdown([]); return base;
  }

  base.decision_id = input.decision_id;
  base.run_id = input.run_id;
  base.target_issue = `${input.target_issue.owner}/${input.target_issue.repo}#${input.target_issue.number}`;
  if (input.seats.length !== 3) fail('seat_count');
  const roles = input.seats.map((seat) => seat.role_id);
  if (new Set(roles).size !== roles.length || !ROLES.every((role) => roles.includes(role))) fail('role_ids');
  const urls = input.seats.map((seat) => seat.comment_url);
  if (new Set(urls).size !== urls.length) fail('comment_urls');
  if (input.seats.filter((seat) => seat.seat_kind === 'coordinator').length > 1) fail('seat_kinds');

  const run1 = runOf(first.run); const run2 = runOf(second.run);
  if (!run1 || !run2) fail('source_unavailable');
  else {
    if (!same(runView(first.run), runView(second.run))) fail('run_changed');
    if (run1.id !== input.run_id || run2.id !== input.run_id) fail('run_mismatch');
  }

  const runtimeKeys = new Set(); const terminals = new Set(); const rows = [];
  for (const seat of input.seats) {
    const role = ROLES.includes(seat.role_id) ? seat.role_id : null;
    if (!role) fail('role_ids', seat.role_id ?? null);
    if (role && seat.assigned_countercase !== COUNTERCASES[role]) fail('countercase_mismatch', role);
    if (!['coordinator', 'reviewer'].includes(seat.seat_kind)) fail('seat_kinds', role);
    if (!SHA.test(seat.seal_sha256 ?? '') || typeof seat.seal_message_id !== 'string') fail('seal_fields', role);
    if (!seat.model_family) fail('model_family', role);
    if (!seat.observed_terminal_handle) fail('runtime_identity_mismatch', role);
    if ((input.excluded_terminal_handles ?? []).includes(seat.observed_terminal_handle)) fail('drafter_or_implementer_counted', role);

    let runtimeKey;
    if (seat.seat_kind === 'coordinator') {
      runtimeKey = `${input.run_id}+generation:${seat.consumer_generation}`;
      if (seat.task_id !== null || seat.dispatch_id !== null || !Number.isSafeInteger(seat.consumer_generation)) fail('runtime_identity_mismatch', role);
      for (const run of [run1, run2]) if (run && (run.consumer_generation !== seat.consumer_generation || run.coordinator_handle !== seat.observed_terminal_handle)) fail('coordinator_generation_stale', role);
    } else {
      runtimeKey = `${seat.task_id}+${seat.dispatch_id}`;
      if (!seat.task_id || !seat.dispatch_id || seat.consumer_generation !== null) fail('runtime_identity_mismatch', role);
      const worker1 = workerOf(first.workers[seat.dispatch_id]); const worker2 = workerOf(second.workers[seat.dispatch_id]);
      if (!worker1 || !worker2) fail('source_unavailable', role);
      else {
        if (!same(workerView(first.workers[seat.dispatch_id]), workerView(second.workers[seat.dispatch_id]))) fail('dispatch_changed', role);
        for (const item of [worker1, worker2]) {
          const handle = item.worker?.agent_terminal_handle ?? item.dispatch.assignee_handle;
          if (item.dispatch.id !== seat.dispatch_id || item.dispatch.task_id !== seat.task_id || item.dispatch.run_id !== input.run_id || item.dispatch.assignee_handle !== seat.observed_terminal_handle || handle !== seat.observed_terminal_handle) fail('runtime_identity_mismatch', role);
        }
      }
    }
    if (runtimeKeys.has(runtimeKey)) fail('runtime_identity_duplicate', role); runtimeKeys.add(runtimeKey);
    if (terminals.has(seat.observed_terminal_handle)) fail('session_not_distinct', role); terminals.add(seat.observed_terminal_handle);

    let verdict = 'unknown';
    const identity = commentId(seat.comment_url);
    if (!identity) fail('comment_url_invalid', role);
    else if (identity.owner !== input.target_issue.owner || identity.repo !== input.target_issue.repo || identity.issue !== input.target_issue.number) fail('comment_issue_mismatch', role);
    const comment1 = commentOf(first.comments[seat.comment_url]); const comment2 = commentOf(second.comments[seat.comment_url]);
    if (!comment1 || !comment2) fail('source_unavailable', role);
    else {
      if (!same(commentView(first.comments[seat.comment_url]), commentView(second.comments[seat.comment_url]))) fail('comment_changed', role);
      const issueApi = `https://api.github.com/repos/${input.target_issue.owner}/${input.target_issue.repo}/issues/${input.target_issue.number}`;
      for (const comment of [comment1, comment2]) {
        if (comment.html_url !== seat.comment_url) fail('comment_url_mismatch', role);
        if (comment.issue_url !== issueApi) fail('comment_issue_mismatch', role);
        if (comment.user?.type !== 'User') fail('comment_author_type', role);
        if (!input.trusted_github_users.includes(comment.user?.login)) fail('comment_author_untrusted', role);
        if (comment.updated_at !== seat.comment_updated_at) fail('comment_edit_unverified', role);
      }
      const manifest = manifestOf(comment2.body);
      if (!manifest || manifest.schema !== VERDICT) fail('verdict_manifest_invalid', role);
      else {
        verdict = manifest.verdict ?? 'unknown';
        const expected = { decision_id: input.decision_id, decision_packet_sha256: input.decision_packet_sha256, role_id: seat.role_id, assigned_countercase: seat.assigned_countercase, seat_kind: seat.seat_kind, task_id: seat.task_id, dispatch_id: seat.dispatch_id, run_id: input.run_id, consumer_generation: seat.consumer_generation, observed_terminal_handle: seat.observed_terminal_handle, model_family: seat.model_family, seal_message_id: seat.seal_message_id, seal_sha256: seat.seal_sha256 };
        for (const [key, value] of Object.entries(expected)) if (!same(manifest[key], value)) fail('comment_mapping_mismatch', role);
        const sealed = manifest.sealed_payload;
        if (!object(sealed) || sealed.schema !== SEALED) fail('sealed_payload_invalid', role);
        else {
          const hash = sha256Canonical(sealed);
          if (hash !== seat.seal_sha256 || hash !== manifest.seal_sha256) fail('seal_hash_mismatch', role);
          for (const [key, value] of Object.entries({ decision_id: input.decision_id, decision_packet_sha256: input.decision_packet_sha256, role_id: seat.role_id, assigned_countercase: seat.assigned_countercase, verdict: manifest.verdict })) if (!same(sealed[key], value)) fail('sealed_payload_mismatch', role);
        }
        if (verdict !== 'approve') fail('verdict_not_approve', role);
      }
    }
    rows.push({ comment_url: seat.comment_url, role_id: seat.role_id, seat_kind: seat.seat_kind, stable_runtime_key: runtimeKey, observed_terminal_handle: seat.observed_terminal_handle, seal_message_id: seat.seal_message_id, seal_sha256: seat.seal_sha256, verdict, verified_at: verifiedAt });
  }
  if (input.seats.length && !input.seats.some((seat) => seat.model_family !== input.drafter_model_family)) fail('model_family_not_mixed');
  rows.sort((left, right) => ROLES.indexOf(left.role_id) - ROLES.indexOf(right.role_id));
  failures.sort((left, right) => `${left.role_id ?? ''}:${left.code}`.localeCompare(`${right.role_id ?? ''}:${right.code}`));
  base.mapping = rows; base.mapping_markdown = markdown(rows); base.verified = failures.length === 0;
  return base;
}

function invocation(command, args) {
  return ['.ts', '.js', '.mjs', '.cjs'].includes(extname(command).toLowerCase()) ? [process.execPath, [command, ...args]] : [command, args];
}
async function fetchJson(command, args, timeout, pass) {
  const [file, values] = invocation(command, args);
  try {
    const { stdout } = await execute(file, values, { timeout, maxBuffer: 8 * 1024 * 1024, windowsHide: true, env: { ...process.env, CF6_VERIFICATION_PASS: pass, FORCE_COLOR: '0', NO_COLOR: '1' } });
    return JSON.parse(stdout);
  } catch { return { fetch_error: true }; }
}
async function collect(input, orca, gh, timeout, pass) {
  const run = fetchJson(orca, ['orchestration', 'run-show', '--id', input.run_id, '--json'], timeout, pass);
  const workers = input.seats.filter((seat) => seat.seat_kind === 'reviewer' && seat.dispatch_id).map(async (seat) => [seat.dispatch_id, await fetchJson(orca, ['orchestration', 'worker-show', '--dispatch', seat.dispatch_id, '--json'], timeout, pass)]);
  const comments = input.seats.map(async (seat) => {
    const id = commentId(seat.comment_url);
    return [seat.comment_url, id ? await fetchJson(gh, ['api', `repos/${id.owner}/${id.repo}/issues/comments/${id.id}`], timeout, pass) : { fetch_error: true }];
  });
  return { run: await run, workers: Object.fromEntries(await Promise.all(workers)), comments: Object.fromEntries(await Promise.all(comments)) };
}
function argumentsOf(argv) {
  if (argv[0] !== 'verify') return null;
  const value = { input: null, format: null, orca: 'orca', gh: 'gh', timeout: 30_000 };
  for (let index = 1; index < argv.length; index += 1) {
    const key = argv[index];
    if (key === '--json' || key === '--markdown') { if (value.format) return null; value.format = key.slice(2); continue; }
    if (!['--input', '--orca-command', '--gh-command', '--timeout-ms'].includes(key) || index + 1 >= argv.length) return null;
    const item = argv[++index];
    if (key === '--input') value.input = item;
    if (key === '--orca-command') value.orca = item;
    if (key === '--gh-command') value.gh = item;
    if (key === '--timeout-ms') value.timeout = Number(item);
  }
  return value.input && value.format && Number.isSafeInteger(value.timeout) && value.timeout >= 50 && value.timeout <= 120_000 ? value : null;
}
async function main() {
  const options = argumentsOf(process.argv.slice(2));
  if (!options) { process.stderr.write('用法：verify-three-party-review.ts verify --input <request.json> (--json|--markdown)\n'); process.exitCode = 2; return; }
  let input;
  try { input = JSON.parse(readFileSync(resolve(options.input), 'utf8')); } catch { process.exitCode = 2; return; }
  if (!object(input) || !Array.isArray(input.seats)) {
    const result = verifyEvidence(input, { run: {}, workers: {}, comments: {} }, { run: {}, workers: {}, comments: {} });
    process.stdout.write(options.format === 'json' ? `${JSON.stringify(result, null, 2)}\n` : result.mapping_markdown);
    process.exitCode = 3;
    return;
  }
  const first = await collect(input, options.orca, options.gh, options.timeout, 'first');
  const second = await collect(input, options.orca, options.gh, options.timeout, 'second');
  const result = verifyEvidence(input, first, second);
  process.stdout.write(options.format === 'json' ? `${JSON.stringify(result, null, 2)}\n` : result.mapping_markdown);
  process.exitCode = result.verified ? 0 : 3;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
