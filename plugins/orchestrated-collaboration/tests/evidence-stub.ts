#!/usr/bin/env node

import { readFileSync } from 'node:fs';

const path = process.env.CF6_STUB_FIXTURE;
if (!path) process.exit(2);
const fixture = JSON.parse(readFileSync(path, 'utf8'));
const snapshot = process.env.CF6_VERIFICATION_PASS === 'second' && fixture.second ? fixture.second : fixture.first;
const args = process.argv.slice(2);

let value;
if (args[0] === 'orchestration' && args[1] === 'run-show') {
  value = snapshot.run;
} else if (args[0] === 'orchestration' && args[1] === 'worker-show') {
  value = snapshot.workers[args[args.indexOf('--dispatch') + 1]];
} else if (args[0] === 'api') {
  const commentId = args[1].match(/\/comments\/(\d+)$/u)?.[1];
  value = Object.values(snapshot.comments).find((comment: any) => comment.html_url.endsWith(`issuecomment-${commentId}`));
}

if (value === undefined) process.exit(3);
process.stdout.write(`${JSON.stringify(value)}\n`);
