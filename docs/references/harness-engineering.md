---
name: harness-engineering
description: OpenAI Harness Engineering 文章的项目化摘要与 Tanwei 落地原则
type: reference
---

# Harness Engineering

## Source

- OpenAI, "Harness engineering: leveraging Codex in an agent-first world", published 2026-02-11
- URL: https://openai.com/index/harness-engineering/

## What Matters For This Repository

这篇文章对本项目最重要的不是“多 agent”，而是下面这些控制面原则：

1. Humans steer. Agents execute.
2. Repository knowledge must be the system of record.
3. Large monolithic instruction files decay quickly.
4. Architecture and taste should be enforced mechanically where possible.
5. Repeated failures should become new tools, docs, checks, or cleanup loops.

## Tanwei Translation

在探微项目中，这些原则落地为：

- `CLAUDE.md` 只保留地图、红线和文档入口
- 结构化知识进入 `docs/`
- Claude Code agents 的职责边界写入 `.claude/agents/`
- agent 文件本身要具备触发样例、边界、质量门和输出契约，而不是只有宽泛角色描述
- `lead-agent -> execution agent -> evaluator-agent -> doc-gardener` 成为默认闭环
- 技术债、计划状态、架构约束都必须 repo 可见

## Documentation Implications

根据文章思路，本仓库文档系统应满足：

- 渐进展开，而不是单文件灌输
- 文档分类清楚：设计、计划、参考、agent 路由
- 每条重要规则有明确归属文件
- 行为变化时，相关文档同步更新

## Harness Checklist

完成复杂工作时，至少检查：

- 任务是否先被拆成 agent-size 子任务
- 接口、边界、性能约束是否写成 repo 可见规则
- 验收是否由独立评估角色完成
- 文档是否跟真实实现一致
- 重复失败是否转化成新的 harness 资产

## Recommended Follow-up Assets

- `docs/design-docs/agent-operating-model.md`
- `docs/references/agent-harness.md`
- `.claude/agents/*.md`
- `docs/exec-plans/tech-debt.md`
