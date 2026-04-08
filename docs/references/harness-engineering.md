---
name: harness-engineering
description: Harness Engineering 在 console + edge-agent + central-agent 架构中的落地规范
type: reference
---

# Harness Engineering

## 1. Source

- OpenAI, "Harness engineering: leveraging Codex in an agent-first world", published 2026-02-11
- URL: https://openai.com/index/harness-engineering/

## 2. What Matters For This Repository

本仓库关注的不是“agent 数量”，而是可验证的控制面机制：

1. Humans steer. Agents execute.
2. Repository knowledge must be the system of record.
3. Large monolithic instruction files decay quickly.
4. Architecture and taste should be enforced mechanically where possible.
5. Repeated failures should become new tools, docs, checks, or cleanup loops.

## 3. Tanwei Translation

在 `console + edge-agent + central-agent` 架构下，以上原则落实为：

- `console` 作为统一控制台，避免多入口分叉治理。
- `edge-agent` 与 `central-agent` 职责解耦，边缘检测与中心分析分离。
- 端云 JSON 情报契约写入文档并由 schema 约束。
- 禁止原始 pcap/payload 上云成为硬红线，不允许口头约定。
- 全网综合研判只允许手动触发，避免误触发自动联动。

## 4. Required Repo Assets

- `CLAUDE.md`: 只保留地图、红线与入口。
- `docs/design-docs/architecture.md`: 架构与端云边界真源。
- `docs/references/api_specs.md`: 接口与契约真源。
- `docs/references/deployment.md`: 运行依赖与失败策略真源。
- `docs/references/agent-harness.md`: 路由、ownership、handoff 真源。
- `docs/exec-plans/*.md`: 当前计划与技术债真源。

## 5. Documentation Implications

文档体系必须满足：

- 渐进展开，而不是单文件灌输
- 分类清楚：设计、计划、参考、agent 路由
- 每条关键规则有明确归属文件
- 行为变化时同步更新相关文档
- 端云契约变更必须至少同步 `architecture/api_specs/deployment`

## 6. Harness Checklist

完成复杂工作时，至少检查：

- 任务是否先被拆成 agent-size 子任务
- 接口、边界、性能与安全约束是否 repo 可见
- 验收是否由独立评估角色完成
- 文档是否跟真实实现一致
- 重复失败是否转化成新的 harness 资产
- 是否确认“单 Edge 可独立分析 + 全网手动触发”未被破坏

## 7. Recommended Follow-up Assets

- `docs/design-docs/agent-operating-model.md`
- `docs/references/agent-harness.md`
- `.claude/agents/*.md`
- `docs/exec-plans/tech-debt.md`
