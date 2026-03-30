---
name: core-beliefs
description: 探微系统核心信仰与物理约束红线
type: project
---

# 探微 (Tanwei) 核心信仰与物理约束

## 1. 物理环境定义

### 1.1 部署架构变更

**旧架构（已废弃）：** 将系统部署于资源极度受限的传统 OpenWrt 路由器中。

**新架构（当前）：** 在网络环境各节点旁路部署独立的**边缘智能计算终端（Edge AI Terminal）**。

| 维度 | 规格 | 说明 |
|------|------|------|
| **硬件形态** | 轻量级工控机 | 独立计算单元，非路由器嵌入式设备 |
| **内存限制** | 2GB ~ 4GB | 相比路由器大幅放宽，但仍需克制 |
| **存储空间** | 10GB ~ 50GB | SSD 推荐 |
| **网络位置** | 旁路部署 | 不承载流量转发，仅做流量镜像分析 |

### 1.2 Docker 容器化部署

Docker Compose 微服务架构**不再仅仅是仿真环境**，而是最终的真实部署形态。

**Why:** 边缘智能终端具备完整 Linux 环境，容器化部署提供：
- 环境一致性（开发/测试/生产）
- 服务隔离与资源限制
- 快速迭代与回滚能力

**How to apply:** 所有服务必须通过 `docker-compose.yml` 编排，严禁裸机部署。

---

## 2. 资源约束红线

### 2.1 允许的技术栈

| 类别 | 允许 | 说明 |
|------|------|------|
| **语言** | Python 3.10 | 主要开发语言 |
| **Web 框架** | FastAPI | 异步高性能，自动文档 |
| **网络解析** | scapy | 流量包解析标准库 |
| **机器学习** | scikit-learn, libsvm | 轻量级 SVM 推理 |
| **分词器** | sentencepiece | TrafficLLM 依赖 |

### 2.2 绝对禁止的依赖

以下库**严禁**在边缘容器（agent-loop, svm-filter-service）中引入：

| 禁止库 | 替代方案 | 原因 |
|--------|----------|------|
| `torch` | llama.cpp server | 内存占用 > 2GB |
| `tensorflow` | llama.cpp server | 内存占用 > 2GB |
| `pandas` | 原生 dict/list | 内存开销过大 |
| `transformers` | llama.cpp server | 依赖链臃肿 |

**Why:** 边缘终端内存有限（2GB~4GB），引入巨型 ML 框架会导致：
- 容器启动缓慢（> 30s）
- 内存溢出风险
- 与 LLM 推理服务资源竞争

**How to apply:** 在 Dockerfile 和 requirements.txt 中严格执行依赖审查。

### 2.3 大模型推理必须独立

LLM 推理**必须**依赖独立的 `llm-service` 容器（llama.cpp server），严禁在 agent-loop 中直接加载模型。

**Why:**
- llama.cpp 是 C/C++ 实现，内存占用约 500MB
- Python transformers 库加载同模型需要 > 2GB 内存

---

## 3. 四容器资源配额

| 容器 | 内存限制 | CPU 限制 | 关键约束 |
|------|----------|----------|----------|
| **llm-service** | 1GB | 2 线程 | 使用 llama.cpp，禁止 PyTorch |
| **svm-filter-service** | 300MB | 1 核 | 仅 scikit-learn，禁止深度学习框架 |
| **agent-loop** | 500MB | 2 核 | 禁止 torch/tensorflow/pandas |
| **edge-test-console** | 512MB | 1 核 | 前后端分离，轻量级代理 |

**总资源占用上限：** 约 2.3GB 内存

---

## 4. 工程红线

### 4.1 性能红线

| 指标 | 目标值 | 红线值 |
|------|--------|--------|
| SVM 单次推理延迟 | < 1ms | > 10ms 告警 |
| LLM 单次推理延迟 | < 100ms | > 500ms 告警 |
| 端到端检测延迟 | < 5s | > 30s 超时 |
| 带宽压降率 | > 70% | < 50% 不达标 |

### 4.2 安全红线

1. **原始载荷不上传：** EdgeAgent 输出的数据绝对不能包含原始 Pcap 载荷
2. **单向调用链：** 前端只能调用 agent-loop，严禁跨级直接调用 SVM 或 LLM
3. **模型文件只读挂载：** 防止运行时篡改

---

## 5. 版本信息

- **架构变更日期：** 2026-03-30
- **变更原因：** 从路由器嵌入式部署迁移至独立边缘智能终端
- **维护者：** 探微架构团队
