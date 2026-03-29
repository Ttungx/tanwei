<template>
  <div class="pipeline-container">
    <!-- Section Header -->
    <div class="section-header">
      <div class="section-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
        </svg>
      </div>
      <div>
        <h2>处理流水线</h2>
        <p>{{ isActive ? '正在处理...' : '等待上传' }}</p>
      </div>
    </div>

    <!-- Progress Bar -->
    <div class="progress-section">
      <div class="progress-header">
        <span class="progress-label">总体进度</span>
        <span class="progress-value">{{ progress }}%</span>
      </div>
      <div class="progress-bar">
        <div
          class="progress-fill"
          :style="{ width: `${progress}%` }"
          :class="progressClass"
        ></div>
      </div>
    </div>

    <!-- Pipeline Stages -->
    <div class="stages-container">
      <div
        v-for="(stage, index) in stages"
        :key="stage.id"
        class="stage-item"
        :class="getStageClass(stage.id)"
      >
        <!-- Connector Line -->
        <div v-if="index > 0" class="connector-line">
          <div class="connector-fill" :class="{ 'filled': isStageCompleted(stages[index - 1].id) }"></div>
        </div>

        <!-- Stage Node -->
        <div class="stage-node">
          <div class="stage-icon">
            <component :is="stage.icon" />
          </div>
          <div class="stage-pulse" v-if="currentStageId === stage.id && isActive"></div>
        </div>

        <!-- Stage Info -->
        <div class="stage-info">
          <span class="stage-name">{{ stage.name }}</span>
          <span class="stage-desc">{{ stage.description }}</span>
        </div>

        <!-- Stage Status -->
        <div class="stage-status">
          <svg v-if="isStageCompleted(stage.id)" viewBox="0 0 24 24" class="status-icon completed">
            <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
          </svg>
          <div v-else-if="currentStageId === stage.id && isActive" class="spinner"></div>
          <div v-else class="status-dot pending"></div>
        </div>
      </div>
    </div>

    <!-- Current Message -->
    <transition name="fade">
      <div v-if="message && isActive" class="current-message">
        <div class="message-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 16v-4M12 8h.01"/>
          </svg>
        </div>
        <span>{{ message }}</span>
      </div>
    </transition>
  </div>
</template>

<script>
import { computed, h } from 'vue'

// Icon components
const FlowIcon = () => h('svg', {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  'stroke-width': '2'
}, [
  h('path', { d: 'M4 6h16M4 12h16M4 18h16' })
])

const FilterIcon = () => h('svg', {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  'stroke-width': '2'
}, [
  h('polygon', { points: '22,3 2,3 10,12.46 10,19 14,21 14,12.46 22,3' })
])

const BrainIcon = () => h('svg', {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  'stroke-width': '2'
}, [
  h('path', { d: 'M12 2a9 9 0 0 1 9 9v7a2 2 0 0 1-2 2h-2v-4h3v-5a8 8 0 0 0-16 0v5h3v4H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 9-9z' }),
  h('path', { d: 'M9 17v4M15 17v4' })
])

const CheckCircleIcon = () => h('svg', {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  'stroke-width': '2'
}, [
  h('path', { d: 'M22 11.08V12a10 10 0 1 1-5.93-9.14' }),
  h('polyline', { points: '22,4 12,14.01 9,11.01' })
])

export default {
  name: 'PipelineStatus',
  props: {
    stage: {
      type: String,
      default: 'pending'
    },
    progress: {
      type: Number,
      default: 0
    },
    message: {
      type: String,
      default: ''
    },
    isActive: {
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const stages = [
      {
        id: 'flow_reconstruction',
        name: '流重组',
        description: '提取五元组、重组双向会话流',
        icon: FlowIcon
      },
      {
        id: 'svm_filtering',
        name: 'SVM 初筛',
        description: '微秒级过滤正常流量',
        icon: FilterIcon
      },
      {
        id: 'llm_inference',
        name: 'LLM 推理',
        description: '大模型 Token 定性分析',
        icon: BrainIcon
      },
      {
        id: 'completed',
        name: '检测完成',
        description: '生成 JSON 结构化日志',
        icon: CheckCircleIcon
      }
    ]

    const stageOrder = ['pending', 'flow_reconstruction', 'svm_filtering', 'llm_inference', 'completed', 'failed']

    const currentStageId = computed(() => {
      return stageOrder.includes(props.stage) ? props.stage : 'pending'
    })

    const progressClass = computed(() => {
      if (props.stage === 'completed') return 'success'
      if (props.stage === 'failed') return 'error'
      if (props.isActive) return 'processing'
      return ''
    })

    const getStageIndex = (stageId) => {
      return stageOrder.indexOf(stageId)
    }

    const isStageCompleted = (stageId) => {
      const currentIndex = getStageIndex(currentStageId.value)
      const stageIndex = getStageIndex(stageId)
      return stageIndex < currentIndex || currentStageId.value === 'completed'
    }

    const getStageClass = (stageId) => {
      if (currentStageId.value === 'failed') return 'failed'
      if (isStageCompleted(stageId)) return 'completed'
      if (currentStageId.value === stageId && props.isActive) return 'active'
      return ''
    }

    return {
      stages,
      currentStageId,
      progressClass,
      isStageCompleted,
      getStageClass
    }
  }
}
</script>

<style scoped>
.pipeline-container {
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
  background: var(--gradient-cyan);
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

/* Progress Bar */
.progress-section {
  background: var(--bg-tertiary);
  padding: var(--space-md);
  border-radius: var(--radius-md);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-sm);
}

.progress-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.progress-value {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.progress-bar {
  height: 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--gradient-primary);
  border-radius: 4px;
  transition: width 0.5s ease, background 0.3s ease;
  position: relative;
}

.progress-fill.processing {
  background: var(--gradient-cyan);
  animation: shimmer 2s ease-in-out infinite;
}

.progress-fill.success {
  background: var(--gradient-success);
}

.progress-fill.error {
  background: var(--gradient-danger);
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* Stages */
.stages-container {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.stage-item {
  display: grid;
  grid-template-columns: auto 40px 1fr auto;
  gap: var(--space-md);
  align-items: center;
  padding: var(--space-md) 0;
  position: relative;
}

.stage-item:first-child {
  padding-top: 0;
}

/* Connector Line */
.connector-line {
  position: absolute;
  left: calc(var(--space-md) + 19px);
  top: 0;
  width: 2px;
  height: var(--space-md);
  background: var(--border-color);
}

.connector-fill {
  width: 100%;
  height: 0%;
  background: var(--gradient-success);
  transition: height 0.5s ease;
}

.connector-fill.filled {
  height: 100%;
}

/* Stage Node */
.stage-node {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border: 2px solid var(--border-color);
  border-radius: 50%;
  position: relative;
  z-index: 1;
  transition: all 0.3s ease;
}

.stage-item.completed .stage-node {
  background: var(--gradient-success);
  border-color: transparent;
  color: white;
}

.stage-item.active .stage-node {
  border-color: var(--accent-cyan);
  background: rgba(34, 211, 238, 0.1);
  color: var(--accent-cyan);
}

.stage-item.failed .stage-node {
  border-color: var(--accent-red);
  background: rgba(239, 68, 68, 0.1);
  color: var(--accent-red);
}

.stage-icon {
  width: 20px;
  height: 20px;
}

.stage-pulse {
  position: absolute;
  inset: -4px;
  border: 2px solid var(--accent-cyan);
  border-radius: 50%;
  animation: pulse-ring 1.5s ease-out infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(1.4); opacity: 0; }
}

/* Stage Info */
.stage-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.stage-name {
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--text-primary);
}

.stage-item.completed .stage-name {
  color: var(--accent-green);
}

.stage-item.active .stage-name {
  color: var(--accent-cyan);
}

.stage-desc {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* Stage Status */
.stage-status {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
}

.status-icon.completed {
  width: 24px;
  height: 24px;
  color: var(--accent-green);
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--accent-cyan);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.pending {
  background: var(--border-light);
}

/* Current Message */
.current-message {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-md);
  background: rgba(34, 211, 238, 0.1);
  border: 1px solid rgba(34, 211, 238, 0.3);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  color: var(--accent-cyan);
}

.message-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.message-icon svg {
  width: 100%;
  height: 100%;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
