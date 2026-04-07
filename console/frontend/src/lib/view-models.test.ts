import { afterEach, describe, expect, it, vi } from 'vitest'
import { getDemoSamples, startDemoDetection } from '../api/client'
import type { DemoSample, DetectionResult } from '../types/api'
import {
  buildConsoleViewModel,
  buildDemoSampleCards,
  buildOverviewViewModel,
  formatBytes,
} from './view-models'

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
    expect(viewModel.architectureCards[0]).toEqual({
      label: '四容器闭环',
      value: 'Console -> Agent Loop -> SVM / LLM',
    })
    expect(viewModel.systemCards[0].value).toBe('前端控制台')
  })

  it('returns an empty evidence state when there is no completed result', () => {
    const viewModel = buildOverviewViewModel(null)

    expect(viewModel.evidenceCards[0].value).toBe('等待首个样本')
    expect(viewModel.evidenceCards[1].value).toBe('完成任务后生成')
    expect(viewModel.architectureCards[0].label).toBe('四容器闭环')
  })
})

describe('buildDemoSampleCards', () => {
  it('maps backend-shaped demo samples into selectable cards', () => {
    const samples: DemoSample[] = [
      {
        id: 'dns-tunnel.pcapng',
        filename: 'dns-tunnel.pcapng',
        display_name: 'dns tunnel',
        size_bytes: 4096,
      },
    ]

    expect(buildDemoSampleCards(samples, 'dns-tunnel.pcapng')).toEqual([
      expect.objectContaining({
        id: 'dns-tunnel.pcapng',
        title: 'dns tunnel',
        meta: '4.0 KB',
        selected: true,
      }),
    ])
  })
})

describe('demo sample api helpers', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('loads demo sample list from backend', async () => {
    const responsePayload = [
      {
        id: 'dns-tunnel.pcapng',
        filename: 'dns-tunnel.pcapng',
        display_name: 'dns tunnel',
        size_bytes: 4096,
      },
    ]
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(responsePayload), { status: 200 }),
    )

    await expect(getDemoSamples()).resolves.toEqual(responsePayload)
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/demo-samples')
  })

  it('throws when demo sample list endpoint is unavailable', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('', { status: 503 }))

    await expect(getDemoSamples()).rejects.toThrow('Demo sample list unavailable')
  })

  it('starts demo detection using selected sample id', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({ status: 'success', task_id: 'task-100', message: 'Detection task started' }),
        { status: 200 },
      ),
    )

    await expect(startDemoDetection('dns-tunnel.pcapng')).resolves.toEqual({
      status: 'success',
      task_id: 'task-100',
      message: 'Detection task started',
    })

    expect(globalThis.fetch).toHaveBeenCalledWith('/api/detect-demo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sample_id: 'dns-tunnel.pcapng' }),
    })
  })

  it('throws backend detail when demo detection fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Unknown demo sample id' }), { status: 400 }),
    )

    await expect(startDemoDetection('missing-sample.pcap')).rejects.toThrow('Unknown demo sample id')
  })
})
