# 部署指南

本文档说明 `console / edge-agent / central-agent` 的部署关系，重点补充 `central-agent` 的 `.env` 外部 LLM 依赖、compose 服务、失败策略，以及它与 edge 本地闭环的解耦约束。

## 1. 命名与职责

- `console`: 管理员界面，当前对应 `edge-test-console`
- `edge-agent`: 边缘站点本地检测闭环，当前由 `agent-loop` 负责主编排
- `central-agent`: 云侧结构化情报归档与综合研判服务

## 2. 部署原则

### 2.1 edge 本地闭环优先

- `console -> edge-agent -> svm-filter-service / llm-service` 构成边缘站点本地闭环。
- 本地检测是否可运行，不依赖 `central-agent`。
- 即使 `central-agent` 宕机、未部署、或外部大模型未配置，edge 本地检测仍应继续工作。

### 2.2 central-agent 是独立云侧能力

- `central-agent` 独立提供报告归档、edge 视图查询、单 edge 分析、全网综合研判。
- `edge-agent` 可以选择性上送结构化 JSON 情报到 `central-agent`。
- `console` 可以单独访问 `central-agent` 来查看 `edge1`、`edge2` 等视图并触发分析。

## 3. 端口与服务

| 服务 | 逻辑名称 | 默认端口 | 说明 |
| --- | --- | --- | --- |
| `edge-test-console` | `console` | `3000` | 管理员控制台 |
| `agent-loop` | `edge-agent` | `8002` | 边缘检测核心 API |
| `svm-filter-service` | 本地过滤服务 | `8001` | edge-agent 依赖 |
| `llm-service` | 本地边缘 LLM | `8080` | edge-agent 依赖 |
| `central-agent` | `central-agent` | `8003` | 云侧情报归档与分析 |

## 4. `.env` 配置

### 4.1 基础示例

根目录 `.env` 示例：

```dotenv
LOG_LEVEL=INFO

# edge-agent 侧已有配置
MAX_TIME_WINDOW=60
MAX_PACKET_COUNT=10
MAX_TOKEN_LENGTH=690

# central-agent 外部 LLM 配置
EXTERNAL_LLM_BASE_URL=https://example-llm-provider/v1
EXTERNAL_LLM_API_KEY=replace-me
EXTERNAL_LLM_MODEL=gpt-4o-mini
EXTERNAL_LLM_TIMEOUT_SECONDS=45
```

### 4.2 central-agent 必需项

对 `central-agent` 来说：

- `EXTERNAL_LLM_BASE_URL`：外部大模型兼容 OpenAI Chat Completions 的基础地址
- `EXTERNAL_LLM_API_KEY`：外部大模型鉴权凭证

可选项：

- `EXTERNAL_LLM_MODEL`：模型名，默认 `gpt-4o-mini`
- `EXTERNAL_LLM_TIMEOUT_SECONDS`：请求超时秒数，默认 `45`
- `LOG_LEVEL`
- `CENTRAL_AGENT_DB_PATH`：报告归档 SQLite 路径，compose 中默认 `/app/data/central-agent.db`

### 4.3 未配置时的行为

如果未设置 `EXTERNAL_LLM_BASE_URL` 或 `EXTERNAL_LLM_API_KEY`：

- `POST /api/v1/edges/{edge_id}/analyze` 返回 `503`
- `POST /api/v1/network/analyze` 返回 `503`
- `POST /api/v1/reports` 仍然可以正常归档报告
- `GET /api/v1/edges`、`GET /api/v1/edges/{edge_id}/reports`、`GET /api/v1/edges/{edge_id}/reports/latest` 仍然可以正常使用

这是一种显式失败策略：分析能力降级，但归档与查询能力保留。

## 5. docker-compose 服务

`docker-compose.yml` 中应包含独立的 `central-agent` 服务，核心要点如下：

```yaml
central-agent:
  build:
    context: .
    dockerfile: central-agent/Dockerfile
  ports:
    - "8003:8003"
  env_file:
    - .env
  environment:
    - CENTRAL_AGENT_DB_PATH=/app/data/central-agent.db
    - EXTERNAL_LLM_BASE_URL=${EXTERNAL_LLM_BASE_URL:-}
    - EXTERNAL_LLM_API_KEY=${EXTERNAL_LLM_API_KEY:-}
    - EXTERNAL_LLM_MODEL=${EXTERNAL_LLM_MODEL:-gpt-4o-mini}
    - EXTERNAL_LLM_TIMEOUT_SECONDS=${EXTERNAL_LLM_TIMEOUT_SECONDS:-45}
    - LOG_LEVEL=${LOG_LEVEL:-INFO}
  volumes:
    - central-agent-data:/app/data
  networks:
    - tanwei-internal
```

部署要求：

- `central-agent` 自带独立端口 `8003`
- 持久化卷 `central-agent-data` 用于 SQLite 归档
- 通过 `.env` 注入外部大模型依赖
- 不要把 `agent-loop` 配成依赖 `central-agent`
- 不要把 `edge-test-console` 的本地检测链路绑定到 `central-agent` 健康状态

## 6. 失败策略

### 6.1 central-agent 自身失败

场景：

- `central-agent` 进程未启动
- `central-agent` 数据库不可写
- `central-agent` HTTP 不可达

影响：

- `console -> central-agent` 的视图查询和分析请求失败
- `edge-agent -> central-agent` 的上送请求失败
- `console -> edge-agent` 的本地检测链路不受影响

处理原则：

- 将 `central-agent` 视为可选增强能力，而不是 edge 检测前提条件
- 上送失败不应阻塞 edge-agent 本地生成结果

### 6.2 外部 LLM 失败

场景：

- `.env` 未配置 `EXTERNAL_LLM_BASE_URL`
- `.env` 未配置 `EXTERNAL_LLM_API_KEY`
- 上游模型 HTTP 5xx / 超时 / 鉴权失败

影响：

- 只有分析接口失败并返回 `503`
- 已归档报告仍可查询

处理原则：

- 报告归档和历史查询优先保证可用
- 管理员可先查看 `edge1`、`edge2` 的最新报告，稍后再重试分析

### 6.3 edge-agent 上送失败

场景：

- `edge-agent -> central-agent` 网络不通
- 上送报告触发契约校验失败

影响：

- 当前报告无法进入 central-agent 归档
- edge 本地检测结果仍保留在 edge 侧

处理原则：

- edge-agent 只能上传结构化 JSON 情报
- 一旦包含 `pcap`、`payload`、`payload_hex`、`flow_text` 等原始字段，central-agent 应直接拒绝
- 不允许通过“临时放宽契约”来换取上送成功

## 7. 启动顺序建议

### 7.1 最小本地闭环

只验证 edge 侧时，启动：

```bash
docker-compose up -d llm-service svm-filter-service agent-loop edge-test-console
```

这时不需要 `central-agent`。

### 7.2 包含 central-agent 的完整拓扑

需要云侧归档与综合研判时，再额外启动：

```bash
docker-compose up -d central-agent
```

或直接整体启动：

```bash
docker-compose up -d
```

说明：

- `central-agent` 可以晚于 edge 闭环启动
- `central-agent` 启动失败，不应要求回退 edge 本地服务

## 8. 健康检查与运维判断

`central-agent` 健康检查：

```bash
curl -s http://localhost:8003/health
```

返回示例：

```json
{
  "status": "healthy",
  "service": "central-agent",
  "version": "1.0.0",
  "external_llm_configured": false
}
```

运维解释：

- `status=healthy` 且 `external_llm_configured=true`：归档与分析都可用
- `status=healthy` 且 `external_llm_configured=false`：归档与查询可用，分析接口预期返回 `503`
- 无法访问 `/health`：仅说明云侧服务不可用，不说明 edge 本地闭环异常

## 9. 部署结论

当前推荐部署策略是：

- 把 `edge-agent` 当作边缘站点必需能力
- 把 `central-agent` 当作云侧可选增强能力
- 用 `.env` 控制 `central-agent` 的外部 LLM 接入
- 让报告归档、edge 视图查询、单 edge 分析、手动全网综合研判彼此职责清晰
- 始终保持 `central-agent` 与 edge 本地闭环解耦
