---
name: tech-debt
description: 技术债务与代码熵管理
type: project
---

# 探微 (Tanwei) - 技术债务追踪

---

## 待处理债务

| ID | 模块 | 问题描述 | 优先级 | 建议 |
|----|------|----------|--------|------|
| TD-003 | edge-agent | 错误处理不够完善，缺少重试机制 | 中 | 添加 `tenacity` 重试装饰器 |

## 已解决债务

| ID | 模块 | 问题描述 | 解决日期 | 解决方案 |
|----|------|----------|----------|----------|
| TD-005 | edge-test-console | 前端组件未拆分，单文件过大 | 2026-04-06 | 已重构为 ConsoleShell 架构，新增 SidebarNav, Topbar, OverviewBand, WorkflowChain, TaskSummary, DemoSampleLibrary 等组件 |

---

## AI Slop 警示记录

### 过度工程化

```python
# 禁止：过度抽象
class FeatureExtractorFactory: ...

# 推荐：直接实现
def extract_features(packets: List[Packet]) -> Dict: ...
```

### 巨型依赖

```python
# 禁止
import pandas as pd

# 推荐
features_dict = {"packet_count": 10, ...}
```

---

## 审查周期

每两周扫描：TODO/FIXME 注释、依赖大小、性能基准
