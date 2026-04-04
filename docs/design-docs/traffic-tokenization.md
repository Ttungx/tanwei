---
name: traffic-tokenization
description: 跨模态协议与双重截断保护机制
type: project
---

# 流量分词规范

## 双重截断保护

| 约束 | 阈值 |
|------|------|
| 时间窗口 | <= 60 秒 |
| 包数量 | <= 前 10 个包 |
| Token 长度 | <= 690 |

```python
MAX_TIME_WINDOW = 60
MAX_PACKET_COUNT = 10
MAX_TOKEN_LENGTH = 690
```

---

## 指令模板

```
Given the following traffic data <packet> that contains protocol fields,
traffic features, and payloads. Please classify this traffic into one of
the following categories: Normal, Malware, Botnet, C&C, DDoS, Scan, Phishing.

Five-tuple: Source: {src_ip}:{src_port}, Destination: {dst_ip}:{dst_port}, Protocol: {protocol}

<packet>: <pck>{hex_encoded_data}<pck>{hex_encoded_data}...

Classification:
```

---

## 32 维特征向量

详细定义见 `docs/references/dataset-feature-engineering.md`

| 类别 | 索引 | 说明 |
|------|------|------|
| 基础统计 | 0-7 | 包长度、TTL |
| 协议类型 | 8-11 | TCP/UDP 比例 |
| TCP 行为 | 12-19 | 标志位、窗口 |
| 时间特征 | 20-23 | 持续时间、速率 |
| 端口特征 | 24-27 | 熵值、知名端口 |
| 地址特征 | 28-31 | IP 分布 |

---

## TrafficLLM 集成

```python
import sys
sys.path.insert(0, '/root/anxun/TrafficLLM-master')
from tokenization.traffic_tokenizer import TrafficTokenizer
from preprocess.packet_data_preprocess import packet_to_instruction
```
