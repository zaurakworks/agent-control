#!/usr/bin/env node

import { spawn } from 'node:child_process';
import { accessSync, constants as fsConstants, existsSync } from 'node:fs';
import { delimiter, extname, isAbsolute, resolve } from 'node:path';

const EXPECTED_VERSION = '20.0.19';
const SCHEMA = 'resource-observability.session/v1';
const MAX_STDOUT_BYTES = 8 * 1024 * 1024;
const MAX_STDERR_BYTES = 64 * 1024;
const DEFAULT_TIMEOUT_MS = 30_000;
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const UUID_SUFFIX_RE = /([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/i;
const SAFE_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._:@+\/-]{0,255}$/;
const SAFE_MODEL_RE = /^[A-Za-z0-9][A-Za-z0-9._:+-]{0,127}$/;

type Provider = 'codex' | 'claude';
type OutputFormat = 'json' | 'summary';
type ReceiptErrorCode =
  | 'invalid_usage'
  | 'dependency_missing'
  | 'dependency_version_mismatch'
  | 'session_not_found'
  | 'session_ambiguous'
  | 'upstream_protocol_unrecognized'
  | 'upstream_failed'
  | 'upstream_timeout'
  | 'upstream_output_too_large';

type ParsedOptions = {
  provider: Provider;
  sessionId: string;
  format: OutputFormat;
  timeoutMs: number;
  command: string;
};

type Invocation = { executable: string; args: string[]; detached: boolean };
type RunResult = { kind: 'ok'; stdout: string } | { kind: ReceiptErrorCode };

function isSafeSessionId(value: unknown): value is string {
  return typeof value === 'string' && SAFE_ID_RE.test(value)
    && value.split('/').every((part) => part.length > 0 && part !== '.' && part !== '..');
}

class ReceiptError extends Error {
  code: ReceiptErrorCode;

  constructor(code: ReceiptErrorCode) {
    super(code);
    this.code = code;
  }
}

function parseArguments(argv: string[]): ParsedOptions {
  const options: Partial<ParsedOptions> & { format: OutputFormat | null; timeoutMs: number; command: string } = {
    format: null,
    timeoutMs: DEFAULT_TIMEOUT_MS,
    command: 'ccusage',
  };
  if (argv[0] !== 'session') throw new ReceiptError('invalid_usage');
  const seen = new Set();
  for (let index = 1; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === '--json' || argument === '--summary') {
      if (options.format !== null) throw new ReceiptError('invalid_usage');
      options.format = argument.slice(2);
      continue;
    }
    if (!['--provider', '--id', '--ccusage-command', '--timeout-ms'].includes(argument)) {
      throw new ReceiptError('invalid_usage');
    }
    if (seen.has(argument) || index + 1 >= argv.length) throw new ReceiptError('invalid_usage');
    seen.add(argument);
    const value = argv[index + 1];
    index += 1;
    if (argument === '--provider') options.provider = value;
    if (argument === '--id') options.sessionId = value;
    if (argument === '--ccusage-command') options.command = value;
    if (argument === '--timeout-ms') {
      if (!/^\d+$/.test(value)) throw new ReceiptError('invalid_usage');
      options.timeoutMs = Number(value);
    }
  }
  if (!['codex', 'claude'].includes(options.provider)) throw new ReceiptError('invalid_usage');
  if (!isSafeSessionId(options.sessionId)) throw new ReceiptError('invalid_usage');
  if (!['json', 'summary'].includes(options.format)) throw new ReceiptError('invalid_usage');
  if (!Number.isSafeInteger(options.timeoutMs) || options.timeoutMs < 50 || options.timeoutMs > 120_000) {
    throw new ReceiptError('invalid_usage');
  }
  if (typeof options.command !== 'string' || options.command.length === 0 || options.command.length > 1024) {
    throw new ReceiptError('invalid_usage');
  }
  return options as ParsedOptions;
}

function isExecutable(path: string): boolean {
  try {
    accessSync(path, process.platform === 'win32' ? fsConstants.F_OK : fsConstants.X_OK);
    return true;
  } catch {
    return false;
  }
}

function resolveCommand(command: string): string | null {
  const pathLike = isAbsolute(command) || command.includes('/') || command.includes('\\');
  if (pathLike) {
    const candidate = resolve(command);
    return existsSync(candidate) ? candidate : null;
  }
  const directories = (process.env.PATH ?? '').split(delimiter).filter(Boolean);
  // npm places a POSIX extensionless shim beside the Windows .cmd shim.
  const extensions = process.platform === 'win32'
    ? (process.env.PATHEXT ?? '.COM;.EXE;.BAT;.CMD').split(';').filter(Boolean)
    : [''];
  for (const directory of directories) {
    for (const extension of extensions) {
      const candidate = resolve(directory, `${command}${extension}`);
      if (isExecutable(candidate)) return candidate;
    }
  }
  return null;
}

function invocation(command: string, args: string[]): Invocation {
  const extension = extname(command).toLowerCase();
  if (extension === '.ts' || extension === '.mjs' || extension === '.js' || extension === '.cjs') {
    return { executable: process.execPath, args: [command, ...args], detached: process.platform !== 'win32' };
  }
  if (process.platform === 'win32' && (extension === '.cmd' || extension === '.bat')) {
    if (/["%\r\n!^&|<>]/.test(command) || args.some((value) => !/^(?:--[A-Za-z0-9-]+|[A-Za-z0-9][A-Za-z0-9._:@+\/-]{0,255})$/.test(value) || value.split('/').some((part) => part === '.' || part === '..' || part.length === 0))) {
      throw new ReceiptError('invalid_usage');
    }
    // cmd.exe /s requires a second leading quote when the command path is quoted.
    // command and args are allow-listed above, so this remains a data-only command line.
    const commandLine = `""${command}" ${args.join(' ')}"`;
    return {
      executable: process.env.ComSpec || 'cmd.exe',
      args: ['/d', '/s', '/c', commandLine],
      detached: false,
    };
  }
  return { executable: command, args, detached: process.platform !== 'win32' };
}

function killTree(child: ReturnType<typeof spawn>): void {
  if (!child.pid) return;
  if (process.platform === 'win32') {
    const killer = spawn('taskkill.exe', ['/pid', String(child.pid), '/t', '/f'], {
      stdio: 'ignore',
      windowsHide: true,
    });
    killer.unref();
    return;
  }
  try {
    process.kill(-child.pid, 'SIGKILL');
  } catch {
    try { child.kill('SIGKILL'); } catch { /* process already exited */ }
  }
}

function runBounded(command: string, args: string[], timeoutMs: number): Promise<RunResult> {
  return new Promise((resolveResult) => {
    let spec;
    try {
      spec = invocation(command, args);
    } catch (error) {
      resolveResult({ kind: error instanceof ReceiptError ? error.code : 'upstream_failed' });
      return;
    }
    let child;
    try {
      child = spawn(spec.executable, spec.args, {
        detached: spec.detached,
      env: { ...process.env, FORCE_COLOR: '0', NO_COLOR: '1', LOG_LEVEL: '0' },
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
      windowsVerbatimArguments: process.platform === 'win32' && (extname(command).toLowerCase() === '.cmd' || extname(command).toLowerCase() === '.bat'),
      });
    } catch {
      resolveResult({ kind: 'upstream_failed' });
      return;
    }
    const chunks = [];
    let stdoutBytes = 0;
    let stderrBytes = 0;
    let terminalKind = null;
    let settled = false;
    const stop = (kind) => {
      if (terminalKind === null) {
        terminalKind = kind;
        killTree(child);
      }
    };
    const timer = setTimeout(() => stop('upstream_timeout'), timeoutMs);
    child.stdout.on('data', (chunk) => {
      stdoutBytes += chunk.length;
      if (stdoutBytes > MAX_STDOUT_BYTES) {
        stop('upstream_output_too_large');
      } else {
        chunks.push(chunk);
      }
    });
    child.stderr.on('data', (chunk) => {
      stderrBytes += chunk.length;
      if (stderrBytes > MAX_STDERR_BYTES) stop('upstream_output_too_large');
    });
    child.on('error', () => {
      terminalKind ??= 'upstream_failed';
    });
    child.on('close', (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (terminalKind !== null) {
        resolveResult({ kind: terminalKind });
        return;
      }
      if (code !== 0) {
        resolveResult({ kind: 'upstream_failed' });
        return;
      }
      try {
        const stdout = new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks));
        resolveResult({ kind: 'ok', stdout });
      } catch {
        resolveResult({ kind: 'upstream_protocol_unrecognized' });
      }
    });
  });
}

function safeInteger(value: unknown): number {
  if (!Number.isSafeInteger(value) || value < 0) throw new ReceiptError('upstream_protocol_unrecognized');
  return value;
}

function safeSum(values: unknown[]): number {
  let total = 0;
  for (const value of values) {
    total += safeInteger(value);
    if (!Number.isSafeInteger(total)) throw new ReceiptError('upstream_protocol_unrecognized');
  }
  return total;
}

function isoTimestamp(value: unknown): string {
  if (typeof value !== 'string') throw new ReceiptError('upstream_protocol_unrecognized');
  const milliseconds = Date.parse(value);
  if (!Number.isFinite(milliseconds)) throw new ReceiptError('upstream_protocol_unrecognized');
  return new Date(milliseconds).toISOString();
}

function plainObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function parseJson(stdout: string): unknown {
  try {
    return JSON.parse(stdout);
  } catch {
    throw new ReceiptError('upstream_protocol_unrecognized');
  }
}

function codexReceipt(payload, requestedId) {
  if (!plainObject(payload) || !Array.isArray(payload.sessions)) throw new ReceiptError('upstream_protocol_unrecognized');
  let matches = payload.sessions.filter((row) => plainObject(row) && row.sessionId === requestedId);
  if (matches.length === 0 && UUID_RE.test(requestedId)) {
    const requestedUuid = requestedId.toLowerCase();
    matches = payload.sessions.filter((row) => {
      if (!plainObject(row) || typeof row.sessionId !== 'string') return false;
      return row.sessionId.match(UUID_SUFFIX_RE)?.[1].toLowerCase() === requestedUuid;
    });
  }
  if (matches.length === 0) throw new ReceiptError('session_not_found');
  if (matches.length > 1) throw new ReceiptError('session_ambiguous');
  const row = matches[0];
  if (typeof row.sessionId !== 'string' || !plainObject(row.models)) throw new ReceiptError('upstream_protocol_unrecognized');
  const sourceSessionId = isSafeSessionId(row.sessionId) ? row.sessionId : null;
  if (sourceSessionId === null) throw new ReceiptError('upstream_protocol_unrecognized');
  const models = Object.keys(row.models);
  if (models.length === 0 || models.some((model) => !SAFE_MODEL_RE.test(model))) {
    throw new ReceiptError('upstream_protocol_unrecognized');
  }
  const tokens = {
    input: safeInteger(row.inputTokens), output: safeInteger(row.outputTokens),
    cache_creation_input: safeInteger(row.cacheCreationTokens), cache_read_input: safeInteger(row.cacheReadTokens),
    total: safeInteger(row.totalTokens),
  };
  if (safeSum([tokens.input, tokens.output, tokens.cache_creation_input, tokens.cache_read_input]) !== tokens.total) {
    throw new ReceiptError('upstream_protocol_unrecognized');
  }
  return {
    sourceSessionId,
    lastActivity: isoTimestamp(row.lastActivity),
    models,
    tokens,
  };
}

function claudeReceipt(payload, requestedId) {
  if (payload === null) throw new ReceiptError('session_not_found');
  if (!plainObject(payload) || payload.sessionId !== requestedId || !Array.isArray(payload.entries) || payload.entries.length === 0) {
    throw new ReceiptError('upstream_protocol_unrecognized');
  }
  const models = new Set();
  const timestamps = [];
  const tokenRows = [];
  for (const entry of payload.entries) {
    if (!plainObject(entry) || !SAFE_MODEL_RE.test(entry.model ?? '')) throw new ReceiptError('upstream_protocol_unrecognized');
    if (entry.model !== 'unknown') models.add(entry.model);
    timestamps.push(isoTimestamp(entry.timestamp));
    tokenRows.push({
      input: safeInteger(entry.inputTokens),
      output: safeInteger(entry.outputTokens),
      cache_creation_input: safeInteger(entry.cacheCreationTokens),
      cache_read_input: safeInteger(entry.cacheReadTokens),
    });
  }
  const tokens = {
    input: safeSum(tokenRows.map((row) => row.input)),
    output: safeSum(tokenRows.map((row) => row.output)),
    cache_creation_input: safeSum(tokenRows.map((row) => row.cache_creation_input)),
    cache_read_input: safeSum(tokenRows.map((row) => row.cache_read_input)),
    total: safeInteger(payload.totalTokens),
  };
  if (safeSum([tokens.input, tokens.output, tokens.cache_creation_input, tokens.cache_read_input]) !== tokens.total) {
    throw new ReceiptError('upstream_protocol_unrecognized');
  }
  return {
    sourceSessionId: payload.sessionId,
    lastActivity: timestamps.sort().at(-1),
    models: models.size === 0 ? null : [...models],
    tokens,
  };
}

function summaryFor(receipt) {
  if (receipt.status !== 'ok') {
    const summaries = {
      invalid_usage: '资源观测不可用：参数无效。',
      dependency_missing: '资源观测不可用：未找到 ccusage。',
      dependency_version_mismatch: '资源观测不可用：ccusage 版本不符合固定版本 20.0.19。',
      session_not_found: '资源观测不可用：未找到指定 Session。',
      session_ambiguous: '资源观测不可用：指定 Session 匹配到多个结果。',
      upstream_protocol_unrecognized: '资源观测失败：ccusage 输出协议无法识别。',
      upstream_failed: '资源观测失败：ccusage 调用失败。',
      upstream_timeout: '资源观测失败：ccusage 调用超时。',
      upstream_output_too_large: '资源观测失败：ccusage 输出超过安全上限。',
    };
    return summaries[receipt.error.code] ?? '资源观测失败。';
  }
  const provider = receipt.provider === 'codex' ? 'Codex' : 'Claude';
  const tokens = receipt.tokens;
  const models = receipt.models === null ? '未知' : receipt.models.join('、');
  return `${provider} Session 已消耗 ${tokens.total.toLocaleString('zh-CN')} Token（输入 ${tokens.input.toLocaleString('zh-CN')}、输出 ${tokens.output.toLocaleString('zh-CN')}、缓存创建 ${tokens.cache_creation_input.toLocaleString('zh-CN')}、缓存读取 ${tokens.cache_read_input.toLocaleString('zh-CN')}），模型：${models}。`;
}

function baseReceipt(provider, sessionId, status) {
  return {
    schema: SCHEMA,
    status,
    provider: provider ?? null,
    session_id: isSafeSessionId(sessionId) ? sessionId : null,
    source_session_id: null,
    observed_at: new Date().toISOString(),
    last_activity: null,
    models: null,
    tokens: {
      input: null,
      output: null,
      cache_creation_input: null,
      cache_read_input: null,
      total: null,
    },
    source: { tool: 'ccusage', version: EXPECTED_VERSION },
  };
}

function statusFor(code) {
  return ['invalid_usage', 'dependency_missing', 'dependency_version_mismatch', 'session_not_found', 'session_ambiguous'].includes(code) ? 'unavailable' : 'error';
}

function emitFailure(code, options, formatHint) {
  const receipt = baseReceipt(options?.provider, options?.sessionId, statusFor(code));
  receipt.error = { code };
  receipt.summary_zh = summaryFor(receipt);
  if ((options?.format ?? formatHint) === 'summary') {
    process.stdout.write(`${receipt.summary_zh}\n`);
  } else {
    process.stdout.write(`${JSON.stringify(receipt)}\n`);
  }
  process.stderr.write(`resource-observability: ${code}\n`);
  process.exitCode = receipt.status === 'unavailable' ? 2 : 1;
}

async function main() {
  let options;
  const formatHint = process.argv.slice(2).includes('--summary') ? 'summary' : 'json';
  try {
    options = parseArguments(process.argv.slice(2));
  } catch (error) {
    emitFailure(error instanceof ReceiptError ? error.code : 'invalid_usage', options, formatHint);
    return;
  }
  const command = resolveCommand(options.command);
  if (command === null) {
    emitFailure('dependency_missing', options, formatHint);
    return;
  }
  const versionResult = await runBounded(command, ['--version'], Math.min(options.timeoutMs, 5_000));
  if (versionResult.kind !== 'ok') {
    emitFailure(versionResult.kind, options, formatHint);
    return;
  }
  if (!new RegExp(`^(?:ccusage\\s+)?${EXPECTED_VERSION.replaceAll('.', '\\.')}\\s*$`).test(versionResult.stdout)) {
    emitFailure('dependency_version_mismatch', options, formatHint);
    return;
  }
  const args = options.provider === 'claude'
    ? ['claude', 'session', '--id', options.sessionId, '--json', '--offline', '--no-cost']
    : ['codex', 'session', '--json', '--offline', '--no-cost'];
  const result = await runBounded(command, args, options.timeoutMs);
  if (result.kind !== 'ok') {
    emitFailure(result.kind, options, formatHint);
    return;
  }
  try {
    const normalized = options.provider === 'codex'
      ? codexReceipt(parseJson(result.stdout), options.sessionId)
      : claudeReceipt(parseJson(result.stdout), options.sessionId);
    const receipt = baseReceipt(options.provider, options.sessionId, 'ok');
    receipt.source_session_id = normalized.sourceSessionId;
    receipt.last_activity = normalized.lastActivity;
    receipt.models = normalized.models;
    receipt.tokens = normalized.tokens;
    receipt.summary_zh = summaryFor(receipt);
    process.stdout.write(options.format === 'summary'
      ? `${receipt.summary_zh}\n`
      : `${JSON.stringify(receipt)}\n`);
  } catch (error) {
    emitFailure(error instanceof ReceiptError ? error.code : 'upstream_protocol_unrecognized', options, formatHint);
  }
}

await main();
