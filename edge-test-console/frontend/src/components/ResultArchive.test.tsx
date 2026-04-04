import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { DetectionResult } from '../types/api'
import { ResultArchive } from './ResultArchive'

function createResult(): DetectionResult {
  return {
    meta: {
      task_id: 'task-9',
      timestamp: '2026-04-04T12:00:00Z',
      agent_version: 'agent-v1',
      processing_time_ms: 3600,
    },
    statistics: {
      total_packets: 2048,
      total_flows: 96,
      normal_flows_dropped: 91,
      anomaly_flows_detected: 5,
      svm_filter_rate: '94.8%',
      bandwidth_reduction: '10.2x',
    },
    threats: [
      {
        id: 't-1',
        five_tuple: {
          src_ip: '10.0.0.4',
          src_port: 443,
          dst_ip: '10.0.0.7',
          dst_port: 55123,
          protocol: 'TCP',
        },
        classification: {
          primary_label: 'Botnet',
          secondary_label: 'Beacon',
          confidence: 0.91,
          model: 'llm-analyst',
        },
        flow_metadata: {
          start_time: '2026-04-04T12:00:00Z',
          end_time: '2026-04-04T12:00:02Z',
          packet_count: 14,
          byte_count: 4096,
          avg_packet_size: 292.5,
        },
        token_info: {
          token_count: 120,
          truncated: false,
        },
      },
    ],
    metrics: {
      original_pcap_size_bytes: 2_097_152,
      json_output_size_bytes: 131_072,
      bandwidth_saved_percent: 93.7,
    },
  }
}

describe('ResultArchive', () => {
  it('renders an empty archive state without a result', () => {
    render(<ResultArchive result={null} />)

    expect(screen.getByRole('heading', { name: '结果归档' })).toBeInTheDocument()
    expect(screen.getByText('等待首个完成任务')).toBeInTheDocument()
  })

  it('renders summary evidence and threat details after completion', () => {
    render(<ResultArchive result={createResult()} />)

    expect(screen.getByText('93.7%')).toBeInTheDocument()
    expect(screen.getByText('Botnet')).toBeInTheDocument()
    expect(screen.getByText('10.0.0.4')).toBeInTheDocument()
    expect(screen.getByText('120')).toBeInTheDocument()
  })
})
