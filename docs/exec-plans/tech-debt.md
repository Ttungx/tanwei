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
| TD-002 | svm-filter-service | 预训练模型使用合成数据，准确率待验证 | 2026-03-29 | ✅ 已修复 |
| TD-003 | agent-loop | 错误处理不够完善，缺少重试机制 | 2026-03-29 | ⏳ 待改进 |

**TD-002 详情：**
- **问题**：当前 SVM 模型使用随机合成数据训练
- **影响**：分类准确率不可控
- **建议方案**：使用 CICIDS2017 或 UNSW-NB15 数据集训练
- **修复日期**：2026-03-31
- **修复方案**：已使用 TrafficLLM 数据集（DAPT, CSIC, ISCX-Botnet, USTC-TFC 混合）训练，共 71,362 样本
- **修复结果**：
  - 准确率: 75.25%
  - 正常流量过滤率: 91.44%
  - 异常检测率: 63.32%
  - 平均推理延迟: 42.99us

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
| TD-006 | svm-filter-service | API 规范定义 14 维特征，但模型使用 32 维特征 | 2026-03-31 | ⏳ 待改进 |

**TD-006 详情：**
- **问题**：`docs/references/api_specs.md` 定义 SVM API 使用 14 维特征，但实际训练的模型使用 32 维特征（与 `dataset-feature-engineering.md` 一致）
- **影响**：API 调用方无法正确使用新模型
- **建议方案**：更新 api_specs.md 以支持 32 维特征，或在 SVM 服务中实现特征映射适配层

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

- **2026-03-31**: README.md 文档园艺完成，修复技术栈描述（Vue 3 → React 18），更新文档链接指向正确的 Harness Engineering 结构
- **2026-03-31**: TD-002 已修复，使用 TrafficLLM 多数据集联合训练 SVM 模型（32维特征）
- **2026-03-30**: TD-001 已修复，改用 PcapReader 流式读取
- **2026-03-30**: 初始化技术债务文档，记录 TD-001 ~ TD-005
