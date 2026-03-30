# 探微 (Tanwei) - EdgeAgent 边缘智能终端系统

> **项目定位**：在网络节点旁路部署的独立边缘智能终端，采用 Docker 四容器微服务架构，实现流量检测与带宽压降。

---

## 强制查阅指令

在执行任何开发任务前，**必须**按以下顺序阅读文档：

| 行为 | 必读文档 |
|------|----------|
| 编写/修改代码 | `docs/design-docs/architecture.md` |
| 处理流量特征 | `docs/design-docs/traffic-tokenization.md` |
| 查看当前任务 | `docs/exec-plans/active-plan.md` |
| 调用内部 API | `docs/references/api_specs.md` |

---

## 核心依赖路径

```
TrafficLLM 分词器:  /root/anxun/TrafficLLM-master
边缘基座模型:       /root/anxun/qwen3.5-0.8b/Qwen3.5-0.8B-Q4_K_M.gguf
```

---

## 架构约束红线

1. **依赖方向**：edge-test-console → agent-loop → svm-filter / llm-service
   - **禁止反向依赖**，禁止跨级调用

2. **禁止依赖**（边缘容器中）：
   - `torch`, `tensorflow`, `transformers`
   - `pandas`
   - 替代方案见 `docs/design-docs/core-beliefs.md`

3. **双重截断保护**：
   - 时间窗口 ≤ 60 秒
   - 包数量 ≤ 前 10 个

---

## 文档园艺协议

每次成功提交复杂代码后，**必须**执行：

1. 扫描 `docs/` 目录，更新过时的 API 或架构描述
2. 若发现不良代码模式，记录到 `docs/exec-plans/tech-debt.md`
3. 保持 System of Record 的准确性

---

## 反馈循环

- 修改代码后，**主动执行**相关测试
- 测试失败不超过 3 次重试，超过则查看日志或记录技术债
- 新学到的教训补充到 `docs/references/`

---

## 文档导航

```
docs/
├── design-docs/              # 架构设计
│   ├── core-beliefs.md       # 物理约束与红线
│   ├── architecture.md       # 四容器拓扑
│   └── traffic-tokenization.md  # 分词规范
├── exec-plans/               # 执行计划
│   ├── active-plan.md        # 当前任务
│   └── tech-debt.md          # 技术债务
└── references/               # 参考手册
    ├── api_specs.md          # API 规范
    ├── deployment.md         # 部署指南
    └── harness-engineering.md  # Harness 方法论
```

---

*本文档遵循 Harness Engineering 规范，作为导航图使用。详细规范请查阅 `docs/` 目录。*
