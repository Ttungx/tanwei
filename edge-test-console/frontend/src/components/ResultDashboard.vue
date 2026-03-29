<template>
  <div class="dashboard-container">
    <!-- Summary Cards -->
    <div class="summary-grid">
      <!-- Total Flows -->
      <div class="summary-card">
        <div class="card-icon flows">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 6h16M4 12h16M4 18h16"/>
          </svg>
        </div>
        <div class="card-content">
          <span class="card-value">{{ statistics.totalFlows }}</span>
          <span class="card-label">总流量数</span>
        </div>
      </div>

      <!-- Normal Flows -->
      <div class="summary-card">
        <div class="card-icon normal">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22,4 12,14.01 9,11.01"/>
          </svg>
        </div>
        <div class="card-content">
          <span class="card-value">{{ statistics.normalFlowsDropped }}</span>
          <span class="card-label">正常流量 (已丢弃)</span>
        </div>
      </div>

      <!-- Anomaly Flows -->
      <div class="summary-card anomaly">
        <div class="card-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
        </div>
        <div class="card-content">
          <span class="card-value">{{ statistics.anomalyFlowsDetected }}</span>
          <span class="card-label">异常流量</span>
        </div>
      </div>

      <!-- Filter Rate -->
      <div class="summary-card">
        <div class="card-icon filter">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="22,3 2,3 10,12.46 10,19 14,21 14,12.46 22,3"/>
          </svg>
        </div>
        <div class="card-content">
          <span class="card-value">{{ statistics.svmFilterRate }}</span>
          <span class="card-label">SVM 过滤率</span>
        </div>
      </div>
    </div>

    <!-- Bandwidth Reduction Chart -->
    <div class="chart-section">
      <div class="section-header">
        <h3>带宽压降指标</h3>
        <div class="highlight-badge" v-if="bandwidthReduction > 70">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
          </svg>
          模拟上行带宽占用降低 > 70%
        </div>
      </div>

      <div class="chart-container">
        <div class="chart-bars">
          <!-- Original Pcap Size -->
          <div class="bar-group">
            <div class="bar-label">
              <span>原始 Pcap 文件</span>
              <span class="size-value">{{ formatBytes(metrics.originalPcapSizeBytes) }}</span>
            </div>
            <div class="bar-wrapper">
              <div
                class="bar original"
                :style="{ width: '100%' }"
              >
                <span class="bar-value">{{ formatBytes(metrics.originalPcapSizeBytes) }}</span>
              </div>
            </div>
          </div>

          <!-- JSON Output Size -->
          <div class="bar-group">
            <div class="bar-label">
              <span>JSON 日志输出</span>
              <span class="size-value">{{ formatBytes(metrics.jsonOutputSizeBytes) }}</span>
            </div>
            <div class="bar-wrapper">
              <div
                class="bar compressed"
                :style="{ width: `${barWidth}%` }"
              >
                <span class="bar-value">{{ formatBytes(metrics.jsonOutputSizeBytes) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Reduction Indicator -->
        <div class="reduction-indicator">
          <div class="arrow-line">
            <svg viewBox="0 0 100 20" preserveAspectRatio="none">
              <line x1="0" y1="10" x2="85" y2="10" stroke="currentColor" stroke-width="2" stroke-dasharray="4,4"/>
              <polygon points="85,5 95,10 85,15" fill="currentColor"/>
            </svg>
          </div>
          <div class="reduction-value">
            <span class="value">{{ bandwidthReduction }}%</span>
            <span class="label">带宽节省</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Threat Table -->
    <div class="threats-section" v-if="threats.length > 0">
      <div class="section-header">
        <h3>检测到的威胁</h3>
        <span class="threat-count">{{ threats.length }} 个威胁</span>
      </div>

      <div class="threats-table">
        <div class="table-header">
          <div class="col-id">ID</div>
          <div class="col-five-tuple">五元组</div>
          <div class="col-label">分类标签</div>
          <div class="col-confidence">置信度</div>
          <div class="col-model">模型</div>
        </div>

        <div
          v-for="threat in threats"
          :key="threat.id"
          class="table-row"
        >
          <div class="col-id">
            <span class="threat-id">{{ threat.id }}</span>
          </div>
          <div class="col-five-tuple">
            <div class="five-tuple-info">
              <span class="protocol">{{ threat.five_tuple.protocol }}</span>
              <span class="ip-flow">
                {{ threat.five_tuple.src_ip }}:{{ threat.five_tuple.src_port }}
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M5 12h14M12 5l7 7-7 7"/>
                </svg>
                {{ threat.five_tuple.dst_ip }}:{{ threat.five_tuple.dst_port }}
              </span>
            </div>
          </div>
          <div class="col-label">
            <div class="label-tags">
              <span class="tag primary" :class="getLabelClass(threat.classification.primary_label)">
                {{ threat.classification.primary_label }}
              </span>
              <span v-if="threat.classification.secondary_label" class="tag secondary">
                {{ threat.classification.secondary_label }}
              </span>
            </div>
          </div>
          <div class="col-confidence">
            <div class="confidence-bar">
              <div
                class="confidence-fill"
                :style="{ width: `${threat.classification.confidence * 100}%` }"
              ></div>
              <span class="confidence-value">{{ (threat.classification.confidence * 100).toFixed(0) }}%</span>
            </div>
          </div>
          <div class="col-model">
            <span class="model-name">{{ threat.classification.model }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="actions-section">
      <button class="btn-secondary" @click="downloadResult">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="7,10 12,15 17,10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
        下载 JSON 结果
      </button>
      <button class="btn-primary" @click="$emit('reset')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M23 4v6h-6"/>
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
        </svg>
        开始新检测
      </button>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'ResultDashboard',
  props: {
    result: {
      type: Object,
      required: true
    },
    filename: {
      type: String,
      default: ''
    }
  },
  emits: ['reset'],
  setup(props) {
    const statistics = computed(() => {
      return props.result?.statistics || {
        total_flows: 0,
        normal_flows_dropped: 0,
        anomaly_flows_detected: 0,
        svm_filter_rate: '0%'
      }
    })

    const threats = computed(() => {
      return props.result?.threats || []
    })

    const metrics = computed(() => {
      return props.result?.metrics || {
        original_pcap_size_bytes: 0,
        json_output_size_bytes: 0,
        bandwidth_saved_percent: 0
      }
    })

    const bandwidthReduction = computed(() => {
      return metrics.value.bandwidth_saved_percent || 0
    })

    const barWidth = computed(() => {
      const original = metrics.value.original_pcap_size_bytes
      const compressed = metrics.value.json_output_size_bytes
      if (original === 0) return 0
      return Math.max(10, (compressed / original) * 100)
    })

    const formatBytes = (bytes) => {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    const getLabelClass = (label) => {
      const labelMap = {
        'Malware': 'malware',
        'Suspicious': 'suspicious',
        'Benign': 'benign',
        'Normal': 'benign'
      }
      return labelMap[label] || 'unknown'
    }

    const downloadResult = () => {
      const dataStr = JSON.stringify(props.result, null, 2)
      const blob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `detection-result-${props.result?.meta?.task_id || 'unknown'}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    }

    return {
      statistics,
      threats,
      metrics,
      bandwidthReduction,
      barWidth,
      formatBytes,
      getLabelClass,
      downloadResult
    }
  }
}
</script>

<style scoped>
.dashboard-container {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
}

/* Summary Grid */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
}

@media (max-width: 1024px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}

.summary-card {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  display: flex;
  align-items: center;
  gap: var(--space-md);
  transition: all 0.3s ease;
}

.summary-card:hover {
  border-color: var(--border-light);
  transform: translateY(-2px);
}

.summary-card.anomaly {
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.05);
}

.card-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.card-icon svg {
  width: 24px;
  height: 24px;
}

.card-icon.flows {
  background: var(--gradient-primary);
  color: white;
}

.card-icon.normal {
  background: var(--gradient-success);
  color: white;
}

.card-icon.filter {
  background: var(--gradient-cyan);
  color: white;
}

.summary-card.anomaly .card-icon {
  background: var(--gradient-danger);
  color: white;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.card-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.summary-card.anomaly .card-value {
  color: var(--accent-red);
}

.card-label {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* Chart Section */
.chart-section {
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-lg);
}

.section-header h3 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.highlight-badge {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs) var(--space-sm);
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.2) 0%, rgba(16, 185, 129, 0.2) 100%);
  border: 1px solid rgba(34, 197, 94, 0.4);
  border-radius: var(--radius-lg);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--accent-green);
  animation: glow 2s ease-in-out infinite;
}

@keyframes glow {
  0%, 100% { box-shadow: 0 0 5px rgba(34, 197, 94, 0.3); }
  50% { box-shadow: 0 0 15px rgba(34, 197, 94, 0.5); }
}

.highlight-badge svg {
  width: 14px;
  height: 14px;
}

.chart-container {
  display: flex;
  gap: var(--space-xl);
  align-items: stretch;
}

.chart-bars {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.bar-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.bar-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.bar-label span:first-child {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.size-value {
  font-size: 0.75rem;
  font-family: var(--font-mono);
  color: var(--text-muted);
}

.bar-wrapper {
  height: 40px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.bar {
  height: 100%;
  display: flex;
  align-items: center;
  padding: 0 var(--space-md);
  border-radius: var(--radius-sm);
  transition: width 1s ease;
  position: relative;
}

.bar.original {
  background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%);
}

.bar.compressed {
  background: linear-gradient(90deg, #22d3ee 0%, #6366f1 100%);
}

.bar-value {
  font-size: 0.75rem;
  font-weight: 600;
  color: white;
  font-family: var(--font-mono);
  white-space: nowrap;
}

/* Reduction Indicator */
.reduction-indicator {
  width: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
}

.arrow-line {
  width: 100%;
  height: 30px;
  color: var(--accent-green);
}

.arrow-line svg {
  width: 100%;
  height: 100%;
}

.reduction-value {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.reduction-value .value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--accent-green);
  font-family: var(--font-mono);
}

.reduction-value .label {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* Threats Table */
.threats-section {
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.threats-section .section-header {
  padding: var(--space-md) var(--space-lg);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.threat-count {
  font-size: 0.75rem;
  padding: var(--space-xs) var(--space-sm);
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--radius-lg);
  color: var(--accent-red);
}

.threats-table {
  overflow-x: auto;
}

.table-header,
.table-row {
  display: grid;
  grid-template-columns: 100px 1fr 180px 120px 120px;
  gap: var(--space-md);
  padding: var(--space-md) var(--space-lg);
  align-items: center;
}

.table-header {
  background: rgba(0, 0, 0, 0.2);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.table-row {
  border-bottom: 1px solid var(--border-color);
  transition: background 0.2s ease;
}

.table-row:last-child {
  border-bottom: none;
}

.table-row:hover {
  background: rgba(255, 255, 255, 0.02);
}

.threat-id {
  font-size: 0.75rem;
  font-family: var(--font-mono);
  color: var(--text-muted);
}

.five-tuple-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.protocol {
  display: inline-block;
  font-size: 0.625rem;
  font-weight: 600;
  padding: 2px 6px;
  background: var(--bg-secondary);
  border-radius: 3px;
  color: var(--accent-cyan);
  width: fit-content;
}

.ip-flow {
  font-size: 0.8125rem;
  font-family: var(--font-mono);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.ip-flow svg {
  width: 14px;
  height: 14px;
  color: var(--text-muted);
}

.label-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
}

.tag {
  font-size: 0.6875rem;
  font-weight: 500;
  padding: 3px 8px;
  border-radius: 4px;
}

.tag.primary {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-red);
}

.tag.primary.suspicious {
  background: rgba(249, 115, 22, 0.15);
  color: var(--accent-orange);
}

.tag.primary.benign {
  background: rgba(34, 197, 94, 0.15);
  color: var(--accent-green);
}

.tag.secondary {
  background: var(--bg-secondary);
  color: var(--text-muted);
}

.confidence-bar {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  position: relative;
  width: 100%;
  height: 24px;
  background: var(--bg-secondary);
  border-radius: 4px;
  overflow: hidden;
}

.confidence-fill {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  background: var(--gradient-success);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.confidence-value {
  position: relative;
  z-index: 1;
  margin-left: auto;
  padding-right: var(--space-sm);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.model-name {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

/* Actions */
.actions-section {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-md);
  padding-top: var(--space-md);
  border-top: 1px solid var(--border-color);
}

.btn-primary,
.btn-secondary {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-lg);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
}

.btn-primary {
  background: var(--gradient-primary);
  color: white;
}

.btn-primary:hover {
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
  transform: translateY(-1px);
}

.btn-secondary {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

.btn-secondary:hover {
  background: var(--bg-hover);
  border-color: var(--border-light);
}

.btn-primary svg,
.btn-secondary svg {
  width: 18px;
  height: 18px;
}

/* Responsive */
@media (max-width: 768px) {
  .chart-container {
    flex-direction: column;
  }

  .reduction-indicator {
    width: 100%;
    flex-direction: row;
    justify-content: center;
  }

  .table-header,
  .table-row {
    grid-template-columns: 1fr;
    gap: var(--space-sm);
  }

  .actions-section {
    flex-direction: column;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
    justify-content: center;
  }
}
</style>
