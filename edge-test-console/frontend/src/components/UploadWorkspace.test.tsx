import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { UploadWorkspace } from './UploadWorkspace'

describe('UploadWorkspace', () => {
  it('rejects unsupported files before calling onUpload', async () => {
    const onUpload = vi.fn().mockResolvedValue(true)

    render(
      <UploadWorkspace
        disabled={false}
        isBusy={false}
        onUpload={onUpload}
      />,
    )

    const input = screen.getByLabelText('上传 Pcap 样本')
    const file = new File(['bad'], 'sample.txt', { type: 'text/plain' })

    fireEvent.change(input, { target: { files: [file] } })

    expect(await screen.findByText('仅支持 .pcap 或 .pcapng 文件。')).toBeInTheDocument()
    expect(onUpload).not.toHaveBeenCalled()
  })

  it('shows the selected pcap file and enables submission', async () => {
    const onUpload = vi.fn().mockResolvedValue(true)

    render(
      <UploadWorkspace
        disabled={false}
        isBusy={false}
        onUpload={onUpload}
      />,
    )

    const input = screen.getByLabelText('上传 Pcap 样本')
    const file = new File(['pcap'], 'traffic.pcap', { type: 'application/octet-stream' })

    fireEvent.change(input, { target: { files: [file] } })
    fireEvent.click(screen.getByRole('button', { name: '提交检测任务' }))

    expect(await screen.findByText('traffic.pcap')).toBeInTheDocument()
    expect(onUpload).toHaveBeenCalledWith(file)
  })
})
