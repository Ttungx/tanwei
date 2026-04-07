import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { buildOverviewViewModel } from '../lib/view-models'
import { SolutionOverview } from './SolutionOverview'

describe('SolutionOverview', () => {
  it('renders value, pipeline, evidence, and system sections', () => {
    const viewModel = buildOverviewViewModel({
      meta: {
        task_id: 'task-7',
        timestamp: '2026-04-04T12:00:00Z',
        agent_version: 'agent-v1',
        processing_time_ms: 5800,
      },
      statistics: {
        total_packets: 9000,
        total_flows: 240,
        normal_flows_dropped: 228,
        anomaly_flows_detected: 12,
        svm_filter_rate: '95.0%',
        bandwidth_reduction: '16.0x',
      },
      threats: [],
      metrics: {
        original_pcap_size_bytes: 9_437_184,
        json_output_size_bytes: 786_432,
        bandwidth_saved_percent: 91.7,
      },
    })

    render(<SolutionOverview viewModel={viewModel} />)

    expect(screen.getByRole('heading', { name: '方案概览' })).toBeInTheDocument()
    expect(screen.getByText('场景与价值')).toBeInTheDocument()
    expect(screen.getByText('检测链路')).toBeInTheDocument()
    expect(screen.getByText('关键证据')).toBeInTheDocument()
    expect(screen.getByText('系统组成')).toBeInTheDocument()
    expect(screen.getByText('91.7%')).toBeInTheDocument()
    expect(screen.getByText('Pcap -> Flow Reconstruction -> SVM Filtering -> LLM Inference -> Threat Archive')).toBeInTheDocument()
  })
})
