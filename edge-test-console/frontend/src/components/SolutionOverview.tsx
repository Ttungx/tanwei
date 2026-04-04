import styles from './SolutionOverview.module.css'
import { buildOverviewViewModel } from '../lib/view-models'

type SolutionOverviewProps = {
  viewModel: ReturnType<typeof buildOverviewViewModel>
}

export function SolutionOverview({ viewModel }: SolutionOverviewProps) {
  return (
    <section className={styles.section} aria-labelledby="solution-overview-title">
      <header className={styles.hero}>
        <div>
          <span className={styles.eyebrow}>SYSTEM NARRATIVE</span>
          <h2 id="solution-overview-title" className={styles.title}>方案概览</h2>
          <p className={styles.lead}>
            以边缘侧预筛为入口，把抓包样本转为可解释的威胁档案，并把量化结果直接映射到工作台。
          </p>
        </div>
        <p className={styles.pipelineLine}>
          Pcap -&gt; Flow Reconstruction -&gt; SVM Filtering -&gt; LLM Inference -&gt; Threat Archive
        </p>
      </header>

      <div className={styles.grid}>
        <article className={styles.card}>
          <h3>场景与价值</h3>
          <p>
            面向高吞吐、成本敏感的网络检测场景，先在边缘侧做快速筛选，再把异常候选交给更重的语义推理链路。
          </p>
        </article>

        <article className={styles.card}>
          <h3>检测链路</h3>
          <ul className={styles.pipelineList}>
            {viewModel.pipeline.map((item) => (
              <li key={item.label}>
                <strong>{item.label}</strong>
                <span>{item.detail}</span>
              </li>
            ))}
          </ul>
        </article>

        <article className={styles.card}>
          <h3>关键证据</h3>
          <div className={styles.metricGrid}>
            {viewModel.evidenceCards.map((item) => (
              <div key={item.label} className={styles.metricCard}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className={styles.card}>
          <h3>系统组成</h3>
          <div className={styles.metricGrid}>
            {viewModel.systemCards.map((item) => (
              <div key={item.label} className={styles.metricCard}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>
        </article>
      </div>
    </section>
  )
}
