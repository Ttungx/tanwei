<template>
  <div class="upload-container">
    <!-- Section Header -->
    <div class="section-header">
      <div class="section-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17,8 12,3 7,8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
      </div>
      <div>
        <h2>上传流量文件</h2>
        <p>支持 .pcap / .pcapng 格式</p>
      </div>
    </div>

    <!-- Drop Zone -->
    <div
      class="drop-zone"
      :class="{ 'drag-over': isDragOver, 'disabled': disabled }"
      @dragover.prevent="handleDragOver"
      @dragleave.prevent="handleDragLeave"
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <input
        type="file"
        ref="fileInput"
        accept=".pcap,.pcapng"
        @change="handleFileChange"
        hidden
      />

      <div class="drop-content">
        <div class="upload-icon">
          <svg viewBox="0 0 64 64" fill="none">
            <circle cx="32" cy="32" r="28" stroke="url(#uploadGradient)" stroke-width="2" stroke-dasharray="4 4"/>
            <path d="M32 20V44M32 20L24 28M32 20L40 28" stroke="url(#uploadGradient2)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
            <defs>
              <linearGradient id="uploadGradient" x1="4" y1="4" x2="60" y2="60">
                <stop offset="0%" stop-color="#6366f1"/>
                <stop offset="100%" stop-color="#8b5cf6"/>
              </linearGradient>
              <linearGradient id="uploadGradient2" x1="24" y1="20" x2="40" y2="44">
                <stop offset="0%" stop-color="#22d3ee"/>
                <stop offset="100%" stop-color="#6366f1"/>
              </linearGradient>
            </defs>
          </svg>
        </div>

        <div class="upload-text">
          <p class="main-text">拖拽文件到此处上传</p>
          <p class="sub-text">或点击选择文件</p>
        </div>

        <div class="upload-specs">
          <span class="spec-item">
            <svg viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0zm3.78 5.28a.75.75 0 0 1 0 1.06l-4 4a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06L7 8.44l3.47-3.47a.75.75 0 0 1 1.06 0z"/>
            </svg>
            最大 100MB
          </span>
          <span class="spec-item">
            <svg viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0zm3.78 5.28a.75.75 0 0 1 0 1.06l-4 4a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06L7 8.44l3.47-3.47a.75.75 0 0 1 1.06 0z"/>
            </svg>
            TCP/UDP 流量
          </span>
        </div>
      </div>
    </div>

    <!-- Selected File Info -->
    <transition name="slide">
      <div v-if="selectedFile" class="file-info">
        <div class="file-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14,2 14,8 20,8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10,9 9,9 8,9"/>
          </svg>
        </div>
        <div class="file-details">
          <span class="file-name">{{ selectedFile.name }}</span>
          <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
        </div>
        <button
          v-if="!disabled"
          class="remove-btn"
          @click.stop="clearFile"
          title="移除文件"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </transition>
  </div>
</template>

<script>
import { ref } from 'vue'

export default {
  name: 'FileUpload',
  props: {
    disabled: {
      type: Boolean,
      default: false
    }
  },
  emits: ['file-selected'],
  setup(props, { emit }) {
    const fileInput = ref(null)
    const selectedFile = ref(null)
    const isDragOver = ref(false)

    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    const handleDragOver = (e) => {
      if (props.disabled) return
      isDragOver.value = true
    }

    const handleDragLeave = () => {
      isDragOver.value = false
    }

    const handleDrop = (e) => {
      if (props.disabled) return
      isDragOver.value = false

      const files = e.dataTransfer.files
      if (files.length > 0) {
        validateAndEmit(files[0])
      }
    }

    const triggerFileInput = () => {
      if (props.disabled) return
      fileInput.value?.click()
    }

    const handleFileChange = (e) => {
      const files = e.target.files
      if (files.length > 0) {
        validateAndEmit(files[0])
      }
    }

    const validateAndEmit = (file) => {
      const validExtensions = ['.pcap', '.pcapng']
      const fileName = file.name.toLowerCase()
      const isValid = validExtensions.some(ext => fileName.endsWith(ext))

      if (!isValid) {
        alert('请上传 .pcap 或 .pcapng 格式的文件')
        return
      }

      if (file.size > 100 * 1024 * 1024) {
        alert('文件大小不能超过 100MB')
        return
      }

      selectedFile.value = file
      emit('file-selected', file)
    }

    const clearFile = () => {
      selectedFile.value = null
      if (fileInput.value) {
        fileInput.value.value = ''
      }
    }

    return {
      fileInput,
      selectedFile,
      isDragOver,
      formatFileSize,
      handleDragOver,
      handleDragLeave,
      handleDrop,
      triggerFileInput,
      handleFileChange,
      clearFile
    }
  }
}
</script>

<style scoped>
.upload-container {
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

/* Section Header */
.section-header {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.section-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gradient-primary);
  border-radius: var(--radius-md);
  color: white;
}

.section-icon svg {
  width: 20px;
  height: 20px;
}

.section-header h2 {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
}

.section-header p {
  font-size: 0.875rem;
  color: var(--text-muted);
}

/* Drop Zone */
.drop-zone {
  border: 2px dashed var(--border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-2xl);
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.drop-zone::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at center, rgba(99, 102, 241, 0.05) 0%, transparent 70%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.drop-zone:hover::before,
.drop-zone.drag-over::before {
  opacity: 1;
}

.drop-zone:hover,
.drop-zone.drag-over {
  border-color: var(--accent-primary);
  background: rgba(99, 102, 241, 0.05);
}

.drop-zone.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.drop-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-lg);
  position: relative;
  z-index: 1;
}

.upload-icon {
  width: 80px;
  height: 80px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.upload-text {
  text-align: center;
}

.main-text {
  font-size: 1rem;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: var(--space-xs);
}

.sub-text {
  font-size: 0.875rem;
  color: var(--text-muted);
}

.upload-specs {
  display: flex;
  gap: var(--space-lg);
  flex-wrap: wrap;
  justify-content: center;
}

.spec-item {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: 0.75rem;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-sm);
}

.spec-item svg {
  width: 12px;
  height: 12px;
  color: var(--accent-green);
}

/* File Info */
.file-info {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.file-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gradient-cyan);
  border-radius: var(--radius-sm);
  color: white;
  flex-shrink: 0;
}

.file-icon svg {
  width: 20px;
  height: 20px;
}

.file-details {
  flex: 1;
  min-width: 0;
}

.file-name {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-size {
  display: block;
  font-size: 0.75rem;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.remove-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.remove-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: var(--accent-red);
  color: var(--accent-red);
}

.remove-btn svg {
  width: 16px;
  height: 16px;
}

/* Transitions */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
