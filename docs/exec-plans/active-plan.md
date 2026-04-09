---
name: active-plan
description: 当前里程碑执行计划（console + edge-agent + central-agent 第一阶段）
type: project
---

# 探微 (Tanwei) - 当前执行计划

## 里程碑：Console + Edge-Agent + Central-Agent 第一阶段

**目标**：完成三层架构收口，确保边缘独立可用与中心研判能力并存，同时守住带宽压降率 > 70% 的核心 KPI。

---

## 阶段目标

1. 命名与认知统一：`console / edge-agent / central-agent`。
2. 端云契约固化：`EdgeReportIn`（顶层字段 + 嵌套 `intel`）成为唯一上云对象。
3. 运行边界明确：单 Edge 可独立分析，全网综合研判仅手动触发。
4. 文档体系收口：architecture/api/deployment/harness 同步。

## 工作包状态

- [x] **WP-1 命名迁移**
  - `edge-test-console -> console`
  - `agent-loop -> edge-agent`

- [x] **WP-2 central-agent 服务骨架**
  - 已提供 `reports/edges/analyze` 基础 API
  - 已接入外部 LLM 推理组件（`EXTERNAL_LLM_*`）

- [x] **WP-3 edge-agent -> central-agent 上报打通**
  - central-agent 服务已落地：reports 接收归档、单 Edge 分析、全网分析 API
  - `EdgeReportIn`（顶层字段 + 嵌套 `intel`）契约已定义于 `central-agent/app/models.py`
  - SQLite 持久化存储已实现
  - 外部 LLM 集成已完成
  - edge-agent 检测完成后自动上报当前 `EdgeReportIn` 契约
  - 上报状态写入 `task.result.meta.central_reporting`
  - central-agent 不可用仅告警，不阻断边缘检测闭环完成

- [x] **WP-4 console 中心分析运营流**
  - console 后端 `central_client.py` 已实现 central-agent 代理层
  - Edge 列表查询 `/api/edges` 已实现
  - 单 Edge 最新报告 `/api/edges/{edge_id}/reports/latest` 已实现
  - 单 Edge 分析触发 `/api/edges/{edge_id}/analyze` 已实现
  - 全网综合研判 `/api/network/analyze` 已实现
  - 前端组件已模块化重构

- [ ] **WP-5 文档与 harness 收口**
  - 设计、接口、部署、agent 路由一致化
  - 清除旧名称与旧拓扑残留
  - 补充端云契约自动化 schema 检查

---

## 模块状态

| 模块 | 状态 | 说明 |
|------|------|------|
| `console/` | ✅ | 统一控制台（FastAPI + React） |
| `edge-agent/` | ✅ | 边缘检测五阶段工作流 |
| `central-agent/` | ✅ | 归档 + 单 Edge 分析 + 全网分析骨架 |
| `svm-filter-service/` | ✅ | 32 维特征在线过滤 |
| `llm-service/` | ✅ | 本地 llama.cpp 推理 |

## 当前红线提醒

- 禁止原始 pcap/payload 上云。
- 每个 Edge 必须可独立查询与独立分析。
- 全网综合研判必须手动触发。
- `console` 必须保持统一入口角色。
