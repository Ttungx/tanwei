import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import * as client from './api/client'

vi.mock('./api/client', () => ({
  uploadPcap: vi.fn(),
  getTaskStatus: vi.fn(),
  getTaskResult: vi.fn(),
  getDemoSamples: vi.fn(),
  startDemoDetection: vi.fn(),
  getEdges: vi.fn(),
  getLatestEdgeReport: vi.fn(),
  startEdgeAnalysis: vi.fn(),
  startNetworkAnalysis: vi.fn(),
}))

function createDeferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })

  return { promise, resolve, reject }
}

afterEach(() => {
  vi.clearAllMocks()
})

beforeEach(() => {
  vi.mocked(client.getEdges).mockResolvedValue([
    {
      edge_id: 'edge1',
      display_name: 'Edge 1',
      status: 'online',
      location: 'Singapore Rack A',
      last_reported_at: '2026-04-07T08:00:00Z',
      threat_count: 2,
      risk_level: 'high',
    },
    {
      edge_id: 'edge2',
      display_name: 'Edge 2',
      status: 'online',
      location: 'Singapore Rack B',
      last_reported_at: '2026-04-07T08:02:00Z',
      threat_count: 0,
      risk_level: 'low',
    },
  ])
  vi.mocked(client.getLatestEdgeReport).mockResolvedValue({
    edge_id: 'edge1',
    report_id: 'edge1-report-001',
    generated_at: '2026-04-07T08:00:00Z',
    summary: {
      headline: '2 threats detected on edge1',
      risk_level: 'high',
      threat_count: 2,
      bandwidth_saved_percent: 87.5,
    },
    report: {
      meta: {
        task_id: 'edge1-task-001',
        timestamp: '2026-04-07T08:00:00Z',
        agent_version: 'edge-agent-v1',
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
            start_time: '2026-04-07T08:00:00Z',
            end_time: '2026-04-07T08:00:02Z',
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
    },
  })
  vi.mocked(client.startEdgeAnalysis).mockImplementation(async (edgeId) => ({
    edge_id: edgeId,
    report_id: `${edgeId}-report-refresh`,
    generated_at: '2026-04-07T09:00:00Z',
    summary: {
      headline: `manual analysis finished for ${edgeId}`,
      risk_level: 'medium',
      threat_count: 1,
      bandwidth_saved_percent: 81.3,
    },
    report: {
      meta: {
        task_id: `${edgeId}-task-refresh`,
        timestamp: '2026-04-07T09:00:00Z',
        agent_version: 'edge-agent-v1',
        processing_time_ms: 3100,
      },
      statistics: {
        total_packets: 2048,
        total_flows: 64,
        normal_flows_dropped: 63,
        anomaly_flows_detected: 1,
        svm_filter_rate: '98.4%',
        bandwidth_reduction: '81.3%',
      },
      threats: [],
      metrics: {
        original_pcap_size_bytes: 2_097_152,
        json_output_size_bytes: 392_014,
        bandwidth_saved_percent: 81.3,
      },
    },
  }))
  vi.mocked(client.startNetworkAnalysis).mockResolvedValue({
    analysis_id: 'network-analysis-001',
    generated_at: '2026-04-07T09:30:00Z',
    summary: {
      edge_count: 2,
      edges_with_alerts: 1,
      total_threats: 3,
      highest_risk_edge: 'edge1',
      recommended_action: 'Escalate edge1 for human review',
    },
    edges: [
      {
        edge_id: 'edge1',
        display_name: 'Edge 1',
        threat_count: 3,
        risk_level: 'high',
        generated_at: '2026-04-07T09:28:00Z',
      },
      {
        edge_id: 'edge2',
        display_name: 'Edge 2',
        threat_count: 0,
        risk_level: 'low',
        generated_at: '2026-04-07T09:27:00Z',
      },
    ],
  })
})

describe('App', () => {
  it('loads the control plane, selects an edge, and supports manual analyses', async () => {
    render(<App />)

    await waitFor(() => {
      expect(client.getEdges).toHaveBeenCalledTimes(1)
      expect(client.getLatestEdgeReport).toHaveBeenCalledWith('edge1')
    })

    expect(screen.getAllByText('Edge 1').length).toBeGreaterThan(0)
    expect(screen.getByText('2 threats detected on edge1')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '选择 Edge 2' }))

    await waitFor(() => {
      expect(client.getLatestEdgeReport).toHaveBeenCalledWith('edge2')
    })

    fireEvent.click(screen.getByRole('button', { name: '触发单 edge 分析' }))
    fireEvent.click(screen.getByRole('button', { name: '触发全网综合研判' }))

    await waitFor(() => {
      expect(client.startEdgeAnalysis).toHaveBeenCalledWith('edge2')
      expect(client.startNetworkAnalysis).toHaveBeenCalledTimes(1)
    })

    expect(screen.getByText('Escalate edge1 for human review')).toBeInTheDocument()
  })

  it('loads demo samples and supports the demo workspace source', async () => {
    vi.mocked(client.getDemoSamples).mockResolvedValue([
      {
        id: 'dns-tunnel',
        filename: 'dns-tunnel.pcapng',
        display_name: 'DNS 隧道外联',
        size_bytes: 524_288,
      },
    ])
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
      meta: {
        task_id: 'demo-task-100',
        timestamp: '2026-04-04T12:00:00Z',
        agent_version: 'agent-v1',
        processing_time_ms: 5100,
      },
      statistics: {
        total_packets: 8192,
        total_flows: 144,
        normal_flows_dropped: 144,
        anomaly_flows_detected: 0,
        svm_filter_rate: '100.0%',
        bandwidth_reduction: '11.4x',
      },
      threats: [],
      metrics: {
        original_pcap_size_bytes: 4_194_304,
        json_output_size_bytes: 393_216,
        bandwidth_saved_percent: 90.6,
      },
    })

    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: '检测工作台' }))
    fireEvent.click(screen.getByRole('button', { name: '演示样本' }))

    await waitFor(() => {
      expect(client.getDemoSamples).toHaveBeenCalledTimes(1)
    })

    fireEvent.click(screen.getByRole('button', { name: '选择 DNS 隧道外联 演示样本' }))
    fireEvent.click(screen.getByRole('button', { name: '启动演示检测' }))

    await waitFor(() => {
      expect(client.startDemoDetection).toHaveBeenCalledWith('dns-tunnel')
      expect(client.getTaskStatus).toHaveBeenCalledWith('demo-task-100')
      expect(client.getTaskResult).toHaveBeenCalledWith('demo-task-100')
    })

    expect(screen.getAllByText('演示检测完成').length).toBeGreaterThan(0)

    fireEvent.click(screen.getByRole('button', { name: '威胁归档' }))

    expect(screen.getByText('归档总览')).toBeInTheDocument()
    expect(screen.getByText('零威胁归档')).toBeInTheDocument()
    expect(screen.getByText(/本次样本未检测到异常候选/)).toBeInTheDocument()
    expect(screen.getByText('归档状态')).toBeInTheDocument()
    expect(screen.getByText('已归档')).toBeInTheDocument()
    expect(screen.getByText('异常威胁')).toBeInTheDocument()
    expect(screen.getByText('demo-task-100')).toBeInTheDocument()
  })

  it('shows the demo empty state when the sample library is empty', async () => {
    vi.mocked(client.getDemoSamples).mockResolvedValue([])

    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: '检测工作台' }))
    fireEvent.click(screen.getByRole('button', { name: '演示样本' }))

    expect(await screen.findByText('暂无可用演示样本')).toBeInTheDocument()
  })

  it('recovers demo sample loading after reset invalidates an in-flight request', async () => {
    const firstLoad = createDeferred<Awaited<ReturnType<typeof client.getDemoSamples>>>()
    vi.mocked(client.getDemoSamples)
      .mockReturnValueOnce(firstLoad.promise)
      .mockResolvedValueOnce([
        {
          id: 'dns-tunnel',
          filename: 'dns-tunnel.pcapng',
          display_name: 'DNS 隧道外联',
          size_bytes: 524_288,
        },
      ])

    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: '检测工作台' }))
    fireEvent.click(screen.getByRole('button', { name: '演示样本' }))

    expect(screen.getByText('演示样本加载中...')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '重置工作台' }))
    firstLoad.resolve([
      {
        id: 'stale-sample',
        filename: 'stale-sample.pcap',
        display_name: '过期样本',
        size_bytes: 1_024,
      },
    ])

    fireEvent.click(screen.getByRole('button', { name: '检测工作台' }))
    fireEvent.click(screen.getByRole('button', { name: '演示样本' }))

    await waitFor(() => {
      expect(client.getDemoSamples).toHaveBeenCalledTimes(2)
    })

    expect(await screen.findByText('DNS 隧道外联')).toBeInTheDocument()
    expect(screen.queryByText('过期样本')).not.toBeInTheDocument()
  })

  it('retries demo sample loading after a transient failure through normal workspace flow', async () => {
    vi.mocked(client.getDemoSamples)
      .mockRejectedValueOnce(new Error('演示样本加载失败'))
      .mockResolvedValueOnce([
        {
          id: 'http-beacon',
          filename: 'http-beacon.pcap',
          display_name: 'HTTP Beacon 回连',
          size_bytes: 262_144,
        },
      ])

    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: '检测工作台' }))
    fireEvent.click(screen.getByRole('button', { name: '演示样本' }))

    expect(await screen.findByText('演示样本加载失败')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '重置工作台' }))
    fireEvent.click(screen.getByRole('button', { name: '检测工作台' }))
    fireEvent.click(screen.getByRole('button', { name: '演示样本' }))

    await waitFor(() => {
      expect(client.getDemoSamples).toHaveBeenCalledTimes(2)
    })

    expect(await screen.findByText('HTTP Beacon 回连')).toBeInTheDocument()
  })

  it('shows the overview section by default and allows switching shell sections', () => {
    vi.mocked(client.getDemoSamples).mockResolvedValue([])

    render(<App />)

    expect(screen.getByRole('navigation', { name: '主导航' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '总览概况' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '系统总览' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '检测工作台' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '威胁归档' })).toBeInTheDocument()
    expect(screen.getByLabelText('workflow-pending')).toHaveAttribute('aria-current', 'step')

    fireEvent.click(screen.getByRole('button', { name: '检测工作台' }))

    expect(screen.getByRole('heading', { name: '上传检测样本' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '威胁归档' }))

    expect(screen.getByRole('heading', { name: '结果归档' })).toBeInTheDocument()
  })

  it('submits a pcap sample and renders the completed archive', async () => {
    vi.mocked(client.getDemoSamples).mockResolvedValue([])
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
    vi.mocked(client.getTaskResult).mockResolvedValue({
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
    })

    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: '检测工作台' }))

    const input = screen.getByLabelText('上传 Pcap 样本')
    const file = new File(['pcap'], 'trace.pcap', { type: 'application/octet-stream' })

    fireEvent.change(input, { target: { files: [file] } })
    fireEvent.click(screen.getByRole('button', { name: '提交检测任务' }))

    await waitFor(() => {
      expect(client.uploadPcap).toHaveBeenCalledWith(file)
      expect(client.getTaskStatus).toHaveBeenCalledWith('task-100')
      expect(client.getTaskResult).toHaveBeenCalledWith('task-100')
    })

    fireEvent.click(screen.getByRole('button', { name: '威胁归档' }))

    const archiveSummary = screen.getByRole('region', { name: '归档总览' })
    const archiveEvidence = screen.getByRole('region', { name: '威胁证据' })

    expect(archiveSummary).toHaveTextContent('归档状态')
    expect(archiveSummary).toHaveTextContent('待复核')
    expect(archiveSummary).toHaveTextContent('异常威胁')
    expect(archiveSummary).toHaveTextContent('6')
    expect(screen.getByText('任务编号')).toBeInTheDocument()
    expect(archiveEvidence).toHaveTextContent('源 IP')
    expect(archiveEvidence).toHaveTextContent('Token')
    expect(archiveEvidence).toHaveTextContent('HTTP POST')
    expect(archiveEvidence).toHaveTextContent('10.0.0.10')
    expect(archiveEvidence).toHaveTextContent('443')
    expect(archiveEvidence).toHaveTextContent('10.0.0.30')
    expect(archiveEvidence).toHaveTextContent('59212')
    expect(archiveEvidence).toHaveTextContent('TCP')
    expect(archiveEvidence).toHaveTextContent('144')
    expect(await screen.findByText('Exfiltration')).toBeInTheDocument()
    expect(screen.getAllByText('90.6%').length).toBeGreaterThan(0)
  })

  it('renders a zero-threat completed archive after normal upload', async () => {
    vi.mocked(client.getDemoSamples).mockResolvedValue([])
    vi.mocked(client.uploadPcap).mockResolvedValue({
      status: 'accepted',
      task_id: 'task-101',
      message: '任务已创建',
    })
    vi.mocked(client.getTaskStatus).mockResolvedValue({
      task_id: 'task-101',
      status: 'completed',
      stage: 'completed',
      progress: 100,
      message: '检测完成',
    })
    vi.mocked(client.getTaskResult).mockResolvedValue({
      meta: {
        task_id: 'task-101',
        timestamp: '2026-04-04T12:10:00Z',
        agent_version: 'agent-v1',
        processing_time_ms: 3200,
      },
      statistics: {
        total_packets: 4096,
        total_flows: 120,
        normal_flows_dropped: 120,
        anomaly_flows_detected: 0,
        svm_filter_rate: '100.0%',
        bandwidth_reduction: '12.0x',
      },
      threats: [],
      metrics: {
        original_pcap_size_bytes: 2_097_152,
        json_output_size_bytes: 131_072,
        bandwidth_saved_percent: 93.8,
      },
    })

    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: '检测工作台' }))

    const input = screen.getByLabelText('上传 Pcap 样本')
    const file = new File(['pcap'], 'zero-threat.pcap', { type: 'application/octet-stream' })

    fireEvent.change(input, { target: { files: [file] } })
    fireEvent.click(screen.getByRole('button', { name: '提交检测任务' }))

    await waitFor(() => {
      expect(client.uploadPcap).toHaveBeenCalledWith(file)
      expect(client.getTaskStatus).toHaveBeenCalledWith('task-101')
      expect(client.getTaskResult).toHaveBeenCalledWith('task-101')
    })

    fireEvent.click(screen.getByRole('button', { name: '威胁归档' }))

    const archiveSummary = screen.getByRole('region', { name: '归档总览' })
    const archiveEvidence = screen.getByRole('region', { name: '威胁证据' })

    expect(archiveSummary).toHaveTextContent('归档状态')
    expect(archiveSummary).toHaveTextContent('已归档')
    expect(archiveSummary).toHaveTextContent('异常威胁')
    expect(archiveSummary).toHaveTextContent('0')
    expect(archiveEvidence).toHaveTextContent('零威胁归档')
    expect(archiveEvidence).toHaveTextContent('本次样本未检测到异常候选')
  })

  it('renders a sparse anomaly fallback when detection statistics report anomalies without threat details', async () => {
    vi.mocked(client.getDemoSamples).mockResolvedValue([])
    vi.mocked(client.uploadPcap).mockResolvedValue({
      status: 'accepted',
      task_id: 'task-102',
      message: '任务已创建',
    })
    vi.mocked(client.getTaskStatus).mockResolvedValue({
      task_id: 'task-102',
      status: 'completed',
      stage: 'completed',
      progress: 100,
      message: '检测完成',
    })
    vi.mocked(client.getTaskResult).mockResolvedValue({
      meta: {
        task_id: 'task-102',
        timestamp: '2026-04-04T12:20:00Z',
        agent_version: 'agent-v1',
        processing_time_ms: 4100,
      },
      statistics: {
        total_packets: 5120,
        total_flows: 160,
        normal_flows_dropped: 156,
        anomaly_flows_detected: 4,
        svm_filter_rate: '97.5%',
        bandwidth_reduction: '9.8x',
      },
      threats: [],
      metrics: {
        original_pcap_size_bytes: 3_145_728,
        json_output_size_bytes: 262_144,
        bandwidth_saved_percent: 89.4,
      },
    })

    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: '检测工作台' }))

    const input = screen.getByLabelText('上传 Pcap 样本')
    const file = new File(['pcap'], 'sparse-result.pcap', { type: 'application/octet-stream' })

    fireEvent.change(input, { target: { files: [file] } })
    fireEvent.click(screen.getByRole('button', { name: '提交检测任务' }))

    await waitFor(() => {
      expect(client.uploadPcap).toHaveBeenCalledWith(file)
      expect(client.getTaskStatus).toHaveBeenCalledWith('task-102')
      expect(client.getTaskResult).toHaveBeenCalledWith('task-102')
    })

    fireEvent.click(screen.getByRole('button', { name: '威胁归档' }))

    const archiveSummary = screen.getByRole('region', { name: '归档总览' })
    const archiveEvidence = screen.getByRole('region', { name: '威胁证据' })

    expect(archiveSummary).toHaveTextContent('待复核')
    expect(archiveSummary).toHaveTextContent('4')
    expect(archiveEvidence).toHaveTextContent('威胁明细待补充')
    expect(archiveEvidence).toHaveTextContent('已检出异常，但当前结果未返回详细威胁记录')
    expect(archiveEvidence).not.toHaveTextContent('零威胁归档')
  })

  it('ignores stale upload completion after reset', async () => {
    vi.mocked(client.getDemoSamples).mockResolvedValue([])
    const uploadDeferred = createDeferred<Awaited<ReturnType<typeof client.uploadPcap>>>()
    vi.mocked(client.uploadPcap).mockReturnValue(uploadDeferred.promise)

    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: '检测工作台' }))

    const input = screen.getByLabelText('上传 Pcap 样本')
    const file = new File(['pcap'], 'delayed.pcap', { type: 'application/octet-stream' })

    fireEvent.change(input, { target: { files: [file] } })
    fireEvent.click(screen.getByRole('button', { name: '提交检测任务' }))
    fireEvent.click(screen.getByRole('button', { name: '重置工作台' }))

    uploadDeferred.resolve({
      status: 'accepted',
      task_id: 'late-task',
      message: '迟到任务',
    })

    await waitFor(() => {
      expect(client.getTaskStatus).not.toHaveBeenCalled()
    })

    expect(screen.getByRole('heading', { name: '总览概况' })).toBeInTheDocument()
    expect(screen.getByText('尚未创建任务')).toBeInTheDocument()
    expect(screen.queryByText('迟到任务')).not.toBeInTheDocument()
  })

  it('surfaces failed workflow state after a task failure', async () => {
    vi.mocked(client.getDemoSamples).mockResolvedValue([])
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

    fireEvent.click(screen.getByRole('button', { name: '检测工作台' }))

    const input = screen.getByLabelText('上传 Pcap 样本')
    const file = new File(['pcap'], 'failed.pcap', { type: 'application/octet-stream' })

    fireEvent.change(input, { target: { files: [file] } })
    fireEvent.click(screen.getByRole('button', { name: '提交检测任务' }))

    await waitFor(() => {
      expect(screen.getAllByText('检测链路中断').length).toBeGreaterThan(0)
    })

    expect(screen.getByText('任务失败')).toBeInTheDocument()
    expect(screen.getAllByText('流程中断').length).toBeGreaterThan(0)
    expect(screen.getByText('本次任务未能完成，需要重新提交样本。')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '系统总览' }))

    expect(screen.getByLabelText('workflow-panel')).toHaveAttribute('data-stage', 'failed')
    expect(screen.getByLabelText('workflow-failed')).toHaveAttribute('data-state', 'failed')
  })
})
