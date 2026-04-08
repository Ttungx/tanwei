# Tanwei Agents Index

> Last synced: 2026-04-08  
> Scope: `console + edge-agent + central-agent` repository

## 1. 当前项目变更基线

- 仓库主架构已统一为 `console + edge-agent + central-agent` 三层协同。
- `central-agent/` 已落地基础能力（reports 接收归档、单 Edge 分析、全网分析触发骨架、外部 LLM 接入）。
- 当前执行计划仍在推进：
  - `WP-3`：`edge-agent -> central-agent` 上报链路打通与失败隔离
  - `WP-4`：`console` 中心分析运营流完善
  - `WP-5`：文档与 harness 收口

## 2. 默认协作闭环

默认链路：

`lead-agent -> specialist -> evaluator-agent -> doc-gardener`

执行规则：

- 跨服务任务先进入 `lead-agent` 拆解。
- 方案不稳或需求仍发散时，先走 `brainstorm-architect`。
- 所有有意义实现变更都要经过 `evaluator-agent` 独立验收。
- 行为/契约/计划变化必须交给 `doc-gardener` 同步文档。
- 每个 agent 文档本身也必须服从 `docs/references/harness-engineering.md` 的 repo-truth 原则。

## 3. Agent 路由总表

| Agent | 主要 ownership | 典型触发场景 | 明确不 owning |
| --- | --- | --- | --- |
| `lead-agent` | 跨服务任务拆解、路由、验收口径、harness 治理 | 需求跨 `console/edge-agent/central-agent`，或需要重构工作流 | 具体领域实现细节 |
| `brainstorm-architect` | 方案探索、优化扫描、问题重构 | 需要多方案对比、先做 leverage scan | 直接落地实现 |
| `edge-agent-engineer` | `edge-agent/` 五阶段编排、edge 上报契约 | 流重组/状态流转/上报字段调整 | `central-agent/` 内部研判逻辑、`console` 交互 |
| `central-agent-engineer` | `central-agent/` 接收归档、单 Edge 分析、全网分析、外部 LLM 集成边界 | reports 入库归档、分析状态机、中心分析接口 | `edge-agent` 检测内部、`console` 展示实现 |
| `console-developer` | `console/` 管理员流、展示层与代理交互 | 控制台页面/后端代理 API/运营交互流 | 检测或研判内部推理实现 |
| `svm-filter-engineer` | `svm-filter-service/` 在线推理路径、校验、模型加载 | runtime 模型兼容、低延迟推理路径 | 训练方案决策 |
| `llm-service-engineer` | `llm-service/` 本地推理服务与输出契约 | 模型服务行为、健康检查、推理响应契约 | 业务编排 ownership |
| `detection-ml-engineer` | SVM 离线训练、特征工程、artifact 产出建议 | 训练脚本、特征变更、模型升级评估 | 在线服务 runtime 路径 |
| `traffic-security-analyst` | 流量语义判定、威胁标签解释、误报漏报分析 | 安全语义解释、标签边界讨论 | 直接生产代码改动 |
| `data-scientist` | 实验设计、统计比较、数据分析结论 | 版本对比、指标显著性、数据分布分析 | 运行时部署/路由 ownership |
| `docker-expert` | Dockerfile/compose/部署 wiring/运行约束 | 启动顺序、健康检查、容器边界与资源策略 | 业务逻辑实现 |
| `evaluator-agent` | 独立验收与证据审查 | 实现后验收、契约一致性复核、风险判断 | 验收阶段再改实现 |
| `doc-gardener` | 文档、计划、harness 一致性治理 | 行为改变后文档同步、计划生命周期维护 | 脱离代码现实的“新架构发明” |

说明：

- `example-demo-agent` 仅用于范式示例，不承担生产 ownership。

## 4. 当前里程碑责任映射（active-plan）

| 工作包 | 主责任 agent | 协同 agent |
| --- | --- | --- |
| `WP-3 edge -> central 上报打通` | `edge-agent-engineer` | `central-agent-engineer`, `docker-expert`, `evaluator-agent`, `doc-gardener` |
| `WP-4 console 中心分析运营流` | `console-developer` | `central-agent-engineer`, `evaluator-agent`, `doc-gardener` |
| `WP-5 文档与 harness 收口` | `doc-gardener` | `lead-agent`, `evaluator-agent` |

## 5. 维护这份文件的触发条件

发生以下任一变化时，必须同步更新本文件：

1. 新增/删除 agent，或 agent ownership 调整。
2. 服务拓扑、契约边界、默认工作流发生变化。
3. 执行计划里程碑切换导致主要责任映射变化。

同步时至少交叉检查：

- `CLAUDE.md`
- `.claude/agents/README.md`
- `docs/design-docs/agent-operating-model.md`
- `docs/references/agent-harness.md`
- `docs/references/harness-engineering.md`
- `docs/exec-plans/active-plan.md`

## 6. 维护 agent 文件时的最低要求

`.claude/agents/*.md` 中每个生产 agent 至少要显式体现：

1. 当前真实 ownership，而不是未来规划。
2. 必读真源文档与真实代码入口文件。
3. 独立验收与文档同步的 handoff 约束。
4. 对 `console` 统一入口、`edge-agent`/`central-agent` 解耦、禁止原始 `pcap/payload` 上云等红线的尊重。
