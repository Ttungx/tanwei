<template>
  <div class="app-container">
    <!-- Header -->
    <header class="header">
      <div class="header-content">
        <div class="logo-section">
          <div class="logo-icon">
            <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="20" cy="20" r="18" stroke="url(#gradient1)" stroke-width="2"/>
              <path d="M12 20L18 26L28 14" stroke="url(#gradient2)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
              <defs>
                <linearGradient id="gradient1" x1="0" y1="0" x2="40" y2="40">
                  <stop offset="0%" stop-color="#6366f1"/>
                  <stop offset="100%" stop-color="#8b5cf6"/>
                </linearGradient>
                <linearGradient id="gradient2" x1="12" y1="14" x2="28" y2="26">
                  <stop offset="0%" stop-color="#22d3ee"/>
                  <stop offset="100%" stop-color="#6366f1"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div class="logo-text">
            <h1>探微</h1>
            <span class="subtitle">EdgeAgent Test Console</span>
          </div>
        </div>
        <div class="status-badge">
          <span class="status-dot"></span>
          <span>系统就绪</span>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="main-content">
      <div class="content-grid">
        <!-- Left Panel - Upload -->
        <section class="upload-section">
          <FileUpload
            @file-selected="handleFileSelected"
            :disabled="isProcessing"
          />
        </section>

        <!-- Right Panel - Pipeline Status -->
        <section class="pipeline-section">
          <PipelineStatus
            :stage="currentStage"
            :progress="currentProgress"
            :message="currentMessage"
            :is-active="isProcessing"
          />
        </section>
      </div>

      <!-- Results Dashboard -->
      <transition name="fade">
        <ResultDashboard
          v-if="showResults"
          :result="detectionResult"
          :filename="uploadedFilename"
          @reset="resetDetection"
        />
      </transition>
    </main>

    <!-- Footer -->
    <footer class="footer">
      <p>EdgeAgent v1.0.0 | Powered by Qwen3.5-0.8B</p>
    </footer>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import axios from 'axios'
import FileUpload from './components/FileUpload.vue'
import PipelineStatus from './components/PipelineStatus.vue'
import ResultDashboard from './components/ResultDashboard.vue'

export default {
  name: 'App',
  components: {
    FileUpload,
    PipelineStatus,
    ResultDashboard
  },
  setup() {
    const isProcessing = ref(false)
    const currentTaskId = ref(null)
    const currentStage = ref('pending')
    const currentProgress = ref(0)
    const currentMessage = ref('')
    const detectionResult = ref(null)
    const uploadedFilename = ref('')

    const showResults = computed(() => detectionResult.value !== null)

    let pollInterval = null

    const handleFileSelected = async (file) => {
      if (isProcessing.value) return

      uploadedFilename.value = file.name
      isProcessing.value = true
      currentStage.value = 'pending'
      currentProgress.value = 0
      currentMessage.value = '正在上传文件...'
      detectionResult.value = null

      try {
        const formData = new FormData()
        formData.append('file', file)

        const response = await axios.post('/api/detect', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })

        currentTaskId.value = response.data.task_id
        startPolling()
      } catch (error) {
        console.error('Upload failed:', error)
        currentMessage.value = `上传失败: ${error.response?.data?.detail || error.message}`
        isProcessing.value = false
      }
    }

    const startPolling = () => {
      pollInterval = setInterval(async () => {
        try {
          const response = await axios.get(`/api/status/${currentTaskId.value}`)
          const { stage, progress, message, status } = response.data

          currentStage.value = stage
          currentProgress.value = progress
          currentMessage.value = message

          if (stage === 'completed' || stage === 'failed') {
            stopPolling()

            if (stage === 'completed') {
              await fetchResult()
            } else {
              currentMessage.value = '检测失败，请重试'
            }
            isProcessing.value = false
          }
        } catch (error) {
          console.error('Status poll failed:', error)
        }
      }, 500)
    }

    const stopPolling = () => {
      if (pollInterval) {
        clearInterval(pollInterval)
        pollInterval = null
      }
    }

    const fetchResult = async () => {
      try {
        const response = await axios.get(`/api/result/${currentTaskId.value}`)
        detectionResult.value = response.data
      } catch (error) {
        console.error('Fetch result failed:', error)
        currentMessage.value = '获取结果失败'
      }
    }

    const resetDetection = () => {
      isProcessing.value = false
      currentTaskId.value = null
      currentStage.value = 'pending'
      currentProgress.value = 0
      currentMessage.value = ''
      detectionResult.value = null
      uploadedFilename.value = ''
    }

    return {
      isProcessing,
      currentStage,
      currentProgress,
      currentMessage,
      detectionResult,
      uploadedFilename,
      showResults,
      handleFileSelected,
      resetDetection
    }
  }
}
</script>

<style>
/* Reset & Base Styles */
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

:root {
  /* Colors */
  --bg-primary: #0a0a0f;
  --bg-secondary: #111118;
  --bg-tertiary: #1a1a24;
  --bg-card: #15151f;
  --bg-hover: #1f1f2e;

  --text-primary: #f0f0f5;
  --text-secondary: #a0a0b0;
  --text-muted: #6b6b7b;

  --border-color: #2a2a3a;
  --border-light: #3a3a4a;

  --accent-primary: #6366f1;
  --accent-secondary: #8b5cf6;
  --accent-cyan: #22d3ee;
  --accent-green: #22c55e;
  --accent-yellow: #eab308;
  --accent-red: #ef4444;
  --accent-orange: #f97316;

  /* Gradients */
  --gradient-primary: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  --gradient-cyan: linear-gradient(135deg, #22d3ee 0%, #6366f1 100%);
  --gradient-success: linear-gradient(135deg, #22c55e 0%, #10b981 100%);
  --gradient-danger: linear-gradient(135deg, #ef4444 0%, #f97316 100%);

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.5);
  --shadow-glow: 0 0 30px rgba(99, 102, 241, 0.15);

  /* Border Radius */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-xl: 24px;

  /* Spacing */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;

  /* Typography */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
}

html {
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  font-family: var(--font-sans);
  background: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.6;
  min-height: 100vh;
}

#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  background-image:
    radial-gradient(ellipse at 20% 0%, rgba(99, 102, 241, 0.08) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 100%, rgba(139, 92, 246, 0.05) 0%, transparent 50%);
}

/* Header */
.header {
  background: rgba(17, 17, 24, 0.8);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space-md) var(--space-xl);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.logo-icon {
  width: 40px;
  height: 40px;
}

.logo-text h1 {
  font-size: 1.5rem;
  font-weight: 700;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.logo-text .subtitle {
  display: block;
  font-size: 0.75rem;
  color: var(--text-muted);
  letter-spacing: 0.5px;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: var(--radius-lg);
  font-size: 0.875rem;
  color: var(--accent-green);
}

.status-dot {
  width: 8px;
  height: 8px;
  background: var(--accent-green);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Main Content */
.main-content {
  flex: 1;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
  padding: var(--space-xl);
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-xl);
}

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

/* Sections */
.upload-section,
.pipeline-section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

/* Footer */
.footer {
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
  padding: var(--space-md) var(--space-xl);
  text-align: center;
  color: var(--text-muted);
  font-size: 0.875rem;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

/* Scrollbar */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--bg-secondary);
}

::-webkit-scrollbar-thumb {
  background: var(--border-light);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}
</style>
