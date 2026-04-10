---
name: trafficllm-qwen-edge-gguf-design
description: TrafficLLM-master 下 Qwen3.5-0.8B LoRA 训练到 GGUF Q4_K_M 交付链路设计
type: project
status: active
updated_at: 2026-04-10
reason_active: 当前仓库仍未落地 qwen_pipeline，训练流水线仍属待实现范围
---

# TrafficLLM Qwen Edge GGUF Design

## Goal

在不污染项目根目录训练逻辑、且不破坏当前 `llama.cpp + GGUF` 线上推理链路的前提下，为 `TrafficLLM-master` 设计并落地一条可在本地小样本验证、可迁移到云端一键启动、最终产出 `Q4_K_M` 量化模型的 `Qwen3.5-0.8B` 训练流水线，用于满足当前 `edge-agent` 的边缘威胁分类需求。

## Context

当前项目的边缘推理链路为：

`console -> edge-agent -> llm-service -> llama.cpp -> GGUF`

当前 `edge-agent` 本质上是编排器，而不是训练或推理框架。它通过 `POST /completion` 调用本地 `llm-service`，后者用 `llama.cpp` 装载 `Qwen3.5-0.8B-Q4_K_M.gguf` 运行推理。

`TrafficLLM-master` 当前已有：

- 流量预处理与数据集构建能力
- ChatGLM2 双阶段训练主线
- Qwen LoRA 设计文档草案
- 本地原始 Qwen 权重：`TrafficLLM-master/models/qwen0.8b/qwen3.5-0.8b/`
- 本地 TrafficLLM 数据集：`TrafficLLM-master/TrafficLLM_Datasets/`

约束条件：

- 最终部署必须继续使用 `llama.cpp`
- 最终模型必须量化为 `Q4_K_M`
- 所有训练相关代码、配置、脚本、文档、产物路径均位于 `TrafficLLM-master/`
- 本地只做小规模链路验证，正式训练在云端环境执行
- 云端环境存在会话时限，训练必须支持一键启动和断点恢复

## Non-Goals

- 不在第一版中引入 `Transformers + PEFT` 作为线上推理运行时
- 不在第一版中训练多个专项模型并在线路由
- 不在第一版中完整复刻 ChatGLM2 的两阶段 Prefix Tuning 方案
- 不将训练中间产物散落到项目根目录
- 不直接消费所有 TrafficLLM 数据集作为同权主训练集

## Recommended Approach

采用单模型统一训练方案：

1. 在 `TrafficLLM-master/` 内新增一套 Qwen LoRA 训练流水线
2. 对 TrafficLLM 原始任务数据做标签归一和 prompt 统一
3. 训练完成后将 LoRA adapter merge 回基座 Qwen 模型
4. 将 merge 后的 HuggingFace 模型导出为 GGUF
5. 将 GGUF 量化为 `Q4_K_M`
6. 使用 `llama.cpp` 做最终运行时验证
7. 将最终 `GGUF` 交付给当前 `llm-service`

该方案的核心原则是：

- 训练时使用最适合 Qwen 的生态
- 部署时回到当前最稳定、最高效的 `llama.cpp`
- 中间过程保留可恢复、可重新量化、可复现实验状态

## Repository Layout

所有新增内容位于 `TrafficLLM-master/` 下：

```text
TrafficLLM-master/
├── qwen_pipeline/
│   ├── README.md
│   ├── bootstrap_cloud.sh
│   ├── bootstrap_local_smoke.sh
│   ├── requirements-qwen.txt
│   ├── train_qwen_lora.py
│   ├── resume_qwen_lora.py
│   ├── merge_lora.py
│   ├── export_gguf.sh
│   ├── quantize_q4km.sh
│   ├── verify_llama_cpp.py
│   ├── build_manifest.py
│   ├── configs/
│   │   ├── local-smoke.yaml
│   │   ├── colab.yaml
│   │   ├── modelscope.yaml
│   │   └── label_mapping.yaml
│   ├── prompts/
│   │   ├── train_prompt_v1.jinja
│   │   └── inference_prompt_v1.txt
│   ├── data/
│   │   ├── prepare_edge_dataset.py
│   │   ├── dataset_registry.py
│   │   ├── label_mapper.py
│   │   ├── prompt_builder.py
│   │   └── sampling.py
│   ├── artifacts/
│   │   ├── manifests/
│   │   ├── smoke/
│   │   └── eval/
│   └── docs/
│       ├── cloud-colab.md
│       ├── cloud-modelscope.md
│       ├── recovery.md
│       └── deployment-handoff.md
```

说明：

- `qwen_pipeline/` 是新增训练子系统的唯一根目录
- `data/` 负责数据集扫描、抽样、标签归一、prompt 构造
- `configs/` 负责本地与不同云环境的配置切换
- `artifacts/` 仅存放该子系统的输出和验证结果
- 当前项目根目录仅接收最终模型文件和必要运行配置调整

## Data Strategy

### Training Objective

第一版只训练一个可直接服务当前 `edge-agent` 的统一威胁分类模型，而不是复刻 TrafficLLM 的多任务专项模型集合。

### Unified Label Space

统一标签空间定义为：

- `Normal`
- `Malware`
- `Botnet`
- `C2`
- `DDoS`
- `Scan`
- `Other`

### Dataset Selection

第一版主训练集优先使用与当前边缘威胁分类目标最接近的数据：

- `ustc-tfc-2016`
- `iscx-botnet-2014`
- `dapt-2020`
- `dohbrw-2020`
- 可选：`csic-2010`

以下数据集不直接作为第一版主训练集：

- `iscx-tor-2016`
- `iscx-vpn-2016`
- `cstnet-2023`
- `app53-2023`
- `cw100-2018-2024`

原因：

- 这些数据更多是应用行为分类或环境识别任务
- 直接加入主任务会污染当前“威胁语义分类”目标
- 第一版优先保证输出语义与 `edge-agent` 当前架构对齐

### Label Mapping Rules

归一映射由 `configs/label_mapping.yaml` 管理，示例策略：

- `ustc-tfc-2016`
  - benign app -> `Normal`
  - malware family -> `Malware`
- `iscx-botnet-2014`
  - `normal` -> `Normal`
  - bot family / botnet family -> `Botnet`
  - 明确 C&C 行为可映射 `C2`
- `dapt-2020`
  - APT / intrusion / remote-control patterns -> `C2` 或 `Other`
- `dohbrw-2020`
  - malicious DoH -> `C2` 或 `Other`
- `csic-2010`
  - web attack -> `Other`

该映射文件必须可配置，不允许硬编码在训练脚本中。

### Input Representation

训练输入沿用 TrafficLLM 的 `instruction/output` 数据格式，但第一版不会直接复用所有旧模板。

统一输入策略：

- 优先使用当前项目更接近线上推理的流文本表示
- 保留 `TrafficLLM` 的任务指令风格
- 保持 `<packet>` 或 `<flow>` 标识
- 避免训练时过度依赖线上不提供的字段

训练样本目标格式：

```json
{"instruction": "Analyze the following network traffic flow ... Categories: Normal, Malware, Botnet, C2, DDoS, Scan, Other.\n\nFive-tuple: ...\n\n<packet>: ...\n\nClassification:", "output": "Botnet"}
```

### Sampling Strategy

数据非常多，第一版必须支持分阶段抽样：

- 本地 smoke test：每类极小样本
- 云端快速验证：每类小样本
- 云端正式训练：按配置上限抽样

抽样要求：

- 类别平衡优先
- 支持按数据集上限裁剪
- 支持固定随机种子
- 支持将抽样结果固化为 manifest，保证可复现

## Training Pipeline

### Local Smoke Validation

本地验证只解决“链路通不通”，不追求性能：

1. 从选定数据集抽极小样本
2. 生成统一 JSONL 训练集/验证集
3. 启动极短步数的 LoRA 训练
4. merge 到基座模型
5. 导出高精 GGUF
6. 量化为 `Q4_K_M`
7. 使用 `llama.cpp` 跑固定 prompt 验证

本地 smoke test 成功的判断标准：

- 训练脚本可启动并保存 checkpoint
- merge 能生成完整 HuggingFace 模型
- HF 模型能转换为 GGUF
- GGUF 能量化为 `Q4_K_M`
- 量化模型能在 `llama.cpp` 下对固定 prompt 产出可解析标签

### Cloud Training

正式训练在云端进行，默认训练过程采用 LoRA。

训练阶段要求：

- 基座模型路径来自 `TrafficLLM-master/models/qwen0.8b/qwen3.5-0.8b/`
- 仅训练 LoRA adapter
- 定期保存 checkpoint
- 定期写入 trainer state 和 manifest
- 中断后可从最新 checkpoint 恢复

第一版采用单阶段任务训练，而不是强制复用 ChatGLM 版本的双阶段 Prefix Tuning。

原因：

- 当前目标是尽快产出与现有部署链路兼容的单模型
- LoRA 更适合会话受限的云端环境
- adapter 小，断点恢复成本低
- 训练完成后可 merge，适合回归 `llama.cpp`

### LoRA Configuration

默认 LoRA 配置参考 TrafficLLM Qwen 草案，但配置项必须外置：

- `r = 8`
- `alpha = 16`
- `lora_dropout = 0.05`
- task type = `CAUSAL_LM`
- target modules:
  - `q_proj`
  - `k_proj`
  - `v_proj`
  - `o_proj`
  - `gate_proj`
  - `up_proj`
  - `down_proj`

同时支持通过配置覆盖：

- batch size
- gradient accumulation
- learning rate
- max steps / epochs
- max length
- eval interval
- save interval
- resume path

## Prompt Design

线上推理稳定性优先，因此第一版训练目标只要求输出单标签，不要求输出 JSON。

训练 prompt 原则：

- 明确输入是 traffic flow / packet text
- 明确输出类别空间
- 保持短输出目标
- 尽量贴近当前 `edge-agent` 调用时的 prompt 结构

推理 prompt 原则：

- 继续支持 `llama.cpp /completion`
- 明确类别集合
- 结尾保留 `Classification:` 锚点
- 避免复杂多轮 chat 依赖

第一版训练输出仅为标签词，原因：

- 量化后短标签生成最稳定
- 当前 `edge-agent` 响应解析逻辑也更容易承接
- 后续如需结构化 JSON，可在模型稳定后单独演进

## Merge, Export, and Quantization

训练完成后，产物链路如下：

1. `adapter checkpoint`
2. `merge_lora.py` 输出完整 HF 模型
3. `export_gguf.sh` 调用 `llama.cpp` 的 HF->GGUF 转换工具，输出高精 GGUF
4. `quantize_q4km.sh` 调用 `llama-quantize` 输出最终 `Q4_K_M.gguf`
5. `verify_llama_cpp.py` 使用固定 prompt 集验证最终模型

### Artifact Requirements

每次成功训练后至少保留：

- LoRA adapter 目录
- merge 后 HF 模型 manifest
- 高精 GGUF 文件路径或 manifest
- 最终 `Q4_K_M.gguf`
- 评估结果 JSON
- 训练配置快照
- 数据抽样 manifest

### Naming Convention

建议统一命名：

```text
Qwen3.5-0.8B-TrafficLLM-Edge-v1/
Qwen3.5-0.8B-TrafficLLM-Edge-v1-f16.gguf
Qwen3.5-0.8B-TrafficLLM-Edge-v1-Q4_K_M.gguf
```

## Runtime Integration

### llm-service

第一版不替换 `llm-service` 技术栈，只修改模型文件和配置：

- 继续使用 `llama.cpp`
- 继续暴露 `/completion`
- 只更新挂载模型路径和文件名

### edge-agent

第一版尽量少改：

- 保持 `call_llm_service()` 接口不变
- 调整 prompt 模板，使其与训练 prompt 更一致
- 解析器继续从短文本标签提取最终分类

必要时允许新增一个轻量配置位，例如：

- `MODEL_PROFILE=edge-qwen-v1`

用于区分不同 prompt / stop token / label parsing 配置，但不引入新的调用协议。

### Architecture Change Scope

允许修改当前架构配置，但限于：

- `llm-service` 模型路径或镜像构建参数
- `edge-agent` prompt 版本化配置
- 部署文档中模型准备步骤

不允许在第一版中引入：

- 线上 HF/PEFT 推理服务
- 多模型动态路由
- 新的 RPC 协议

## Cloud Execution Design

### One-Click Entry

云端环境统一入口为：

- `bootstrap_cloud.sh`

该入口负责：

1. 安装依赖
2. 校验数据与模型路径
3. 准备输出目录
4. 根据配置启动训练或恢复训练
5. 训练完成后自动触发 merge / GGUF 导出 / Q4_K_M 量化 / 运行时验证
6. 生成交付 manifest

云平台差异通过配置文件适配：

- `configs/colab.yaml`
- `configs/modelscope.yaml`

### Resume Strategy

为适配时限环境，训练必须天然支持恢复：

- 周期性保存 checkpoint
- 在持久化目录写入最新 checkpoint 标记
- 新会话启动时自动检测并恢复
- merge / export / quantize 支持独立重跑

这意味着“训练状态”和“模型导出状态”必须分离，避免导出失败后重新训练。

### Persistent Outputs

所有长时保留文件必须输出到云端可持久目录：

- checkpoints
- logs
- manifests
- eval results
- merged model metadata
- gguf metadata

脚本不得假定 notebook 临时目录可长期存在。

## Verification Strategy

### Local Verification

本地只做极小规模 smoke test：

- 数据抽样正确
- 训练脚本可跑
- merge 成功
- GGUF 导出成功
- `Q4_K_M` 量化成功
- `llama.cpp` 推理结果可解析

### Cloud Verification

云端验证包括两类：

1. 训练期指标
   - train loss
   - eval loss
   - per-label metrics
2. 最终运行时验证
   - merge 后 HF 模型抽样输出
   - `llama.cpp` 下 GGUF 抽样输出
   - 固定 prompt 集的一致性检查

必须验证“量化后模型”而不只验证“merge 后 HF 模型”。

### Acceptance Criteria

一版可接受的完成标准：

- 本地 smoke test 全链路通过
- 云端可一键启动训练
- 云端中断后能从 checkpoint 恢复
- 最终成功产出 `Q4_K_M.gguf`
- 最终模型可由 `llama.cpp` 正常运行
- 最终标签空间与当前 `edge-agent` 架构兼容

## Risks and Mitigations

### Risk 1: 标签语义混杂

风险：

- 将 VPN/Tor/App 行为分类数据直接混入主任务会损害威胁分类稳定性

缓解：

- 第一版严格限定主训练数据集
- 使用外置标签映射
- 将易污染数据集延后纳入

### Risk 2: 量化后输出退化

风险：

- HF 模型表现正常，但 `Q4_K_M` 下标签输出不稳定

缓解：

- 第一版只训练短标签输出
- 固定推理 prompt
- 在 `llama.cpp` 运行时做最终验证

### Risk 3: 云端训练中断

风险：

- Colab / ModelScope Notebook 会话超时导致训练终止

缓解：

- 使用 LoRA 而非全量训练
- 高频 checkpoint
- 单入口自动恢复
- 导出步骤独立于训练步骤

### Risk 4: 训练产物无法顺利导出 GGUF

风险：

- merge 后模型格式或 tokenizer 与导出脚本不兼容

缓解：

- 本地 smoke test 必须提前验证导出链路
- 在文档中锁定可用 `llama.cpp` 版本
- 产出 manifest 记录转换命令和版本

## Testing Plan

实现阶段测试应至少覆盖：

- 标签映射单元测试
- 数据抽样与 manifest 稳定性测试
- prompt 构建测试
- 训练配置解析测试
- checkpoint 恢复逻辑测试
- merge 命令构建测试
- GGUF 导出命令构建测试
- `llama.cpp` 验证脚本测试
- 端到端 smoke test

## Rollout Plan

建议分三步交付：

1. 本地链路打通
   - 小样本预处理
   - 短步数 LoRA
   - merge / GGUF / quantize / llama.cpp 验证
2. 云端一键训练
   - Colab / ModelScope 配置
   - 断点恢复
   - 自动产出交付物
3. 当前项目接入
   - 替换模型
   - 微调 prompt / parser
   - 更新部署文档

## Open Decisions Resolved

本设计已明确以下决策：

- 采用单模型统一训练，而非多专项模型
- 训练阶段允许使用 `Transformers + PEFT`
- 部署阶段严格使用 `llama.cpp + GGUF`
- 最终量化格式为 `Q4_K_M`
- 所有训练相关内容只放在 `TrafficLLM-master/`
- 本地只做 smoke test，正式训练在云端
- 云端必须支持一键启动和断点恢复

## Implementation Handoff

后续实施计划应围绕以下工作包展开：

1. 数据归一与标签映射子系统
2. Qwen LoRA 训练与恢复子系统
3. merge / GGUF 导出 / 量化子系统
4. `llama.cpp` 验证与交付 manifest 子系统
5. 云端启动与恢复文档
6. 当前项目的最小接入改动
