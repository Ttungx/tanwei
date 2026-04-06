# 探微 (Tanwei) 文档中心

本目录是 Tanwei EdgeAgent 项目的事实来源。文档系统按 Harness Engineering 思路组织：`CLAUDE.md` 负责导航，`docs/` 负责承载可执行知识。

## 文档结构

```text
docs/
├── design-docs/             # 架构、边界、核心原则
│   ├── core-beliefs.md
│   ├── architecture.md
│   ├── traffic-tokenization.md
│   └── agent-operating-model.md
├── exec-plans/              # 当前计划、归档、技术债
│   ├── active-plan.md
│   ├── completed/
│   └── tech-debt.md
├── references/              # 可直接给 agent 消费的参考手册
│   ├── api_specs.md
│   ├── deployment.md
│   ├── dataset-feature-engineering.md
│   ├── harness-engineering.md
│   └── agent-harness.md
└── superpowers/             # 设计与实施历史
```

## Read Paths

| 场景 | 推荐起点 |
|------|----------|
| 新 agent 或新成员了解仓库 | `CLAUDE.md` -> `design-docs/agent-operating-model.md` |
| 改架构或跨服务任务 | `design-docs/architecture.md` |
| 改流量处理和分词 | `design-docs/traffic-tokenization.md` |
| 改训练、特征或评估 | `references/dataset-feature-engineering.md` |
| 改部署和容器 | `references/deployment.md` |
| 了解 agent 协作方式 | `references/agent-harness.md` |

## Documentation Rules

1. AI 不可见即不存在，重要决策必须落在 repo 中。
2. `CLAUDE.md` 是地图，不是巨型操作手册。
3. 行为改变时，相关文档必须同步更新。
4. 技术债应被记录，而不是隐藏在对话里。

## Maintenance Loop

- `lead-agent` 维护控制面和派工方式
- `evaluator-agent` 做独立验收
- `doc-gardener` 清理漂移、更新计划和知识库
- `brainstorm-architect` 定期扫描并提出优化建议
