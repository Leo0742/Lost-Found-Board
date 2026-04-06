import { Item } from '../../types/item'
import { ModerationSignal } from '../../api/items'
import { ModerationSignals } from './ModerationSignals'
import { useSettings } from '../../context/SettingsContext'

type QueueProps = {
  items: Item[]
  signals: Record<number, ModerationSignal>
  selectedIds?: number[]
  onToggleSelected?: (itemId: number) => void
  canDelete: boolean
  onDelete: (itemId: number) => void
  onIgnoreComplaint: (itemId: number) => void
}

export const ModerationQueueFeed = ({
  items,
  signals,
  selectedIds = [],
  onToggleSelected,
  canDelete,
  onDelete,
  onIgnoreComplaint,
}: QueueProps) => {
  const { t } = useSettings()

  return (
    <>
      {items.length === 0 ? <p className="subtle">{t('admin.queue.empty')}</p> : items.map((item) => (
      <article className="card stack" key={item.id}>
        {onToggleSelected ? (
          <label className="queue-select">
            <input type="checkbox" checked={selectedIds.includes(item.id)} onChange={() => onToggleSelected(item.id)} /> {t('admin.queue.select')} #{item.id}
          </label>
        ) : null}
        <strong>#{item.id} {item.title}</strong>
        <p className="subtle">{item.category} · {item.location} · @{item.owner_telegram_username || item.telegram_username || 'n/a'}</p>
        <ModerationSignals signal={signals[item.id]} />
        <div className="actions-row">
          <button className="button-neutral" onClick={() => onIgnoreComplaint(item.id)}>{t('admin.action.ignoreComplaint')}</button>
          {canDelete ? <button className="button-danger" onClick={() => onDelete(item.id)}>{t('admin.action.deletePost')}</button> : null}
        </div>
      </article>
      ))}
    </>
  )
}
