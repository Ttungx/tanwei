import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import * as client from './api/client'

vi.mock('./api/client', () => ({
  analyzeEdge: vi.fn(),
  analyzeNetwork: vi.fn(),
  getDemoSamples: vi.fn(),
  getEdgeAnalysis: vi.fn(),
  getEdgeReport: vi.fn(),
  getEdges: vi.fn(),
  getNetworkAnalysis: vi.fn(),
  getTaskResult: vi.fn(),
  getTaskStatus: vi.fn(),
  startDemoDetection: vi.fn(),
  uploadPcap: vi.fn(),
}))

const demoSample = {
  id: 'dns-tunnel',
  filename: 'dns-tunnel.pcapng',
  display_name: 'DNS 隧道外联',
  size_bytes: 524_288,
}

const edgeItem = {
  edge_id: 'edge-1',
  report_count: 3,
  latest_report_id: 'report-1',
  latest_reported_at: '2026-04-04T12:00:00Z',
  latest_analysis_status: 'ready',
  latest_threat_level: 'medium',
}

const edgeReport = {
  schema_version: '1.0',
  report_id: 'report-1',
  edge_id: 'edge-1',
  producer: {
    service: 'edge-agent',
    agent_version: 'agent-v1',
    reported_at: '2026-04-04T12:00:00Z',
  },
  analysis_constraints: {
    max_time_window_s: 30,
    max_packet_count: 2048,
    max_token_length: 512,
  },
  meta: {},
  statistics: {},
  threats: [],
  metrics: {},
}

const edgeAnalysis = {
  mode: 'single-edge' as const,
  edge_id: 'edge-1',
  threat_level: 'medium',
  summary: '边缘风险可控',
  analysis: '当前威胁集中在低频可疑流。',
  recommendations: ['持续观察 edge-1'],
  analysis_state: 'completed',
}

const networkAnalysis = {
  mode: 'network-wide' as const,
  edge_count: 2,
  threat_level: 'low',
  summary: '全网风险已收敛',
  analysis: '未发现跨 edge 协同异常。',
  recommendations: ['继续保持现有策略'],
  analysis_state: 'completed',
}

const detectionResultWithThreat = {
  meta: {
    task_id: 'task-100',
    timestamp: '2026-04-04T12:00:00Z',
    agent_version: 'agent-v1',
    processing_time_ms: 5100,
  },
  statistics: {
    total_packets: 8192,
    total_flows: 144,
    normal_flows_dropped: 138,
    anomaly_flows_detected: 6,
    svm_filter_rate: '95.8%',
    bandwidth_reduction: '11.4x',
  },
  threats: [
    {
      id: 'threat-100',
      five_tuple: {
        src_ip: '10.0.0.10',
        src_port: 443,
        dst_ip: '10.0.0.30',
        dst_port: 59212,
        protocol: 'TCP',
      },
      classification: {
        primary_label: 'Exfiltration',
        secondary_label: 'HTTP POST',
        confidence: 0.96,
        model: 'llm-analyst',
      },
      flow_metadata: {
        start_time: '2026-04-04T12:00:00Z',
        end_time: '2026-04-04T12:00:05Z',
        packet_count: 17,
        byte_count: 6144,
        avg_packet_size: 361.4,
      },
      token_info: {
        token_count: 144,
        truncated: false,
      },
    },
  ],
  metrics: {
    original_pcap_size_bytes: 4_194_304,
    json_output_size_bytes: 393_216,
    bandwidth_saved_percent: 90.6,
  },
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(client.getDemoSamples).mockResolvedValue([demoSample])
  vi.mocked(client.getEdges).mockResolvedValue([edgeItem])
  vi.mocked(client.getEdgeReport).mockResolvedValue(edgeReport)
  vi.mocked(client.getEdgeAnalysis).mockResolvedValue(edgeAnalysis)
  vi.mocked(client.getNetworkAnalysis).mockResolvedValue(networkAnalysis)
  vi.mocked(client.analyzeEdge).mockResolvedValue(edgeAnalysis)
  vi.mocked(client.analyzeNetwork).mockResolvedValue(networkAnalysis)
  vi.mocked(client.uploadPcap).mockResolvedValue({
    status: 'accepted',
    task_id: 'task-default',
    message: '任务已创建',
  })
  vi.mocked(client.startDemoDetection).mockResolvedValue({
    status: 'accepted',
    task_id: 'demo-task-default',
    message: '演示任务已创建',
  })
  vi.mocked(client.getTaskStatus).mockResolvedValue({
    task_id: 'task-default',
    status: 'completed',
    stage: 'completed',
    progress: 100,
    message: '检测完成',
  })
  vi.mocked(client.getTaskResult).mockResolvedValue(detectionResultWithThreat)
})

describe('App', () => {
  it('renders overview by default and allows switching sections', async () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: '统一控制台 + 边缘检测 + 中心研判' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^系统总览/ })).toHaveAttribute('aria-current', 'page')

    fireEvent.click(screen.getByRole('button', { name: /^Edge 控制台/ }))
    expect(await screen.findByRole('heading', { name: '上传样本' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /^Central 智能体/ }))
    expect(await screen.findByRole('heading', { name: '中心侧控制' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Edge 控制' }))
    expect(await screen.findByRole('heading', { name: '上传样本' })).toBeInTheDocument()
  })

  it('loads demo samples and central registry on initial render', async () => {
    render(<App />)

    await waitFor(() => {
      expect(client.getDemoSamples).toHaveBeenCalledTimes(1)
      expect(client.getEdges).toHaveBeenCalledTimes(1)
      expect(client.getNetworkAnalysis).toHaveBeenCalledTimes(1)
    })

    await waitFor(() => {
      expect(client.getEdgeReport).toHaveBeenCalledWith('edge-1')
      expect(client.getEdgeAnalysis).toHaveBeenCalledWith('edge-1')
    })

    expect(screen.getByText('当前边缘：edge-1')).toBeInTheDocument()
  })

  it('starts demo detection from edge workspace and renders completed output', async () => {
    vi.mocked(client.startDemoDetection).mockResolvedValue({
      status: 'accepted',
      task_id: 'demo-task-100',
      message: '演示任务已创建',
    })
    vi.mocked(client.getTaskStatus).mockResolvedValue({
      task_id: 'demo-task-100',
      status: 'completed',
      stage: 'completed',
      progress: 100,
      message: '演示检测完成',
    })
    vi.mocked(client.getTaskResult).mockResolvedValue({
      ...detectionResultWithThreat,
      meta: {
        ...detectionResultWithThreat.meta,
        task_id: 'demo-task-100',
      },
      statistics: {
        ...detectionResultWithThreat.statistics,
        anomaly_flows_detected: 0,
      },
      threats: [],
    })

    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /^Edge 控制台/ }))
    fireEvent.click(await screen.findByRole('button', { name: /DNS 隧道外联/ }))

    await waitFor(() => {
      expect(client.startDemoDetection).toHaveBeenCalledWith('dns-tunnel')
      expect(client.getTaskStatus).toHaveBeenCalledWith('demo-task-100')
      expect(client.getTaskResult).toHaveBeenCalledWith('demo-task-100')
    })

    expect(await screen.findByText('演示检测完成')).toBeInTheDocument()
    expect(screen.getByText('任务编号：demo-task-100')).toBeInTheDocument()
    expect(screen.getByText('0')).toBeInTheDocument()
  })

  it('uploads a pcap file and renders threat details from edge output', async () => {
    vi.mocked(client.uploadPcap).mockResolvedValue({
      status: 'accepted',
      task_id: 'task-100',
      message: '任务已创建',
    })
    vi.mocked(client.getTaskStatus).mockResolvedValue({
      task_id: 'task-100',
      status: 'completed',
      stage: 'completed',
      progress: 100,
      message: '检测完成',
    })

    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /^Edge 控制台/ }))

    const input = screen.getByLabelText(/选择 .*pcap.*pcapng.*提交到 edge-agent/i)
    const file = new File(['pcap'], 'trace.pcap', { type: 'application/octet-stream' })
    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() => {
      expect(client.uploadPcap).toHaveBeenCalledWith(file)
      expect(client.getTaskStatus).toHaveBeenCalledWith('task-100')
      expect(client.getTaskResult).toHaveBeenCalledWith('task-100')
    })

    expect(await screen.findByText('Exfiltration')).toBeInTheDocument()
    expect(screen.getByText('任务编号：task-100')).toBeInTheDocument()
  })

  it('allows running central-side actions', async () => {
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /^Central 智能体/ }))

    fireEvent.click(await screen.findByRole('button', { name: '分析 edge-1' }))
    await waitFor(() => {
      expect(client.analyzeEdge).toHaveBeenCalledWith('edge-1')
    })
    expect(screen.getAllByText('edge-1 的中心分析已更新。').length).toBeGreaterThan(0)

    fireEvent.click(screen.getByRole('button', { name: '手动触发全网综合研判' }))
    await waitFor(() => {
      expect(client.analyzeNetwork).toHaveBeenCalledTimes(1)
    })

    expect(screen.getAllByText('全网综合研判结果已更新。').length).toBeGreaterThan(0)
    expect(screen.getByText('全网风险已收敛')).toBeInTheDocument()
  })

  it('surfaces failed pipeline status when task execution fails', async () => {
    vi.mocked(client.uploadPcap).mockResolvedValue({
      status: 'accepted',
      task_id: 'task-failed',
      message: '任务已创建',
    })
    vi.mocked(client.getTaskStatus).mockResolvedValue({
      task_id: 'task-failed',
      status: 'failed',
      stage: 'failed',
      progress: 100,
      message: '检测链路中断',
    })

    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /^Edge 控制台/ }))

    const input = screen.getByLabelText(/选择 .*pcap.*pcapng.*提交到 edge-agent/i)
    const file = new File(['pcap'], 'failed.pcap', { type: 'application/octet-stream' })
    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() => {
      expect(screen.getAllByText('检测链路中断').length).toBeGreaterThan(0)
    })

    expect(screen.getAllByText('流程失败').length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { name: '当前任务报错' })).toBeInTheDocument()
    expect(screen.getAllByText('Edge Failed').length).toBeGreaterThan(0)
    expect(client.getTaskResult).not.toHaveBeenCalled()
  })
})
