---
name: api-specs
description: 服务间 API 接口规范
type: reference
---

# 探微 (Tanwei) - API 接口规范

## 1. 服务间通信概览

```
edge-test-console ──► agent-loop ──► svm-filter-service
                           │
                           └──► llm-service
```

---

## 2. API 详细规范

### 2.1 edge-test-console → agent-loop

#### POST /api/detect

**描述**：上传 Pcap 文件并启动检测流程

**请求**：
```http
POST /api/detect HTTP/1.1
Content-Type: multipart/form-data

file: <pcap_file>
```

**响应**：
```json
{
  "status": "success",
  "task_id": "uuid-string",
  "message": "Detection task started"
}
```

#### GET /api/status/{task_id}

**描述**：查询检测任务状态

**响应**：
```json
{
  "task_id": "uuid-string",
  "status": "processing|completed|failed",
  "stage": "flow_reconstruction|svm_filtering|llm_inference|completed",
  "progress": 75,
  "message": "LLM 正在进行 Token 推理"
}
```

#### GET /api/result/{task_id}

**描述**：获取检测结果

**响应**：
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
      "timestamp": "2026-03-30T10:30:00Z"
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

---

### 2.2 agent-loop → svm-filter-service

#### POST /api/classify

**描述**：对流量特征向量进行二分类

**请求** (32 维特征向量，详见 `docs/references/dataset-feature-engineering.md`)：
```json
{
  "features": {
    "avg_packet_len": 512.5,
    "std_packet_len": 128.3,
    "avg_ip_len": 500.0,
    "std_ip_len": 120.5,
    "avg_tcp_len": 460.0,
    "std_tcp_len": 110.2,
    "total_bytes": 5120.0,
    "avg_ttl": 64.0,
    "ip_proto": 6,
    "tcp_ratio": 1.0,
    "udp_ratio": 0.0,
    "other_proto_ratio": 0.0,
    "avg_window_size": 65535.0,
    "std_window_size": 0.0,
    "syn_count": 1,
    "ack_count": 8,
    "push_count": 5,
    "fin_count": 0,
    "rst_count": 0,
    "avg_hdr_len": 32.0,
    "total_duration": 30.5,
    "avg_inter_arrival": 3.05,
    "std_inter_arrival": 1.2,
    "packet_rate": 0.33,
    "src_port_entropy": 54321.0,
    "dst_port_entropy": 443.0,
    "well_known_port_ratio": 1.0,
    "high_port_ratio": 0.0,
    "unique_dst_ip_count": 1,
    "internal_ip_ratio": 0.0,
    "df_flag_ratio": 0.5,
    "avg_ip_id": 0.5
  }
}
```

**响应**：
```json
{
  "prediction": 1,
  "label": "anomaly",
  "confidence": 0.87,
  "latency_ms": 0.15
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| prediction | int | 0: 正常, 1: 疑似异常 |
| label | string | "normal" 或 "anomaly" |
| confidence | float | 置信度 (0.0-1.0) |
| latency_ms | float | 推理延迟（毫秒） |

**特征维度说明** (32 维)：

| 类别 | 索引 | 特征名 | 说明 |
|------|------|--------|------|
| A. 基础统计 | 0-7 | avg_packet_len, std_packet_len, ... | 包长度统计、TTL 等 |
| B. 协议类型 | 8-11 | ip_proto, tcp_ratio, ... | 协议分布 |
| C. TCP 行为 | 12-19 | avg_window_size, syn_count, ... | TCP 标志与窗口 |
| D. 时间特征 | 20-23 | total_duration, packet_rate, ... | 时间统计 |
| E. 端口特征 | 24-27 | src_port_entropy, well_known_port_ratio, ... | 端口分布 |
| F. 地址特征 | 28-31 | unique_dst_ip_count, internal_ip_ratio, ... | IP 地址特征 |

详细特征定义请参考 `docs/references/dataset-feature-engineering.md`。

---

### 2.3 agent-loop → llm-service

#### POST /completion

**描述**：调用 llama.cpp server 进行文本补全

**请求**：
```json
{
  "prompt": "Given the following traffic data <packet>: ...\nPlease classify this traffic:",
  "n_predict": 64,
  "temperature": 0.1,
  "stop": ["</s>", "\n"]
}
```

**响应**：
```json
{
  "content": "Malware Traffic",
  "tokens_evaluated": 156,
  "tokens_predicted": 3,
  "timings": {
    "prompt_ms": 45.2,
    "predicted_ms": 12.8,
    "total_ms": 58.0
  }
}
```

---

### 2.4 健康检查接口

所有服务均需实现健康检查端点：

#### GET /health

**响应**：
```json
{
  "status": "healthy",
  "service": "agent-loop",
  "version": "1.0.0",
  "uptime_seconds": 3600
}
```

---

## 3. 错误响应格式

所有 API 在出错时返回统一格式：

```json
{
  "status": "error",
  "error_code": "INVALID_PCAP_FILE",
  "message": "The uploaded file is not a valid PCAP format",
  "details": {
    "filename": "test.pcap",
    "expected_format": "pcap or pcapng"
  }
}
```

### 错误码定义

| 错误码 | HTTP 状态码 | 说明 |
|--------|-------------|------|
| INVALID_PCAP_FILE | 400 | 无效的 Pcap 文件格式 |
| SVM_SERVICE_UNAVAILABLE | 503 | SVM 服务不可用 |
| LLM_SERVICE_UNAVAILABLE | 503 | LLM 服务不可用 |
| TASK_NOT_FOUND | 404 | 任务 ID 不存在 |
| INTERNAL_ERROR | 500 | 内部服务错误 |

---

## 4. 流水线状态枚举

| 状态 | 说明 |
|------|------|
| `pending` | 任务等待处理 |
| `flow_reconstruction` | 正在提取五元组、重组流 |
| `svm_filtering` | SVM 初筛丢弃正常流量 |
| `llm_inference` | 大模型正在进行 Token 推理 |
| `completed` | 检测完成 |
| `failed` | 检测失败 |

---

## 5. JSON 结构化日志格式

agent-loop 返回给 edge-test-console 的最终 JSON 格式：

```json
{
  "meta": {
    "task_id": "uuid-string",
    "timestamp": "2026-03-30T10:30:00Z",
    "agent_version": "1.0.0",
    "processing_time_ms": 1250
  },
  "statistics": {
    "total_packets": 1500,
    "total_flows": 150,
    "normal_flows_dropped": 148,
    "anomaly_flows_detected": 2,
    "svm_filter_rate": "98.67%",
    "bandwidth_reduction": "78.5%"
  },
  "threats": [
    {
      "id": "threat-001",
      "five_tuple": {
        "src_ip": "192.168.1.100",
        "src_port": 54321,
        "dst_ip": "10.0.0.1",
        "dst_port": 443,
        "protocol": "TCP"
      },
      "classification": {
        "primary_label": "Malware",
        "secondary_label": "Botnet",
        "confidence": 0.92,
        "model": "Qwen3.5-0.8B"
      },
      "flow_metadata": {
        "start_time": "2026-03-30T10:29:30Z",
        "end_time": "2026-03-30T10:30:00Z",
        "packet_count": 10,
        "byte_count": 5120,
        "avg_packet_size": 512.0
      },
      "token_info": {
        "token_count": 156,
        "truncated": false
      }
    }
  ],
  "metrics": {
    "original_pcap_size_bytes": 1048576,
    "json_output_size_bytes": 225280,
    "bandwidth_saved_percent": 78.5
  }
}
```

---

## 6. 调用示例

### 6.1 完整检测流程

```bash
# 1. 上传 Pcap 文件
curl -X POST http://localhost:3000/api/detect \
  -F "file=@test.pcap"

# 响应: {"task_id": "abc-123", ...}

# 2. 轮询状态
curl http://localhost:3000/api/status/abc-123

# 响应: {"stage": "llm_inference", "progress": 75, ...}

# 3. 获取结果
curl http://localhost:3000/api/result/abc-123

# 响应: 完整的 JSON 结构化日志
```

### 6.2 直接调用 SVM 服务（仅限 agent-loop 内部）

```bash
curl -X POST http://svm-filter-service:8001/api/classify \
  -H "Content-Type: application/json" \
  -d '{"features": {...}}'
```

### 6.3 直接调用 LLM 服务（仅限 agent-loop 内部）

```bash
curl -X POST http://llm-service:8080/completion \
  -H "Content-Type: application/json" \
  -d '{"prompt": "...", "n_predict": 64}'
```

---

## 7. 端口汇总

| 服务 | 端口 | 说明 |
|------|------|------|
| edge-test-console | 3000 | Web 控制台（对外开放） |
| agent-loop | 8002 | 主控程序 |
| svm-filter-service | 8001 | SVM 过滤服务 |
| llm-service | 8080 | LLM 推理服务 |

---

## 8. 版本信息

- **API 版本**：1.0.0
- **更新日期**：2026-03-30
- **维护者**：探微架构团队
