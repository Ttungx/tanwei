import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import App from './App'
import * as client from './api/client'

vi.mock('./api/client', () => ({
  uploadPcap: vi.fn(),
  getTaskStatus: vi.fn(),
  getTaskResult: vi.fn(),
}))

describe('App', () => {
  it('shows the overview mode by default and allows switching to the console', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: '方案概览' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '控制台' }))

    expect(screen.getByRole('heading', { name: '上传检测样本' })).toBeInTheDocument()
  })

  it('submits a pcap sample and renders the completed archive', async () => {
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

    fireEvent.click(screen.getByRole('button', { name: '控制台' }))

    const input = screen.getByLabelText('上传 Pcap 样本')
    const file = new File(['pcap'], 'trace.pcap', { type: 'application/octet-stream' })

    fireEvent.change(input, { target: { files: [file] } })
    fireEvent.click(screen.getByRole('button', { name: '提交检测任务' }))

    await waitFor(() => {
      expect(client.uploadPcap).toHaveBeenCalledWith(file)
      expect(client.getTaskStatus).toHaveBeenCalledWith('task-100')
      expect(client.getTaskResult).toHaveBeenCalledWith('task-100')
    })

    expect(await screen.findByText('Exfiltration')).toBeInTheDocument()
    expect(screen.getAllByText('90.6%').length).toBeGreaterThan(0)
  })
})
