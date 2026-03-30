---
name: tech-debt
description: 技术债务与代码熵管理
type: project
---

# 探微 (Tanwei) - 技术债务追踪

本文档记录开发过程中产生的 AI Slop（不良代码模式）、性能瓶颈与待重构项。

---

## 技术债务登记

### 高优先级（影响稳定性）

| ID | 模块 | 问题描述 | 创建日期 | 状态 |
|----|------|----------|----------|------|
| TD-001 | agent-loop | scapy 全量读取 Pcap 可能导致 OOM | 2026-03-29 | ✅ 已修复 |

**TD-001 详情：**
- **问题**：`scapy.rdpcap()` 一次性加载整个 Pcap 文件到内存
- **影响**：大文件（> 100MB）可能导致内存溢出
- **解决方案**：已改用 `scapy.PcapReader` 流式读取
- **代码位置**：`agent-loop/app/flow_processor.py`
- **修复日期**：2026-03-30

```python
# 已修复的实现
from scapy.all import PcapReader
with PcapReader(pcap_path) as pcap_reader:
    for packet in pcap_reader:
        # 流式处理，避免 OOM
```

---

### 中优先级（影响可维护性）

| ID | 模块 | 问题描述 | 创建日期 | 状态 |
|----|------|----------|----------|------|
| TD-002 | svm-filter-service | 预训练模型使用合成数据，准确率待验证 | 2026-03-29 | ⏳ 待改进 |
| TD-003 | agent-loop | 错误处理不够完善，缺少重试机制 | 2026-03-29 | ⏳ 待改进 |

**TD-002 详情：**
- **问题**：当前 SVM 模型使用随机合成数据训练
- **影响**：分类准确率不可控
- **建议方案**：使用 CICIDS2017 或 UNSW-NB15 数据集训练

**TD-003 详情：**
- **问题**：调用 SVM/LLM 服务时缺少重试机制
- **影响**：网络抖动可能导致检测失败
- **建议方案**：添加 `tenacity` 重试装饰器

---

### 低优先级（代码质量）

| ID | 模块 | 问题描述 | 创建日期 | 状态 |
|----|------|----------|----------|------|
| TD-004 | 多模块 | 日志格式不统一 | 2026-03-29 | ⏳ 待改进 |
| TD-005 | edge-test-console | 前端组件未拆分，单文件过大 | 2026-03-29 | ⏳ 待改进 |

---

## AI Slop 警示记录

### 模式 1：过度工程化

**现象**：在不必要的地方引入抽象层

```python
# 不推荐：过度抽象
class FeatureExtractorFactory:
    def create_extractor(self, type: str) -> FeatureExtractor:
        if type == "statistical":
            return StatisticalFeatureExtractor()
        elif type == "temporal":
            return TemporalFeatureExtractor()
        ...

# 推荐：直接实现
def extract_features(packets: List[Packet]) -> Dict:
    ...
```

**教训**：边缘设备资源有限，避免过度设计

### 模式 2：巨型依赖

**现象**：引入不必要的重型库

```python
# 禁止
import pandas as pd
df = pd.DataFrame(features)

# 推荐
features_dict = {"packet_count": 10, ...}
```

**教训**：始终检查依赖大小，优先使用标准库

---

## 定期审查

技术债务审查周期：**每两周**

审查内容：
1. 扫描新增 TODO/FIXME 注释
2. 检查依赖大小变化
3. 性能基准测试对比
4. 代码复杂度分析

---

## 更新日志

- **2026-03-30**: TD-001 已修复，改用 PcapReader 流式读取
- **2026-03-30**: 初始化技术债务文档，记录 TD-001 ~ TD-005
