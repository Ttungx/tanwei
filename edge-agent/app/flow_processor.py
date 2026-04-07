"""
探微 (Tanwei) - 流重组与特征提取模块
负责五元组流重组、双重截断、统计特征提取
"""

import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import binascii

import numpy as np
from scapy.all import IP, TCP, UDP
from loguru import logger


# 日志配置
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>edge-agent</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)


def setup_logger():
    """配置 logger"""
    logger.remove()
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_format = os.environ.get("LOG_FORMAT", "console").lower()

    if log_format == "json":
        format_str = '{"timestamp": "{time:YYYY-MM-DDTHH:mm:ss.SSSZ}", "level": "{level}", "service": "edge-agent", "function": "{function}", "line": {line}, "message": "{message}"}'
    else:
        format_str = LOG_FORMAT

    logger.add(
        sink=sys.stdout,
        format=format_str,
        level=log_level,
        colorize=(log_format != "json"),
        enqueue=True,
    )
    return logger.bind(service="edge-agent")


logger = setup_logger()


@dataclass
class FiveTuple:
    """五元组数据结构"""
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str

    def to_dict(self) -> dict:
        return {
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "protocol": self.protocol
        }

    def __hash__(self):
        return hash((self.src_ip, self.dst_ip, self.src_port, self.dst_port, self.protocol))

    def __eq__(self, other):
        if not isinstance(other, FiveTuple):
            return False
        return (
            self.src_ip == other.src_ip and
            self.dst_ip == other.dst_ip and
            self.src_port == other.src_port and
            self.dst_port == other.dst_port and
            self.protocol == other.protocol
        )


@dataclass
class PacketInfo:
    """数据包信息"""
    timestamp: float
    size: int
    tcp_flags: int = 0
    payload: bytes = b""
    raw_data: bytes = b""

    # TCP 标志位解析
    @property
    def flag_syn(self) -> int:
        return (self.tcp_flags & 0x02) >> 1

    @property
    def flag_ack(self) -> int:
        return (self.tcp_flags & 0x10) >> 4

    @property
    def flag_fin(self) -> int:
        return self.tcp_flags & 0x01

    @property
    def flag_rst(self) -> int:
        return (self.tcp_flags & 0x04) >> 2

    @property
    def flag_psh(self) -> int:
        return (self.tcp_flags & 0x08) >> 3


@dataclass
class Flow:
    """双向会话流"""
    five_tuple: FiveTuple
    packets: List[PacketInfo] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0

    def add_packet(self, packet: PacketInfo):
        """添加数据包到流"""
        if not self.packets:
            self.start_time = packet.timestamp
        self.packets.append(packet)
        self.end_time = packet.timestamp

    @property
    def duration(self) -> float:
        """流持续时间（秒）"""
        if not self.packets:
            return 0.0
        return self.end_time - self.start_time

    @property
    def total_bytes(self) -> int:
        """总字节数"""
        return sum(p.size for p in self.packets)

    @property
    def packet_count(self) -> int:
        """数据包数量"""
        return len(self.packets)


class FlowProcessor:
    """流处理器：五元组重组 + 双重截断 + 特征提取"""

    # 配置参数
    MAX_TIME_WINDOW = 60  # 时间窗口最大值（秒）
    MAX_PACKET_COUNT = 10  # 最大包数量
    MAX_PACKET_LENGTH = 256  # 单包最大长度（字节）

    def __init__(self, max_time_window: int = 60, max_packet_count: int = 10):
        self.max_time_window = max_time_window
        self.max_packet_count = max_packet_count
        logger.info(f"FlowProcessor initialized: time_window={max_time_window}s, max_packets={max_packet_count}")

    def _get_five_tuple(self, packet) -> Optional[FiveTuple]:
        """从数据包提取五元组"""
        if not packet.haslayer(IP):
            return None

        ip_layer = packet[IP]
        src_ip = ip_layer.src
        dst_ip = ip_layer.dst
        protocol = "Unknown"
        src_port = 0
        dst_port = 0

        if packet.haslayer(TCP):
            protocol = "TCP"
            tcp_layer = packet[TCP]
            src_port = tcp_layer.sport
            dst_port = tcp_layer.dport
        elif packet.haslayer(UDP):
            protocol = "UDP"
            udp_layer = packet[UDP]
            src_port = udp_layer.sport
            dst_port = udp_layer.dport
        else:
            protocol_num = ip_layer.proto
            protocol = f"IP_{protocol_num}"

        return FiveTuple(
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_port=src_port,
            dst_port=dst_port,
            protocol=protocol
        )

    def _get_packet_info(self, packet) -> Optional[PacketInfo]:
        """从数据包提取信息"""
        try:
            timestamp = float(packet.time)
            size = len(packet)
            tcp_flags = 0
            payload = b""

            if packet.haslayer(TCP):
                tcp_flags = int(packet[TCP].flags)
                if packet.haslayer(TCP):
                    payload = bytes(packet[TCP].payload)
            elif packet.haslayer(UDP):
                payload = bytes(packet[UDP].payload)

            raw_data = bytes(packet)

            return PacketInfo(
                timestamp=timestamp,
                size=size,
                tcp_flags=tcp_flags,
                payload=payload,
                raw_data=raw_data
            )
        except Exception as e:
            logger.warning(f"Failed to extract packet info: {e}")
            return None

    def _normalize_five_tuple(self, five_tuple: FiveTuple) -> FiveTuple:
        """
        标准化五元组，确保双向流归并到同一会话
        规则：将较小的 IP:Port 组合放在前面
        """
        endpoint1 = (five_tuple.src_ip, five_tuple.src_port)
        endpoint2 = (five_tuple.dst_ip, five_tuple.dst_port)

        if endpoint1 > endpoint2:
            return FiveTuple(
                src_ip=five_tuple.dst_ip,
                dst_ip=five_tuple.src_ip,
                src_port=five_tuple.dst_port,
                dst_port=five_tuple.src_port,
                protocol=five_tuple.protocol
            )
        return five_tuple

    def extract_flows(self, pcap_path: str) -> List[Flow]:
        """
        阶段1：基于五元组的流重组（流式读取，防 OOM）

        Args:
            pcap_path: Pcap 文件路径

        Returns:
            流列表
        """
        from scapy.all import PcapReader
        logger.info(f"Extracting flows from: {pcap_path} in stream mode")

        # 流重组字典
        flows_dict: Dict[FiveTuple, Flow] = {}
        packet_count = 0

        try:
            with PcapReader(pcap_path) as pcap_reader:
                for packet in pcap_reader:
                    packet_count += 1
                    five_tuple = self._get_five_tuple(packet)
                    if five_tuple is None:
                        continue

                    packet_info = self._get_packet_info(packet)
                    if packet_info is None:
                        continue

                    # 标准化五元组以合并双向流
                    normalized_tuple = self._normalize_five_tuple(five_tuple)

                    if normalized_tuple not in flows_dict:
                        flows_dict[normalized_tuple] = Flow(five_tuple=normalized_tuple)

                    flow = flows_dict[normalized_tuple]
                    
                    # 物理截断防线：包数达标或时间超窗口直接跳过记录
                    if flow.packet_count >= self.max_packet_count:
                        continue
                    if flow.packet_count > 0 and (packet_info.timestamp - flow.start_time) > self.max_time_window:
                        continue
                        
                    flow.add_packet(packet_info)
        except Exception as e:
            logger.error(f"Failed to read pcap file: {e}")
            return []

        flows = list(flows_dict.values())
        logger.info(f"Extracted {len(flows)} flows from {packet_count} packets")

        return flows

    def truncate_flow(self, flow: Flow) -> Flow:
        """
        阶段2：双重特征截断
        - 时间窗口 <= max_time_window 秒
        - 提取包数量 <= max_packet_count 个
        """
        truncated_packets = []
        start_time = None

        for packet in flow.packets:
            # 初始化起始时间
            if start_time is None:
                start_time = packet.timestamp
                truncated_packets.append(packet)
                continue

            # 时间窗口检查
            time_elapsed = packet.timestamp - start_time
            if time_elapsed > self.max_time_window:
                break

            # 包数量检查
            if len(truncated_packets) >= self.max_packet_count:
                break

            truncated_packets.append(packet)

        # 创建截断后的流
        truncated_flow = Flow(
            five_tuple=flow.five_tuple,
            packets=truncated_packets,
            start_time=truncated_packets[0].timestamp if truncated_packets else 0.0,
            end_time=truncated_packets[-1].timestamp if truncated_packets else 0.0
        )

        return truncated_flow

    def extract_statistical_features(self, flow: Flow) -> dict:
        """
        提取 32 维统计特征用于 SVM 分类

        参考: docs/references/dataset-feature-engineering.md

        Returns:
            特征字典，符合 SVM 服务 API 规范 (32 维)
        """
        if not flow.packets:
            return {}

        n = len(flow.packets)
        packet_sizes = [p.size for p in flow.packets]
        inter_arrival_times = []

        for i in range(1, len(flow.packets)):
            iat = flow.packets[i].timestamp - flow.packets[i-1].timestamp
            inter_arrival_times.append(iat)

        # TCP 标志统计
        flag_syn = sum(p.flag_syn for p in flow.packets)
        flag_ack = sum(p.flag_ack for p in flow.packets)
        flag_fin = sum(p.flag_fin for p in flow.packets)
        flag_rst = sum(p.flag_rst for p in flow.packets)
        flag_psh = sum(p.flag_psh for p in flow.packets)

        # 协议判断
        protocol = flow.five_tuple.protocol
        is_tcp = 1 if protocol == "TCP" else 0
        is_udp = 1 if protocol == "UDP" else 0
        ip_proto = 6 if is_tcp else (17 if is_udp else 0)

        # TCP 头长度（假设标准 20 字节 + 选项）
        tcp_hdr_lens = []
        window_sizes = []
        for p in flow.packets:
            if is_tcp:
                # 从原始数据中提取 TCP 头长度（简化：使用默认值）
                tcp_hdr_lens.append(32)  # 默认 32 字节（含选项）
                window_sizes.append(65535)  # 默认窗口大小
            else:
                tcp_hdr_lens.append(0)
                window_sizes.append(0)

        # TTL 提取（需要从 IP 层获取，这里使用默认值）
        ip_ttls = [64] * n  # 默认 TTL
        ip_lens = packet_sizes  # 简化：使用帧长度
        tcp_lens = [p.size - 40 for p in flow.packets]  # 简化：减去 IP+TCP 头

        # 流持续时间
        flow_duration = flow.duration if flow.duration > 0 else 0.001

        # 端口熵计算（简化版）
        def calc_entropy(values):
            if not values:
                return 0.0
            from collections import Counter
            counter = Counter(values)
            total = len(values)
            entropy = 0.0
            for count in counter.values():
                if count > 0:
                    p = count / total
                    entropy -= p * np.log2(p + 1e-10)
            return entropy

        dst_port = flow.five_tuple.dst_port
        src_port = flow.five_tuple.src_port

        # 内网 IP 判断
        def is_internal_ip(ip: str) -> int:
            if not ip:
                return 0
            parts = ip.split('.')
            if len(parts) != 4:
                return 0
            try:
                first = int(parts[0])
                second = int(parts[1])
                if first == 10:
                    return 1
                if first == 172 and 16 <= second <= 31:
                    return 1
                if first == 192 and second == 168:
                    return 1
            except ValueError:
                return 0
            return 0

        # 构建 32 维特征字典
        features = {
            # A. 基础统计特征 (0-7)
            "avg_packet_len": float(np.mean(packet_sizes)) if packet_sizes else 0.0,
            "std_packet_len": float(np.std(packet_sizes)) if n > 1 else 0.0,
            "avg_ip_len": float(np.mean(ip_lens)) if ip_lens else 0.0,
            "std_ip_len": float(np.std(ip_lens)) if n > 1 else 0.0,
            "avg_tcp_len": float(np.mean(tcp_lens)) if tcp_lens else 0.0,
            "std_tcp_len": float(np.std(tcp_lens)) if n > 1 else 0.0,
            "total_bytes": float(flow.total_bytes),
            "avg_ttl": float(np.mean(ip_ttls)) if ip_ttls else 64.0,

            # B. 协议类型特征 (8-11)
            "ip_proto": float(ip_proto),
            "tcp_ratio": float(is_tcp),
            "udp_ratio": float(is_udp),
            "other_proto_ratio": float(0 if (is_tcp or is_udp) else 1),

            # C. TCP 行为特征 (12-19)
            "avg_window_size": float(np.mean(window_sizes)) if window_sizes else 0.0,
            "std_window_size": float(np.std(window_sizes)) if n > 1 else 0.0,
            "syn_count": flag_syn,
            "ack_count": flag_ack,
            "push_count": flag_psh,
            "fin_count": flag_fin,
            "rst_count": flag_rst,
            "avg_hdr_len": float(np.mean(tcp_hdr_lens)) if tcp_hdr_lens else 0.0,

            # D. 时间特征 (20-23)
            "total_duration": flow_duration,
            "avg_inter_arrival": float(np.mean(inter_arrival_times)) if inter_arrival_times else 0.0,
            "std_inter_arrival": float(np.std(inter_arrival_times)) if len(inter_arrival_times) > 1 else 0.0,
            "packet_rate": n / flow_duration if flow_duration > 0 else 0.0,

            # E. 端口特征 (24-27)
            "src_port_entropy": float(src_port),  # 简化：直接使用端口值
            "dst_port_entropy": float(dst_port),
            "well_known_port_ratio": 1.0 if dst_port <= 1023 else 0.0,
            "high_port_ratio": 1.0 if dst_port > 1023 else 0.0,

            # F. 地址特征 (28-31)
            "unique_dst_ip_count": 1,  # 单流只有一个目标 IP
            "internal_ip_ratio": float(is_internal_ip(flow.five_tuple.dst_ip)),
            "df_flag_ratio": 0.5,  # 默认值
            "avg_ip_id": 0.5  # 默认归一化值
        }

        return features

    def flow_to_text(self, flow: Flow) -> str:
        """
        按照 TrafficLLM 可理解的领域规范格式进行跨模态指代文本拼接。
        """
        text_packets = []
        for packet in flow.packets[:self.max_packet_count]:
            packet_len = packet.size
            proto_val = flow.five_tuple.protocol
            src_port = flow.five_tuple.src_port
            dst_port = flow.five_tuple.dst_port
            # 将各维度硬编码为键值对纯文本
            text_desc = f"ip.len: {packet_len}, ip.proto: {proto_val}, tcp.srcport: {src_port}, tcp.dstport: {dst_port}, flags: {packet.tcp_flags}"
            text_packets.append(text_desc)
            
        return " | ".join(text_packets)

    def process_pcap(self, pcap_path: str) -> Tuple[List[Flow], dict]:
        """
        完整处理 Pcap 文件

        Returns:
            (截断后的流列表, 统计信息)
        """
        start_time = time.time()

        # 阶段1：流重组
        flows = self.extract_flows(pcap_path)

        # 阶段2：双重截断
        truncated_flows = [self.truncate_flow(flow) for flow in flows]

        # 统计信息
        stats = {
            "total_packets": sum(f.packet_count for f in flows),
            "total_flows": len(flows),
            "processing_time_ms": (time.time() - start_time) * 1000
        }

        logger.info(f"Pcap processing completed: {stats}")

        return truncated_flows, stats
