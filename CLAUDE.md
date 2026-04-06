# 探微 (Tanwei) - EdgeAgent 边缘智能终端系统

> `CLAUDE.md` 是导航图，不是巨型说明书。详细知识在 `docs/`，agent 角色在 `.claude/agents/`。

## Start Here

执行任何任务前，按需要阅读：

| 场景 | 必读文档 |
|------|----------|
| 任何跨服务任务 | `docs/design-docs/agent-operating-model.md` |
| 编写或修改业务代码 | `docs/design-docs/architecture.md` |
| 处理流量重组或分词 | `docs/design-docs/traffic-tokenization.md` |
| 查看当前工作重点 | `docs/exec-plans/active-plan.md` |
| 调整内部 API 或提示词契约 | `docs/references/api_specs.md` |
| 训练 SVM 或改特征工程 | `docs/references/dataset-feature-engineering.md` |
| 调整部署或容器 | `docs/references/deployment.md` |
| 理解 agent 工作流 | `docs/references/agent-harness.md` |

## Core Constraints

1. 依赖方向：`edge-test-console -> agent-loop -> svm-filter-service / llm-service`
2. 禁止前端绕过 `agent-loop` 直接调用下游服务
3. 边缘容器禁止引入 `torch`、`tensorflow`、`transformers`、`pandas`
4. 双重截断红线：时间窗口 `<= 60s`，包数量 `<= 10`
5. 输出禁止包含原始 Pcap 载荷和完整应用层内容

## Agent Workflow

1. 默认入口是 `lead-agent`
2. 实现工作派发给领域 agent
3. 完成后必须进入 `evaluator-agent`
4. 通过后触发 `doc-gardener` 更新知识库和计划
5. 需求发散、方案不稳或需要周期扫描时，调用 `brainstorm-architect`

## Documentation System

- `docs/design-docs/`: 架构、边界、核心原则
- `docs/exec-plans/`: 当前计划、归档计划、技术债
- `docs/references/`: 给 agent 直接消费的手册
- `.claude/agents/`: Claude Code agent 的职责边界与触发条件

## Feedback Loops

- 修改后主动运行相关验证
- 不要对同一失败无休止重试；超过合理次数应补 harness、脚本、文档或计划
- 行为变化时必须同步更新 `docs/`
- 发现 AI slop、坏模式或未完成设计时，记录到 `docs/exec-plans/tech-debt.md`

## Key Paths

```text
TrafficLLM tokenizer: /root/anxun/TrafficLLM-master
Base model:          /root/anxun/qwen3.5-0.8b/Qwen3.5-0.8B-Q4_K_M.gguf
```
