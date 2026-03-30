---
name: traffic-tokenization
description: 跨模态协议与双重截断保护机制
type: project
---

# 探微 (Tanwei) 跨模态协议与流量分词规范

## 1. 概述

本文档定义了将原始网络流量转换为 LLM 可理解的 Token 序列的规范，包括 TrafficLLM 分词映射与双重截断保护机制。

---

## 2. TrafficLLM 分词映射规范

### 2.1 分词流程

```
原始 Pcap
    │
    ▼
┌─────────────────┐
│  五元组提取      │  IP/TCP/UDP 层解析
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  协议字段提取    │  提取关键字段值
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  指令文本构建    │  "ip.len: 1360, ip.proto: 6..."
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Token 序列化    │  sentencepiece 编码
└────────┬────────┘
         │
         ▼
    Token 序列 (≤690)
```

### 2.2 字段提取格式

将流量包解析为以下格式的指令文本：

```
ip.len: 1360, ip.proto: 6, tcp.srcport: 54321, tcp.dstport: 443, tcp.flags: 0x18, ...
```

**提取字段列表：**

| 层级 | 字段 | 格式示例 | 说明 |
|------|------|----------|------|
| **IP 层** | `ip.len` | `ip.len: 1360` | IP 总长度 |
| | `ip.proto` | `ip.proto: 6` | 协议号 (6=TCP, 17=UDP) |
| | `ip.ttl` | `ip.ttl: 64` | 生存时间 |
| | `ip.flags` | `ip.flags: 0x40` | IP 标志位 |
| **TCP 层** | `tcp.srcport` | `tcp.srcport: 54321` | 源端口 |
| | `tcp.dstport` | `tcp.dstport: 443` | 目的端口 |
| | `tcp.seq` | `tcp.seq: 1234567890` | 序列号 |
| | `tcp.ack` | `tcp.ack: 9876543210` | 确认号 |
| | `tcp.flags` | `tcp.flags: 0x18` | TCP 标志位 |
| | `tcp.window` | `tcp.window: 65535` | 窗口大小 |
| **UDP 层** | `udp.srcport` | `udp.srcport: 53` | 源端口 |
| | `udp.dstport` | `udp.dstport: 12345` | 目的端口 |
| | `udp.len` | `udp.len: 128` | UDP 长度 |

### 2.3 完整指令模板

```
Given the following traffic data <packet> that contains protocol fields,
traffic features, and payloads. Please classify this traffic into one of
the following categories: Normal, Malware, Botnet, C&C, DDoS, Scan, Phishing.

Five-tuple: Source: {src_ip}:{src_port}, Destination: {dst_ip}:{dst_port}, Protocol: {protocol}

<packet>: <pck>{hex_encoded_data}<pck>{hex_encoded_data}...

Classification:
```

**示例：**

```
Given the following traffic data <packet> that contains protocol fields,
traffic features, and payloads. Please classify this traffic into one of
the following categories: Normal, Malware, Botnet, C&C, DDoS, Scan, Phishing.

Five-tuple: Source: 192.168.1.100:54321, Destination: 10.0.0.1:443, Protocol: TCP

<packet>: <pck>450002d0000100004006><pck>70747470...

Classification:
```

---

## 3. 双重截断保护机制

### 3.1 强制约束

在流重组阶段，必须严格执行以下双重截断：

| 约束类型 | 阈值 | 说明 |
|----------|------|------|
| **时间窗口截断** | ≤ 60 秒 | 从流的第一个包开始计时 |
| **包数量截断** | ≤ 前 10 个包 | 只提取流的前 10 个数据包 |

**Why:**
- 防止内存溢出（OOM）
- 保证推理延迟可控
- 早期流量已足够判断威胁特征

**How to apply:**
在 `agent-loop/app/flow_processor.py` 中实现：

```python
MAX_TIME_WINDOW = 60  # 秒
MAX_PACKET_COUNT = 10  # 包数量

def truncate_flow(packets: List[Packet]) -> List[Packet]:
    """
    双重截断保护
    """
    if not packets:
        return packets

    # 时间窗口截断
    start_time = float(packets[0].time)
    truncated_by_time = [
        p for p in packets
        if float(p.time) - start_time <= MAX_TIME_WINDOW
    ]

    # 包数量截断
    truncated = truncated_by_time[:MAX_PACKET_COUNT]

    return truncated
```

### 3.2 Token 长度约束

最终生成的 Token 序列长度不得超过 **690**。

```python
MAX_TOKEN_LENGTH = 690

def tokenize_flow(instruction: str, tokenizer) -> List[int]:
    """
    分词并截断到最大长度
    """
    tokens = tokenizer.encode(instruction)
    if len(tokens) > MAX_TOKEN_LENGTH:
        tokens = tokens[:MAX_TOKEN_LENGTH]
    return tokens
```

---

## 4. 统计特征提取（14 维向量）

用于 SVM 分类的数值特征：

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

---

## 5. TrafficLLM 依赖路径

```
/root/anxun/TrafficLLM-master/
├── preprocess/
│   ├── flow_data_preprocess.py    # 流级数据提取
│   └── packet_data_preprocess.py  # 包级数据提取
└── tokenization/
    └── traffic_tokenizer.py       # 流量分词器
```

**集成方式：**

```python
import sys
sys.path.insert(0, '/root/anxun/TrafficLLM-master')

from tokenization.traffic_tokenizer import TrafficTokenizer
from preprocess.packet_data_preprocess import packet_to_instruction

# 初始化分词器
tokenizer = TrafficTokenizer()

# 包转指令
instruction = packet_to_instruction(packet)

# 分词
tokens = tokenizer.encode(instruction)
```

---

## 6. 版本信息

- **规范版本**：1.0.0
- **创建日期**：2026-03-30
- **维护者**：探微架构团队
