---
name: agent-harness
description: Tanwei 项目中 Claude Code agents 的触发规则、派工方式与验收闭环
type: reference
---

# Agent Harness Guide

## Purpose

本文件定义本仓库中 Claude Code agents 的实际协作范式。它是执行层参考手册，不是泛化人设说明。

## Subagent File Format

项目级 Claude Code subagent 文件放在 `.claude/agents/`，应遵循以下结构：

1. YAML frontmatter
2. 必填字段：`name`、`description`
3. 常用可选字段：`model`、`color`、`memory`、`tools`
4. `description` 应尽量包含可触发的具体场景，必要时附 1-2 个 `<example>` block
5. 正文写清楚职责、边界、必读上下文、工作方式、质量门、输出契约
6. 如果 agent 使用持久化 memory，必须把 repo 文件视为真源，memory 只作补充上下文

`description` 要足够具体，便于 Claude Code 自动匹配。不要使用泛化模板或与当前仓库无关的互联网示例。

## Entry Rule

默认入口是 `lead-agent`。只有在任务天然单域且边界明确时，才允许直接点名执行 agent。

## Routing Matrix

| 场景 | 默认 agent |
|------|-------------|
| 跨容器任务、计划拆解、harness 修订 | `lead-agent` |
| 方案比较、优化建议、定期扫描 | `brainstorm-architect` |
| `edge-agent/` 编排与服务契约 | `edge-agent-engineer` |
| SVM 训练、特征工程、离线评估 | `detection-ml-engineer` |
| `svm-filter-service/` 与 `llm-service/` 中心推理运行时与契约 | `central-agent-engineer` |
| 流量语义、标签、误报漏报分析 | `traffic-security-analyst` |
| 数据分析、实验设计、统计对比 | `data-scientist` |
| `console/` 前端与其控制台后端 | `console-developer` |
| Dockerfile、compose、运行边界 | `docker-expert` |
| 独立验收 | `evaluator-agent` |
| 文档同步、计划归档、技术债记录 | `doc-gardener` |

> 兼容说明：`llm-service-engineer` 与 `svm-filter-engineer` 仍保留为兼容别名文件；新任务默认路由到 `central-agent-engineer`。

## Mandatory Handoffs

- 实现完成后必须进入 `evaluator-agent`
- 影响行为、接口、计划、架构、知识库的变更通过后必须进入 `doc-gardener`
- `brainstorm-architect` 输出的建议必须回到 `lead-agent` 决策

## Acceptance Expectations

完成工作的证据必须尽量接近真实系统，而不是抽象自述：

- 相关测试或脚本结果
- API、模型、提示词或流程契约说明
- 文档更新
- 已知风险说明

## Harness Maintenance Rules

- `CLAUDE.md` 只做地图和关键约束，不做巨型手册
- `docs/design-docs/` 放架构、边界、核心原则
- `docs/exec-plans/` 放当前计划、归档计划、技术债
- `docs/references/` 放 agent 可消费的手册
- `.claude/agents/` 放角色路由与职责边界
- agent 文件应是“可路由、可交接、可验证”的运行说明，而不是抽象人设卡

## Recurring Background Work

建议定期触发两类维护任务：

1. `brainstorm-architect`
   扫描技术债、重复失败模式、文档漂移热点，提出优化建议
2. `doc-gardener`
   清理过时文档、更新计划状态、补齐新沉淀的 repo 知识
