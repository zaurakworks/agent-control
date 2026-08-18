#!/usr/bin/env node

const scenario = process.env.CCUSAGE_STUB_SCENARIO ?? 'codex_ok';
const args: string[] = process.argv.slice(2);
const codexId = 'workspace/019f1234-5678-79d1-8abc-0123456789ab';
const claudeId = 'claude-session-1';

if (args[0] === '--version') {
  process.stdout.write(`${scenario === 'bad_version' ? '20.0.18' : '20.0.19'}\n`);
  process.exit(0);
}
if (scenario === 'failed') process.exit(7);
if (scenario === 'timeout') setTimeout(() => {}, 5_000);
if (scenario === 'large') process.stdout.write('x'.repeat(9 * 1024 * 1024));

if (args[0] === 'codex') {
  const normal = { sessionId: codexId, inputTokens: 10, outputTokens: 20, cacheCreationTokens: 3, cacheReadTokens: 4, totalTokens: 37, lastActivity: '2026-08-10T12:00:00Z', models: { 'gpt-5.6': {} }, directory: 'C:/secret/path', sessionFile: 'C:/secret/session.json', reasoningOutputTokens: 9 };
  if (scenario === 'codex_not_found') process.stdout.write(JSON.stringify({ sessions: [] }));
  else if (scenario === 'codex_ambiguous') process.stdout.write(JSON.stringify({ sessions: [normal, { ...normal, sessionId: `other/${codexId.slice(-36)}` }] }));
  else if (scenario === 'protocol') process.stdout.write(JSON.stringify({ sessions: [{ ...normal, totalTokens: 38 }] }));
  else process.stdout.write(JSON.stringify({ sessions: [normal] }));
} else if (args[0] === 'claude') {
  if (scenario === 'claude_not_found') process.stdout.write('null');
  else if (scenario === 'protocol') process.stdout.write(JSON.stringify({ sessionId: claudeId, totalTokens: 1, entries: [{ inputTokens: 10, outputTokens: 20, cacheCreationTokens: 3, cacheReadTokens: 4, model: 'claude-sonnet-4', timestamp: '2026-08-10T12:01:00Z' }] }));
  else if (scenario === 'claude_unknown') process.stdout.write(JSON.stringify({ sessionId: claudeId, totalTokens: 37, entries: [{ inputTokens: 10, outputTokens: 20, cacheCreationTokens: 3, cacheReadTokens: 4, model: 'unknown', timestamp: '2026-08-10T12:01:00Z' }] }));
  else if (scenario === 'claude_mixed_models') process.stdout.write(JSON.stringify({ sessionId: claudeId, totalTokens: 74, entries: [{ inputTokens: 10, outputTokens: 20, cacheCreationTokens: 3, cacheReadTokens: 4, model: 'unknown', timestamp: '2026-08-10T12:01:00Z' }, { inputTokens: 10, outputTokens: 20, cacheCreationTokens: 3, cacheReadTokens: 4, model: 'claude-sonnet-4', timestamp: '2026-08-10T12:02:00Z' }] }));
  else process.stdout.write(JSON.stringify({ sessionId: claudeId, totalTokens: 37, entries: [{ inputTokens: 10, outputTokens: 20, cacheCreationTokens: 3, cacheReadTokens: 4, model: 'claude-sonnet-4', timestamp: '2026-08-10T12:01:00Z' }] }));
} else process.exit(8);
