# llama.cpp Server Dockerfile
# 用于构建 Qwen3.5-0.8B 本地推理引擎

FROM ubuntu:22.04 AS builder

# 安装编译依赖
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    cmake \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 克隆并编译 llama.cpp
WORKDIR /build
RUN git clone --depth 1 https://github.com/ggerganov/llama.cpp.git . \
    && mkdir build \
    && cd build \
    && cmake .. -DLLAMA_BUILD_SERVER=ON \
    && cmake --build . --config Release -j$(nproc) \
    # 验证编译产物
    && ls -la bin/ || ls -la ../

# 运行时镜像
FROM ubuntu:22.04

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制可执行文件
COPY --from=builder /build/build/bin/llama-server /usr/local/bin/llama-server

# 验证可执行文件存在
RUN test -f /usr/local/bin/llama-server || (echo "llama-server not found, checking alternative paths..." && exit 1)

# 创建模型目录
RUN mkdir -p /models

# 暴露端口
EXPOSE 8080

# 健康检查脚本
COPY healthcheck.sh /healthcheck.sh
RUN chmod +x /healthcheck.sh

# 默认启动命令
ENTRYPOINT ["/usr/local/bin/llama-server"]
CMD ["--help"]
