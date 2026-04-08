---
name: agent-operating-model
description: Tanwei 项目的 console + edge-agent + central-agent 时代协作模型
type: project
---

# Agent Operating Model

## Why This Exists

本仓库在 `console + edge-agent + central-agent` 架构下组织 agent。目标是让跨端云任务可拆解、可交接、可验收，并避免职责重叠。

## Core Principle

- Humans steer. Agents execute.
- Repository knowledge is the system of record.
- Evaluation must be independent from implementation.
- Repeated failures should tighten the harness, not only trigger retries.
- 行为改变必须同步文档，尤其 architecture/api/deployment。

## Agent Layers

### Control Plane

- `lead-agent`: 总控，负责任务拆解、派工、验收标准、harness 维护
- `brainstorm-architect`: 方案探索、周期扫描、优化建议

### Execution Plane

- `edge-agent-engineer`
- `central-agent-engineer`
- `console-developer`
- `detection-ml-engineer`
- `svm-filter-engineer`
- `llm-service-engineer`
- `traffic-security-analyst`
- `data-scientist`
- `docker-expert`

### Evaluation Plane

- `evaluator-agent`: 独立验收，不 owning 实现

### Documentation Plane

- `doc-gardener`: 维护 repo 知识系统和计划生命周期

## Default Workflow

1. 用户任务默认先进入 `lead-agent`
2. `lead-agent` 明确 `task / scope / constraints / acceptance`
3. 如果需求发散或方案不稳，先调用 `brainstorm-architect`
4. 派发到对应执行 agent
5. 实现完成后交给 `evaluator-agent`
6. 通过后由 `doc-gardener` 更新知识库与计划状态
7. `lead-agent` 汇总并决定是否继续下一轮

## Service Ownership

| 路径/服务 | Owner | 边界说明 |
|------|------|------|
| `console/` | `console-developer` | 统一控制台与管理员交互，不 owning 检测/研判内部实现 |
| `edge-agent/` | `edge-agent-engineer` | 边缘检测闭环与上报契约，不 owning central 内部 |
| `central-agent/` | `central-agent-engineer` | 情报归档、单 Edge 分析、全网分析，不 owning边缘检测 |
| `svm-filter-service/` runtime | `svm-filter-engineer` | 在线过滤服务 |
| `svm-filter-service/models/` training | `detection-ml-engineer` | 训练数据、特征工程与模型演进 |
| `llm-service/` | `llm-service-engineer` | 边缘侧本地推理服务 |
| 多容器运行边界 | `docker-expert` | compose、依赖、资源与失败策略 |

## Required Task Packet

每个执行 agent 接单时都应具备最小输入：

- `task`: 要完成什么
- `scope`: 允许修改哪些目录或服务
- `constraints`: 架构、性能、依赖、安全红线
- `acceptance`: 什么证据算完成
- `contract_impact`: 是否影响 `EdgeIntelligenceReport` 或 central API

## Escalation Rules

- 跨多个服务或跨多个角色的任务，由 `lead-agent` 拆解
- 实现 agent 不得自我验收
- 行为改变但文档未更新，视为未完成
- 同类错误反复出现时，必须补充 harness，而不是继续裸重试
- 端云契约变更必须同步更新：
  - `docs/design-docs/architecture.md`
  - `docs/references/api_specs.md`
  - `docs/references/deployment.md`
