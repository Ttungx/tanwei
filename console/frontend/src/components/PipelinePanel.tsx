import type { PipelineStage } from '../types/api'
import styles from './PipelinePanel.module.css'

type PipelinePanelProps = {
  stage: PipelineStage
  progress: number
  message: string
}

const STAGES: { id: PipelineStage; label: string; detail: string }[] = [
  { id: 'pending', label: '等待处理', detail: '任务进入队列，准备接管样本。' },
  { id: 'flow_reconstruction', label: '流重组', detail: '复原会话并构建后续分析上下文。' },
  { id: 'svm_filtering', label: 'SVM 初筛', detail: '快速丢弃正常流，控制推理开销。' },
  { id: 'llm_inference', label: 'LLM 推理', detail: '对可疑流进行语义分类与标签判定。' },
  { id: 'completed', label: '结果归档', detail: '生成异常档案与压降汇总。' },
  { id: 'failed', label: '流程中断', detail: '本次任务未能完成，需要重新提交样本。' },
]

export function PipelinePanel({ stage, progress, message }: PipelinePanelProps) {
  const activeStage = STAGES.find((item) => item.id === stage) ?? STAGES[0]
  const statusLabel = stage === 'failed' ? '任务失败' : stage === 'completed' ? '任务完成' : '处理中'

  return (
    <section className={styles.card}>
      <div className={styles.header}>
        <div>
          <span className={styles.eyebrow}>PIPELINE TRACE</span>
          <h3>{activeStage.label}</h3>
        </div>
        <div className={styles.headerMeta}>
          <span className={styles.status}>{statusLabel}</span>
          <strong>{progress}%</strong>
        </div>
      </div>

      <p className={styles.lead}>{message || activeStage.detail}</p>

      <div className={styles.list}>
        {STAGES.map((item) => {
          const active = item.id === stage
          return (
            <div key={item.id} className={`${styles.item} ${active ? styles.itemActive : ''}`}>
              <span className={styles.badge}>{item.label}</span>
              <p>{item.detail}</p>
            </div>
          )
        })}
      </div>

      <div className={styles.progressTrack}>
        <div className={styles.progressFill} style={{ width: `${progress}%` }} />
      </div>
    </section>
  )
}
