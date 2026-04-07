---
name: active-plan
description: 当前里程碑执行计划
type: project
---

# 探微 (Tanwei) - 当前执行计划

## 里程碑：边缘智能终端系统完善

**目标**：完整微服务闭环，带宽压降率 > 70%

---

## 待办事项

- [ ] **端到端集成测试**
  - 准备测试 Pcap 文件
  - 验证完整检测流程
  - 性能基准测试

- [x] **前端控制台重构** (已完成 2026-04-06)
  - 桌面优先控制台架构
  - 双样本源（本地上传 + 演示样本）
  - 总览优先信息架构

- [x] **文档完善**
  - 更新 API 规范（新增演示样本 API）
  - 更新模块状态（shared 模块已移除）
  - 添加故障排除手册（见 `docs/references/deployment.md`）

---

## 模块状态

| 模块 | 状态 | 说明 |
|------|------|------|
| llm-service | ✅ | llama.cpp server |
| svm-filter-service | ✅ | 32 维特征，TrafficLLM 训练 |
| edge-agent | ✅ | 五阶段工作流 |
| edge-test-console | ✅ | React 18 + FastAPI，已重构为桌面控制台 |

> **注**: `shared/` 模块已移除，日志配置已内联到各服务中。
