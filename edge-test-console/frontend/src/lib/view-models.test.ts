import { describe, expect, it } from 'vitest'
import type { DetectionResult } from '../types/api'
import { buildConsoleViewModel, buildOverviewViewModel, formatBytes } from './view-models'

function createResult(overrides?: Partial<DetectionResult>): DetectionResult {
  return {
    meta: {
      task_id: 'task-42',
      timestamp: '2026-04-04T12:00:00Z',
      agent_version: 'agent-v1',
      processing_time_ms: 4200,
    },
    statistics: {
      total_packets: 4096,
      total_flows: 128,
      normal_flows_dropped: 120,
      anomaly_flows_detected: 8,
      svm_filter_rate: '93.8%',
      bandwidth_reduction: '12.4x',
    },
    threats: [
      {
        id: 'threat-1',
        five_tuple: {
          src_ip: '10.0.0.1',
          src_port: 443,
          dst_ip: '10.0.0.8',
          dst_port: 58000,
          protocol: 'TCP',
        },
        classification: {
          primary_label: 'C2',
          secondary_label: 'Beaconing',
          confidence: 0.92,
          model: 'llm-analyst',
        },
        flow_metadata: {
          start_time: '2026-04-04T12:00:00Z',
          end_time: '2026-04-04T12:00:02Z',
          packet_count: 12,
          byte_count: 2048,
          avg_packet_size: 170.6,
        },
        token_info: {
          token_count: 88,
          truncated: false,
        },
      },
    ],
    metrics: {
      original_pcap_size_bytes: 4_194_304,
      json_output_size_bytes: 524_288,
      bandwidth_saved_percent: 87.5,
    },
    ...overrides,
  }
}

describe('formatBytes', () => {
  it('formats megabytes for dashboard metrics', () => {
    expect(formatBytes(4_194_304)).toBe('4.00 MB')
  })
})

describe('buildConsoleViewModel', () => {
  it('uses idle placeholders before any task completes', () => {
    const viewModel = buildConsoleViewModel({
      appState: 'idle',
      stage: 'pending',
      message: '',
      result: null,
      error: null,
    })

    expect(viewModel.stateLabel).toBe('待命')
    expect(viewModel.heroMetrics.map((item) => item.value)).toEqual([
      '边缘侧预检',
      'SVM + LLM',
      '威胁档案',
    ])
  })

  it('uses live result metrics after completion', () => {
    const viewModel = buildConsoleViewModel({
      appState: 'completed',
      stage: 'completed',
      message: '检测完成',
      result: createResult(),
      error: null,
    })

    expect(viewModel.stateLabel).toBe('已完成')
    expect(viewModel.heroMetrics.map((item) => item.value)).toEqual([
      '8',
      '87.5%',
      '4.20s',
    ])
  })
})

describe('buildOverviewViewModel', () => {
  it('derives truthful evidence cards from the result payload', () => {
    const viewModel = buildOverviewViewModel(createResult())

    expect(viewModel.evidenceCards.map((item) => item.value)).toEqual([
      '87.5%',
      '8 / 128',
      '4.20s',
    ])
    expect(viewModel.pipeline[2]).toEqual({
      label: 'SVM 初筛',
      detail: '快速过滤大部分正常流量，压低后续推理成本。',
    })
    expect(viewModel.systemCards[0].value).toBe('前端控制台')
  })

  it('returns an empty evidence state when there is no completed result', () => {
    const viewModel = buildOverviewViewModel(null)

    expect(viewModel.evidenceCards[0].value).toBe('等待首个样本')
    expect(viewModel.evidenceCards[1].value).toBe('完成任务后生成')
  })
})
