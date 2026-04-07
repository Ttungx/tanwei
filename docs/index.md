---
title: 探微 (Tanwei) - EdgeAgent 边缘智能终端系统
---

# 探微 (Tanwei)

> 面向边缘智能终端的威胁检测与带宽优化平台

## 文档目录

### 入门指南

1. [项目概览与核心价值](1-xiang-mu-gai-lan-yu-he-xin-jie-zhi)
2. [快速启动与三步部署](2-kuai-su-qi-dong-yu-san-bu-bu-shu)
3. [演示样本库使用](3-yan-shi-yang-ben-ku-shi-yong)

### 深入解析

#### 系统架构设计

4. [四容器拓扑与微服务架构](4-si-rong-qi-tuo-bu-yu-wei-fu-wu-jia-gou)
5. [五阶段检测工作流](5-wu-jie-duan-jian-ce-gong-zuo-liu)
6. [通信边界约束与资源红线](6-tong-xin-bian-jie-yue-shu-yu-zi-yuan-hong-xian)

#### 核心服务模块

7. [Agent-Loop 主控服务与工作流编排](7-agent-loop-zhu-kong-fu-wu-yu-gong-zuo-liu-bian-pai)
8. [SVM 过滤服务与微秒级推理](8-svm-guo-lu-fu-wu-yu-wei-miao-ji-tui-li)
9. [LLM 推理服务与边缘模型部署](9-llm-tui-li-fu-wu-yu-bian-yuan-mo-xing-bu-shu)
10. [测试控制台与可视化界面](10-ce-shi-kong-zhi-tai-yu-ke-shi-hua-jie-mian)

#### 流量处理与特征工程

11. [流量分词规范与双重截断保护](11-liu-liang-fen-ci-gui-fan-yu-shuang-zhong-jie-duan-bao-hu)
12. [32 维特征向量设计](12-32-wei-te-zheng-xiang-liang-she-ji)
13. [TrafficLLM 数据集与标签映射](13-trafficllm-shu-ju-ji-yu-biao-qian-ying-she)

#### 开发与运维参考

14. [服务间 API 接口规范](14-fu-wu-jian-api-jie-kou-gui-fan)
15. [部署指南与环境配置](15-bu-shu-zhi-nan-yu-huan-jing-pei-zhi)
16. [Agent Harness 协作工作流](16-agent-harness-xie-zuo-gong-zuo-liu)

---

## 核心特性

- **边缘智能**: 本地闭环验证，无需云端依赖
- **四级漏斗过滤**: SVM微秒级初筛 + LLM深度推理
- **带宽压降**: 70%以上带宽压降
- **资源友好**: 适用于2GB~4GB内存的边缘设备
