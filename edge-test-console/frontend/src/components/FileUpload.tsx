import { useState, useRef, useCallback } from 'react'
import styles from './FileUpload.module.css'

interface FileUploadProps {
  onUpload: (file: File) => Promise<boolean>
  disabled?: boolean
}

export default function FileUpload({ onUpload, disabled }: FileUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [validationMessage, setValidationMessage] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const isSupportedFile = useCallback((file: File) => {
    return /\.(pcap|pcapng)$/i.test(file.name)
  }, [])

  const acceptFile = useCallback((file: File | null) => {
    if (!file) {
      return
    }

    if (!isSupportedFile(file)) {
      setSelectedFile(null)
      setValidationMessage('仅支持 .pcap 或 .pcapng 文件。')
      return
    }

    setValidationMessage(null)
    setSelectedFile(file)
  }, [isSupportedFile])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    if (disabled) {
      return
    }
    setIsDragging(true)
  }, [disabled])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (disabled) {
      return
    }

    acceptFile(e.dataTransfer.files[0] ?? null)
  }, [acceptFile, disabled])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    acceptFile(e.target.files?.[0] ?? null)
    e.target.value = ''
  }, [acceptFile])

  const handleUpload = useCallback(async () => {
    if (selectedFile) {
      const uploaded = await onUpload(selectedFile)

      if (uploaded) {
        setSelectedFile(null)
        setValidationMessage(null)
      }
    }
  }, [selectedFile, onUpload])

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  return (
    <div
      className={`${styles.uploadContainer} ${isDragging ? styles.dragging : ''} ${disabled ? styles.disabled : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className={styles.uploadTopline}>
        <span className={styles.uploadTag}>样本接入</span>
        <span className={styles.uploadTagMuted}>{disabled ? '任务执行中' : '可立即投递'}</span>
      </div>

      <svg className={styles.uploadIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
      </svg>

      <div className={styles.copyBlock}>
        <h3 className={styles.uploadTitle}>投递原始流量样本</h3>
        <p className={styles.uploadText}>把抓包文件拖到这里，或者从本地磁盘选择一份待分析的 Pcap。</p>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".pcap,.pcapng"
        onChange={handleFileSelect}
        className={styles.fileInput}
        disabled={disabled}
      />

      <div className={styles.actionRow}>
        <button
          onClick={() => inputRef.current?.click()}
          className={styles.browseButton}
          disabled={disabled}
          type="button"
        >
          浏览文件
        </button>

        <span className={styles.uploadHint}>支持 .pcap 与 .pcapng，建议单文件上传。</span>
      </div>

      {validationMessage && <div className={styles.validation}>{validationMessage}</div>}

      {selectedFile && (
        <div className={styles.selectedState}>
          <div className={styles.selectedFile}>
            <span className={styles.fileName}>{selectedFile.name}</span>
            <span className={styles.fileSize}>{formatFileSize(selectedFile.size)}</span>
          </div>

          <button
            onClick={handleUpload}
            className={styles.uploadButton}
            disabled={disabled}
            type="button"
          >
            开始检测
          </button>
        </div>
      )}
    </div>
  )
}
