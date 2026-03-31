---
name: dataset-feature-engineering
description: TrafficLLM 数据集分析与 SVM 特征工程参考
type: reference
---

# TrafficLLM 数据集深度分析报告

> **分析日期**: 2026-03-31
> **数据源路径**: `/root/anxun/data/tran_data/TrafficLLM_Datasets`
> **分析目标**: 为 EdgeAgent 边缘智能终端的 SVM 二分类模型提供特征工程依据

---

## 1. 数据概览

### 1.1 数据集目录结构

TrafficLLM 预处理数据集采用分任务组织方式，包含 12 个子数据集：

| 数据集名称 | 训练集记录数 | 测试集记录数 | 任务类型 |
|-----------|-------------|-------------|---------|
| ustc-tfc-2016 | 48,282 | 2,537 | 加密恶意软件检测 (20类) |
| cstnet-2023 | 92,822 | 4,885 | 未知 |
| app53-2023 | 102,600 | 5,400 | 应用分类 (53类) |
| cw100-2024 | 53,200 | 2,800 | 网站指纹识别 (63类) |
| cw100-2018 | 7,200 | 200 | 网站指纹识别 |
| iscx-vpn-2016 | 61,609 | 3,242 | VPN 流量分类 (14类) |
| dohbrw-2020 | 47,500 | 2,500 | DoH 浏览检测 |
| iscx-tor-2016 | 38,000 | 2,000 | Tor 行为检测 (8类) |
| iscx-botnet-2014 | 23,750 | 1,250 | 僵尸网络检测 (5类) |
| csic-2010 | 25,953 | 8,651 | HTTP 攻击检测 (2类) |
| dapt-2020 | 9,500 | 500 | APT 攻击检测 (2类) |
| instructions | 9,209 | - | 指令微调数据 |

**总计**: 约 520,000+ 条流量样本

### 1.2 数据格式规范

所有数据集采用统一的 JSON Lines 格式（每行一个 JSON 对象）：

```json
{
    "instruction": "任务描述 + <packet>标签 + 协议字段序列",
    "output": "分类标签"
}
```

---

## 2. 协议元信息解析

`<packet>` 标识符后的纯文本字符串包含四层协议栈的完整元信息。

### 2.1 Layer 1: Frame 层（数据帧元信息）

| 字段名 | 示例值 | 语义说明 |
|--------|--------|---------|
| `frame.encap_type` | 1 | 封装类型 (1=Ethernet) |
| `frame.time` | Jan 1, 1970 08:13:56.125909000 CST | 时间戳 |
| `frame.time_epoch` | 836.125909000 | Unix 时间戳 |
| `frame.time_delta` | 0.000016000 | 与上一帧时间差(秒) |
| `frame.time_relative` | 0.000083000 | 相对于流起始时间 |
| `frame.number` | 6 | 帧序号 |
| `frame.len` | 1518 | 帧长度(字节) |
| `frame.marked` | 0 | 标记位 |
| `frame.protocols` | eth:ethertype:ip:tcp:nbss | 协议栈 |

### 2.2 Layer 2: Ethernet 层（链路层）

| 字段名 | 示例值 | 语义说明 |
|--------|--------|---------|
| `eth.dst` | 02:1a:c5:01:00:00 | 目标 MAC 地址 |
| `eth.src` | 02:1a:c5:02:00:00 | 源 MAC 地址 |
| `eth.type` | 0x00000800 | 以太网类型 (0x0800=IPv4) |

### 2.3 Layer 3: IP 层（网络层）

| 字段名 | 示例值 | 语义说明 |
|--------|--------|---------|
| `ip.version` | 4 | IP 版本 |
| `ip.hdr_len` | 20 | IP 头长度(字节) |
| `ip.len` | 1500 | IP 包总长度(字节) |
| `ip.id` | 0x0000449a | 分片标识 |
| `ip.flags.df` | 1 | 禁止分片标志 |
| `ip.frag_offset` | 0 | 分片偏移 |
| `ip.ttl` | 32 | 生存时间 |
| `ip.proto` | 6 | 上层协议 (6=TCP, 17=UDP) |
| `ip.src` | 1.2.196.67 | 源 IP 地址 |
| `ip.dst` | 1.1.219.29 | 目标 IP 地址 |
| `ip.dsfield.dscp` | 0 | 差分服务代码点 |
| `ip.dsfield.ecn` | 0 | 显式拥塞通知 |

### 2.4 Layer 4: TCP 层（传输层）

| 字段名 | 示例值 | 语义说明 |
|--------|--------|---------|
| `tcp.srcport` | 139 | 源端口 |
| `tcp.dstport` | 50871 | 目标端口 |
| `tcp.len` | 1448 | TCP 数据长度(字节) |
| `tcp.seq` | 6160 | 序列号 |
| `tcp.ack` | 1 | 确认号 |
| `tcp.hdr_len` | 32 | TCP 头长度(字节) |
| `tcp.flags` | 0x00000018 | TCP 标志位组合 |
| `tcp.flags.syn` | 0 | SYN 标志 |
| `tcp.flags.ack` | 1 | ACK 标志 |
| `tcp.flags.push` | 1 | PSH 标志 |
| `tcp.flags.fin` | 0 | FIN 标志 |
| `tcp.flags.reset` | 0 | RST 标志 |
| `tcp.window_size` | 18824 | TCP 窗口大小 |
| `tcp.window_size_scalefactor` | -1 | 窗口缩放因子 |
| `tcp.payload` | e2:c3:4d:9e:d3:69... | 负载数据(十六进制) |

### 2.5 Layer 4: UDP 层（传输层）

| 字段名 | 示例值 | 语义说明 |
|--------|--------|---------|
| `udp.srcport` | 53 | 源端口 |
| `udp.dstport` | 60839 | 目标端口 |
| `udp.length` | 107 | UDP 长度 |

---

## 3. 标签映射关系（Label Alignment）

### 3.1 二分类标签映射

以下数据集可直接用于二分类任务：

#### DAPT-2020（APT 攻击检测）

```json
{
    "normal": 0,    // 正常流量
    "APT": 1        // APT 攻击流量
}
```

#### CSIC-2010（HTTP 攻击检测）

```json
{
    "benign": 0,       // 正常流量
    "malicious": 1     // 恶意流量
}
```

### 3.2 多分类标签映射

以下数据集需要重新映射为二分类：

#### USTC-TFC-2016（加密恶意软件检测）

**原始标签**:
```json
{
    "Geodo": 0, "Cridex": 1, "Tinba": 2, "Shifu": 3,
    "Gmail": 4, "SMB": 5, "Weibo": 6, "WorldOfWarcraft": 7,
    "Zeus": 8, "FTP": 9, "MySQL": 10, "BitTorrent": 11,
    "Skype": 12, "Miuref": 13, "Htbot": 14, "Outlook": 15,
    "Facetime": 16, "Virut": 17, "Nsis-ay": 18, "Neris": 19
}
```

**二分类映射建议**:
- **恶意流量 (label=1)**: Cridex, Geodo, Htbot, Miuref, Neris, Nsis-ay, Shifu, Tinba, Virut, Zeus
- **正常流量 (label=0)**: BitTorrent, FTP, Facetime, Gmail, MySQL, Outlook, SMB, Skype, Weibo, WorldOfWarcraft

#### ISCX-Botnet-2014（僵尸网络检测）

**原始标签**:
```json
{
    "IRC": 0,      // 正常/IRC协议
    "normal": 1,   // 正常流量
    "Virut": 2,    // 僵尸网络
    "Neris": 3,    // 僵尸网络
    "RBot": 4      // 僵尸网络
}
```

**二分类映射建议**:
- **恶意流量 (label=1)**: Virut, Neris, RBot
- **正常流量 (label=0)**: IRC, normal

#### ISCX-Tor-2016（Tor 行为检测）

**原始标签**:
```json
{
    "browsing": 0, "file": 1, "voip": 2, "audio": 3,
    "chat": 4, "mail": 5, "p2p": 6, "video": 7
}
```

**注意**: 此数据集为行为分类，所有样本均为 Tor 网络流量，不适合直接用于恶意/正常二分类。

---

## 4. SVM 降维特征提取策略

### 4.1 约束条件

根据 `docs/design-docs/core-beliefs.md` 中的物理约束：

1. **双重截断保护**:
   - 时间窗口 <= 60 秒
   - 包数量 <= 前 10 个数据包

2. **边缘容器禁止依赖**:
   - 禁止使用 pandas, torch, tensorflow, transformers
   - 需使用 numpy, scipy 等轻量级库

### 4.2 特征维度设计

基于协议字段分析，设计以下 **32 维数值特征向量**：

#### A. 基础统计特征 (8 维)

| 索引 | 特征名 | 计算方式 |
|------|--------|---------|
| 0 | `avg_packet_len` | 10个包的 frame.len 平均值 |
| 1 | `std_packet_len` | 10个包的 frame.len 标准差 |
| 2 | `avg_ip_len` | 10个包的 ip.len 平均值 |
| 3 | `std_ip_len` | 10个包的 ip.len 标准差 |
| 4 | `avg_tcp_len` | 10个包的 tcp.len 平均值 |
| 5 | `std_tcp_len` | 10个包的 tcp.len 标准差 |
| 6 | `total_bytes` | 10个包的总字节数 |
| 7 | `avg_ttl` | 10个包的 ip.ttl 平均值 |

#### B. 协议类型特征 (4 维)

| 索引 | 特征名 | 计算方式 |
|------|--------|---------|
| 8 | `ip_proto` | ip.proto 值 (6=TCP, 17=UDP) |
| 9 | `tcp_ratio` | TCP 包占比 |
| 10 | `udp_ratio` | UDP 包占比 |
| 11 | `other_proto_ratio` | 其他协议占比 |

#### C. TCP 行为特征 (8 维)

| 索引 | 特征名 | 计算方式 |
|------|--------|---------|
| 12 | `avg_window_size` | tcp.window_size 平均值 |
| 13 | `std_window_size` | tcp.window_size 标准差 |
| 14 | `syn_count` | SYN 标志出现次数 |
| 15 | `ack_count` | ACK 标志出现次数 |
| 16 | `push_count` | PSH 标志出现次数 |
| 17 | `fin_count` | FIN 标志出现次数 |
| 18 | `rst_count` | RST 标志出现次数 |
| 19 | `avg_hdr_len` | tcp.hdr_len 平均值 |

#### D. 时间特征 (4 维)

| 索引 | 特征名 | 计算方式 |
|------|--------|---------|
| 20 | `total_duration` | 10个包的总时间跨度(秒) |
| 21 | `avg_inter_arrival` | 平均包间到达时间 |
| 22 | `std_inter_arrival` | 包间到达时间标准差 |
| 23 | `packet_rate` | 包速率(包/秒) |

#### E. 端口特征 (4 维)

| 索引 | 特征名 | 计算方式 |
|------|--------|---------|
| 24 | `src_port_entropy` | 源端口熵值 |
| 25 | `dst_port_entropy` | 目标端口熵值 |
| 26 | `well_known_port_ratio` | 知名端口(<=1023)占比 |
| 27 | `high_port_ratio` | 高端口(>1023)占比 |

#### F. 地址特征 (4 维)

| 索引 | 特征名 | 计算方式 |
|------|--------|---------|
| 28 | `unique_dst_ip_count` | 唯一目标 IP 数量 |
| 29 | `internal_ip_ratio` | 内网 IP 比例 |
| 30 | `df_flag_ratio` | DF 标志位比例 |
| 31 | `avg_ip_id` | IP ID 平均值(归一化) |

---

## 5. 特征提取实现

### 5.1 单包特征提取

```python
import numpy as np
from collections import Counter

def extract_packet_features(instruction_text: str) -> np.ndarray:
    """
    从 instruction 文本中提取 32 维特征向量

    Args:
        instruction_text: 包含 <packet> 标签的原始文本

    Returns:
        32 维 numpy 数组
    """
    # 1. 解析 <packet> 内容
    if '<packet>:' not in instruction_text:
        return np.zeros(32)

    packet_content = instruction_text.split('<packet>:')[-1]

    # 2. 提取字段键值对
    fields = {}
    for item in packet_content.split(', '):
        if ':' in item:
            key, value = item.split(':', 1)
            fields[key.strip()] = value.strip()

    # 3. 构建特征向量
    features = np.zeros(32)

    # A. 基础统计特征 (0-7)
    frame_len = _safe_float(fields.get('frame.len', 0))
    ip_len = _safe_float(fields.get('ip.len', 0))
    tcp_len = _safe_float(fields.get('tcp.len', 0))
    ip_ttl = _safe_float(fields.get('ip.ttl', 0))

    features[0] = frame_len           # avg_packet_len (单包情况)
    features[1] = 0                   # std_packet_len
    features[2] = ip_len              # avg_ip_len
    features[3] = 0                   # std_ip_len
    features[4] = tcp_len             # avg_tcp_len
    features[5] = 0                   # std_tcp_len
    features[6] = frame_len           # total_bytes
    features[7] = ip_ttl              # avg_ttl

    # B. 协议类型特征 (8-11)
    ip_proto = _safe_float(fields.get('ip.proto', 0))
    features[8] = ip_proto            # ip_proto
    features[9] = 1 if ip_proto == 6 else 0  # tcp_ratio
    features[10] = 1 if ip_proto == 17 else 0  # udp_ratio
    features[11] = 1 if ip_proto not in [6, 17] else 0  # other_proto_ratio

    # C. TCP 行为特征 (12-19)
    window_size = _safe_float(fields.get('tcp.window_size', 0))
    features[12] = window_size        # avg_window_size
    features[13] = 0                  # std_window_size
    features[14] = _safe_float(fields.get('tcp.flags.syn', 0))  # syn_count
    features[15] = _safe_float(fields.get('tcp.flags.ack', 0))  # ack_count
    features[16] = _safe_float(fields.get('tcp.flags.push', 0))  # push_count
    features[17] = _safe_float(fields.get('tcp.flags.fin', 0))  # fin_count
    features[18] = _safe_float(fields.get('tcp.flags.reset', 0))  # rst_count
    features[19] = _safe_float(fields.get('tcp.hdr_len', 0))  # avg_hdr_len

    # D. 时间特征 (20-23)
    time_delta = _safe_float(fields.get('frame.time_delta', 0))
    features[20] = time_delta         # total_duration
    features[21] = time_delta         # avg_inter_arrival
    features[22] = 0                  # std_inter_arrival
    features[23] = 1.0 / max(time_delta, 0.000001)  # packet_rate

    # E. 端口特征 (24-27)
    src_port = _safe_float(fields.get('tcp.srcport', fields.get('udp.srcport', 0)))
    dst_port = _safe_float(fields.get('tcp.dstport', fields.get('udp.dstport', 0)))
    features[24] = 0 if src_port == 0 else 1  # src_port_entropy (简化)
    features[25] = 0 if dst_port == 0 else 1  # dst_port_entropy
    features[26] = 1 if dst_port <= 1023 else 0  # well_known_port_ratio
    features[27] = 1 if dst_port > 1023 else 0  # high_port_ratio

    # F. 地址特征 (28-31)
    df_flag = _safe_float(fields.get('ip.flags.df', 0))
    features[28] = 1                  # unique_dst_ip_count (单包情况)
    features[29] = _is_internal_ip(fields.get('ip.dst', ''))  # internal_ip_ratio
    features[30] = df_flag            # df_flag_ratio
    features[31] = _normalize_ip_id(fields.get('ip.id', '0'))  # avg_ip_id

    return features
```

### 5.2 流级特征聚合

```python
def extract_flow_features(packet_list: list) -> np.ndarray:
    """
    从 10 个包的列表中提取聚合特征向量

    Args:
        packet_list: 包含 10 个包字段的字典列表

    Returns:
        32 维 numpy 数组
    """
    if not packet_list:
        return np.zeros(32)

    n = len(packet_list)
    features = np.zeros(32)

    # 提取所有包的数值
    frame_lens = [p.get('frame.len', 0) for p in packet_list]
    ip_lens = [p.get('ip.len', 0) for p in packet_list]
    tcp_lens = [p.get('tcp.len', 0) for p in packet_list]
    ip_ttls = [p.get('ip.ttl', 0) for p in packet_list]
    window_sizes = [p.get('tcp.window_size', 0) for p in packet_list]
    time_deltas = [p.get('frame.time_delta', 0) for p in packet_list]

    # A. 基础统计特征
    features[0] = np.mean(frame_lens)
    features[1] = np.std(frame_lens) if n > 1 else 0
    features[2] = np.mean(ip_lens)
    features[3] = np.std(ip_lens) if n > 1 else 0
    features[4] = np.mean(tcp_lens)
    features[5] = np.std(tcp_lens) if n > 1 else 0
    features[6] = sum(frame_lens)
    features[7] = np.mean(ip_ttls)

    # B. 协议类型特征
    ip_protos = [p.get('ip.proto', 0) for p in packet_list]
    features[8] = max(set(ip_protos), key=ip_protos.count) if ip_protos else 0
    features[9] = ip_protos.count(6) / n
    features[10] = ip_protos.count(17) / n
    features[11] = 1 - features[9] - features[10]

    # C. TCP 行为特征
    features[12] = np.mean(window_sizes)
    features[13] = np.std(window_sizes) if n > 1 else 0
    features[14] = sum(p.get('tcp.flags.syn', 0) for p in packet_list)
    features[15] = sum(p.get('tcp.flags.ack', 0) for p in packet_list)
    features[16] = sum(p.get('tcp.flags.push', 0) for p in packet_list)
    features[17] = sum(p.get('tcp.flags.fin', 0) for p in packet_list)
    features[18] = sum(p.get('tcp.flags.reset', 0) for p in packet_list)
    hdr_lens = [p.get('tcp.hdr_len', 0) for p in packet_list]
    features[19] = np.mean(hdr_lens)

    # D. 时间特征
    features[20] = sum(time_deltas)
    features[21] = np.mean(time_deltas)
    features[22] = np.std(time_deltas) if n > 1 else 0
    features[23] = n / max(features[20], 0.000001)

    # E. 端口特征
    src_ports = [p.get('tcp.srcport', p.get('udp.srcport', 0)) for p in packet_list]
    dst_ports = [p.get('tcp.dstport', p.get('udp.dstport', 0)) for p in packet_list]
    features[24] = _calculate_entropy(src_ports)
    features[25] = _calculate_entropy(dst_ports)
    features[26] = sum(1 for p in dst_ports if p <= 1023) / n
    features[27] = sum(1 for p in dst_ports if p > 1023) / n

    # F. 地址特征
    dst_ips = [p.get('ip.dst', '') for p in packet_list]
    features[28] = len(set(dst_ips))
    features[29] = sum(_is_internal_ip(ip) for ip in dst_ips) / n
    features[30] = sum(p.get('ip.flags.df', 0) for p in packet_list) / n
    ip_ids = [_normalize_ip_id(p.get('ip.id', '0')) for p in packet_list]
    features[31] = np.mean(ip_ids)

    return features
```

### 5.3 辅助函数

```python
def _safe_float(value, default=0.0):
    """安全转换为浮点数"""
    try:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith('0x'):
                return float(int(value, 16))
            return float(value)
        return float(value)
    except (ValueError, TypeError):
        return default


def _is_internal_ip(ip: str) -> int:
    """判断是否为内网 IP"""
    if not ip:
        return 0
    # 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
    parts = ip.split('.')
    if len(parts) != 4:
        return 0
    try:
        first = int(parts[0])
        second = int(parts[1])
        if first == 10:
            return 1
        if first == 172 and 16 <= second <= 31:
            return 1
        if first == 192 and second == 168:
            return 1
    except ValueError:
        return 0
    return 0


def _normalize_ip_id(ip_id: str) -> float:
    """归一化 IP ID (0-65535 -> 0-1)"""
    try:
        if ip_id.startswith('0x'):
            value = int(ip_id, 16)
        else:
            value = int(ip_id)
        return value / 65535.0
    except ValueError:
        return 0.0


def _calculate_entropy(values: list) -> float:
    """计算离散值的熵"""
    if not values:
        return 0.0
    counter = Counter(values)
    n = len(values)
    entropy = 0.0
    for count in counter.values():
        if count > 0:
            p = count / n
            entropy -= p * np.log2(p)
    return entropy
```

---

## 6. 边缘部署优化

针对边缘容器的资源约束，提出以下优化策略：

1. **特征维度剪枝**: 使用特征重要性分析，选择 Top-16 关键特征
2. **数值精度优化**: 使用 float32 替代 float64
3. **预处理缓存**: 对常见端口、协议映射建立静态查找表
4. **增量计算**: 避免全量重算，支持流式更新统计量

### 6.1 关键特征排序建议

```python
# 基于恶意流量检测的经验值排序
PRIORITY_FEATURES = [
    0,   # avg_packet_len
    9,   # tcp_ratio
    12,  # avg_window_size
    20,  # total_duration
    21,  # avg_inter_arrival
    23,  # packet_rate
    26,  # well_known_port_ratio
    14,  # syn_count
    15,  # ack_count
    16,  # push_count
    28,  # unique_dst_ip_count
    30,  # df_flag_ratio
    1,   # std_packet_len
    13,  # std_window_size
    22,  # std_inter_arrival
    7,   # avg_ttl
]
```

---

## 7. 数据集选择建议

| 任务场景 | 推荐数据集 | 原因 |
|---------|-----------|------|
| 恶意软件检测 | USTC-TFC-2016 | 类别丰富，样本量大 |
| APT 攻击检测 | DAPT-2020 | 标签直接为二分类 |
| HTTP 攻击检测 | CSIC-2010 | 标签直接为二分类 |
| 僵尸网络检测 | ISCX-Botnet-2014 | 包含多种僵尸网络类型 |

---

## 8. 与现有系统的关系

### 8.1 特征向量差异

| 版本 | 维度 | 来源 |
|------|------|------|
| 原版（traffic-tokenization.md） | 14 维 | 基础统计特征 |
| **本版** | 32 维 | 扩展特征，包含协议行为、时间、端口、地址特征 |

### 8.2 集成建议

- SVM 服务可先用 14 维特征快速验证
- 后续升级到 32 维特征以提升准确率
- 特征提取模块应独立于 SVM 服务，便于迭代

---

## 9. 版本信息

- **文档版本**: 1.0.0
- **创建日期**: 2026-03-31
- **维护者**: 探微架构团队
- **数据源**: TrafficLLM 预处理数据集
