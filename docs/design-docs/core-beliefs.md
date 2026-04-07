---
name: core-beliefs
description: 探微系统在 console + edge-agent + central-agent 架构下的核心信仰与红线
type: project
---

# 核心信仰与物理约束

## 1. 架构信仰

1. `console` 是统一控制台，不再是“单边缘测试页面”。
2. `edge-agent` 必须可以独立完成边缘检测闭环。
3. `central-agent` 只消费结构化情报，不重跑边缘检测。
4. 全网综合研判必须由管理员手动触发，不做自动实时联动。
5. 端云链路永远优先带宽与隐私安全。

## 2. 部署与资源约束

系统面向边缘部署场景，默认 Docker 容器化运行。

| 维度 | 规格 |
|------|------|
| 内存 | 2GB ~ 4GB |
| 存储 | 10GB ~ 50GB SSD |
| 总容器内存上限（基础闭环） | ~2.3GB |
| 中心侧推理方式 | 外部 LLM API（central-agent 不本地加载巨型模型） |

## 3. 技术栈红线

### 3.1 允许的技术栈

| 类别 | 允许 |
|------|------|
| 语言 | Python 3.10 |
| Web 框架 | FastAPI |
| 网络解析 | scapy |
| 机器学习 | scikit-learn, libsvm |
| 分词器 | sentencepiece |
| 中心推理接入 | 通过 Base URL + API Key 访问外部 LLM |

### 3.2 绝对禁止的依赖/模式

| 禁止库 | 替代方案 | 原因 |
|--------|----------|------|
| torch/tensorflow | llama.cpp server | 内存 > 2GB |
| pandas | 原生 dict/list | 内存开销大 |
| transformers | llama.cpp server | 依赖链臃肿 |
| central 本地大模型常驻 | 外部 LLM API | 违背中心节点轻量原则 |

## 4. 工程指标红线

| 指标 | 目标值 | 红线值 |
|------|--------|--------|
| SVM 推理延迟 | < 1ms | > 10ms 告警 |
| LLM 推理延迟 | < 100ms | > 500ms 告警 |
| 端到端检测延迟 | < 5s | > 30s 超时 |
| 带宽压降率 | > 70% | < 50% 不达标 |

## 5. 端云数据安全红线

### 5.1 绝对禁止上云

- 原始 pcap 二进制
- 原始 payload
- 完整数据包十六进制
- 边缘 prompt/完整模型输出
- 本地路径、内部 URL、环境变量、异常栈

### 5.2 必须保留的上云信息

- `edge_id`、`report_id`、`schema_version`
- 五元组与流量元信息
- SVM 与边缘分类结果
- 压缩 token 与带宽压降统计

## 6. 运行边界红线

1. `edge-agent` 失败不传播为全网不可用。
2. `edge-agent -> central-agent` 上报失败不阻断边缘本地完成。
3. `central-agent` 单 Edge 分析失败不破坏归档。
4. `central-agent` 全网分析失败不影响单 Edge 查询和分析。
