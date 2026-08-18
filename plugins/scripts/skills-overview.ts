#!/usr/bin/env node
// 生成 plugins/docs/skills-overview.md：写给负责人的选型面。
//
// 只有三句话是手写的（写在 plugins/tests/workflow-routing.json 的 skillOverview 里）：
// 它替你做什么、什么时候用、你怎么知道它在起作用。其余全部推导——版本来自
// pluginVersions，复核状态来自 skillLifecycle，L1/L2/L3 与递归维护面来自实测字节。
//
// **它是生成产物，不是手写文档。** 符合性测试会重新生成并与文件比对，因此
// 它不可能与来源漂移——这正是 plugins/docs/lifecycle.md 要防的东西，选型面自己也得守。
//
// 运行：node plugins/scripts/skills-overview.ts --write

import { existsSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (path: string): string =>
  readFileSync(path, 'utf8').replace(/^﻿/, '').replace(/\r\n/g, '\n');

type Manifest = {
  descriptionBudget: { maxUtf8Bytes: number };
  pluginVersions: Record<string, string>;
  skillLifecycle: {
    entries: Record<
      string,
      { lastVerified: string | null; suspect: boolean; invalidatedWhen: string }
    >;
  };
  skillOverview: {
    entries: Record<string, { forYou: string; whenToUse: string; workingSignals: string }>;
  };
};

const manifest = JSON.parse(read(join(repoRoot, 'tests', 'workflow-routing.json'))) as Manifest;

type SkillSize = {
  description: number;
  main: number;
  references: number;
  maintenance: number;
};

function markdownBytesRecursively(root: string): number {
  if (!existsSync(root)) return 0;
  let total = 0;
  for (const entry of readdirSync(root)) {
    const path = join(root, entry);
    if (statSync(path).isDirectory()) {
      total += markdownBytesRecursively(path);
    } else if (entry.endsWith('.md')) {
      total += Buffer.byteLength(read(path), 'utf8');
    }
  }
  return total;
}

function deliveredDescriptionBytes(skillBody: string): number {
  const match = /^description:\s*[>|][-+]?\s*\n(?<body>(?: {2,}.*(?:\n|$))*)/mu.exec(skillBody);
  if (!match?.groups?.body) throw new Error('SKILL.md frontmatter 缺少可折叠 description');
  const delivered = match.groups.body
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .join(' ');
  return Buffer.byteLength(delivered, 'utf8');
}

function skillSize(plugin: string, skill: string): SkillSize {
  const root = join(repoRoot, plugin, 'skills', skill);
  const mainBody = read(join(root, 'SKILL.md'));
  const main = Buffer.byteLength(mainBody, 'utf8');
  const references = markdownBytesRecursively(join(root, 'references'));
  return {
    description: deliveredDescriptionBytes(mainBody),
    main,
    references,
    maintenance: main + references,
  };
}

export function render(): string {
  const rows = Object.entries(manifest.skills).map(([skill, spec]) => ({
    skill,
    plugin: spec.plugin,
    size: skillSize(spec.plugin, skill),
  }));
  const totals = rows.reduce(
    (sum, row) => ({
      description: sum.description + row.size.description,
      main: sum.main + row.size.main,
      references: sum.references + row.size.references,
      maintenance: sum.maintenance + row.size.maintenance,
    }),
    { description: 0, main: 0, references: 0, maintenance: 0 },
  );
  rows.sort((a, b) => b.size.maintenance - a.size.maintenance);

  const lines: string[] = [
    '<!-- 生成产物：node plugins/scripts/skills-overview.ts --write。不要手改；',
    '     三句话的来源是 plugins/tests/workflow-routing.json 的 skillOverview。 -->',
    '',
    '# Skill 选型面',
    '',
    '这是给人看的入口：每个 Skill 替你做什么、什么时候会用到、你怎么看出它在起作用，',
    '以及它在不同加载层和维护面上的实测体积。`SKILL.md` 是给 Agent 执行的行为合同，优先保证触发、硬门、分支和退出完整，不是按顺序阅读的教程；只有维护或审查行为时才需要下钻。',
    '',
    `当前 ${rows.length} 个 Skill：L1 descriptions ${totals.description.toLocaleString('en-US')} 字节；` +
      `L2 主合同 ${totals.main.toLocaleString('en-US')} 字节；` +
      `L3 按需 references ${totals.references.toLocaleString('en-US')} 字节；` +
      `递归维护面合计 ${totals.maintenance.toLocaleString('en-US')} 字节。`,
    '',
    `L1 受每项 ${manifest.descriptionBudget.maxUtf8Bytes} UTF-8 字节可见性门约束；` +
      'L2 只在选择 Skill 后加载；L3 只在正文明确路由后按需加载。三者不是同一个运行上下文预算。维护面递归计量全部可执行 Markdown，但不设置会诱导搬运文字的字节上限。',
    '',
    '| Skill | 版本 | L1 描述 | L2 主合同 | L3 引用 | 维护面占比 | 上次复核 |',
    '| --- | --- | ---: | ---: | ---: | ---: | --- |',
  ];
  for (const row of rows) {
    const life = manifest.skillLifecycle.entries[row.skill];
    const verified = life?.suspect
      ? '**存疑**'
      : life?.lastVerified
        ? life.lastVerified
        : '**从未**';
    lines.push(
      `| [${row.skill}](#${row.skill}) | ${manifest.pluginVersions[row.plugin]} | ` +
        `${row.size.description.toLocaleString('en-US')} B | ` +
        `${(row.size.main / 1024).toFixed(1)} KB | ${(row.size.references / 1024).toFixed(1)} KB | ` +
        `${((row.size.maintenance / totals.maintenance) * 100).toFixed(1)}% | ${verified} |`,
    );
  }
  lines.push('');

  for (const row of rows) {
    const overview = manifest.skillOverview.entries[row.skill];
    const life = manifest.skillLifecycle.entries[row.skill];
    lines.push(
      `## ${row.skill}`,
      '',
      `**它替你做什么** ${overview.forYou}`,
      '',
      `**什么时候用** ${overview.whenToUse}`,
      '',
      `**你怎么知道它在起作用** ${overview.workingSignals}`,
      '',
      `**什么会让它失效** ${life.invalidatedWhen}`,
      '',
      `所属 Plugin \`${row.plugin}\` \`${manifest.pluginVersions[row.plugin]}\`｜` +
        `L1 ${row.size.description.toLocaleString('en-US')} B｜L2 ${(row.size.main / 1024).toFixed(1)} KB｜` +
        `L3 ${(row.size.references / 1024).toFixed(1)} KB｜递归维护面 ${(row.size.maintenance / 1024).toFixed(1)} KB（占总维护面 ${((row.size.maintenance / totals.maintenance) * 100).toFixed(1)}%）｜` +
        `Agent 行为合同（维护／审查时读取）[\`plugins/${row.plugin}/skills/${row.skill}/SKILL.md\`](../${row.plugin}/skills/${row.skill}/SKILL.md)`,
      '',
    );
  }
  return lines.join('\n');
}

if (process.argv.includes('--write')) {
  const target = join(repoRoot, 'docs', 'skills-overview.md');
  writeFileSync(target, render(), 'utf8');
  console.log(`已生成 ${target}`);
}
