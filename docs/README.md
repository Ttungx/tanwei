# 探微 (Tanwei) 文档中心

本目录是 EdgeAgent 系统的事实来源 (System of Record)，遵循 Harness Engineering 原则组织。

## 文档结构

```
docs/
├── design-docs/          # 架构设计与核心信仰
│   ├── core-beliefs.md   # 物理约束与红线规范
│   ├── architecture.md   # 四容器拓扑与通信边界
│   └── traffic-tokenization.md  # 跨模态协议
│
├── exec-plans/           # 执行计划与技术债
│   ├── active-plan.md    # 当前里程碑任务
│   └── tech-debt.md      # 技术债务追踪
│
└── references/           # 参考手册
    ├── api_specs.md      # API 接口规范
    ├── deployment.md     # 部署指南
    ├── dataset-feature-engineering.md  # TrafficLLM 数据集与 SVM 特征工程
    └── harness-engineering.md  # Harness 工程方法论
```

## 快速导航

| 角色 | 推荐阅读顺序 |
|------|--------------|
| 新成员 | core-beliefs → architecture → active-plan |
| 开发者 | architecture → api_specs → traffic-tokenization |
| 运维 | deployment → architecture |
| AI Agent | core-beliefs → active-plan → tech-debt |

## 文档维护原则

1. **AI 不可见即不存在**：所有架构决策必须落库为 markdown
2. **单一来源**：每个知识点只在一处定义，避免冗余
3. **渐进式展开**：本文档作为目录，具体内容在子目录

---

*本文档由 Claude Code 维护，遵循 Harness Engineering 规范*
