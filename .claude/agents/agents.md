# Tanwei Agents Index

> Last synced: 2026-04-11  
> Scope: `console + edge-agent + central-agent` repository

## 1. 当前项目变更基线

- 第一阶段服务实现已打通：`console`、`edge-agent`、`central-agent` 均可独立运行并协同。
- `edge-agent` 检测完成后会写入 `meta.central_reporting`，上报失败不阻断边缘闭环。
- `console` 已支持单 Edge 历史报告浏览（`GET /api/edges/{edge_id}/reports`）与中心上报状态展示。
- `central-agent/tests/test_contract_governance.py` 已加入端云契约自动校验，覆盖真实 mapper 输出与 forbidden 字段红线。
- 当前剩余治理主线：
  - `TD-012` 多 Edge 实际联动与批量校验

## 2. 默认协作闭环

默认链路：

`lead-agent -> specialist -> evaluator-agent -> doc-gardener`

执行规则：

- 跨服务任务先进入 `lead-agent` 拆解。
- 方案不稳或需求发散时，先走 `brainstorm-architect`。
- 所有实现变更必须经过 `evaluator-agent` 独立验收。
- 行为/契约/计划变化必须进入 `doc-gardener` 做知识同步。

## 3. Agent 路由总表

| Agent | 主要 ownership | 明确不 owning |
| --- | --- | --- |
| `lead-agent` | 跨服务拆解、路由、验收口径、harness 治理 | 具体领域实现细节 |
| `brainstorm-architect` | 方案探索、优化扫描、问题重构 | 直接落地实现 |
| `edge-agent-engineer` | `edge-agent/` 编排与上报契约 | `central-agent/` 研判内部、`console/` 展示层 |
| `central-agent-engineer` | `central-agent/` 归档、单 Edge 分析、全网分析 | `edge-agent/` 检测内部、`console/` 交互 |
| `console-developer` | `console/` 管理员流与展示面 | 检测/研判内部推理实现 |
| `svm-filter-engineer` | `svm-filter-service/` 在线推理与加载路径 | 离线训练策略 |
| `llm-service-engineer` | `llm-service/` 推理服务与输出契约 | 业务编排 ownership |
| `detection-ml-engineer` | SVM 离线训练、特征工程、artifact 演进 | 在线 runtime serving |
| `traffic-security-analyst` | 流量语义判定、威胁标签解释 | 直接生产代码改动 |
| `data-scientist` | 实验设计、统计比较、数据分析 | 运行时部署/路由 ownership |
| `docker-expert` | Dockerfile/compose/部署 wiring | 业务逻辑实现 |
| `evaluator-agent` | 独立验收与证据审查 | 验收阶段改实现 |
| `doc-gardener` | 文档、计划、harness 一致性治理 | 脱离代码现实的架构发明 |

说明：`example-demo-agent` 仅用于范式示例，不承担生产 ownership。

## 4. 当前责任映射（第一阶段收口后）

- 第一阶段服务实现已完成，当前主责任转向治理与防漂移：
  - 文档与计划生命周期：`doc-gardener`
  - 契约自动校验维护：`central-agent-engineer` + `edge-agent-engineer`
  - 独立验收：`evaluator-agent`

## 5. 维护触发条件

发生以下任一变化时，必须同步更新本文件：

1. 新增/删除 agent，或 ownership 调整。
2. 服务拓扑、契约边界、默认工作流变化。
3. 执行计划里程碑切换导致责任映射变化。

同步时至少交叉检查：

- `CLAUDE.md`
- `.claude/agents/README.md`
- `docs/design-docs/agent-operating-model.md`
- `docs/references/agent-harness.md`
- `docs/references/harness-engineering.md`
- `docs/exec-plans/active-plan.md`
