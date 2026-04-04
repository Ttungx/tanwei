---
name: architecture
description: 四容器拓扑规范与通信边界约束
type: project
---

# 四容器拓扑与边界规范

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    EdgeAgent 四容器拓扑                          │
├─────────────────────────────────────────────────────────────────┤
│   ┌─────────────────┐                                           │
│   │ edge-test-console │ ◄── 用户上传 Pcap 文件                   │
│   │ (React + FastAPI) │     端口: 3000                           │
│   └────────┬────────┘                                           │
│            │ HTTP API (唯一入口)                                 │
│            ▼                                                     │
│   ┌─────────────────┐      ┌─────────────────┐                  │
│   │   agent-loop    │─────►│  llm-service    │                  │
│   │   (核心大脑)     │      │ (Qwen3.5-0.8B)  │                  │
│   │   端口: 8002    │      │   端口: 8080    │                  │
│   └────────┬────────┘      └─────────────────┘                  │
│            │                                                     │
│            ▼                                                     │
│   ┌─────────────────┐                                           │
│   │svm-filter-service│ ◄── 微秒级二分类                          │
│   │   端口: 8001    │                                           │
│   └─────────────────┘                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 容器规格

| 容器 | 端口 | 内存 | 技术栈 |
|------|------|------|--------|
| llm-service | 8080 | 1GB | llama.cpp server |
| svm-filter-service | 8001 | 300MB | FastAPI + scikit-learn |
| agent-loop | 8002 | 500MB | FastAPI + scapy |
| edge-test-console | 3000 | 512MB | React 18 + FastAPI |

---

## 通信规则（单向调用）

```
[edge-test-console] ──► [agent-loop]           ✅ 允许
[agent-loop] ──► [svm-filter]                  ✅ 允许
[agent-loop] ──► [llm-service]                 ✅ 允许

[edge-test-console] ──► [svm-filter]           ❌ 禁止
[edge-test-console] ──► [llm-service]          ❌ 禁止
[svm-filter] ──► [llm-service]                 ❌ 禁止
```

**Why:** 单向调用链保证安全边界，防止绕过主控审计机制。

---

## Agent-Loop 五阶段工作流

1. **流重组**: 按五元组重组会话
2. **双重截断**: 时间 <= 60s, 包数 <= 10
3. **SVM 初筛**: 调用 svm-filter-service
4. **分词**: TrafficLLM 分词器，Token <= 690
5. **LLM 推理**: 调用 llm-service 获取标签

---

## 数据输出约束

**允许输出:** 五元组、标签、置信度、流元信息

**禁止输出:** 原始 Pcap 载荷、应用层内容、完整数据包十六进制

---

## 关键依赖

- **TrafficLLM**: `/root/anxun/TrafficLLM-master`
- **模型**: `/root/anxun/qwen3.5-0.8b/Qwen3.5-0.8B-Q4_K_M.gguf`
