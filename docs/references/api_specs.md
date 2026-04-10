---
name: api-specs
description: console + edge-agent + central-agent 服务接口与当前实现契约
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
  仅传结构化 JSON 情报
```

核心约束：

- `console` 是唯一统一控制台入口。
- `console` 不得绕过 `edge-agent` 直接调用 `svm-filter-service` / `llm-service`。
- `edge-agent -> central-agent` 禁止上传原始 `pcap/payload/raw bytes/packet hex`。
- 全网综合研判仅允许手动触发。
- `central-agent` 不可用时，不得阻断边缘检测闭环完成。

## 2. Console 对外 API

### 2.1 检测工作台

#### POST `/api/detect`

上传 `pcap/pcapng` 并转发给 `edge-agent`。

```json
{
  "status": "success",
  "task_id": "uuid-string",
  "message": "Detection task started"
}
```

#### POST `/api/detect-demo`

基于演示样本发起检测。

请求：

```json
{
  "sample_id": "dns-tunnel.pcapng"
}
```

#### GET `/api/demo-samples`

返回演示样本列表：

```json
[
  {
    "id": "dns-tunnel.pcapng",
    "filename": "dns-tunnel.pcapng",
    "display_name": "Dns Tunnel",
    "size_bytes": 524288
  }
]
```

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

返回检测最终结果：

```json
{
  "meta": {
    "task_id": "uuid-string",
    "timestamp": "2026-04-08T10:00:00Z",
    "agent_version": "edge-agent-v1",
    "processing_time_ms": 1250,
    "central_reporting": {
      "status": "stored",
      "report_id": "uuid-string"
    }
  },
  "statistics": {
    "total_packets": 1500,
    "total_flows": 150,
    "normal_flows_dropped": 148,
    "anomaly_flows_detected": 2,
    "svm_filter_rate": "98.7%",
    "bandwidth_reduction": "78.5%"
  },
  "threats": [],
  "metrics": {
    "original_pcap_size_bytes": 1048576,
    "json_output_size_bytes": 225280,
    "bandwidth_saved_percent": 78.5
  }
}
```

### 2.2 central-agent 代理 API

`console/backend/app/central_client.py` 会把 `central-agent` 的归档 / 分析结果适配成前端消费的 view model。

#### GET `/api/edges`

返回控制面 Edge 列表：

```json
[
  {
    "edge_id": "edge1",
    "display_name": "Edge1",
    "status": "online",
    "location": "Central Archive",
    "last_reported_at": "2026-04-08T10:00:00Z",
    "threat_count": 2,
    "risk_level": "medium"
  }
]
```

#### GET `/api/edges/{edge_id}/reports/latest`

返回控制台展示使用的最新 Edge 情报摘要：

```json
{
  "edge_id": "edge1",
  "report_id": "report-001",
  "generated_at": "2026-04-08T10:00:00Z",
  "summary": {
    "headline": "2 threats detected on edge1",
    "risk_level": "medium",
    "threat_count": 2,
    "bandwidth_saved_percent": 78.5
  },
  "report": {
    "meta": {
      "task_id": "report-001",
      "timestamp": "2026-04-08T10:00:00Z",
      "agent_version": "edge-agent",
      "processing_time_ms": 0
    },
    "statistics": {
      "total_packets": 0,
      "total_flows": 2,
      "normal_flows_dropped": 0,
      "anomaly_flows_detected": 2,
      "svm_filter_rate": "0.0%",
      "bandwidth_reduction": "78.5%"
    },
    "threats": [],
    "metrics": {
      "original_pcap_size_bytes": 0,
      "json_output_size_bytes": 0,
      "bandwidth_saved_percent": 78.5
    }
  }
}
```

#### GET `/api/edges/{edge_id}/reports`

返回单个 Edge 的历史归档报告列表。返回值为数组，元素字段形状与 `/api/edges/{edge_id}/reports/latest` 一致，用于前端归档页历史切换。

```json
[
  {
    "edge_id": "edge1",
    "report_id": "report-002",
    "generated_at": "2026-04-08T10:00:00Z",
    "summary": {
      "headline": "2 threats detected on edge1",
      "risk_level": "medium",
      "threat_count": 2,
      "bandwidth_saved_percent": 78.5
    },
    "report": {
      "meta": {
        "task_id": "report-002",
        "timestamp": "2026-04-08T10:00:00Z",
        "agent_version": "edge-agent",
        "processing_time_ms": 0,
        "central_reporting": {
          "status": "stored",
          "report_id": "report-002"
        }
      },
      "statistics": {
        "total_packets": 0,
        "total_flows": 2,
        "normal_flows_dropped": 0,
        "anomaly_flows_detected": 2,
        "svm_filter_rate": "0.0%",
        "bandwidth_reduction": "78.5%"
      },
      "threats": [],
      "metrics": {
        "original_pcap_size_bytes": 0,
        "json_output_size_bytes": 0,
        "bandwidth_saved_percent": 78.5
      }
    }
  }
]
```

#### POST `/api/edges/{edge_id}/analyze`

手动触发单 Edge 中心分析；控制台返回值仍适配为 `EdgeLatestReport` 风格的展示对象。

#### POST `/api/network/analyze`

手动触发全网综合研判；控制台返回值适配为展示摘要：

```json
{
  "analysis_id": "uuid-string",
  "generated_at": "2026-04-08T10:05:00Z",
  "summary": {
    "edge_count": 2,
    "edges_with_alerts": 1,
    "total_threats": 3,
    "highest_risk_edge": "edge1",
    "recommended_action": "Review edge1 via central-agent"
  },
  "edges": [
    {
      "edge_id": "edge1",
      "display_name": "Edge1",
      "threat_count": 3,
      "risk_level": "high",
      "generated_at": "2026-04-08T10:00:00Z"
    }
  ]
}
```

## 3. edge-agent API

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

#### edge-agent -> llm-service

`POST /completion`

```json
{
  "prompt": "...",
  "n_predict": 64,
  "temperature": 0.1
}
```

## 4. edge-agent -> central-agent 归档契约

### 4.1 上报端点

#### POST `/api/v1/reports`

请求体为当前实现的 `EdgeReportIn`。当前线上契约为顶层 `edge_id / report_id / source / reported_at` + 嵌套 `intel`，旧的平铺字段描述已归档不再使用：

```json
{
  "edge_id": "edge1",
  "report_id": "task-20260409-0001",
  "source": "edge-agent",
  "reported_at": "2026-04-09T10:12:30Z",
  "intel": {
    "schema_version": "edge-intel/v1",
    "summary": {
      "headline": "2 threat(s) detected on edge1",
      "risk_level": "medium",
      "threat_count": 2
    },
    "threats": [
      {
        "threat_id": "threat-001",
        "title": "Suspicious DNS beacon",
        "severity": "medium",
        "confidence": 0.78,
        "category": "command-and-control",
        "summary": "Edge-detected suspicious flow",
        "evidence": {
          "five_tuple": {
            "src_ip": "192.168.1.10",
            "src_port": 49231,
            "dst_ip": "203.0.113.8",
            "dst_port": 53,
            "protocol": "UDP"
          },
          "flow_metadata": {
            "packet_count": 18,
            "byte_count": 2048,
            "duration_ms": 3200
          },
          "traffic_tokens": {
            "token_count": 420,
            "truncated": true
          },
          "edge_classification": {
            "primary_label": "Suspicious DNS beacon",
            "secondary_label": "command-and-control",
            "confidence": 0.78
          }
        }
      }
    ],
    "statistics": {
      "total_flows": 150,
      "anomaly_flows_detected": 2
    },
    "metrics": {
      "bandwidth_saved_percent": 81.4
    },
    "context": {
      "analysis_constraints": {
        "max_time_window_s": 60,
        "max_packet_count": 10,
        "max_token_length": 690
      }
    }
  }
}
```

成功响应：

```json
{
  "status": "stored",
  "report_id": "task-20260409-0001",
  "edge_id": "edge1",
  "reported_at": "2026-04-09T10:12:30+00:00",
  "received_at": "2026-04-09T10:12:31+00:00"
}
```

### 4.2 允许字段

- `edge_id / report_id / source / reported_at`
- `intel.summary`
- `intel.threats`
- `intel.statistics`
- `intel.metrics`
- `intel.tags`
- `intel.context`

### 4.3 禁止字段

任意层级均禁止出现以下字段或等价变体（与 `central-agent/app/security.py` 的校验保持一致）：

- `pcap`
- `payload`
- `payload_hex`
- `raw_packet`
- `raw_bytes`
- `flow_text`
- `packet_bytes`
- `packet_hex`
- `application_payload`
- `full_l7_content`

## 5. central-agent API

### GET `/api/v1/edges`

返回归档视图：

```json
{
  "edges": [
    {
      "edge_id": "edge1",
      "report_count": 3,
      "latest_reported_at": "2026-04-08T10:00:00+00:00",
      "latest_received_at": "2026-04-08T10:00:01+00:00"
    }
  ]
}
```

### GET `/api/v1/edges/{edge_id}/reports`

返回某个 Edge 的归档列表：

```json
{
  "edge_id": "edge1",
  "reports": [
    {
      "report_id": "rep-20260408-0001",
      "edge_id": "edge1",
      "source": "edge-agent",
      "reported_at": "2026-04-08T10:00:00+00:00",
      "received_at": "2026-04-08T10:00:01+00:00",
      "report": {
        "schema_version": "edge-intel/v1",
        "summary": {},
        "threats": [],
        "statistics": {},
        "metrics": {},
        "tags": [],
        "context": {}
      }
    }
  ]
}
```

### GET `/api/v1/edges/{edge_id}/reports/latest`

返回最新归档，结构同单条 `ReportEnvelope`。

### POST `/api/v1/edges/{edge_id}/analyze`

请求体：

```json
{
  "question": "Summarize the most important risks and response priorities for this edge.",
  "instructions": "",
  "max_reports": 5
}
```

响应：

```json
{
  "analysis_id": "uuid-string",
  "scope": "edge",
  "edge_id": "edge1",
  "edge_ids": ["edge1"],
  "analyzed_report_count": 3,
  "provider_response_id": "resp_123",
  "model": "gpt-4o-mini",
  "analysis": {
    "summary": "edge summary",
    "findings": [],
    "recommended_actions": [],
    "confidence_notes": ""
  },
  "source_reports": [
    {
      "report_id": "rep-20260408-0001",
      "edge_id": "edge1",
      "reported_at": "2026-04-08T10:00:00+00:00",
      "source": "edge-agent"
    }
  ]
}
```

### POST `/api/v1/network/analyze`

请求体：

```json
{
  "edge_ids": [],
  "question": "Compare edges, identify correlated risks, and recommend network-wide response priorities.",
  "instructions": "",
  "max_reports_per_edge": 3
}
```

响应结构与单 Edge 分析相同，但：

- `scope = "network"`
- `edge_id = null`
- `edge_ids` 为实际参与研判的 Edge 列表

## 6. 错误响应

`central-agent` 当前通过 HTTPException handler 输出：

```json
{
  "status": "error",
  "error_code": "EDGE_REPORT_NOT_FOUND",
  "message": "No reports found for edge_id `edge1`."
}
```

常见错误码：

| error_code | HTTP | 说明 |
| --- | --- | --- |
| `REPORT_ID_CONFLICT` | 409 | `report_id` 已存在 |
| `REPORT_STORE_FAILED` | 500 | 归档写入失败 |
| `EDGE_REPORT_NOT_FOUND` | 404 | 指定 Edge 没有归档 |
| `NETWORK_REPORTS_NOT_FOUND` | 404 | 指定网络范围内没有可分析报告 |
| `EXTERNAL_LLM_NOT_CONFIGURED` | 503 | 未配置外部 LLM |
| `EXTERNAL_LLM_UNAVAILABLE` | 503 | 外部 LLM 调用失败 |
| `EXTERNAL_LLM_INVALID_RESPONSE` | 503 | 外部 LLM 返回结构异常 |
