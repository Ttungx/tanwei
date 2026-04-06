import { buildConsoleViewModel } from '../lib/view-models'
import styles from '../App.module.css'

type TaskSummaryProps = {
  stateLabel: string
  stageLabel: string
  stageDetail: string
  metrics: ReturnType<typeof buildConsoleViewModel>['heroMetrics']
}

export function TaskSummary({ stateLabel, stageLabel, stageDetail, metrics }: TaskSummaryProps) {
  return (
    <section className={styles.panel}>
      <div className={styles.panelHeader}>
        <span className={styles.panelEyebrow}>Task Status</span>
        <h3>当前任务</h3>
      </div>

      <div className={styles.summaryLead}>
        <span className={styles.summaryBadge}>{stateLabel}</span>
        <strong>{stageLabel}</strong>
        <p>{stageDetail}</p>
      </div>

      <div className={styles.summaryMetrics}>
        {metrics.map((item) => (
          <article key={item.label} className={styles.metricTile}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>
    </section>
  )
}
