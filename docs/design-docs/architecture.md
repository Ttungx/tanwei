---
name: architecture
description: console / edge-agent / central-agent 架构与边界规范
type: project
---

# Tanwei Architecture

## 1. 命名统一

- `console`: 面向管理员的演示与操作界面，当前对应 `edge-test-console`
- `edge-agent`: 边缘检测闭环，当前由 `agent-loop` 作为核心编排，联动 `svm-filter-service` 与本地 `llm-service`
- `central-agent`: 云侧结构化情报归档与综合研判服务

文档、接口、部署说明统一使用以上三组名称。实现层若仍保留现有目录或容器名，不改变其职责边界。

## 2. 总体拓扑

```text
                           ┌──────────────────────────────┐
                           │         console              │
                           │   管理员操作 / 结果查看       │
                           └──────────────┬───────────────┘
                                          │
                                          │ HTTP
                                          ▼
┌────────────────────────────────────────────────────────────────────┐
│                           边缘站点                                  │
│                                                                    │
│  ┌───────────────────────┐        ┌─────────────────────────────┐  │
│  │      edge-agent       │───────►│      svm-filter-service     │  │
│  │   流重组 / 截断 / 编排  │        └─────────────────────────────┘  │
│  │                       │                                        │
│  │                       └───────►┌─────────────────────────────┐  │
│  │                                │        llm-service          │  │
│  └───────────────┬────────────────┴─────────────────────────────┘  │
│                  │                                                 │
└──────────────────┼─────────────────────────────────────────────────┘
                   │ 上送结构化 JSON 情报
                   ▼
        ┌───────────────────────────────────────┐
        │            central-agent             │
        │  归档 edge1 / edge2 / ... 各边报告    │
        │  单 edge 研判 / 全网综合研判           │
        └───────────────────────────────────────┘
```

## 3. 关键边界

### 3.1 edge-agent 本地闭环

- `console -> edge-agent` 是管理员驱动的本地检测入口。
- `edge-agent -> svm-filter-service -> llm-service` 构成边缘站点本地闭环。
- `central-agent` 不是本地闭环的前置依赖。
- 即使 `central-agent` 未启动、外部大模型未配置，单个 edge 的本地检测仍可独立运行。

### 3.2 central-agent 云侧职责

- 接收来自多个 edge 的结构化 JSON 情报报告。
- 按 `edge_id` 建立视图，例如 `edge1`、`edge2`、`edge3`。
- 支持查看某个 edge 的历史报告与最新报告。
- 支持基于某个 edge 的历史报告做单独分析。
- 支持管理员手动触发全网综合研判，对多个 edge 的历史报告做关联分析。

## 4. 端云 JSON 情报契约

central-agent 只接受结构化 JSON，不接受原始网络载荷。

### 4.1 顶层请求

```json
{
  "edge_id": "edge1",
  "report_id": "rep-20260407-0001",
  "source": "edge-agent",
  "reported_at": "2026-04-07T08:30:00Z",
  "intel": {
    "schema_version": "edge-intel/v1",
    "summary": {},
    "threats": [],
    "statistics": {},
    "metrics": {},
    "tags": [],
    "context": {}
  }
}
```

### 4.2 `intel` 语义

- `summary`: 本次边缘检测摘要，例如告警总数、主要风险、处置优先级
- `threats`: 结构化威胁项数组，每项包含标题、严重级别、置信度、证据摘要等
- `statistics`: 统计结果，例如流量总量、异常流数量、协议分布
- `metrics`: 性能或压缩指标，例如耗时、节省带宽、分类数
- `tags`: 便于检索的标签
- `context`: 辅助上下文，例如站点名称、设备组、时间窗口、模型版本

### 4.3 禁止字段

任意层级一旦出现以下原始载荷字段，central-agent 必须拒绝请求：

- `pcap`
- `raw_payload`
- `payload`
- `payload_hex`
- `flow_text`
- 以及语义等价的字段变体，例如大小写变化、下划线变化、`rawpacket`、`packet_hex`

设计原则是“只上传情报，不上传原始内容”。

## 5. 视图与分析模型

### 5.1 edge 视图

- `GET /api/v1/edges` 返回当前已有报告的 edge 列表。
- 典型结果会包含 `edge1`、`edge2` 等视图。
- `GET /api/v1/edges/{edge_id}/reports` 查看某个 edge 的历史报告。
- `GET /api/v1/edges/{edge_id}/reports/latest` 查看某个 edge 的最新报告。

### 5.2 单 edge 分析

- `POST /api/v1/edges/{edge_id}/analyze`
- 读取该 edge 最近 N 份结构化报告。
- 输出该 edge 的风险摘要、关键发现、建议动作和可信度说明。
- 当外部大模型未配置时，该接口返回 `503`，但不影响报告归档和查询。

### 5.3 全网综合研判

- `POST /api/v1/network/analyze`
- 由管理员手动触发，不作为 edge-agent 本地闭环的自动步骤。
- 可指定若干 edge，例如 `edge1` 与 `edge2`。
- central-agent 聚合多个 edge 的历史报告，输出跨边关联风险、统一处置建议和关注优先级。

## 6. 存储与可靠性

- central-agent 当前使用本地 SQLite 持久化归档报告。
- 存储的对象是经校验后的结构化 JSON 情报，不存原始包内容。
- 分析接口是“读历史报告再调用外部大模型”的附加能力，不阻塞报告入库。

## 7. 演进约束

- 允许未来替换 SQLite 为外部数据库，但不改变现有 REST 契约。
- 允许增加新的 `intel` 子字段，但必须保持 JSON 结构化并继续禁止原始载荷字段。
- edge-agent 与 central-agent 之间保持松耦合；任何云侧能力都不能反向成为本地检测的强依赖。
