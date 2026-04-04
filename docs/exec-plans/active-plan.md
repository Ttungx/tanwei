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

- [ ] **文档完善**
  - 更新部署指南
  - 添加故障排除手册

---

## 模块状态

| 模块 | 状态 | 说明 |
|------|------|------|
| llm-service | ✅ | llama.cpp server |
| svm-filter-service | ✅ | 32 维特征，TrafficLLM 训练 |
| agent-loop | ✅ | 五阶段工作流 |
| edge-test-console | ✅ | React 18 + FastAPI |
| shared | ✅ | 统一日志配置 |
