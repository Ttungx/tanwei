# LLM Service - Qwen3.5-0.8B 推理引擎

## 服务概述

本容器使用 llama.cpp server 模式运行 Qwen3.5-0.8B INT4 量化模型，为 EdgeAgent 提供 LLM 推理能力。

## 技术规格

| 属性 | 值 |
|------|-----|
| 基础镜像 | ghcr.io/ggerganov/llama.cpp:server |
| 模型 | Qwen3.5-0.8B-Q4_K_M.gguf |
| 模型大小 | ~508MB |
| 量化方式 | INT4 (Q4_K_M) |
| 上下文长度 | 2048 tokens |
| 服务端口 | 8080 |

## 启动参数说明

```bash
llama-server \
  --model /models/Qwen3.5-0.8B-Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --ctx-size 2048 \        # 上下文窗口大小
  --n-gpu-layers 0 \       # CPU 推理（边缘设备无 GPU）
  --threads 2 \            # 推理线程数
  --memory-f32 0           # 使用半精度节省内存
```

## API 调用示例

### 文本补全

```bash
curl http://localhost:8080/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Given the following traffic data, classify the threat:",
    "n_predict": 64,
    "temperature": 0.1,
    "stop": ["</s>", "\n"]
  }'
```

### 健康检查

```bash
curl http://localhost:8080/health
```

### 获取模型信息

```bash
curl http://localhost:8080/props
```

## 资源约束

- **内存限制**: 1GB
- **CPU**: 2 线程
- **预计推理速度**: ~15-30 tokens/s (CPU)

## 注意事项

1. 首次启动需加载模型，约需 5-10 秒
2. 该容器不包含 Python 运行时，纯 C/C++ 实现
3. 模型文件以只读方式挂载，确保安全性
