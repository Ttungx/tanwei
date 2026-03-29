#!/usr/bin/env python3
"""
LLM Service 测试脚本
用于验证 llama.cpp server 是否正常工作

用法:
    python test_llm.py [--host HOST] [--port PORT]
"""

import argparse
import json
import requests
import time


def test_health(base_url: str) -> bool:
    """测试健康检查端点"""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✓ Health check passed")
            return True
        else:
            print(f"✗ Health check failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def test_props(base_url: str) -> bool:
    """获取模型属性"""
    try:
        response = requests.get(f"{base_url}/props", timeout=10)
        if response.status_code == 200:
            props = response.json()
            print(f"✓ Model properties:")
            print(f"  - CPU Info: {props.get('cpu_info', 'N/A')}")
            print(f"  - Total Threads: {props.get('total_threads', 'N/A')}")
            return True
        else:
            print(f"✗ Props request failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Props request failed: {e}")
        return False


def test_completion(base_url: str, prompt: str) -> bool:
    """测试文本补全"""
    payload = {
        "prompt": prompt,
        "n_predict": 32,
        "temperature": 0.1,
        "stop": ["</s>", "\n\n"]
    }

    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/completion",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=60
        )
        elapsed = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            content = result.get("content", "")
            tokens_predicted = result.get("tokens_predicted", 0)
            tokens_evaluated = result.get("tokens_evaluated", 0)

            print(f"✓ Completion successful:")
            print(f"  - Prompt tokens: {tokens_evaluated}")
            print(f"  - Generated tokens: {tokens_predicted}")
            print(f"  - Time: {elapsed:.2f}s")
            print(f"  - Response: {content[:100]}...")
            return True
        else:
            print(f"✗ Completion failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Completion failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test LLM Service")
    parser.add_argument("--host", default="localhost", help="LLM service host")
    parser.add_argument("--port", type=int, default=8080, help="LLM service port")
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"
    print(f"Testing LLM Service at {base_url}")
    print("=" * 50)

    # 测试健康检查
    if not test_health(base_url):
        print("\n服务未就绪，请确保 llama.cpp server 正在运行")
        return

    # 测试模型属性
    test_props(base_url)

    # 测试文本补全
    test_prompt = "Given the following network traffic data, classify if it is malicious or normal:"
    print(f"\n测试补全提示: {test_prompt}")
    test_completion(base_url, test_prompt)

    # 测试流量分类提示
    traffic_prompt = """Analyze this network traffic and classify the threat type:
<src_ip>192.168.1.100</src_ip>
<dst_ip>10.0.0.1</dst_ip>
<dst_port>443</dst_port>
<protocol>TCP</protocol>
<payload_size>512</payload_size>

Classification:"""

    print(f"\n测试流量分类提示...")
    test_completion(base_url, traffic_prompt)

    print("\n" + "=" * 50)
    print("测试完成")


if __name__ == "__main__":
    main()
