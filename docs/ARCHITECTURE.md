# 探微 (Tanwei) - EdgeAgent 架构设计文档

## 1. 系统概述

探微 (Tanwei) 是一个边缘智能体本地闭环仿真与测试系统，采用四容器微服务架构，用于在 WSL 环境下验证 EdgeAgent 的流量检测能力。

### 1.1 核心目标

- **带宽压降**：模拟核心网上行带宽占用降低 > 70%
- **实时检测**：微秒级初筛 + LLM 推理定性的二级漏斗架构
- **本地验证**：基于离线 Pcap 流量包的完整闭环测试

### 1.2 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    EdgeAgent 仿真四容器拓扑                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────┐                                           │
│   │ edge-test-console │ ◄── 用户上传 Pcap 文件                   │
│   │ (Vue3 + FastAPI)  │                                         │
│   └────────┬────────┘                                           │
│            │ HTTP API                                           │
│            ▼                                                     │
│   ┌─────────────────┐      ┌─────────────────┐                  │
│   │   agent-loop    │─────►│  llm-service    │                  │
│   │   (核心大脑)     │      │ (Qwen3.5-0.8B)  │                  │
│   └────────┬────────┘      └─────────────────┘                  │
│            │                                                     │
│            ▼                                                     │
│   ┌─────────────────┐                                           │
│   │svm-filter-service│ ◄── 微秒级二分类                          │
│   │   (SVM 初筛)     │                                          │
│   └─────────────────┘                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 容器详细设计

### 2.1 容器 1：LLM 推理引擎 (llm-service)

| 属性 | 规格 |
|------|------|
| **镜像** | `ghcr.io/ggerganov/llama.cpp:server` |
| **端口** | 8080 |
| **内存限制** | 1GB |
| **模型** | Qwen3.5-0.8B-Q4_K_M.gguf (~508MB) |

**设计原则：**
- 使用 C/C++ 编写的 llama.cpp，禁止 PyTorch/Transformers
- 模拟真实路由器设备的极低资源消耗
- 对外暴露 HTTP API 供 agent-loop 调用

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

### 2.4 容器 4：本地测试与可视化控制台 (edge-test-console)

| 属性 | 规格 |
|------|------|
| **端口** | 3000 (外部访问) |
| **内存限制** | 512MB |
| **前端** | Vue 3 + Vite |
| **后端** | FastAPI (代理层) |

**功能模块：**
1. **Pcap 文件上传组件**
2. **流水线状态跟踪**：动态展示执行状态
3. **工程 KPI 仪表盘**：
   - 检测结果展示
   - 带宽压降对比图（原始 Pcap 大小 vs JSON 日志大小）

## 3. 网络拓扑

```
┌─────────────────────────────────────────────────────────────┐
│                   Docker Network: tanwei-internal            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [edge-test-console:3000] ──► [agent-loop:8002]            │
│                                   │                         │
│                    ┌──────────────┴──────────────┐         │
│                    ▼                             ▼         │
│           [svm-filter:8001]            [llm-service:8080]   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**通信规则：**
- edge-test-console → agent-loop：允许
- agent-loop → svm-filter-service：允许
- agent-loop → llm-service：允许
- **禁止跨级调用**：edge-test-console 不能直接调用 svm-filter-service 或 llm-service

## 4. 资源约束

| 容器 | CPU | 内存 | 说明 |
|------|-----|------|------|
| llm-service | 2 线程 | 1GB | 量化模型推理 |
| svm-filter-service | 1 核 | 300MB | 轻量级 ML |
| agent-loop | 2 核 | 500MB | 主控逻辑 |
| edge-test-console | 1 核 | 512MB | Web 服务 |

**总资源占用**：约 2.3GB 内存

## 5. 关键依赖

### 5.1 TrafficLLM 集成

- **路径**：`/root/anxun/TrafficLLM-master`
- **使用模块**：
  - `preprocess/flow_data_preprocess.py` - 流级数据提取
  - `preprocess/packet_data_preprocess.py` - 包级数据提取
  - `tokenization/traffic_tokenizer.py` - 流量分词器

### 5.2 模型文件

- **路径**：`/root/anxun/qwen3.5-0.8b/Qwen3.5-0.8B-Q4_K_M.gguf`
- **大小**：532MB
- **量化**：INT4 (Q4_K_M)

## 6. 启动命令

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

## 7. 数据流与处理细节

### 7.1 Pcap 解析流程

```
Pcap 文件
    │
    ▼
┌─────────────────┐
│   scapy.rdpcap  │  读取原始包
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  五元组提取      │  IP/TCP/UDP 层解析
│  FiveTuple      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  流重组          │  按 normalized five-tuple 分组
│  FlowProcessor  │  双向流合并
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  双重截断        │  时间窗口 ≤ 60s
│  truncate_flow  │  包数量 ≤ 10
└─────────────────┘
```

### 7.2 特征提取（14 维向量）

| 索引 | 特征名 | 类型 | 说明 |
|------|--------|------|------|
| 0 | packet_count | int | 流中包数量 |
| 1 | avg_packet_size | float | 平均包大小（字节） |
| 2 | std_packet_size | float | 包大小标准差 |
| 3 | flow_duration | float | 流持续时间（秒） |
| 4 | avg_inter_arrival_time | float | 平均包间隔时间 |
| 5 | tcp_flag_syn | int | SYN 标志计数 |
| 6 | tcp_flag_ack | int | ACK 标志计数 |
| 7 | tcp_flag_fin | int | FIN 标志计数 |
| 8 | tcp_flag_rst | int | RST 标志计数 |
| 9 | tcp_flag_psh | int | PSH 标志计数 |
| 10 | unique_dst_ports | int | 唯一目的端口数 |
| 11 | unique_src_ports | int | 唯一源端口数 |
| 12 | bytes_per_second | float | 每秒字节数 |
| 13 | packets_per_second | float | 每秒包数 |

### 7.3 跨模态分词格式

```
输入：流数据（十六进制）
<pck>74707070<pck>70747470...

输出：LLM 提示词
Given the following traffic data <packet> that contains protocol fields,
traffic features, and payloads. Please classify this traffic...

Five-tuple: Source: 192.168.1.100:54321, Destination: 10.0.0.1:443, Protocol: TCP

<packet>: <pck>74707070<pck>70747470...

Classification:
```

### 7.4 JSON 输出结构

```json
{
  "meta": {
    "task_id": "uuid-string",
    "timestamp": "2026-03-29T10:30:00Z",
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
  "threats": [...],
  "metrics": {
    "original_pcap_size_bytes": 1048576,
    "json_output_size_bytes": 225280,
    "bandwidth_saved_percent": 78.5
  }
}
```

---

## 8. 技术选型理由

### 8.1 为什么选择 llama.cpp？

| 考量因素 | llama.cpp | PyTorch/Transformers |
|----------|-----------|---------------------|
| 内存占用 | ~500MB | >2GB |
| 启动时间 | <5s | >30s |
| 依赖大小 | ~100MB | >1GB |
| CPU 推理 | 优化 | 较慢 |
| 边缘适用性 | ✅ 优秀 | ❌ 不适合 |

### 8.2 为什么选择 SVM 而非深度学习？

| 考量因素 | SVM | 深度学习 |
|----------|-----|---------|
| 推理延迟 | <1ms | >10ms |
| 内存占用 | <10MB | >100MB |
| 训练数据需求 | 少量 | 大量 |
| 可解释性 | ✅ 高 | ❌ 低 |
| 边缘部署 | ✅ 简单 | ❌ 复杂 |

### 8.3 为什么选择 FastAPI？

- **异步支持**：原生支持 async/await，适合 I/O 密集型任务
- **自动文档**：内置 Swagger UI，无需额外维护
- **类型验证**：Pydantic 集成，自动请求验证
- **性能优秀**：基于 Starlette，性能接近 Go

---

## 9. 安全设计

### 9.1 网络隔离

```yaml
# docker-compose.yml 网络配置
networks:
  tanwei-internal:
    driver: bridge
    internal: false  # 允许外部访问控制台
```

### 9.2 访问控制

- **LLM 服务**：仅允许 agent-loop 访问
- **SVM 服务**：仅允许 agent-loop 访问
- **Agent 服务**：仅允许 edge-test-console 访问
- **控制台**：对外开放

### 9.3 数据安全

- 模型文件只读挂载 (`:ro`)
- 上传文件隔离存储
- 无敏感信息日志记录

---

## 10. 扩展性设计

### 10.1 水平扩展

```yaml
# 增加工作节点
agent-loop:
  deploy:
    replicas: 3
```

### 10.2 模型替换

```yaml
# 替换为其他 GGUF 模型
llm-service:
  volumes:
    - ./models/your-model.gguf:/models/model.gguf:ro
  command: --model /models/model.gguf ...
```

### 10.3 添加新检测器

在 agent-loop 中注册新的检测服务：

```python
# 在 flow_processor.py 中添加
DETECTOR_REGISTRY = {
    "svm": svm_filter,
    "rule": rule_filter,  # 新增规则引擎
    "stat": stat_filter,  # 新增统计检测
}
```

---

## 11. 版本信息

- **项目阶段**：第一阶段（本地单节点验证）
- **创建日期**：2026-03-29
- **维护者**：探微架构团队
- **技术栈版本**：
  - Python: 3.10
  - FastAPI: 0.109.0
  - Vue: 3.4.21
  - llama.cpp: latest
