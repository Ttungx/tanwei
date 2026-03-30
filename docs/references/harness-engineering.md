---
name:Harness Engineering 理念文档
description:若需了解harness engineering则参考该文档
type: reference
---
以下是基于 Harness Engineering 理念，关于如何维护文档结构，以及如何在 Anthropic 的 Claude Code 中落地并实现“自动维护”的详尽实践指南。

---

### 一、 如何维护文档结构（Harness-Engineering 标准）


#### 1. 黄金文档结构推荐
不要把所有规则塞进一个文件。将 `CLAUDE.md` 作为**目录（Table of Contents）**，指向结构化的 `docs/` 目录：

```text
/ (项目根目录)
├── CLAUDE.md               # 核心路由：约 100 行，定义大基调、指令集，并指向 docs/ 目录
├── docs/                   # Agent 的事实来源 (System of Record)
│   ├── design-docs/        # 架构设计文档
│   │   ├── core-beliefs.md # 团队/项目的“黄金原则”(如：优先用哪些库、禁止的写法)
│   │   └── index.md        
│   ├── exec-plans/         # 执行计划 (非常重要！)
│   │   ├── active/         # 当前正在执行的任务拆解
│   │   ├── completed/      # 已完成的架构决策和任务记录
│   │   └── tech-debt.md    # 技术债追踪 (AI 生成的不完美代码先记在这里)
│   ├── references/         # LLM 专用的参考手册
│   │   ├── api-specs.md    # 内部 API 的契约规范
│   │   └── ui-llm.txt      # 专门写给 AI 看的 UI 组件使用说明
│   └── generated/          # 自动化脚本或 Agent 自动生成的产物 (如 DB schema)
```

#### 2. 文档维护的核心原则
*   **AI 不可见即不存在（Agent Legibility）**：存在于 Slack 讨论、飞书文档或人脑中的架构决策，对 Claude 来说都不存在。**所有决策必须落库为 markdown 文件**。
*   **机器强制校验（Mechanical Enforcement）**：文档不能只给人看。应该编写 Linter 或脚本来检查 `docs/` 中的文档是否互相冲突、是否包含死链接。

---

### 二、 如何在 Claude Code 中实践 Harness Engineering

在 Claude Code 中实践 Harness Engineering，意味着你要把精力从“教它写代码”转移到“给它设定物理定律和工具”。模型是概率性的（经常发散），而 Harness 必须是确定性的。

#### 1. 编写 Harness 友好的 `CLAUDE.md`
在你的 `CLAUDE.md` 中，不要写长篇大论，而是写入环境约束和工作流：
```markdown
# 项目引导
本项目由 Claude Code 完全驱动。你的目标是遵循 `docs/design-docs/core-beliefs.md` 中的架构原则。

# 架构约束 (Architectural Constraints)
1. 依赖方向：Types -> Config -> Service -> UI。绝对禁止反向依赖。
2. 在编写任何业务代码前，必须先查阅 `docs/exec-plans/active/` 下的当前计划。

# 反馈循环 (Feedback Loops)
- 修改代码后，你**必须主动执行** `npm run lint` 和 `npm run test`。
- 如果测试失败，不要盲目重试超过 3 次。去查看 `logs/` 目录或执行排错脚本寻找原因。
```

#### 2. 建立结构化的架构约束（Linters as Prompting）
Harness 工程强调：**不要用 Prompt 让 AI 写好代码，而是用 Linter 逼它写好代码**。
*   配置极度严格的 ESLint/TSLint 或架构测试（ArchUnit）。
*   **关键实践**：自定义报错信息。当 Linter 报错时，输出的信息中必须包含**给 Agent 的修复指南**（例如：“*Error: UI component importing Database logic. Remediation for Agent: Move the DB logic to a Provider in the Service layer.*”）。Claude 看到这个报错会自动明白如何修正。

#### 3. 隔离的可观测环境
给予 Claude Code 独立的环境权限，让它能自己查日志。比如提供脚本 `npm run test:e2e:agent`，该脚本在报错时会自动把 DOM 快照或错误日志提取成纯文本，方便 Claude Code 在同一次会话中直接读取并闭环修复。

---

### 三、 让 Claude Code 自动维护文档与 Harness 架构

AI 会制造“熵（Entropy）”——随着代码量增加，AI 会复制自己之前写的不优雅代码，导致代码库腐化。我们要利用 Claude Code 本身来做“垃圾回收（Garbage Collection）”和文档园丁工作。

你可以通过以下特定的 Prompt 或定期执行的脚本，让 Claude Code 实现自动维护：

#### 1. 自动执行“文档园艺 (Doc-Gardening)”
创建一个例行任务，每当你完成一个大功能后，向 Claude Code 发送以下指令：
> 💡 **Prompt 给 Claude Code**：
> "作为整个 codebase 的维护者，你现在需要进行 '文档园艺'。请读取最近 5 次的代码提交差异（Git diff），并扫描 `docs/` 下的所有 markdown。找出所有与当前真实代码库行为不符的描述、过时的架构说明，并直接修改那些 Markdown 文件，开启一个 fix-up commit。"

#### 2. 技术债回收与执行计划更新 (Entropy Management)
让 Claude 建立一个长期跟踪任务，每次遇到不好修的 Bug 或者过度绕弯子的代码，先不花几个小时死扣，而是：
> 💡 **Prompt 给 Claude Code**：
> "你当前的尝试已经陷入僵局。停止当前方向，记录你的失败原因以及代码中的不良模式（AI Slop），将它们归档到 `docs/exec-plans/tech-debt.md`，并在代码中留下 TODO 注释。"

到了周末，运行一次清理任务：
> 💡 **Prompt 给 Claude Code**：
> "读取 `docs/exec-plans/tech-debt.md` 以及 `docs/design-docs/core-beliefs.md` 中的黄金原则。在整个项目中进行一次全局重构，确保代码符合黄金原则（如：抽取重复逻辑到公共 util、检查数据边界校验等），并解决技术债文档中的第一项任务。"

#### 3. 利用 Claude Code 建立自我进化的技能 (Self-Refining Skills)
在 `CLAUDE.md` 中增加一条固定的复盘反馈流程：
> "每次你成功完成一项跨层级的复杂 Feature 开发后，必须执行以下步骤：
> 1. 反思本次开发中遇到的最大障碍（如某个特定的库不好调用、某个测试总是 flaky）。
> 2. 将这次学到的教训（Lessons Learned）或新沉淀的架构模式补充到 `docs/references/` 下的对应文件中。
> 3. 以便未来的 Agent（也就是你自己）再次遇到时能够避坑。"

### 总结

Harness Engineering 的核心是：**与其把模型变聪明，不如把包裹模型的环境变得坚不可摧**。在 Claude Code 中实践时，**你不再是一个 Coder，而是一个系统架构师**。用极简的 `CLAUDE.md` 作为大地图，用严格的 Linting 充当物理法则，提供 `docs/` 作为它的记忆库，最后让 Claude 自己充当清洁工定期打扫代码和文档的卫生。