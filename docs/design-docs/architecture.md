---
name: architecture
description: 四容器拓扑规范与通信边界约束
type: project
---

# 探微 (Tanwei) 四容器拓扑与边界规范

## 1. 系统概述

探微 (Tanwei) 是一个边缘智能体本地闭环仿真与测试系统，采用四容器微服务架构，部署于网络节点旁路的独立边缘智能终端。

### 1.1 核心目标

- **带宽压降**：模拟核心网上行带宽占用降低 > 70%
- **实时检测**：微秒级初筛 + LLM 推理定性的二级漏斗架构
- **本地验证**：基于离线 Pcap 流量包的完整闭环测试

### 1.2 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    EdgeAgent 四容器拓扑                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
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
│   │   端口: 8001    │                                          │
│   └─────────────────┘                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 容器详细设计

### 2.1 容器 1：LLM 推理引擎 (llm-service)

| 属性 | 规格 |
|------|------|
| **镜像** | `ghcr.io/ggerganov/llama.cpp:server` |
| **端口** | 8080 |
| **内存限制** | 1GB |
| **模型** | Qwen3.5-0.8B-Q4_K_M.gguf (~508MB) |

**设计原则：**
- 使用 C/C++ 编写的 llama.cpp，**绝对禁止** PyTorch/Transformers
- 模拟真实边缘设备的极低资源消耗
- 对外暴露 HTTP API 供 agent-loop 调用

**调用示例：**
```bash
curl -X POST http://llm-service:8080/completion \
  -H "Content-Type: application/json" \
  -d '{"prompt": "...", "n_predict": 64}'
```

---

### 2.2 容器 2：前置轻量级过滤服务 (svm-filter-service)

| 属性 | 规格 |
|------|------|
| **基础镜像** | python:3.10-slim |
| **端口** | 8001 |
| **内存限制** | 300MB |
| **技术栈** | FastAPI + scikit-learn |

**设计原则：**
- 充当第一级漏斗，过滤 99% 高置信度正常流量
- 微秒级响应延迟
- 接收数值特征向量，返回二分类结果

**调用示例：**
```bash
curl -X POST http://svm-filter-service:8001/api/classify \
  -H "Content-Type: application/json" \
  -d '{"features": {...}}'
```

---

### 2.3 容器 3：智能体主控程序 (agent-loop)

| 属性 | 规格 |
|------|------|
| **基础镜像** | python:3.10-slim |
| **端口** | 8002 |
| **内存限制** | 500MB |
| **技术栈** | FastAPI + scapy + sentencepiece |

**五阶段工作流：**

```
┌─────────────────────────────────────────────────────────────────┐
│                     Agent-Loop 五阶段工作流                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  阶段 1: 基于五元组的流重组                                       │
│  ├── 读取 .pcap 文件                                            │
│  └── 按 (src_ip, dst_ip, src_port, dst_port, proto) 重组会话     │
│                                                                 │
│  阶段 2: 双重特征截断                                            │
│  ├── 时间窗口 ≤ 60 秒                                           │
│  └── 提取包数量 ≤ 前 10 个                                       │
│                                                                 │
│  阶段 3: SVM 初筛调用                                            │
│  ├── 提取统计数值特征                                            │
│  ├── 调用 svm-filter-service                                    │
│  └── 正常流直接 Drop，异常流进入阶段 4                            │
│                                                                 │
│  阶段 4: 跨模态对齐与分词                                         │
│  ├── 导入 TrafficLLM 分词器                                      │
│  ├── 解析为指令文本                                              │
│  └── 压缩为 Token 序列 (长度 ≤ 690)                              │
│                                                                 │
│  阶段 5: LLM 标签化与 JSON 封装                                   │
│  ├── 调用 llm-service 获取定性标签                               │
│  └── 生成 JSON 结构化日志返回                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2.4 容器 4：本地测试与可视化控制台 (edge-test-console)

| 属性 | 规格 |
|------|------|
| **端口** | 3000 (外部访问) |
| **内存限制** | 512MB |
| **前端** | React 18 + TypeScript + Vite |
| **后端** | FastAPI (代理层) |

**功能模块：**
1. **Pcap 文件上传组件**
2. **流水线状态跟踪**：动态展示执行状态
3. **工程 KPI 仪表盘**：
   - 检测结果展示
   - 带宽压降对比图（原始 Pcap 大小 vs JSON 日志大小）

---

## 3. 网络拓扑与通信边界

### 3.1 网络配置

```yaml
# docker-compose.yml 网络配置
networks:
  tanwei-internal:
    driver: bridge
    internal: false  # 允许外部访问控制台
```

### 3.2 通信规则（强制单向调用）

```
┌─────────────────────────────────────────────────────────────┐
│                   允许的调用关系                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [edge-test-console:3000] ──► [agent-loop:8002]    ✅ 允许   │
│  [agent-loop:8002] ──► [svm-filter:8001]            ✅ 允许   │
│  [agent-loop:8002] ──► [llm-service:8080]           ✅ 允许   │
│                                                             │
│  [edge-test-console] ──► [svm-filter]              ❌ 禁止   │
│  [edge-test-console] ──► [llm-service]              ❌ 禁止   │
│  [svm-filter] ──► [llm-service]                     ❌ 禁止   │
│  [svm-filter] ──► [agent-loop]                      ❌ 禁止   │
│  [llm-service] ──► [任何服务]                       ❌ 禁止   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Why:**
- 单向调用链保证安全边界
- 前端越权直接调用 SVM/LLM 会绕过主控的审计与截断机制
- 防止内部服务被外部直接攻击

**How to apply:**
- 在 docker-compose.yml 中通过 `depends_on` 和网络隔离实现
- agent-loop 作为唯一入口点

---

## 4. 带外隐私通信

### 4.1 数据输出约束

EdgeAgent 输出给前端或云端的数据**绝对不能包含原始 Pcap 载荷**。

**允许输出：**
- 五元组信息 (src_ip, dst_ip, src_port, dst_port, protocol)
- 疑似标签 (Malware, Botnet, C&C, DDoS 等)
- Token 特征统计信息
- 流元信息（包数、字节数、持续时间）
- 置信度分数

**禁止输出：**
- 原始 Pcap 二进制数据
- 应用层载荷内容（HTTP body, DNS query content 等）
- 完整数据包十六进制转储

### 4.2 JSON 输出结构

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

## 5. 资源约束

| 容器 | CPU | 内存 | 说明 |
|------|-----|------|------|
| llm-service | 2 线程 | 1GB | 量化模型推理 |
| svm-filter-service | 1 核 | 300MB | 轻量级 ML |
| agent-loop | 2 核 | 500MB | 主控逻辑 |
| edge-test-console | 1 核 | 512MB | Web 服务 |

**总资源占用**：约 2.3GB 内存

---

## 6. 关键依赖

### 6.1 TrafficLLM 集成

- **路径**：`/root/anxun/TrafficLLM-master`
- **使用模块**：
  - `preprocess/flow_data_preprocess.py` - 流级数据提取
  - `preprocess/packet_data_preprocess.py` - 包级数据提取
  - `tokenization/traffic_tokenizer.py` - 流量分词器

### 6.2 模型文件

- **路径**：`/root/anxun/qwen3.5-0.8b/Qwen3.5-0.8B-Q4_K_M.gguf`
- **大小**：532MB
- **量化**：INT4 (Q4_K_M)

---

## 7. 启动命令

```bash
# 构建并启动所有服务
docker-compose up --build -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f agent-loop

# 停止所有服务
docker-compose down
```

---

## 8. 版本信息

- **项目阶段**：第一阶段（本地单节点验证）
- **架构变更日期**：2026-03-30
- **维护者**：探微架构团队
- **技术栈版本**：
  - Python: 3.10
  - FastAPI: 0.109.0
  - React: 18.3.1
  - TypeScript: 5.6
  - llama.cpp: latest
