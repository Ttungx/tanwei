---
name: api-specs
description: console / edge-agent / central-agent API 规范
type: reference
---

# Tanwei API Specs

本文档统一使用以下命名：

- `console`: 管理员控制台，当前对应 `edge-test-console`
- `edge-agent`: 边缘检测闭环核心，当前由 `agent-loop` 编排本地检测
- `central-agent`: 云侧结构化情报归档与综合研判服务

## 1. 通信概览

```text
console ─────► edge-agent
console ─────► central-agent
edge-agent ──► central-agent
```

说明：

- `console -> edge-agent` 用于发起本地检测、查看边缘检测结果。
- `edge-agent -> central-agent` 用于上送结构化 JSON 情报报告。
- `console -> central-agent` 用于查看 `edge1`、`edge2` 等 edge 视图，以及触发单 edge 或全网综合研判。

## 2. 通用错误格式

所有服务错误响应统一使用：

```json
{
  "status": "error",
  "error_code": "ERROR_CODE",
  "message": "Human readable message"
}
```

常见错误码：

| error_code | HTTP | 说明 |
| --- | --- | --- |
| `INVALID_EDGE_REPORT` | 400 | Edge JSON 情报契约不合法 |
| `RAW_INTEL_FIELD_FORBIDDEN` | 400 | 上传内容包含原始载荷类字段 |
| `REPORT_ID_CONFLICT` | 409 | `report_id` 已存在 |
| `EDGE_REPORT_NOT_FOUND` | 404 | 指定 edge 没有历史报告 |
| `NETWORK_REPORTS_NOT_FOUND` | 404 | 指定网络范围内没有可分析报告 |
| `EXTERNAL_LLM_NOT_CONFIGURED` | 503 | central-agent 未配置外部大模型 |
| `EXTERNAL_LLM_UNAVAILABLE` | 503 | 外部大模型调用失败 |

## 3. console -> edge-agent

### 3.1 `POST /api/detect`

用途：上传 pcap 文件并启动边缘本地检测流程。

请求：

```http
POST /api/detect HTTP/1.1
Content-Type: multipart/form-data

file: <pcap_file>
```

响应：

```json
{
  "status": "success",
  "task_id": "uuid-string",
  "message": "Detection task started"
}
```

### 3.2 `GET /api/status/{task_id}`

用途：查询边缘检测任务状态。

响应：

```json
{
  "task_id": "uuid-string",
  "status": "processing|completed|failed",
  "stage": "flow_reconstruction|svm_filtering|llm_inference|completed",
  "progress": 75,
  "message": "LLM inference in progress"
}
```

### 3.3 `GET /api/result/{task_id}`

用途：读取边缘检测的结构化结果摘要。

响应示例：

```json
{
  "task_id": "uuid-string",
  "status": "completed",
  "summary": {
    "total_flows": 150,
    "normal_flows": 148,
    "anomaly_flows": 2,
    "bandwidth_reduction": "78.5%"
  },
  "anomaly_details": [
    {
      "five_tuple": {
        "src_ip": "192.168.1.100",
        "dst_ip": "10.0.0.1",
        "src_port": 54321,
        "dst_port": 443,
        "protocol": "TCP"
      },
      "label": "Malware",
      "confidence": 0.92,
      "timestamp": "2026-04-07T10:30:00Z"
    }
  ],
  "metrics": {
    "original_pcap_size": 1048576,
    "json_output_size": 225280,
    "bandwidth_saved_bytes": 823296,
    "bandwidth_reduction_percent": 78.5
  }
}
```

## 4. edge-agent -> central-agent

### 4.1 `POST /api/v1/reports`

用途：将某个 edge 的结构化 JSON 情报归档到 central-agent。

请求体是 Edge JSON 情报契约：

```json
{
  "edge_id": "edge1",
  "report_id": "rep-20260407-0001",
  "source": "edge-agent",
  "reported_at": "2026-04-07T10:30:00Z",
  "intel": {
    "schema_version": "edge-intel/v1",
    "summary": {
      "headline": "Suspicious outbound activity detected",
      "risk_level": "high"
    },
    "threats": [
      {
        "threat_id": "threat-001",
        "title": "Possible C2 beaconing",
        "severity": "high",
        "confidence": 0.92,
        "category": "command-and-control",
        "summary": "Repeated outbound callbacks to a rare destination.",
        "evidence": {
          "five_tuple": {
            "src_ip": "192.168.1.10",
            "src_port": 49231,
            "dst_ip": "203.0.113.8",
            "dst_port": 443,
            "protocol": "TCP"
          },
          "packet_count": 10,
          "byte_count": 5120
        }
      }
    ],
    "statistics": {
      "total_flows": 150,
      "anomalous_flows": 2
    },
    "metrics": {
      "processing_time_ms": 1250,
      "bandwidth_saved_percent": 78.5
    },
    "tags": ["site-a", "edge1", "high-priority"],
    "context": {
      "site_name": "branch-a",
      "model_version": "qwen3.5-0.8b",
      "window_start": "2026-04-07T10:29:00Z",
      "window_end": "2026-04-07T10:30:00Z"
    }
  }
}
```

成功响应：

```json
{
  "status": "stored",
  "report_id": "rep-20260407-0001",
  "edge_id": "edge1",
  "reported_at": "2026-04-07T10:30:00+00:00",
  "received_at": "2026-04-07T10:30:01+00:00"
}
```

### 4.2 Edge JSON 情报契约约束

允许字段：

- `edge_id`
- `report_id`
- `source`
- `reported_at`
- `intel.schema_version`
- `intel.summary`
- `intel.threats`
- `intel.statistics`
- `intel.metrics`
- `intel.tags`
- `intel.context`

禁止字段：

- 原始 `pcap`
- 原始 `payload`
- `payload_hex`
- `raw_payload`
- `flow_text`
- 语义等价变体，例如 `rawpacket`、`packet_hex`、`application_payload`

规则：

- central-agent 只接收结构化 JSON 情报，不接收原始包或应用层内容。
- 任意层级出现禁止字段都应返回 `400`。
- `edge_id` 视图采用显式命名，例如 `edge1`、`edge2`。

## 5. console -> central-agent

### 5.1 `GET /api/v1/edges`

用途：列出当前 central-agent 中已有归档的 edge 视图。

响应示例：

```json
{
  "edges": [
    {
      "edge_id": "edge1",
      "report_count": 5,
      "latest_reported_at": "2026-04-07T10:30:00+00:00",
      "latest_received_at": "2026-04-07T10:30:01+00:00"
    },
    {
      "edge_id": "edge2",
      "report_count": 3,
      "latest_reported_at": "2026-04-07T10:28:00+00:00",
      "latest_received_at": "2026-04-07T10:28:01+00:00"
    }
  ]
}
```

### 5.2 `GET /api/v1/edges/{edge_id}/reports`

用途：查看某个 edge 的历史报告。

查询参数：

- `limit`: 默认 `20`，范围 `1-100`

响应示例：

```json
{
  "edge_id": "edge1",
  "reports": [
    {
      "report_id": "rep-20260407-0001",
      "edge_id": "edge1",
      "source": "edge-agent",
      "reported_at": "2026-04-07T10:30:00+00:00",
      "received_at": "2026-04-07T10:30:01+00:00",
      "report": {
        "schema_version": "edge-intel/v1",
        "summary": {
          "headline": "Suspicious outbound activity detected"
        },
        "threats": [],
        "statistics": {},
        "metrics": {},
        "tags": ["edge1"],
        "context": {}
      }
    }
  ]
}
```

### 5.3 `GET /api/v1/edges/{edge_id}/reports/latest`

用途：查看某个 edge 的最新一份报告。

响应体与单个 `report` 对象一致。

### 5.4 `POST /api/v1/edges/{edge_id}/analyze`

用途：基于某个 edge 最近 N 份历史报告做单 edge 分析。

请求示例：

```json
{
  "question": "Summarize the most important risks and response priorities for this edge.",
  "instructions": "Prioritize actions for branch office responders.",
  "max_reports": 5
}
```

响应示例：

```json
{
  "analysis_id": "0a8f8b57-5c2a-4d37-b815-0d228f143739",
  "scope": "edge",
  "edge_id": "edge1",
  "edge_ids": ["edge1"],
  "analyzed_report_count": 5,
  "provider_response_id": "resp_123",
  "model": "gpt-4o-mini",
  "analysis": {
    "summary": "edge1 shows repeated outbound suspicious activity.",
    "findings": [
      "Likely beaconing behavior persisted across multiple reports."
    ],
    "recommended_actions": [
      "Isolate the affected host.",
      "Block the destination IP at the branch firewall."
    ],
    "confidence_notes": "Assessment is based only on structured edge intelligence."
  },
  "source_reports": [
    {
      "report_id": "rep-20260407-0001",
      "edge_id": "edge1",
      "reported_at": "2026-04-07T10:30:00+00:00",
      "source": "edge-agent"
    }
  ]
}
```

说明：

- 这是“每个 edge 可单独分析”的正式接口。
- 若 central-agent 未配置 `EXTERNAL_LLM_BASE_URL` 或 `EXTERNAL_LLM_API_KEY`，返回 `503`。

### 5.5 `POST /api/v1/network/analyze`

用途：管理员手动触发全网综合研判。

请求示例：

```json
{
  "edge_ids": ["edge1", "edge2"],
  "question": "Compare edges, identify correlated risks, and recommend network-wide response priorities.",
  "instructions": "Focus on shared indicators and the first three containment actions.",
  "max_reports_per_edge": 3
}
```

响应示例：

```json
{
  "analysis_id": "4e749462-d182-4efa-b9b9-5721c2cbb4a3",
  "scope": "network",
  "edge_id": null,
  "edge_ids": ["edge1", "edge2"],
  "analyzed_report_count": 6,
  "provider_response_id": "resp_456",
  "model": "gpt-4o-mini",
  "analysis": {
    "summary": "edge1 and edge2 exhibit overlapping suspicious outbound patterns.",
    "findings": [
      "Both edges reference the same destination cluster.",
      "The activity window overlaps by 15 minutes."
    ],
    "recommended_actions": [
      "Block shared infrastructure indicators centrally.",
      "Pull endpoint triage from both sites.",
      "Escalate to incident commander for coordinated response."
    ],
    "confidence_notes": "Cross-edge analysis is limited to uploaded structured JSON intelligence."
  },
  "source_reports": [
    {
      "report_id": "rep-edge1-001",
      "edge_id": "edge1",
      "reported_at": "2026-04-07T10:30:00+00:00",
      "source": "edge-agent"
    },
    {
      "report_id": "rep-edge2-001",
      "edge_id": "edge2",
      "reported_at": "2026-04-07T10:28:00+00:00",
      "source": "edge-agent"
    }
  ]
}
```

说明：

- 这是“管理员手动触发全网综合研判”的接口。
- `edge_ids` 为空时，central-agent 可以对当前已归档的全部 edge 进行聚合。
- 该接口不属于 edge-agent 本地自动检测链路，不应成为边缘站点运行前提。

## 6. 健康检查

### `GET /health`

central-agent 响应示例：

```json
{
  "status": "healthy",
  "service": "central-agent",
  "version": "1.0.0",
  "external_llm_configured": true
}
```

说明：

- `external_llm_configured=false` 不代表服务不可用，只表示分析接口会返回 `503`。
- 报告归档、edge 列表查询、历史报告查询仍应正常工作。
