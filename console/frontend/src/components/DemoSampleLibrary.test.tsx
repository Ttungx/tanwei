import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { DemoSample } from '../types/api'
import { DemoSampleLibrary } from './DemoSampleLibrary'

const demoSamples: DemoSample[] = [
  {
    id: 'dns-tunnel',
    filename: 'dns-tunnel.pcapng',
    display_name: 'DNS 隧道外联',
    size_bytes: 512_000,
  },
  {
    id: 'http-beacon',
    filename: 'http-beacon.pcap',
    display_name: 'HTTP Beacon 回连',
    size_bytes: 256_000,
  },
]

describe('DemoSampleLibrary', () => {
  it('renders demo sample cards and submits the selected sample', async () => {
    const onSelect = vi.fn()
    const onStart = vi.fn().mockResolvedValue(true)

    render(
      <DemoSampleLibrary
        samples={demoSamples}
        selectedSampleId="http-beacon"
        disabled={false}
        isBusy={false}
        isLoading={false}
        error={null}
        onSelect={onSelect}
        onStart={onStart}
      />,
    )

    expect(screen.getByText('DNS 隧道外联')).toBeInTheDocument()
    expect(screen.getByText('500.0 KB')).toBeInTheDocument()
    expect(screen.getByText('HTTP Beacon 回连')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '选择 DNS 隧道外联 演示样本' }))
    expect(onSelect).toHaveBeenCalledWith('dns-tunnel')

    fireEvent.click(screen.getByRole('button', { name: '启动演示检测' }))
    expect(onStart).toHaveBeenCalledWith('http-beacon')
  })

  it('shows an empty state when no demo samples are available', () => {
    render(
      <DemoSampleLibrary
        samples={[]}
        selectedSampleId={null}
        disabled={false}
        isBusy={false}
        isLoading={false}
        error={null}
        onSelect={vi.fn()}
        onStart={vi.fn()}
      />,
    )

    expect(screen.getByText('暂无可用演示样本')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '启动演示检测' })).toBeDisabled()
  })

  it('surfaces loading and error states', () => {
    render(
      <DemoSampleLibrary
        samples={[]}
        selectedSampleId={null}
        disabled={false}
        isBusy={false}
        isLoading
        error="演示样本加载失败"
        onSelect={vi.fn()}
        onStart={vi.fn()}
      />,
    )

    expect(screen.getByText('演示样本加载中...')).toBeInTheDocument()
    expect(screen.getByText('演示样本加载失败')).toBeInTheDocument()
  })
})
