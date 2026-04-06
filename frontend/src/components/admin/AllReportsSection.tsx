import { ModerationSignal } from '../../api/items'
import { Item } from '../../types/item'
import { EmptyState } from '../ui'
import { ModerationSignals } from './ModerationSignals'
import { useSettings } from '../../context/SettingsContext'

type Props = {
  items: Item[]
  signals: Record<number, ModerationSignal>
  role: 'admin' | 'moderator' | null
  selectedIds: number[]
  onToggleSelected: (itemId: number) => void
  onSelectAllVisible: () => void
  onClearSelection: () => void
  onBulkIgnoreComplaints: () => void
  onBulkDelete: () => void
  onIgnoreComplaint: (itemId: number) => void
  onDelete: (itemId: number) => void
}

export const AllReportsSection = ({
  items,
  signals,
  role,
  selectedIds,
  onToggleSelected,
  onSelectAllVisible,
  onClearSelection,
  onBulkIgnoreComplaints,
  onBulkDelete,
  onIgnoreComplaint,
  onDelete,
}: Props) => {
  const { t } = useSettings()

  if (items.length === 0) {
    return <EmptyState title={t('admin.reports.emptyTitle')} subtitle={t('admin.reports.emptySubtitle')} />
  }

  return (
    <div className="stack">
      <div className="actions-row">
        <button className="button-neutral" onClick={onSelectAllVisible}>{t('admin.selectAll')}</button>
        <button className="button-neutral" onClick={onClearSelection}>{t('admin.clearSelection')}</button>
        <span className="subtle">{t('admin.selectedCount', { count: selectedIds.length })}</span>
      </div>
      {selectedIds.length > 0 ? (
        <div className="actions-row bulk-strip">
          <button className="button-neutral" onClick={onBulkIgnoreComplaints}>{t('admin.action.ignoreComplaintSelected')}</button>
          {role === 'admin' ? <button className="button-danger" onClick={onBulkDelete}>{t('admin.action.deletePostSelected')}</button> : null}
        </div>
      ) : null}
      <div className="grid">
        {items.map((item) => (
          <article key={item.id} className="card stack">
            <label><input type="checkbox" checked={selectedIds.includes(item.id)} onChange={() => onToggleSelected(item.id)} /> {t('admin.queue.select')} #{item.id}</label>
            <h3>#{item.id} {item.title}</h3>
            <p className="subtle">{item.category} · {item.location} · @{item.owner_telegram_username || item.telegram_username || 'n/a'}</p>
            <ModerationSignals signal={signals[item.id]} />
            <div className="status-row">
              <span className={`badge ${item.status}`}>{item.status === 'lost' ? t('board.status.lost') : t('board.status.found')}</span>
              <span className={`badge ${item.lifecycle}`}>{t(`item.lifecycle.${item.lifecycle}`)}</span>
              <span className={`badge ${item.moderation_status}`}>{t(`item.moderation.${item.moderation_status}`)}</span>
              {signals[item.id]?.suspicion_markers?.length ? <span className="badge flagged">{t('admin.signals.highRisk')}</span> : null}
            </div>
            <div className="actions-row">
              {item.moderation_status === 'flagged' ? (
                <button className="button-neutral" onClick={() => onIgnoreComplaint(item.id)}>{t('admin.action.ignoreComplaint')}</button>
              ) : null}
              {role === 'admin' ? (
                <>
                  <button className="button-danger" onClick={() => onDelete(item.id)}>{t('admin.action.deletePost')}</button>
                </>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
