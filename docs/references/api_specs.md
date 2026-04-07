---
name: api-specs
description: console + edge-agent + central-agent 服务接口与端云 JSON 情报契约
type: reference
---

# 探微 (Tanwei) API 规范

## 1. 通信总览

```text
Client/Admin
  -> console (统一控制台, :3000 对外 / :8000 容器内)
      -> edge-agent (:8002)
          -> svm-filter-service (:8001)
          -> llm-service (:8080)
      -> central-agent (:8003)

edge-agent -> central-agent
  仅传 EdgeIntelligenceReport
```

核心约束：

- `console` 是唯一统一控制台入口。
- 每个 `edge_id` 必须支持独立分析。
- 全网综合研判仅允许手动触发。
- 禁止原始 `pcap/payload` 上云。

## 2. Console 对外 API（管理员入口）

### 2.1 检测与任务查询

#### POST `/api/detect`

上传 pcap 并发起检测任务（转发给 `edge-agent`）。

```http
POST /api/detect
Content-Type: multipart/form-data

file: <pcap|pcapng>
```

```json
{
  "status": "success",
  "task_id": "uuid-string",
  "message": "Detection task started"
}
```

#### POST `/api/detect-demo`

基于演示样本发起检测任务。

```json
{
  "sample_id": "dns-tunnel.pcapng"
}
```

#### GET `/api/demo-samples`

返回演示样本列表。

#### GET `/api/status/{task_id}`

返回控制台侧任务状态。

```json
{
  "task_id": "uuid-string",
  "status": "processing|completed|failed",
  "stage": "pending|flow_reconstruction|svm_filtering|llm_inference|completed|failed",
  "progress": 75,
  "message": "SVM 初筛丢弃正常流量"
}
```

#### GET `/api/result/{task_id}`

返回检测最终结果（来源于 `edge-agent` 结果）。

### 2.2 central-agent 代理 API

#### GET `/api/edges`

列出当前已知 `edge_id` 与最近状态（代理 central `/api/v1/edges`）。

#### GET `/api/edges/{edge_id}/reports/latest`

查看某个 Edge 最新归档报告。

#### GET `/api/edges/{edge_id}/analysis`

查看某个 Edge 最近一次已完成的中心侧分析。

#### POST `/api/edges/{edge_id}/analyze`

手动触发单 Edge 中心分析。

#### GET `/api/network/analysis`

查看最近一次已完成的全网综合研判结果。

#### POST `/api/network/analyze`

手动触发全网综合研判。

## 3. edge-agent API（边缘检测）

### 3.1 northbound（给 console）

- `POST /api/detect`
- `GET /api/status/{task_id}`
- `GET /api/result/{task_id}`
- `DELETE /api/task/{task_id}`
- `GET /health`

### 3.2 southbound（给内部推理服务）

#### edge-agent -> svm-filter-service

`POST /api/classify`

```json
{
  "features": {
    "avg_packet_len": 512.5,
    "std_packet_len": 128.3
  }
}
```

```json
{
  "prediction": 1,
  "label": "anomaly",
  "confidence": 0.87,
  "latency_ms": 0.15
}
```

#### edge-agent -> llm-service

`POST /completion`

```json
{
  "prompt": "...",
  "n_predict": 64,
  "temperature": 0.1
}
```

## 4. edge-agent -> central-agent 情报上报契约

### 4.1 上报端点

#### POST `/api/v1/reports`

用途：上报单份 `EdgeIntelligenceReport`。

行为：

- 以 `report_id` 做幂等覆盖写入。
- 按 `edge_id` 归档。
- 不自动触发全网综合研判。

成功响应：

```json
{
  "status": "stored",
  "storage_state": "available_for_analysis",
  "edge_id": "edge1",
  "report_id": "report-001"
}
```

### 4.2 EdgeIntelligenceReport 顶层结构

```json
{
  "schema_version": "v1",
  "report_id": "report-001",
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

字段约束：

- 顶层字段全部必填。
- `schema_version` 必填，供后续演进。
- `edge_id` 必填，作为单 Edge 独立分析主键。
- schema 采用 `extra=forbid`，未知字段会被拒绝。

### 4.3 威胁条目建议结构

```json
{
  "threat_id": "threat-001",
  "five_tuple": {
    "src_ip": "10.1.1.5",
    "dst_ip": "8.8.8.8",
    "src_port": 50123,
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
    "confidence": 0.91
  },
  "flow_metadata": {
    "packet_count": 8,
    "byte_count": 4120
  },
  "traffic_tokens": {
    "encoding": "TrafficLLM",
    "sequence": ["tok_184", "tok_033", "tok_912"],
    "token_count": 128,
    "truncated": true
  }
}
```

### 4.4 上云字段白名单/黑名单

白名单（允许）：

- 五元组
- SVM 初筛结果
- 边缘分类标签与置信度
- 流量统计元信息
- 压缩 token 序列与带宽压降指标

黑名单（禁止）：

- 原始 pcap、raw bytes、raw packet
- 原始 payload、payload hex
- `flow_text`
- prompt、stack trace、env 等敏感调试信息
- `progress/stage/message` 等过程态执行字段

## 5. central-agent API（中心归档与研判）

### 5.1 GET `/api/v1/edges`

返回 Edge 注册视图：

```json
{
  "edges": [
    {
      "edge_id": "edge1",
      "report_count": 3,
      "latest_report_id": "report-003",
      "latest_reported_at": "2026-04-07T12:10:00Z",
      "latest_analysis_status": "completed",
      "latest_threat_level": "high"
    }
  ]
}
```

### 5.2 GET `/api/v1/edges/{edge_id}/reports`

查看某个 Edge 历史归档。

```json
{
  "edge_id": "edge1",
  "reports": [
    {
      "schema_version": "v1",
      "report_id": "report-001",
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
  ]
}
```

### 5.3 GET `/api/v1/edges/{edge_id}/reports/latest`

查看某个 Edge 最新归档。

```json
{
  "schema_version": "v1",
  "report_id": "report-003",
  "edge_id": "edge1",
  "producer": {
    "service": "edge-agent",
    "agent_version": "1.0.0",
    "reported_at": "2026-04-07T12:10:00Z"
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

### 5.4 POST `/api/v1/edges/{edge_id}/analyze`

手动触发单 Edge 分析。

返回语义：

- `mode: single-edge`
- `edge_id`
- `threat_level`
- `summary`
- `analysis`
- `recommendations`
- `analysis_state`

示例响应：

```json
{
  "mode": "single-edge",
  "edge_id": "edge1",
  "threat_level": "high",
  "summary": "发现持续 C2 Beaconing 行为",
  "analysis": "该 Edge 在过去 3 份报告中持续命中相近目标与时序特征",
  "recommendations": [
    "隔离 edge1 相关主机",
    "核查出口 ACL 与 DNS 解析日志"
  ],
  "analysis_state": "completed"
}
```

### 5.5 GET `/api/v1/edges/{edge_id}/analysis`

查看最近一次已完成的单 Edge 分析结果；若该 Edge 尚未执行中心分析，则返回 `404`。

返回结构与 `POST /api/v1/edges/{edge_id}/analyze` 相同。

### 5.6 GET `/api/v1/network/analysis`

查看最近一次已完成的全网综合研判结果；若尚未执行全网研判，则返回 `404`。

返回结构与 `POST /api/v1/network/analyze` 相同。

### 5.7 POST `/api/v1/network/analyze`

手动触发全网综合研判（汇总多个 Edge 最新报告）。

该接口是手动触发入口，不会由上报流程自动触发。

返回语义：

- `mode: network-wide`
- `edge_count`
- `threat_level`
- `summary`
- `analysis`
- `recommendations`
- `analysis_state`

示例响应：

```json
{
  "mode": "network-wide",
  "edge_count": 3,
  "threat_level": "medium",
  "summary": "发现 edge1 与 edge3 存在可疑横向活动关联",
  "analysis": "多个 Edge 在相同时间窗命中相同外联目标，且 token 语义相近",
  "recommendations": [
    "对关联资产执行统一阻断策略",
    "手动复核受影响网段主机清单"
  ],
  "analysis_state": "completed"
}
```

## 6. 状态枚举

### 6.1 edge-agent task state

`pending | flow_reconstruction | svm_filtering | llm_inference | completed | failed`

### 6.2 central-agent storage state

`received | stored | available_for_analysis`

### 6.3 central-agent analysis state

- 单 Edge：`idle | analyzing_edge | completed | failed`
- 全网：`idle | analyzing_network | completed | failed`

## 7. 错误响应格式

统一错误结构：

```json
{
  "status": "error",
  "error_code": "TASK_NOT_FOUND",
  "message": "Task not found",
  "details": {}
}
```

推荐错误码：

| 错误码 | HTTP | 场景 |
|------|------|------|
| `INVALID_PCAP_FILE` | 400 | 上传格式非法 |
| `TASK_NOT_FOUND` | 404 | 任务不存在 |
| `EDGE_REPORT_NOT_FOUND` | 404 | 某 Edge 无归档 |
| `NO_EDGE_REPORTS` | 404 | 全网分析前无任何归档 |
| `FORBIDDEN_RAW_FIELD` | 400 | 上报含禁传字段 |
| `EXTERNAL_LLM_UNAVAILABLE` | 503 | central 外部 LLM 不可用 |
| `INTERNAL_ERROR` | 500 | 其他内部错误 |

## 8. 端口与暴露策略

| 服务 | 容器端口 | 对外策略 |
|------|------|------|
| `console` | 8000 | 映射为宿主 `3000`，唯一外部入口 |
| `edge-agent` | 8002 | 内网服务 |
| `central-agent` | 8003 | 内网服务 |
| `svm-filter-service` | 8001 | 内网服务 |
| `llm-service` | 8080 | 内网服务 |

## 9. 版本

- API version: `2.0.0`
- Updated at: `2026-04-07`
- Maintainer: Tanwei architecture team
