import { buildOverviewViewModel } from '../lib/view-models'
import styles from '../App.module.css'
import type { PipelineStage } from '../types/api'

type WorkflowChainProps = {
  items: ReturnType<typeof buildOverviewViewModel>['pipeline']
  activeStage: PipelineStage
}

const STAGE_TO_ITEM_ID: Record<PipelineStage, string> = {
  pending: 'waiting',
  flow_reconstruction: 'flow_reconstruction',
  svm_filtering: 'svm_filtering',
  llm_inference: 'llm_inference',
  completed: 'archive',
  failed: 'failed',
}

const ITEM_IDS = ['waiting', 'flow_reconstruction', 'svm_filtering', 'llm_inference', 'archive'] as const

export function WorkflowChain({ items, activeStage }: WorkflowChainProps) {
  const currentId = STAGE_TO_ITEM_ID[activeStage]

  return (
    <section className={styles.panel} aria-label="workflow-panel" data-stage={activeStage}>
      <div className={styles.panelHeader}>
        <span className={styles.panelEyebrow}>Stage Filtering</span>
        <h3>检测链路</h3>
      </div>

      <div className={styles.chainList}>
        {items.map((item, index) => {
          const itemId = ITEM_IDS[index]
          const active = currentId === itemId
          const failed = activeStage === 'failed' && index === ITEM_IDS.length - 1

          return (
            <article
              key={item.label}
              className={`${styles.chainItem} ${active || failed ? styles.chainItemActive : ''}`}
              aria-label={
                failed
                  ? 'workflow-failed'
                  : itemId === 'waiting'
                    ? 'workflow-pending'
                    : `workflow-${itemId}`
              }
              aria-current={active ? 'step' : undefined}
              data-state={failed ? 'failed' : active ? 'active' : 'idle'}
            >
              <span className={styles.chainIndex}>{String(index + 1).padStart(2, '0')}</span>
              <div>
                <strong>{item.label}</strong>
                <p>{item.detail}</p>
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}
