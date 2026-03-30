import type { PipelineStage } from '../types/api'
import styles from './PipelineStatus.module.css'

interface PipelineStatusProps {
  stage: PipelineStage
  progress: number
  message: string
}

const STAGES: { id: PipelineStage; label: string; detail: string }[] = [
  { id: 'pending', label: '等待处理', detail: '任务进入队列，准备接管样本。' },
  { id: 'flow_reconstruction', label: '流重组', detail: '复原会话并构建后续分析上下文。' },
  { id: 'svm_filtering', label: 'SVM 初筛', detail: '快速丢弃正常流，控制推理开销。' },
  { id: 'llm_inference', label: 'LLM 推理', detail: '对可疑流进行语义分类与标签判定。' },
  { id: 'completed', label: '完成', detail: '生成异常档案与压降汇总。' },
]

export default function PipelineStatus({ stage, progress, message }: PipelineStatusProps) {
  const getStageStatus = (stageId: PipelineStage): 'pending' | 'active' | 'completed' | 'failed' => {
    if (stage === 'failed') {
      return stageId === STAGES[STAGES.length - 1].id ? 'failed' : 'pending'
    }

    const currentIndex = STAGES.findIndex(s => s.id === stage)
    const stageIndex = STAGES.findIndex(s => s.id === stageId)

    if (stageIndex < currentIndex) return 'completed'
    if (stageIndex === currentIndex) return stage === 'completed' ? 'completed' : 'active'
    return 'pending'
  }

  const activeStage = STAGES.find((item) => item.id === stage) ?? STAGES[0]

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <div className={styles.eyebrow}>Pipeline Trace</div>
          <h3 className={styles.title}>{activeStage.label}</h3>
        </div>
        <div className={styles.progressValue}>{progress}%</div>
      </div>

      <p className={styles.lead}>{message || activeStage.detail}</p>

      <div className={styles.pipeline}>
        {STAGES.map((s, index) => {
          const status = getStageStatus(s.id)
          return (
            <div key={s.id} className={styles.stage}>
              <div className={`${styles.stageIcon} ${styles[status]}`}>
                <span className={styles.stageNumber}>{String(index + 1).padStart(2, '0')}</span>
                {status === 'completed' && (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                )}
                {status === 'active' && (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                )}
                {status === 'failed' && (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                )}
                {status === 'pending' && (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="4" />
                  </svg>
                )}
              </div>
              <div className={styles.stageText}>
                <span className={`${styles.stageLabel} ${styles[status]}`}>{s.label}</span>
                <span className={styles.stageDetail}>{s.detail}</span>
              </div>
            </div>
          )
        })}
      </div>

      <div className={styles.progressContainer}>
        <div className={styles.progressBar}>
          <div className={styles.progressFill} style={{ width: `${progress}%` }} />
        </div>
        <div className={styles.progressText}>
          <span>执行进度</span>
          <span>边缘链路已推进 {progress}%</span>
        </div>
      </div>
    </div>
  )
}
