import { buildDemoSampleCards } from '../lib/view-models'
import type { DemoSample } from '../types/api'
import styles from './DemoSampleLibrary.module.css'

type DemoSampleLibraryProps = {
  samples: DemoSample[]
  selectedSampleId: string | null
  disabled: boolean
  isBusy: boolean
  isLoading: boolean
  error: string | null
  onSelect: (sampleId: string) => void
  onStart: (sampleId: string) => Promise<boolean>
}

export function DemoSampleLibrary({
  samples,
  selectedSampleId,
  disabled,
  isBusy,
  isLoading,
  error,
  onSelect,
  onStart,
}: DemoSampleLibraryProps) {
  const cards = buildDemoSampleCards(samples, selectedSampleId)

  return (
    <section className={styles.card}>
      <div className={styles.topline}>
        <span className={styles.tag}>演示样本</span>
        <span className={styles.tagMuted}>{isBusy ? '任务执行中' : '内置样本库'}</span>
      </div>

      <div className={styles.copy}>
        <h3>内置演示样本</h3>
        <p>直接选择平台预置流量样本，验证完整检测链路与状态回传。</p>
      </div>

      {isLoading && <p className={styles.status}>演示样本加载中...</p>}
      {error && <p className={styles.error}>{error}</p>}

      {!isLoading && cards.length === 0 && (
        <div className={styles.emptyState}>
          <strong>暂无可用演示样本</strong>
          <p>当前样本库为空，请稍后刷新或检查后端服务。</p>
        </div>
      )}

      {cards.length > 0 && (
        <div className={styles.list}>
          {cards.map((card) => (
            <button
              key={card.id}
              type="button"
              className={`${styles.sampleCard} ${card.selected ? styles.sampleCardSelected : ''}`}
              disabled={disabled}
              aria-pressed={card.selected}
              aria-label={`选择 ${card.title} 演示样本`}
              onClick={() => onSelect(card.id)}
            >
              <div className={styles.sampleCardHeader}>
                <strong>{card.title}</strong>
                <span>{card.meta}</span>
              </div>
              <span className={styles.filename}>{card.filename}</span>
            </button>
          ))}
        </div>
      )}

      <div className={styles.actions}>
        <button
          type="button"
          className={styles.primaryButton}
          disabled={disabled || !selectedSampleId}
          onClick={() => (selectedSampleId ? onStart(selectedSampleId) : Promise.resolve(false))}
        >
          启动演示检测
        </button>
      </div>
    </section>
  )
}
