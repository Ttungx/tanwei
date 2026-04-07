---
name: tech-debt
description: 技术债务与代码熵管理（console + edge-agent + central-agent）
type: project
---

# 探微 (Tanwei) - 技术债务追踪

---

## 待处理债务

| ID | 模块 | 问题描述 | 优先级 | 建议 |
|----|------|----------|--------|------|
| TD-006 | edge-agent | 尚未直接上报 `EdgeIntelligenceReport` 到 `central-agent` | 高 | 增加端云上报适配层，失败仅告警不阻断边缘完成 |
| TD-007 | console | 中央分析代理接口只有 latest 视图，历史报告检索能力不足 | 中 | 增补单 Edge 历史报告代理接口与前端入口 |
| TD-008 | deployment | 主 compose 默认未纳入 central-agent 服务 | 中 | 增加 `central-agent` 服务与 `CENTRAL_AGENT_URL` 一致配置 |
| TD-009 | central-agent | 归档目前为内存存储，重启后丢失历史报告 | 中 | 引入轻量持久化存储（首选 SQLite） |
| TD-010 | contract-governance | 端云契约尚无自动化 schema 漂移检查 | 中 | 在 CI 增加 schema 校验与 forbidden 字段检查 |

## 已解决债务

| ID | 模块 | 问题描述 | 解决日期 | 解决方案 |
|----|------|----------|----------|----------|
| TD-005 | console | 前端组件未拆分，单文件过大 | 2026-04-06 | 已重构为模块化组件结构（SidebarNav、OverviewBand、WorkflowChain 等） |
| TD-011 | docs | 文档仍以旧架构命名描述系统 | 2026-04-07 | 已切换到 `console + edge-agent + central-agent` 体系并重写核心文档 |

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

每两周扫描：

- TODO/FIXME 注释
- 端云契约漂移
- 旧命名残留（`edge-test-console`、`agent-loop`）
- 依赖大小与性能基准
