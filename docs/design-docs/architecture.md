---
name: architecture
description: console + edge-agent + central-agent 协同架构与端云契约边界
type: project
---

# Console + Edge-Agent + Central-Agent 架构规范

## 1. 逻辑拓扑

```
console (统一控制台)
  ├─► edge-agent (边缘检测智能体)
  │     ├─► svm-filter-service
  │     └─► llm-service
  └─► central-agent (中心智能体)

edge-agent ──► central-agent
  仅传输 EdgeIntelligenceReport（结构化高压缩 JSON 情报）
  禁止传输原始 pcap/payload/完整十六进制包
```

## 2. 三层平面

- `console`：控制平面（管理员入口、统一操作与查看）
- `edge-agent`：边缘数据平面（本地检测闭环）
- `central-agent`：中心认知平面（跨边缘归档与研判）

## 3. 服务职责边界

### 3.1 console（统一控制台）

Owned:

- 统一管理员入口
- 浏览多个 `edge_id` 的情报与状态
- 手动触发单 Edge 中心分析
- 手动触发全网综合研判

Not owned:

- 流量检测流程实现
- 边缘特征/分类推理实现
- 中心推理模型内部实现

### 3.2 edge-agent（边缘检测智能体）

Owned:

- 本地 pcap 处理、五元组重组、双重截断
- 调用 `svm-filter-service` 与本地 `llm-service`
- 生成终态结构化情报（`EdgeIntelligenceReport`）
- 按 `edge_id` 上报到 `central-agent`

Not owned:

- 跨 Edge 综合研判
- 管理员全局视图
- 中心归档策略

### 3.3 central-agent（中心智能体）

Owned:

- 接收并归档多个 `edge_id` 的情报
- 为单个 `edge_id` 提供中心侧分析
- 提供手动触发的全网综合研判
- 通过外部 LLM 输出可读结论

Not owned:

- 重新执行边缘检测
- 接收原始 pcap/payload
- console 展示层

## 4. 通信 Allowlist / Denylist

### 4.1 Allowlist

| 调用链 | 状态 | 说明 |
|------|------|------|
| `console -> edge-agent` | ✅ | 检测任务提交、状态查询、结果查看 |
| `edge-agent -> svm-filter-service` | ✅ | 边缘侧初筛 |
| `edge-agent -> llm-service` | ✅ | 边缘侧分类 |
| `edge-agent -> central-agent` | ✅ | 上报结构化情报 |
| `console -> central-agent` | ✅ | Edge 列表、报告查询、分析触发 |

### 4.2 Denylist

| 调用链/数据 | 状态 | 原因 |
|------|------|------|
| `console -> svm-filter-service` | ❌ | 绕过边缘治理边界 |
| `console -> llm-service` | ❌ | 绕过边缘治理边界 |
| `central-agent <- raw pcap/payload` | ❌ | 隐私与带宽红线 |
| `central-agent` 自动触发全网分析 | ❌ | 第一阶段明确手动触发 |

## 5. 端云 JSON 情报契约（当前实现）

当前 `central-agent` 接收的是 `EdgeReportIn`，顶层结构为：

- `edge_id`
- `report_id`
- `source`
- `reported_at`
- `intel`

其中 `intel` 为结构化情报主体，当前真实字段包括：

- `schema_version`
- `summary`
- `threats`
- `statistics`
- `metrics`
- `tags`
- `context`

### 5.2 字段白名单（允许上云）

- 五元组
- SVM 结果（label/confidence）
- 边缘分类标签与置信度
- 流量元信息（包数、字节数、时间窗）
- 压缩后 traffic token 序列
- 带宽压降统计

### 5.3 字段黑名单（禁止上云）

- 原始 pcap 二进制
- 原始 payload
- 完整十六进制包内容
- `flow_text`
- 边缘 prompt 或模型全文输出
- 本地路径、内部 URL、环境变量、异常栈
- 过程态字段：`progress`、`stage`、`message`

## 6. 状态边界

### 6.1 edge-agent task state

`pending | flow_reconstruction | svm_filtering | llm_inference | completed | failed`

### 6.2 central-agent archive / analysis boundary

- 报告归档响应与分析响应是两类不同 contract
- 归档接口返回存储结果
- 单 Edge 分析与全网分析直接返回分析结果对象

规则：

- 边缘检测态与中心分析态必须解耦
- 单 Edge 分析请求与全网分析请求必须解耦
- `console` 只展示状态，不创造独立业务状态

## 7. 失败隔离策略

- 某个 `edge-agent` 任务失败，只影响该边缘任务
- `edge-agent -> central-agent` 上报失败，不得阻断边缘闭环完成
- `central-agent` 单 Edge 分析失败，不得破坏已归档报告
- `central-agent` 全网分析失败，不得影响单 Edge 查询与分析

## 8. 第一阶段守则

- `console` 是唯一统一控制台
- 每个 Edge 可独立完成分析与查看
- 全网综合研判只允许管理员手动触发
- 严禁原始 pcap/payload 上云
