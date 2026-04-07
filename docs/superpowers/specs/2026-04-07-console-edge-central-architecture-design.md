---
name: console-edge-central-architecture-design
description: 第一阶段将 edge-only 仓库重构为 console + edge-agent + central-agent 协同架构的设计规格
type: project
---

# Console + Edge-Agent + Central-Agent Architecture Design

> 第一阶段设计规格。目标是在不破坏当前边缘检测闭环的前提下，引入中心智能体与统一控制台，并持续死守“核心网上行带宽占用降低 70% 以上”的硬性物理 KPI。

---

## 1. Goal

将当前以 `agent-loop` 和 `edge-test-console` 为核心的单边缘仿真仓库，重构为更清晰的三层系统：

- `console`：整个项目的统一控制台
- `edge-agent`：边缘侧检测智能体，负责本地流量分析和高压缩情报生产
- `central-agent`：中心侧智能体，负责多 Edge 情报归档、单 Edge 分析、全网综合研判

第一阶段只完成架构、命名、契约、sub-agent/harness 和文档系统设计，不要求真实端到端联调闭环。

## 2. Scope

### In Scope

- 将 `agent-loop` 统一改名为 `edge-agent`
- 将 `edge-test-console` 统一改名为 `console`
- 定义 `central-agent` 的职责、接口与运行边界
- 定义 `edge-agent -> central-agent` 的结构化情报契约
- 定义 `console -> edge-agent` 与 `console -> central-agent` 的控制关系
- 定义新的 sub-agent roster、ownership 和 handoff
- 同步更新架构、API、部署和 harness 文档

### Out of Scope

- 真实多 Edge 联调
- 自动实时全网研判
- 定时批处理调度
- 消息队列、复杂数据库、分布式任务系统
- 复杂权限系统
- 将原始 Pcap、原始 payload 或完整十六进制包上送中心侧

## 3. Architecture

### 3.1 Logical Topology

第一阶段的目标拓扑如下：

```text
console -> edge-agent -> svm-filter-service / llm-service
console -> central-agent
edge-agent -> central-agent   (仅上报结构化情报，不上报原始证据)
```

### 3.2 Control Plane vs Data Plane

- `console` 属于控制平面，只负责管理员操作、查看结果和触发分析
- `edge-agent` 属于边缘数据平面，负责本地检测闭环
- `central-agent` 属于中心认知平面，负责跨 Edge 情报理解与综合分析

### 3.3 Hard Red Lines

- `edge-agent -> central-agent` 绝对禁止发送原始 Pcap 二进制
- 绝对禁止发送原始应用层 payload
- 绝对禁止发送完整包十六进制、边缘侧原始 prompt、内部模型路径、环境变量或异常栈
- `central-agent` 绝对不能本地加载巨型模型，只能通过 `.env` 中的 Base URL 和 API Key 调用外部大模型
- `edge-agent` 本地检测闭环不得因 `central-agent` 不可用而失败

## 4. Service Responsibilities

### 4.1 console

`console` 是整个系统的统一控制台，而不是单纯的边缘测试页面。

Owned responsibilities:

- 管理员入口
- 查看多个 `edge_id` 的上报结果
- 查看 `central-agent` 生成的单 Edge 分析结果
- 手动触发单 Edge 分析
- 手动触发全网综合研判

Not owned:

- 流量检测实现
- 边缘情报生成
- 中心侧大模型推理实现

### 4.2 edge-agent

`edge-agent` 是边缘侧检测智能体，代表每个边缘节点自己的本地分析器。

Owned responsibilities:

- 接收本地 Pcap
- 五元组重组与双重截断
- 调用 `svm-filter-service`
- 调用本地 `llm-service`
- 生成终态结构化情报
- 将情报按 `edge_id` 上报给 `central-agent`

Not owned:

- 跨 Edge 汇总分析
- 中心归档
- 管理员全局视图

### 4.3 central-agent

`central-agent` 是中心侧智能体，不重跑边缘检测，而是消费边缘侧输出的结构化情报。

Owned responsibilities:

- 接收多个 `edge_id` 的情报上报
- 按 `edge_id` 归档情报
- 对某个 `edge_id` 单独做中心侧分析
- 对多个 `edge_id` 做手动触发的全网综合研判
- 调用外部大模型生成管理员可读结论

Not owned:

- 本地 Pcap 分析
- 边缘检测阶段流转
- `console` 展示层

## 5. Intelligence Contract

### 5.1 Contract Principle

`central-agent` 只接收 `edge-agent` 的终态结构化情报报告，而不是中间执行状态。

推荐上报对象名称：

- `EdgeIntelligenceReport`

### 5.2 Top-Level Shape

```json
{
  "schema_version": "v1",
  "report_id": "task-uuid",
  "edge_id": "edge1",
  "producer": {
    "service": "edge-agent",
    "agent_version": "1.0.0",
    "reported_at": "2026-04-07T12:00:00Z"
  },
  "analysis_constraints": {
    "max_time_window_s": 60,
    "max_packet_count": 10,
    "max_token_length": 690
  },
  "meta": {},
  "statistics": {},
  "threats": [],
  "metrics": {}
}
```

Required rules:

- `edge_id` is mandatory, e.g. `edge1`, `edge2`
- `report_id` is the idempotency and trace key
- `schema_version` is mandatory for future evolution
- `meta/statistics/threats/metrics` should reuse the current edge result skeleton wherever possible

### 5.3 Threat Entry Shape

每条威胁情报建议具备下列语义层：

- `five_tuple`
- `svm_result`
- `edge_classification`
- `flow_metadata`
- `traffic_tokens`

推荐结构：

```json
{
  "threat_id": "threat-001",
  "five_tuple": {
    "src_ip": "10.1.1.5",
    "dst_ip": "8.8.8.8",
    "src_port": 51514,
    "dst_port": 443,
    "protocol": "TCP"
  },
  "svm_result": {
    "label": "anomaly",
    "confidence": 0.87
  },
  "edge_classification": {
    "primary_label": "Botnet",
    "secondary_label": "C2 Beaconing",
    "confidence": 0.91,
    "model": "edge-llm"
  },
  "flow_metadata": {
    "start_time": "2026-04-07T11:59:00Z",
    "end_time": "2026-04-07T11:59:08Z",
    "packet_count": 8,
    "byte_count": 4120,
    "avg_packet_size": 515.0
  },
  "traffic_tokens": {
    "encoding": "TrafficLLM",
    "sequence": ["tok_184", "tok_033", "tok_912"],
    "token_count": 128,
    "truncated": true
  }
}
```

### 5.4 Allowed and Forbidden Fields

Allowed:

- 五元组
- SVM 初筛结果
- 边缘侧小模型标签
- 流量元信息
- 压缩后的 TrafficLLM token 序列
- 带宽压降相关统计

Forbidden:

- 原始 Pcap 二进制
- 原始 payload
- 完整十六进制包内容
- `flow_text`
- 边缘侧 prompt
- 边缘侧模型全文响应
- 本地路径、上传文件名、内部服务 URL、环境变量、异常栈
- `progress`, `stage`, `message` 这类执行过程字段

## 6. central-agent API Design

### 6.1 Edge Report Ingestion

`POST /api/v1/reports`

Purpose:

- `edge-agent` 上报一份 `EdgeIntelligenceReport`

Behavior:

- 幂等写入
- 按 `edge_id` 归档
- 不自动触发全网综合研判

### 6.2 Edge Registry View

`GET /api/v1/edges`

Purpose:

- `console` 获取当前已知 `edge_id` 列表及其最近状态

Recommended output:

- `edge_id`
- latest report timestamp
- report count
- latest single-edge analysis status

### 6.3 Edge Report View

- `GET /api/v1/edges/{edge_id}/reports`
- `GET /api/v1/edges/{edge_id}/reports/latest`

Purpose:

- 查看某个 Edge 的历史归档和最新归档

### 6.4 Single-Edge Analysis

`POST /api/v1/edges/{edge_id}/analyze`

Purpose:

- 管理员手动触发某个 `edge_id` 的中心侧分析

Behavior:

- 读取该 `edge_id` 已归档情报
- 调用外部大模型
- 生成中心侧单 Edge 分析结论

Expected output semantics:

- threat level
- key findings
- attack path interpretation
- remediation suggestions

### 6.5 Network-Wide Analysis

`POST /api/v1/network/analyze`

Purpose:

- 管理员手动触发全网综合研判

Behavior:

- 汇总多个 `edge_id` 的已归档情报
- 调用外部大模型做中心侧综合分析
- 生成全网威胁态势、跨 Edge 关联与处置建议

This endpoint is:

- manual
- non-incremental
- not automatically triggered by ingestion

## 7. State Boundaries

状态必须分三层：

- `edge-agent` task state
- `central-agent` storage state
- `central-agent` analysis state

### 7.1 edge-agent State

Examples:

- `pending`
- `flow_reconstruction`
- `svm_filtering`
- `llm_inference`
- `completed`
- `failed`

### 7.2 central-agent Storage State

Examples:

- `received`
- `stored`
- `available_for_analysis`

### 7.3 central-agent Analysis State

Single-edge analysis:

- `idle`
- `analyzing_edge`
- `completed`
- `failed`

Network-wide analysis:

- `idle`
- `analyzing_network`
- `completed`
- `failed`

Rule:

- 边缘检测状态不等于中心分析状态
- 单 Edge 分析状态不等于全网综合研判状态
- `console` 只展示状态，不创造独立业务状态

## 8. Failure Policy

- `edge-agent` 本地检测失败，只影响当前 Edge 任务
- `edge-agent -> central-agent` 上报失败，不得影响边缘闭环完成
- `central-agent` 单 Edge 分析失败，不得破坏已归档原始情报
- `central-agent` 全网综合研判失败，不得影响单 Edge 归档和查看

Core rule:

- storage and analysis must be decoupled
- edge detection and central analysis must be decoupled

## 9. Naming and Path Migration

第一阶段推荐将命名统一落实到 repo 路径，而不仅仅是文档称呼：

- `edge-test-console/ -> console/`
- `agent-loop/ -> edge-agent/`

Reason:

- 避免文档、目录、agent roster 三套名称并存
- 降低后续 agent routing 与文档治理成本

## 10. Sub-Agent and Harness Changes

### 10.1 Recommended Agent Roster

新增/改名后的关键执行 agent：

- `edge-agent-engineer.md`
- `central-agent-engineer.md`
- `console-developer.md`

### 10.2 Existing Agents to Update

- `lead-agent.md`
- `docker-expert.md`
- `evaluator-agent.md`
- `doc-gardener.md`
- `.claude/agents/README.md`

### 10.3 Ownership Summary

`edge-agent-engineer`

- owns `edge-agent/`
- owns edge-side contracts to `svm-filter-service`, `llm-service`, and `central-agent`
- does not own `central-agent/` internals or `console/`

`central-agent-engineer`

- owns `central-agent/`
- owns report ingestion, edge archive, single-edge analysis, network-wide analysis, and external LLM integration
- does not own `edge-agent/` internals or `console/`

`console-developer`

- owns `console/`
- owns administrator flows for edge browsing and analysis triggering
- does not own detection or central reasoning internals

### 10.4 Default Handoff

Default path remains:

`lead-agent -> specialist -> evaluator-agent -> doc-gardener`

Typical specialist set for this redesign:

- `edge-agent-engineer`
- `central-agent-engineer`
- `console-developer`
- `docker-expert` when deployment assets change

## 11. Documentation Changes

### 11.1 Documents That Must Be Updated

- `CLAUDE.md`
- `docs/design-docs/architecture.md`
- `docs/references/api_specs.md`
- `docs/references/deployment.md`
- `docs/design-docs/agent-operating-model.md`
- `docs/references/agent-harness.md`
- `.claude/agents/README.md`

### 11.2 Required Documentation Outcomes

`CLAUDE.md`

- 地图级命名更新为 `console / edge-agent / central-agent`
- 增加端云契约变更必须同步 architecture/api/deployment 的规则

`architecture.md`

- 从“四容器拓扑”升级为 “console + edge-agent + central-agent” 协同架构
- 明确数据面与控制面区别
- 明确端云 allowlist/denylist

`api_specs.md`

- 修复当前 edge result schema 漂移
- 新增 `console -> edge-agent`
- 新增 `console -> central-agent`
- 新增 `edge-agent -> central-agent`

`deployment.md`

- 记录 `central-agent` 的外部 LLM 依赖、环境变量、运行模式和失败策略

`agent-operating-model.md`

- 将 service ownership 改为 `console / edge-agent / central-agent`

## 12. Implementation Packaging

第一阶段后续实现建议拆成 5 个工作包：

1. 命名与目录迁移
2. `central-agent` 服务骨架
3. `edge-agent` 端云契约接入
4. `console` 控制台重构
5. 文档与 harness 收口

## 13. Non-Goals for This Phase

- 自动实时全网研判
- 定时调度批处理
- 真实多 Edge 联调
- 消息队列
- 复杂权限系统
- 大规模数据库抽象扩展

## 14. Final Design Summary

第一阶段完成后，仓库应表达出如下真实结构：

- `console` 是统一控制台
- `edge-agent` 是边缘侧检测智能体
- `central-agent` 是中心侧汇聚与综合研判智能体
- 每份边缘情报必须带 `edge_id`
- `central-agent` 同时支持单 Edge 分析与手动触发的全网综合研判
- 端云之间只传高压缩结构化情报，绝不传原始 Pcap 和原始载荷
