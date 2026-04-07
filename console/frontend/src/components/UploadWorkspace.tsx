import { useCallback, useRef, useState } from 'react'
import styles from './UploadWorkspace.module.css'

type UploadWorkspaceProps = {
  disabled: boolean
  isBusy: boolean
  onUpload: (file: File) => Promise<boolean>
}

export function UploadWorkspace({ disabled, isBusy, onUpload }: UploadWorkspaceProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [validationMessage, setValidationMessage] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const acceptFile = useCallback((file: File | null) => {
    if (!file) {
      return
    }

    if (!/\.(pcap|pcapng)$/i.test(file.name)) {
      setSelectedFile(null)
      setValidationMessage('仅支持 .pcap 或 .pcapng 文件。')
      return
    }

    setSelectedFile(file)
    setValidationMessage(null)
  }, [])

  const handleUpload = useCallback(async () => {
    if (!selectedFile) {
      return
    }

    await onUpload(selectedFile)
  }, [onUpload, selectedFile])

  return (
    <section className={styles.card}>
      <div className={styles.topline}>
        <span className={styles.tag}>样本接入</span>
        <span className={styles.tagMuted}>{isBusy ? '任务执行中' : '就绪'}</span>
      </div>

      <div className={styles.copy}>
        <h3>上传检测样本</h3>
        <p>提交 pcap 或 pcapng 样本，触发边缘侧重组、SVM 初筛和 LLM 精判流程。</p>
      </div>

      <label className={styles.hiddenLabel} htmlFor="pcap-upload-input">
        上传 Pcap 样本
      </label>
      <input
        ref={inputRef}
        id="pcap-upload-input"
        className={styles.hiddenInput}
        type="file"
        accept=".pcap,.pcapng"
        disabled={disabled}
        onChange={(event) => acceptFile(event.target.files?.[0] ?? null)}
      />

      <div className={styles.actions}>
        <button
          type="button"
          className={styles.secondaryButton}
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
        >
          选择样本
        </button>
        <button
          type="button"
          className={styles.primaryButton}
          disabled={disabled || !selectedFile}
          onClick={handleUpload}
        >
          提交检测任务
        </button>
      </div>

      {validationMessage && <p className={styles.validation}>{validationMessage}</p>}

      {selectedFile && (
        <div className={styles.fileCard}>
          <span>{selectedFile.name}</span>
          <span>{Math.max(1, Math.round(selectedFile.size / 1024))} KB</span>
        </div>
      )}
    </section>
  )
}
