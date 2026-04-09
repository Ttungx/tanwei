---
name: deployment
description: console + edge-agent + central-agent 的部署模式、环境变量与失败策略
type: reference
---

# 部署指南（Console + Edge + Central）

## 1. 目标拓扑

```text
console -> edge-agent -> svm-filter-service / llm-service
console -> central-agent
edge-agent -> central-agent (结构化情报上报)
```

关键约束：

- `console` 是统一控制台入口。
- `edge-agent` 保持本地检测闭环可独立运行。
- `central-agent` 只消费结构化 JSON，不接收原始 pcap/payload。
- 全网综合研判仅手动触发，不自动调度。

## 2. 资源与依赖

### 2.1 硬件建议

| 环境 | CPU | 内存 | 磁盘 |
|------|------|------|------|
| 开发/演示 | 4 cores | 8 GB | 20 GB |
| 边缘节点 | 2-4 cores | 2-4 GB | 10-50 GB SSD |
| 中心节点（不含大模型本地推理） | 2+ cores | 2+ GB | 10+ GB |

### 2.2 软件版本

| 软件 | 最低版本 | 推荐版本 |
|------|------|------|
| Docker | 20.10 | 24.0+ |
| Docker Compose | 2.0 | 2.20+ |
| Linux Kernel | 4.18 | 5.10+ |

## 3. 端口与暴露策略

| 服务 | 容器端口 | 暴露策略 |
|------|------|------|
| `console` | 8000 | 映射宿主 `3000`（管理员首选入口） |
| `edge-agent` | 8002 | 开发/联调用途映射宿主 `8002` |
| `central-agent` | 8003 | 开发/联调用途映射宿主 `8003` |
| `svm-filter-service` | 8001 | 开发诊断用途映射宿主 `8001` |
| `llm-service` | 8080 | 开发诊断用途映射宿主 `8080` |

## 4. 环境变量

### 4.1 console

| 变量 | 默认值 | 说明 |
|------|------|------|
| `EDGE_AGENT_URL` | `http://edge-agent:8002` | console -> edge-agent |
| `CENTRAL_AGENT_URL` | `http://central-agent:8003` | console -> central-agent |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `DEMO_SAMPLES_DIR` | `/app/demo-samples` | 演示样本路径 |

### 4.2 edge-agent

| 变量 | 默认值 | 说明 |
|------|------|------|
| `SVM_SERVICE_URL` | `http://svm-filter-service:8001` | SVM 初筛服务 |
| `LLM_SERVICE_URL` | `http://llm-service:8080` | 本地 LLM 推理服务 |
| `CENTRAL_AGENT_URL` | `http://central-agent:8003` | 上报 central-agent（空则跳过自动上报） |
| `CENTRAL_AGENT_TIMEOUT_SECONDS` | `5` | 上报超时（秒） |
| `EDGE_ID` | `edge1` | 边缘节点 ID |
| `MAX_TIME_WINDOW` | `60` | 时间窗截断 |
| `MAX_PACKET_COUNT` | `10` | 包数截断 |
| `MAX_TOKEN_LENGTH` | `690` | token 长度上限 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

### 4.3 central-agent

| 变量 | 默认值 | 说明 |
|------|------|------|
| `EXTERNAL_LLM_BASE_URL` | 空 | 外部 LLM Base URL（必填） |
| `EXTERNAL_LLM_API_KEY` | 空 | 外部 LLM API Key（必填） |
| `EXTERNAL_LLM_MODEL` | `gpt-4o-mini` | 推理模型 |
| `EXTERNAL_LLM_TIMEOUT_SECONDS` | `45` | 外部 LLM 请求超时 |
| `CENTRAL_AGENT_DB_PATH` | `/app/data/central-agent.db` | SQLite 归档路径 |

说明：`central-agent` 不本地加载巨型模型，只通过外部 LLM API 工作。

## 5. 部署模式

### 5.1 模式 A：边缘闭环（不含 central-agent）

用于仅验证边缘检测链路：

```bash
docker compose up -d llm-service svm-filter-service edge-agent console
```

此模式下，`console` 的中央分析入口不可用，但边缘检测闭环应可正常工作。
`console` 不应对 `central-agent` 健康做启动级硬依赖；中央侧缺席时只降级对应按钮和查询。

### 5.2 模式 B：完整三层（推荐）

主 `docker-compose.yml` 已纳入 `central-agent`。启动前请在宿主环境或 `.env` 中准备：

```bash
export EXTERNAL_LLM_BASE_URL="https://your-llm-endpoint.example/v1"
export EXTERNAL_LLM_API_KEY="your-api-key"
export EXTERNAL_LLM_MODEL="gpt-4o-mini"
```

启动：

```bash
docker compose up -d
```

## 6. 运行检查

```bash
curl -s http://localhost:3000/health
curl -s http://localhost:8002/health
curl -s http://localhost:8001/health
curl -s http://localhost:8080/health
curl -s http://localhost:8003/health
```

central 可用时，可从 console 触发：

- `POST /api/edges/{edge_id}/analyze`（单 Edge）
- `POST /api/network/analyze`（全网手动综合研判）

## 7. 失败策略

1. `edge-agent` 检测失败仅影响该任务，不影响其他 Edge。
2. `edge-agent -> central-agent` 上报失败，不阻断本地检测闭环完成。
3. `central-agent` 外部 LLM 不可用时，分析接口返回失败，但已归档报告仍可查询。
4. 全网综合研判失败，不影响单 Edge 查询与分析。

## 8. 数据安全与上云红线

绝对禁止上云字段：

- 原始 pcap 二进制
- 原始 payload
- 完整十六进制包内容
- 其他 pcap/payload-like 衍生字段（如 `packet hex`、`application payload`）

补充说明：`prompt`、异常栈、环境变量等敏感调试信息同样不应进入上云契约，但当前 `central-agent` 的强制校验重点仍是 pcap/payload-like 字段。

仅允许上云：

- `intel` 中的结构化字段（五元组、统计、威胁条目、压缩 token、指标）
- 顶层必须包含 `edge_id/report_id`，并通过嵌套 `intel` 提供情报主体
