# 探微 (Tanwei) - Console + Edge-Agent + Central-Agent

> `CLAUDE.md` 是导航图，不是巨型说明书。详细知识在 `docs/`，agent 角色在 `.claude/agents/`。

## Start Here

执行任何任务前，按需阅读：

| 场景 | 必读文档 |
|------|----------|
| 任何跨服务任务 | `docs/design-docs/agent-operating-model.md` |
| 架构与边界判断 | `docs/design-docs/architecture.md` |
| 处理流量重组/分词 | `docs/design-docs/traffic-tokenization.md` |
| 调整 API 或提示词契约 | `docs/references/api_specs.md` |
| 调整部署与容器 | `docs/references/deployment.md` |
| 调整 harness / sub-agent | `docs/references/agent-harness.md` |
| 查看当前执行重点 | `docs/exec-plans/active-plan.md` |

## Core Constraints

1. 拓扑方向：
   - `console -> edge-agent -> svm-filter-service / llm-service`
   - `console -> central-agent`
   - `edge-agent -> central-agent`（仅结构化情报）
2. 禁止 `console` 绕过 `edge-agent` 直接调用 `svm-filter-service` / `llm-service`
3. `edge-agent -> central-agent` 绝对禁止上送原始 pcap、原始 payload、完整十六进制包内容
4. 边缘红线：时间窗口 `<= 60s`，包数量 `<= 10`
5. `central-agent` 不能本地加载巨型模型；仅允许通过环境变量配置外部 LLM
6. `central-agent` 不可用时，不得阻断 `edge-agent` 本地检测闭环

## Agent Roster

| Agent | Ownership |
|------|-----------|
| `lead-agent` | 跨服务拆解、路由、harness 控制面治理 |
| `edge-agent-engineer` | `edge-agent/` 与 edge-side contracts |
| `central-agent-engineer` | `central-agent/` 接收归档 + 分析编排 |
| `console-developer` | `console/` 管理员流与展示层 |
| `svm-filter-engineer` / `llm-service-engineer` | 边缘下游运行时服务 |
| `detection-ml-engineer` / `data-scientist` | 离线训练与分析评估 |
| `traffic-security-analyst` | 安全语义判断与工程映射 |
| `docker-expert` | 容器编排与部署边界 |
| `evaluator-agent` | 独立验收 |
| `doc-gardener` | 文档/计划/harness 收口 |
| `brainstorm-architect` | 实施前方案探索 |

## Agent Workflow

1. 默认入口：`lead-agent`
2. 派发给一个或多个 specialist（典型：`edge-agent-engineer`、`central-agent-engineer`、`console-developer`）
3. 实施后必须进入 `evaluator-agent`
4. 验收通过后交 `doc-gardener` 同步文档/计划/harness
5. 当问题边界不清或需要方案对比时，先走 `brainstorm-architect`

## Documentation System

- `docs/design-docs/`: 架构、边界、核心原则
- `docs/exec-plans/`: 当前计划、归档计划、技术债
- `docs/references/`: 给 agent 直接消费的手册
- `.claude/agents/`: sub-agent 角色、边界、触发条件

## Feedback Loops

- 行为变化必须同步更新 architecture / api / deployment / harness 文档
- 不要无限重试同一失败；超过合理次数应补脚本、harness 或计划
- 发现 AI slop、坏模式或未完成设计，记录到 `docs/exec-plans/tech-debt.md`

## Key Paths

```text
TrafficLLM tokenizer: /root/anxun/TrafficLLM-master
Base model:          /root/anxun/qwen3.5-0.8b/Qwen3.5-0.8B-Q4_K_M.gguf
```
