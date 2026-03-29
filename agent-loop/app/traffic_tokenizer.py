"""
探微 (Tanwei) - 跨模态分词模块
复用 TrafficLLM 的预处理逻辑，将流量转换为 Token 序列
"""

import os
import sys
from typing import List, Optional, Tuple

from loguru import logger

# 添加 TrafficLLM 路径
TRAFFICLLM_PATH = os.environ.get("TRAFFICLLM_PATH", "/app/TrafficLLM")
if os.path.exists(TRAFFICLLM_PATH):
    sys.path.insert(0, TRAFFICLLM_PATH)


class TrafficTokenizer:
    """
    流量分词器：将网络流量转换为 LLM 可理解的文本格式

    设计原则：
    1. 不依赖 PyTorch/Transformers 等重型框架
    2. 使用轻量级的文本预处理
    3. 生成符合 TrafficLLM 指令格式的文本
    """

    # Token 长度约束
    MAX_TOKEN_LENGTH = 690

    # 检测任务指令模板
    DETECTION_INSTRUCTION = (
        "Given the following traffic data <packet> that contains protocol fields, "
        "traffic features, and payloads. Please classify this traffic and determine "
        "if it is normal or malicious. If malicious, identify the threat type. "
        "Categories include: 'Normal', 'Malware', 'Botnet', 'C&C', 'DDoS', 'Scan', 'Other'."
    )

    # 简化的检测指令
    SIMPLE_INSTRUCTION = (
        "Analyze the following network traffic packet data. "
        "Classify as: Normal, Malware, Botnet, C&C, DDoS, Scan, or Other."
    )

    def __init__(self, max_token_length: int = 690):
        self.max_token_length = max_token_length
        logger.info(f"TrafficTokenizer initialized: max_token_length={max_token_length}")

    def _estimate_token_count(self, text: str) -> int:
        """
        估算 Token 数量
        使用简单的启发式方法：平均每 4 个字符约等于 1 个 token
        """
        # 对于十六进制数据，比例会有所不同
        # 英文文本约 4 字符/token
        # 十六进制数据约 2 字符/token（因为词汇表通常没有这些组合）
        hex_chars = sum(1 for c in text if c in '0123456789abcdefABCDEF')
        other_chars = len(text) - hex_chars

        estimated_tokens = (hex_chars // 2) + (other_chars // 4)
        return estimated_tokens

    def _truncate_to_token_limit(self, text: str) -> Tuple[str, bool]:
        """
        截断文本以符合 Token 长度限制

        Returns:
            (截断后的文本, 是否被截断)
        """
        estimated = self._estimate_token_count(text)

        if estimated <= self.max_token_length:
            return text, False

        # 需要截断
        # 保留指令部分，截断数据部分
        ratio = self.max_token_length / estimated
        target_length = int(len(text) * ratio * 0.95)  # 留 5% 余量

        truncated = text[:target_length]
        return truncated, True

    def build_detection_prompt(self, flow_text: str, five_tuple: dict) -> str:
        """
        构建检测任务的提示词

        Args:
            flow_text: 流的文本表示
            five_tuple: 五元组信息

        Returns:
            完整的提示词
        """
        # 构建元信息
        meta_info = (
            f"Source: {five_tuple.get('src_ip', 'unknown')}:{five_tuple.get('src_port', 0)}, "
            f"Destination: {five_tuple.get('dst_ip', 'unknown')}:{five_tuple.get('dst_port', 0)}, "
            f"Protocol: {five_tuple.get('protocol', 'unknown')}"
        )

        # 构建完整提示
        prompt = (
            f"{self.SIMPLE_INSTRUCTION}\n\n"
            f"Five-tuple: {meta_info}\n\n"
            f"<packet>: {flow_text}\n\n"
            f"Classification:"
        )

        return prompt

    def tokenize_flow(self, flow_text: str, five_tuple: dict) -> Tuple[str, int, bool]:
        """
        将流数据转换为 Token 序列

        Args:
            flow_text: 流的文本表示
            five_tuple: 五元组信息

        Returns:
            (提示词, Token 数量估算, 是否被截断)
        """
        # 构建提示词
        prompt = self.build_detection_prompt(flow_text, five_tuple)

        # 截断到限制
        truncated_prompt, was_truncated = self._truncate_to_token_limit(prompt)

        # 重新估算 Token 数量
        token_count = self._estimate_token_count(truncated_prompt)

        return truncated_prompt, token_count, was_truncated

    def parse_llm_response(self, response: str) -> dict:
        """
        解析 LLM 响应，提取分类结果

        Args:
            response: LLM 返回的文本

        Returns:
            分类结果字典
        """
        response = response.strip().lower()

        # 定义类别关键词
        categories = {
            "malware": ["malware", "malicious", "virus", "trojan", "worm", "ransomware"],
            "botnet": ["botnet", "bot", "zombie", "c&c", "command and control", "cc"],
            "ddos": ["ddos", "dos", "denial of service", "flood"],
            "scan": ["scan", "scanner", "reconnaissance", "probe", "port scan"],
            "normal": ["normal", "benign", "legitimate", "safe"],
            "other": ["other", "unknown", "suspicious"]
        }

        # 匹配类别
        detected_label = "Unknown"
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in response:
                    detected_label = category.capitalize()
                    if category in ["malware", "botnet", "ddos", "scan"]:
                        detected_label = category.capitalize()
                    elif category == "normal":
                        detected_label = "Normal"
                    else:
                        detected_label = "Suspicious"
                    break
            if detected_label != "Unknown":
                break

        return {
            "primary_label": detected_label,
            "secondary_label": None,
            "raw_response": response[:200]  # 保留原始响应前 200 字符
        }


class TrafficTextBuilder:
    """
    流量文本构建器
    参考 TrafficLLM 的预处理逻辑
    """

    @staticmethod
    def build_packet_text(packet_hex: str, max_length: int = 256) -> str:
        """
        将单个包的十六进制数据转换为文本格式

        类似 TrafficLLM 的 "traffic words" 特征
        """
        # 截断到最大长度
        truncated = packet_hex[:max_length]

        # 可以添加空格分隔以增加可读性
        # byte_list = [truncated[i:i+2] for i in range(0, len(truncated), 2)]
        # return " ".join(byte_list)

        return truncated

    @staticmethod
    def build_flow_text(packet_hex_list: List[str], max_packets: int = 10, max_packet_length: int = 256) -> str:
        """
        构建流的文本表示

        格式：<pck>hex_data<pck>hex_data...
        """
        truncated_packets = packet_hex_list[:max_packets]

        formatted_packets = []
        for packet_hex in truncated_packets:
            truncated = packet_hex[:max_packet_length]
            formatted_packets.append(truncated)

        flow_text = "<pck>" + "<pck>".join(formatted_packets)
        return flow_text

    @staticmethod
    def build_instruction_text(flow_text: str, task_type: str = "detection") -> str:
        """
        构建带指令的完整文本

        参考 TrafficLLM 的 build_td_text_dataset 函数
        """
        if task_type == "detection":
            instruction = (
                "Given the following traffic data <packet> that contains protocol fields, "
                "traffic features, and payloads. Please classify this traffic and determine "
                "if it is normal or malicious. Categories include: Normal, Malware, Botnet, "
                "C&C, DDoS, Scan, Other."
            )
        else:
            instruction = "Analyze the following network traffic:"

        full_text = f"{instruction}\n<packet>: {flow_text}"
        return full_text
