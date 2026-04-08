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
2. 端云契约固化：`EdgeIntelligenceReport` 成为唯一上云对象。
3. 运行边界明确：单 Edge 可独立分析，全网综合研判仅手动触发。
4. 文档体系收口：architecture/api/deployment/harness 同步。

## 工作包状态

- [x] **WP-1 命名迁移**
  - `edge-test-console -> console`
  - `agent-loop -> edge-agent`

- [x] **WP-2 central-agent 服务骨架**
  - 已提供 `reports/edges/analyze` 基础 API
  - 已接入外部 LLM 推理组件（`EXTERNAL_LLM_*`）

- [ ] **WP-3 edge-agent -> central-agent 上报打通**
  - 将边缘终态结果映射为 `EdgeIntelligenceReport`
  - 增加上报失败不阻断边缘完成的策略

- [ ] **WP-4 console 中心分析运营流**
  - 单 Edge 查询/分析流程完善
  - 全网手动综合研判交互完善

- [ ] **WP-5 文档与 harness 收口**
  - 设计、接口、部署、agent 路由一致化
  - 清除旧名称与旧拓扑残留

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
