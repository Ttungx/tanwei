---
name: core-beliefs
description: 探微系统核心信仰与物理约束红线
type: project
---

# 核心信仰与物理约束

## 部署架构

边缘智能计算终端，旁路部署，Docker 容器化。

| 维度 | 规格 |
|------|------|
| 内存 | 2GB ~ 4GB |
| 存储 | 10GB ~ 50GB SSD |
| 总容器内存上限 | ~2.3GB |

---

## 资源约束红线

### 允许的技术栈

| 类别 | 允许 |
|------|------|
| 语言 | Python 3.10 |
| Web 框架 | FastAPI |
| 网络解析 | scapy |
| 机器学习 | scikit-learn, libsvm |
| 分词器 | sentencepiece |

### 绝对禁止的依赖

| 禁止库 | 替代方案 | 原因 |
|--------|----------|------|
| torch/tensorflow | llama.cpp server | 内存 > 2GB |
| pandas | 原生 dict/list | 内存开销大 |
| transformers | llama.cpp server | 依赖链臃肿 |

---

## 工程红线

| 指标 | 目标值 | 红线值 |
|------|--------|--------|
| SVM 推理延迟 | < 1ms | > 10ms 告警 |
| LLM 推理延迟 | < 100ms | > 500ms 告警 |
| 端到端检测延迟 | < 5s | > 30s 超时 |
| 带宽压降率 | > 70% | < 50% 不达标 |

---

## 安全红线

1. **原始载荷不上传**: 输出不含原始 Pcap 载荷
2. **单向调用链**: 前端只能调用 edge-agent
3. **模型文件只读挂载**: 防止运行时篡改
