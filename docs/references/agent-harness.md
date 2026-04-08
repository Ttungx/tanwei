---
name: agent-harness
description: Tanwei 在 console + edge-agent + central-agent 架构下的 agent 路由与交付闭环
type: reference
---

# Agent Harness Guide

## 1. Purpose

本文件定义仓库内 Claude Code agents 的执行协作规则，重点保障三层架构下的职责清晰与交付闭环。

默认闭环：

`lead-agent -> specialist -> evaluator-agent -> doc-gardener`

## 2. Entry Rule

- 默认入口是 `lead-agent`。
- 仅在任务天然单域时可直接点名 specialist。
- 跨 `console/edge-agent/central-agent` 的需求必须先拆解再派发。

## 3. Routing Matrix

| 场景 | 默认 agent |
|------|------|
| 跨服务拆解、优先级、验收口径 | `lead-agent` |
| 架构探索、方案比较、阶段复盘 | `brainstorm-architect` |
| `edge-agent/` 边缘检测与上报契约 | `edge-agent-engineer` |
| `central-agent/` 归档、单 Edge 分析、全网研判 | `central-agent-engineer` |
| `console/` 统一控制台与代理接口 | `console-developer` |
| `svm-filter-service/` 在线推理 | `svm-filter-engineer` |
| 特征工程、训练评估 | `detection-ml-engineer` |
| `llm-service/` 推理服务 | `llm-service-engineer` |
| 流量语义、攻击分析 | `traffic-security-analyst` |
| 实验统计与对比 | `data-scientist` |
| compose/Docker 运行边界 | `docker-expert` |
| 独立验收 | `evaluator-agent` |
| 文档/计划维护 | `doc-gardener` |

## 4. Ownership Contract

### 4.1 edge-agent-engineer

- owns `edge-agent/`
- owns `edge-agent -> central-agent` 情报上报契约
- does not own `central-agent/` 推理内部实现

### 4.2 central-agent-engineer

- owns `central-agent/`
- owns Edge 归档、单 Edge 分析、全网综合研判接口
- does not own `edge-agent/` 检测内部实现

### 4.3 console-developer

- owns `console/`
- owns 统一控制台管理员流程与代理接口
- does not own detection/central reasoning internals

## 5. Mandatory Handoffs

1. 所有实现变更必须进入 `evaluator-agent`。
2. 影响接口、架构、计划或知识库的变更必须进入 `doc-gardener`。
3. `brainstorm-architect` 的方案输出必须回到 `lead-agent` 做取舍与落地决策。

## 6. Required Task Packet

每个 specialist 接单时最少应有：

- `task`: 具体交付目标
- `scope`: 可改目录/服务
- `constraints`: 红线（禁止原始 pcap/payload 上云等）
- `acceptance`: 完成证据
- `contract_impact`: 是否影响 `EdgeIntelligenceReport` 或 central `/api/v1/*`

## 7. Acceptance Expectations

验收证据必须 repo 可见：

- 关键接口行为或命令输出摘要
- 契约变化与兼容性说明
- 文档同步（architecture/api/deployment 至少之一）
- 已知风险与后续建议

## 8. Harness Maintenance Rules

- `CLAUDE.md` 只保留地图和红线，不膨胀成巨型手册。
- 设计边界放 `docs/design-docs/`。
- 计划与技术债放 `docs/exec-plans/`。
- 可执行手册放 `docs/references/`。
- agent 角色与触发规则放 `.claude/agents/`。

## 9. Red-Line Reminders

- 禁止把原始 pcap/payload/完整十六进制包上传到 `central-agent`。
- 每个 Edge 必须能独立查询与独立分析。
- 全网综合研判必须手动触发，不能由上报自动拉起。
- `console` 是统一控制台入口，不允许旁路调用破坏治理边界。
