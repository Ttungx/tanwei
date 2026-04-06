---
name: agent-operating-model
description: Tanwei 项目的 Claude Code agent 分层、职责边界与闭环
type: project
---

# Agent Operating Model

## Why This Exists

本仓库采用 Harness Engineering 思路组织 Claude Code agent。目标不是堆更多人设，而是把任务拆解、执行、评估、文档化做成一个稳定闭环。

## Core Principle

- Humans steer. Agents execute.
- Repository knowledge is the system of record.
- Evaluation must be independent from implementation.
- Repeated failures should tighten the harness, not only trigger retries.

## Agent Layers

### Control Plane

- `lead-agent`: 总控，负责任务拆解、派工、验收标准、harness 维护
- `brainstorm-architect`: 方案探索、周期扫描、优化建议

### Execution Plane

- `agent-loop-engineer`
- `detection-ml-engineer`
- `svm-filter-engineer`
- `llm-service-engineer`
- `traffic-security-analyst`
- `data-scientist`
- `frontend-developer`
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

## Required Task Packet

每个执行 agent 接单时都应具备以下最小输入：

- `task`: 要完成什么
- `scope`: 允许修改哪些目录或服务
- `constraints`: 架构、性能、依赖、安全红线
- `acceptance`: 什么证据算完成

## Service Ownership

- `edge-test-console/`: `frontend-developer`
- `agent-loop/`: `agent-loop-engineer`
- `svm-filter-service/` runtime: `svm-filter-engineer`
- `svm-filter-service/models/` training side: `detection-ml-engineer`
- `llm-service/`: `llm-service-engineer`
- multi-container runtime: `docker-expert`

## Escalation Rules

- 跨多个服务或跨多个角色的任务，由 `lead-agent` 拆解
- 实现 agent 不得自我验收
- 行为改变但文档未更新，视为未完成
- 同类错误反复出现时，必须补充 harness，而不是继续裸重试
